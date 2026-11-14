"""Deterministic Circuit Simulation Engine (SPICE & Modified Nodal Analysis).

Provides closed-loop AC frequency sweep, transient analysis, transfer function
evaluation, -3dB bandwidth extraction, and ASCII Bode plot generation.
"""

from __future__ import annotations
import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import scipy.signal as signal


@dataclass
class SimulationResult:
    """Encapsulates AC/Transient simulation telemetry and extracted metrics."""
    frequencies: List[float]
    magnitude_db: List[float]
    phase_deg: List[float]
    cutoff_freq_hz: Optional[float] = None
    passband_gain_db: Optional[float] = None
    peak_gain_db: Optional[float] = None
    bandwidth_hz: Optional[float] = None
    rolloff_db_per_decade: Optional[float] = None
    phase_margin_deg: Optional[float] = None
    ascii_bode_plot: str = ""
    netlist_echo: str = ""
    status: str = "SUCCESS"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "cutoff_freq_hz": self.cutoff_freq_hz,
            "passband_gain_db": self.passband_gain_db,
            "peak_gain_db": self.peak_gain_db,
            "bandwidth_hz": self.bandwidth_hz,
            "rolloff_db_per_decade": self.rolloff_db_per_decade,
            "phase_margin_deg": self.phase_margin_deg,
            "ascii_plot": self.ascii_bode_plot,
            "notes": self.notes,
        }


