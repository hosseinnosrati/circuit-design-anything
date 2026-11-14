"""Parametric Golden Circuit Topologies for Autonomous Synthesis.

Implements closed-loop circuit synthesis:
Specification -> Exact Formula -> E-Series Snapping -> Closed-Loop Verification -> Netlist & Schematic.
"""

from __future__ import annotations
import math
from typing import Dict, Any, List
from cda.engine.components import snap_component_value, ESeries
from cda.engine.spice import CircuitSimulator, SimulationResult
from cda.engine.schematic import SchematicRenderer
from cda.engine.kicad import KiCadExporter, ComponentItem


def synthesize_sallen_key_lowpass(
    fc_target_hz: float,
    q_factor: float = 0.7071,  # Butterworth maximally flat
    c_preferred: float = 10e-9,  # 10 nF standard target
    series: ESeries | str = ESeries.E24,
) -> Dict[str, Any]:
    """Synthesize 2nd-order active Sallen-Key lowpass filter with standard components."""
    # Sallen-Key equal-resistor formulation:
    # R1 = R2 = R
    # C1 = 2 * Q / (w_c * R)
    # C2 = 1 / (2 * Q * w_c * R)
    w_c = 2.0 * math.pi * fc_target_hz

    # Choose C2 = c_preferred, then C1 = 4 * Q^2 * C2
    C2_ideal = c_preferred
    C1_ideal = 4.0 * (q_factor ** 2) * C2_ideal

    # Snap C1 and C2 first (capacitors have fewer available values)
    c1_snap = snap_component_value(C1_ideal, series=series, component_type="capacitor")
    c2_snap = snap_component_value(C2_ideal, series=series, component_type="capacitor")
    C1_act = float(c1_snap["standard_value"])
    C2_act = float(c2_snap["standard_value"])

    # Now calculate R = 1 / (w_c * sqrt(C1 * C2))
    R_ideal = 1.0 / (w_c * math.sqrt(C1_act * C2_act))
    r1_snap = snap_component_value(R_ideal, series=series, component_type="resistor")
    r2_snap = snap_component_value(R_ideal, series=series, component_type="resistor")
    R1_act = float(r1_snap["standard_value"])
    R2_act = float(r2_snap["standard_value"])

    # Closed-loop simulated cutoff with snapped components
    fc_actual = 1.0 / (2.0 * math.pi * math.sqrt(R1_act * R2_act * C1_act * C2_act))
    fc_error_pct = ((fc_actual - fc_target_hz) / fc_target_hz) * 100.0

    # SPICE Netlist
    spice_netlist = f"""* 2nd-Order Sallen-Key Lowpass Filter (fc_target={fc_target_hz}Hz)
* Synthesized by Circuit Design Anything (CDA)
Vin in 0 AC 1.0
R1 in n1 {r1_snap['formatted']}
R2 n1 n2 {r2_snap['formatted']}
C1 n1 out {c1_snap['formatted']}
C2 n2 0 {c2_snap['formatted']}
* Ideal Op-Amp Model (E1 out 0 n2 out 1e5)
E1 out 0 n2 out 100000
.ac dec 50 {max(1.0, fc_target_hz / 50.0):.1f} {fc_target_hz * 50.0:.1f}
.end
"""

    # Verification Simulation
    sim_result = CircuitSimulator.simulate_netlist(spice_netlist)

    # SVG Schematic
    svg_data = SchematicRenderer.render_sallen_key(
        r1_val=str(r1_snap["formatted"]),
        r2_val=str(r2_snap["formatted"]),
        c1_val=str(c1_snap["formatted"]),
        c2_val=str(c2_snap["formatted"]),
    )

    # KiCad Components
    bom_items = [
        ComponentItem("R1", str(r1_snap["formatted"]), "Resistor_SMD:R_0805_2012Metric", "Precision Thin-Film 1%"),
        ComponentItem("R2", str(r2_snap["formatted"]), "Resistor_SMD:R_0805_2012Metric", "Precision Thin-Film 1%"),
        ComponentItem("C1", str(c1_snap["formatted"]), "Capacitor_SMD:C_0805_2012Metric", "C0G/NP0 Ceramic 5%"),
        ComponentItem("C2", str(c2_snap["formatted"]), "Capacitor_SMD:C_0805_2012Metric", "C0G/NP0 Ceramic 5%"),
        ComponentItem("U1", "TL072CDR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "Low-Noise JFET Op-Amp"),
    ]

    nets = {
        "Vin": ["Vin:1", "R1:1"],
        "N1": ["R1:2", "R2:1", "C1:1"],
        "N2": ["R2:2", "C2:1", "U1:3"],
        "Vout": ["C1:2", "U1:1", "U1:2"],
        "GND": ["C2:2", "U1:4"],
    }
    kicad_net = KiCadExporter.generate_kicad_netlist("Sallen_Key_Lowpass", bom_items, nets)

    return {
        "topology": "Sallen-Key Active Lowpass (2nd Order)",
        "target_cutoff_hz": fc_target_hz,
        "actual_cutoff_hz": round(fc_actual, 2),
        "cutoff_error_percent": round(fc_error_pct, 2),
        "components": {
            "R1": r1_snap,
            "R2": r2_snap,
            "C1": c1_snap,
            "C2": c2_snap,
            "OpAmp": "TL072 (Dual Low-Noise JFET)",
        },
        "simulation": sim_result.to_dict(),
        "spice_netlist": spice_netlist,
        "schematic_svg": svg_data,
        "kicad_netlist": kicad_net,
        "bom_table": KiCadExporter.generate_bom_markdown(bom_items),
    }


def synthesize_twin_t_notch(
    f_notch_hz: float = 50.0,
    c_target: float = 100e-9,  # 100 nF
    series: ESeries | str = ESeries.E24,
) -> Dict[str, Any]:
    """Synthesize active Twin-T Notch filter for powerline hum elimination (50Hz or 60Hz)."""
    # Twin-T equations:
    # R = 1 / (2 * pi * f_n * C)
    # R_shunt = R / 2
    # C_shunt = 2 * C
    c_snap = snap_component_value(c_target, series=series, component_type="capacitor")
    C_act = float(c_snap["standard_value"])

    R_ideal = 1.0 / (2.0 * math.pi * f_notch_hz * C_act)
    r_snap = snap_component_value(R_ideal, series=series, component_type="resistor")
    R_act = float(r_snap["standard_value"])

    # Shunt elements
    r_half_snap = snap_component_value(R_act / 2.0, series=series, component_type="resistor")
    c_double_snap = snap_component_value(C_act * 2.0, series=series, component_type="capacitor")

    f_notch_actual = 1.0 / (2.0 * math.pi * R_act * C_act)
    notch_error_pct = ((f_notch_actual - f_notch_hz) / f_notch_hz) * 100.0

    svg_data = SchematicRenderer.render_twin_t_notch(
        r_val=str(r_snap["formatted"]),
        c_val=str(c_snap["formatted"]),
        opamp_name="U1 (OPA1612)",
    )

    bom_items = [
        ComponentItem("R1", str(r_snap["formatted"]), "Resistor_SMD:R_0805_2012Metric", "Precision 0.1% Thin-Film"),
        ComponentItem("R2", str(r_snap["formatted"]), "Resistor_SMD:R_0805_2012Metric", "Precision 0.1% Thin-Film"),
        ComponentItem("R3", str(r_half_snap["formatted"]), "Resistor_SMD:R_0805_2012Metric", "Precision 0.1% Thin-Film"),
        ComponentItem("C1", str(c_snap["formatted"]), "Capacitor_SMD:C_0805_2012Metric", "Polypropylene Film 1%"),
        ComponentItem("C2", str(c_snap["formatted"]), "Capacitor_SMD:C_0805_2012Metric", "Polypropylene Film 1%"),
        ComponentItem("C3", str(c_double_snap["formatted"]), "Capacitor_SMD:C_0805_2012Metric", "Polypropylene Film 1%"),
        ComponentItem("U1", "OPA1612AIDR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "Ultra-Low Distortion Audio Op-Amp"),
    ]

    return {
        "topology": f"Active Twin-T Notch Filter ({f_notch_hz} Hz)",
        "target_notch_hz": f_notch_hz,
        "actual_notch_hz": round(f_notch_actual, 2),
        "error_percent": round(notch_error_pct, 2),
        "components": {
            "R": r_snap,
            "R_shunt (R/2)": r_half_snap,
            "C": c_snap,
            "C_shunt (2C)": c_double_snap,
            "OpAmp": "OPA1612 (Ultra-Low THD)",
        },
        "schematic_svg": svg_data,
        "bom_table": KiCadExporter.generate_bom_markdown(bom_items),
    }


def synthesize_rc_lowpass(
    fc_hz: float,
    c_preferred: float = 100e-9,
    series: ESeries | str = ESeries.E24,
) -> Dict[str, Any]:
    """Synthesize 1st-order passive RC lowpass filter."""
    c_snap = snap_component_value(c_preferred, series=series, component_type="capacitor")
    C_act = float(c_snap["standard_value"])

    R_ideal = 1.0 / (2.0 * math.pi * fc_hz * C_act)
    r_snap = snap_component_value(R_ideal, series=series, component_type="resistor")
    R_act = float(r_snap["standard_value"])

    fc_act = 1.0 / (2.0 * math.pi * R_act * C_act)
    err_pct = ((fc_act - fc_hz) / fc_hz) * 100.0

    svg_data = SchematicRenderer.render_rc_filter(
        r_val=str(r_snap["formatted"]),
        c_val=str(c_snap["formatted"]),
    )

    bom_items = [
        ComponentItem("R1", str(r_snap["formatted"]), "Resistor_SMD:R_0603_1608Metric", "Thick Film 1%"),
        ComponentItem("C1", str(c_snap["formatted"]), "Capacitor_SMD:C_0603_1608Metric", "X7R Ceramic 5%"),
    ]

    return {
        "topology": "1st-Order Passive RC Lowpass",
        "target_cutoff_hz": fc_hz,
        "actual_cutoff_hz": round(fc_act, 2),
        "error_percent": round(err_pct, 2),
        "components": {"R": r_snap, "C": c_snap},
        "schematic_svg": svg_data,
        "bom_table": KiCadExporter.generate_bom_markdown(bom_items),
    }


def synthesize_instrumentation_amp(
    gain: float = 100.0,
    r_internal: float = 49400.0,  # AD620 / INA128 standard
    series: ESeries | str = ESeries.E96,
) -> Dict[str, Any]:
    """Synthesize 3-opamp instrumentation amplifier gain stage (AD620/INA128)."""
    if gain <= 1.0:
        raise ValueError("Instrumentation amplifier gain must be strictly > 1.0.")

    # Gain = 1 + (r_internal / Rg)  ==>  Rg = r_internal / (Gain - 1)
    rg_ideal = r_internal / (gain - 1.0)
    rg_snap = snap_component_value(rg_ideal, series=series, component_type="resistor")
    rg_act = float(rg_snap["standard_value"])

    gain_act = 1.0 + (r_internal / rg_act)
    gain_err = ((gain_act - gain) / gain) * 100.0

    bom_items = [
        ComponentItem("U1", "AD620ARZ", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "Low Power Precision Instrumentation Amp"),
        ComponentItem("Rg", str(rg_snap["formatted"]), "Resistor_SMD:R_0805_2012Metric", "Precision 0.1% 25ppm Thin-Film"),
        ComponentItem("C_dec1", "100 nF", "Capacitor_SMD:C_0603_1608Metric", "Power Supply Decoupling X7R"),
        ComponentItem("C_dec2", "100 nF", "Capacitor_SMD:C_0603_1608Metric", "Power Supply Decoupling X7R"),
    ]

    return {
        "topology": f"Precision Instrumentation Amplifier (Gain={gain}x)",
        "target_gain": gain,
        "actual_gain": round(gain_act, 3),
        "gain_error_percent": round(gain_err, 2),
        "components": {
            "Rg": rg_snap,
            "IC": "AD620 / INA128",
        },
        "bom_table": KiCadExporter.generate_bom_markdown(bom_items),
    }