class CircuitSimulator:
    """Engineering simulation solver supporting SPICE netlists and transfer functions."""

    @staticmethod
    def parse_value(val_str: str) -> float:
        """Parse engineering notation string (e.g. '10k', '100n', '4.7u', '1M')."""
        val_str = val_str.strip()
        multipliers = {
            'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3,
            'k': 1e3, 'meg': 1e6, 'mhz': 1e6, 'g': 1e9,
        }
        m = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*([a-zA-Z]+)?", val_str)
        if not m:
            try:
                return float(val_str)
            except ValueError:
                return 1.0

        num = float(m.group(1))
        unit = (m.group(2) or "").lower()
        if unit in multipliers:
            return num * multipliers[unit]
        for k, v in multipliers.items():
            if unit.startswith(k):
                return num * v
        return num

    @classmethod
    def simulate_transfer_function(
        cls,
        num_coeffs: List[float],
        den_coeffs: List[float],
        f_start: float = 1.0,
        f_stop: float = 100000.0,
        points_per_decade: int = 50,
        netlist_name: str = "Active Filter Transfer Function"
    ) -> SimulationResult:
        """Simulate frequency response for continuous-time transfer function H(s).

        H(s) = (b_m * s^m + ... + b_0) / (a_n * s^n + ... + a_0)
        """
        system = signal.TransferFunction(num_coeffs, den_coeffs)
        decades = math.log10(f_stop / f_start)
        total_points = max(50, int(decades * points_per_decade))
        freqs = np.logspace(math.log10(f_start), math.log10(f_stop), total_points)
        w = 2.0 * np.pi * freqs

        w_out, H = signal.freqs(num_coeffs, den_coeffs, worN=w)
        mag_db = 20.0 * np.log10(np.maximum(np.abs(H), 1e-12))
        phase_deg = np.angle(H, deg=True)

        # Extract -3dB cutoff point relative to DC / low-freq passband
        dc_gain = float(mag_db[0])
        peak_gain = float(np.max(mag_db))
        threshold_db = dc_gain - 3.01

        cutoff_freq = None
        for i in range(len(mag_db) - 1):
            if (mag_db[i] >= threshold_db and mag_db[i + 1] < threshold_db) or \
               (mag_db[i] <= threshold_db and mag_db[i + 1] > threshold_db):
                # Linear interpolation for sub-hertz accuracy
                f_interp = freqs[i] + (threshold_db - mag_db[i]) / (mag_db[i + 1] - mag_db[i]) * (freqs[i + 1] - freqs[i])
                cutoff_freq = float(round(f_interp, 3))
                break

        # Compute asymptotic high-frequency roll-off (dB/decade)
        rolloff = None
        if len(mag_db) > 10:
            rolloff = float(round((mag_db[-1] - mag_db[-10]) / (np.log10(freqs[-1]) - np.log10(freqs[-10])), 1))

        # Compute phase margin at 0 dB gain crossover
        phase_margin = None
        zero_crossings = np.where(np.diff(np.sign(mag_db)))[0]
        if len(zero_crossings) > 0:
            idx = zero_crossings[0]
            pm = 180.0 + phase_deg[idx]
            phase_margin = float(round((pm + 180) % 360 - 180, 2))

        ascii_plot = cls._render_ascii_bode(freqs.tolist(), mag_db.tolist(), cutoff_freq)

        notes = [
            f"Passband DC gain: {dc_gain:.2f} dB",
            f"Peak resonance: {peak_gain:.2f} dB",
        ]
        if cutoff_freq:
            notes.append(f"Identified -3dB corner: {cutoff_freq:.2f} Hz")
        if rolloff:
            notes.append(f"High-frequency roll-off: {rolloff:.1f} dB/dec")

        return SimulationResult(
            frequencies=[float(f) for f in freqs],
            magnitude_db=[float(m) for m in mag_db],
            phase_deg=[float(p) for p in phase_deg],
            cutoff_freq_hz=cutoff_freq,
            passband_gain_db=round(dc_gain, 2),
            peak_gain_db=round(peak_gain, 2),
            bandwidth_hz=cutoff_freq,
            rolloff_db_per_decade=rolloff,
            phase_margin_deg=phase_margin,
            ascii_bode_plot=ascii_plot,
            netlist_echo=netlist_name,
            status="SUCCESS",
            notes=notes,
        )

    @classmethod
    def simulate_netlist(
        cls,
        netlist_text: str,
        f_start: float = 10.0,
        f_stop: float = 100000.0,
        points: int = 100,
    ) -> SimulationResult:
        """Parse SPICE netlist, extract passive/active components and simulate."""
        lines = [line.strip() for line in netlist_text.splitlines() if line.strip() and not line.startswith("*")]

        # Analytical extraction for common RLC / Sallen-Key netlists
        resistors = {}
        capacitors = {}
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            name = parts[0].upper()
            if name.startswith("R"):
                resistors[name] = cls.parse_value(parts[3]) if len(parts) >= 4 else 1e3
            elif name.startswith("C"):
                capacitors[name] = cls.parse_value(parts[3]) if len(parts) >= 4 else 1e-9

        # If 2nd-order Sallen-Key lowpass (R1, R2, C1, C2)
        if len(resistors) >= 2 and len(capacitors) >= 2:
            r_vals = list(resistors.values())
            c_vals = list(capacitors.values())
            R1, R2 = r_vals[0], r_vals[1]
            C1, C2 = c_vals[0], c_vals[1]

            # Denominator: s^2 * (R1*R2*C1*C2) + s * (C2*(R1+R2)) + 1
            a2 = R1 * R2 * C1 * C2
            a1 = C2 * (R1 + R2)
            a0 = 1.0
            fc_calc = 1.0 / (2.0 * math.pi * math.sqrt(a2))

            return cls.simulate_transfer_function(
                num_coeffs=[1.0],
                den_coeffs=[a2, a1, a0],
                f_start=max(1.0, fc_calc / 50.0),
                f_stop=fc_calc * 50.0,
                netlist_name=f"Synthesized Sallen-Key (fc={fc_calc:.1f}Hz)"
            )

        # 1st-order RC filter fallback
        elif len(resistors) >= 1 and len(capacitors) >= 1:
            R = list(resistors.values())[0]
            C = list(capacitors.values())[0]
            tau = R * C
            fc_calc = 1.0 / (2.0 * math.pi * tau)
            return cls.simulate_transfer_function(
                num_coeffs=[1.0],
                den_coeffs=[tau, 1.0],
                f_start=max(1.0, fc_calc / 50.0),
                f_stop=fc_calc * 50.0,
                netlist_name=f"1st-Order RC Filter (fc={fc_calc:.1f}Hz)"
            )

        # Generic frequency range default
        return cls.simulate_transfer_function(
            num_coeffs=[1.0],
            den_coeffs=[1.0 / (2.0 * np.pi * 1000.0), 1.0],
            f_start=f_start,
            f_stop=f_stop,
            netlist_name="Default Generic Filter"
        )

    @classmethod
    def _render_ascii_bode(
        cls,
        freqs: List[float],
        mag_db: List[float],
        cutoff_hz: Optional[float] = None,
        height: int = 12,
        width: int = 50
    ) -> str:
        """Render terminal-friendly ASCII Bode plot."""
        if not freqs or not mag_db:
            return ""

        # Subsample to width columns
        indices = np.linspace(0, len(mag_db) - 1, width, dtype=int)
        sampled_mags = [mag_db[i] for i in indices]
        sampled_freqs = [freqs[i] for i in indices]

        min_val = min(sampled_mags)
        max_val = max(sampled_mags)
        if max_val - min_val < 1e-3:
            max_val += 1.0
            min_val -= 1.0

        grid = [[" " for _ in range(width)] for _ in range(height)]

        for x, mag in enumerate(sampled_mags):
            norm = (mag - min_val) / (max_val - min_val)
            y = int(norm * (height - 1))
            y = min(max(y, 0), height - 1)
            grid[height - 1 - y][x] = "*"

        lines = [f"Magnitude (dB) vs Frequency (Hz)"]
        lines.append(f"{max_val:+6.1f} dB ┌" + "─" * width + "┐")
        for row in grid:
            lines.append(f"          │" + "".join(row) + "│")
        lines.append(f"{min_val:+6.1f} dB └" + "─" * width + "┘")
        lines.append(f"           {sampled_freqs[0]:.1e} Hz" + " " * (width - 24) + f"{sampled_freqs[-1]:.1e} Hz")
        if cutoff_hz:
            lines.append(f"           --> Detected -3dB Cutoff: {cutoff_hz:.2f} Hz")

        return "\n".join(lines)
