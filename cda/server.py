"""Circuit Design Anything (CDA) MCP Server.

Provides autonomous EDA tools for Claude Code, Cursor, and AI agents:
- Closed-loop circuit synthesis & verification
- SPICE simulation & AC frequency response extraction
- IEC 60063 E-series component snapping
- Schematic rendering (SVG/PNG)
- KiCad netlist & manufacturing BOM export
"""

from __future__ import annotations
import os
import sys
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP

from cda.engine.components import snap_component_value, ESeries
from cda.engine.spice import CircuitSimulator
from cda.engine.schematic import SchematicRenderer
from cda.engine.kicad import KiCadExporter, ComponentItem
from cda.templates.library import (
    synthesize_sallen_key_lowpass,
    synthesize_twin_t_notch,
    synthesize_rc_lowpass,
    synthesize_instrumentation_amp,
)

# Initialize FastMCP Server
mcp = FastMCP(
    "Circuit-Design-Anything",
)


@mcp.tool()
def synthesize_active_filter(
    topology: str = "sallen_key",
    frequency_hz: float = 100.0,
    q_factor: float = 0.7071,
    series: str = "E24",
) -> Dict[str, Any]:
    """Synthesize an analog active filter circuit with real commercial components.

    Args:
        topology: 'sallen_key' (lowpass), 'twin_t_notch' (50/60Hz hum rejection),
                  'rc_lowpass' (passive 1st order), or 'instrumentation_amp'.
        frequency_hz: Cutoff frequency (-3dB) or Notch frequency in Hertz.
        q_factor: Quality factor (0.7071 for Butterworth maximally flat).
        series: IEC 60063 tolerance series: 'E12' (10%), 'E24' (5%), or 'E96' (1%).

    Returns:
        Structured dictionary containing commercial component values, tolerance errors,
        SPICE netlist, ASCII Bode plot, and Bill of Materials.
    """
    topo = topology.lower().replace("-", "_")

    if "sallen" in topo:
        result = synthesize_sallen_key_lowpass(fc_target_hz=frequency_hz, q_factor=q_factor, series=series)
    elif "notch" in topo or "twin" in topo:
        result = synthesize_twin_t_notch(f_notch_hz=frequency_hz, series=series)
    elif "rc" in topo:
        result = synthesize_rc_lowpass(fc_hz=frequency_hz, series=series)
    elif "inst" in topo or "amp" in topo:
        result = synthesize_instrumentation_amp(gain=frequency_hz, series=series)
    else:
        raise ValueError(f"Unknown topology '{topology}'. Choose 'sallen_key', 'twin_t_notch', or 'rc_lowpass'.")

    # Keep output clean for LLM context (omit large raw SVG string in summary)
    return {
        "status": "SUCCESS",
        "topology": result.get("topology"),
        "target_frequency_hz": frequency_hz,
        "actual_frequency_hz": result.get("actual_cutoff_hz") or result.get("actual_notch_hz"),
        "error_percent": result.get("cutoff_error_percent") or result.get("error_percent"),
        "components": result.get("components"),
        "spice_netlist": result.get("spice_netlist", ""),
        "bode_plot": result.get("simulation", {}).get("ascii_plot", ""),
        "bom_table": result.get("bom_table", ""),
    }


@mcp.tool()
def simulate_spice_netlist(
    netlist: str,
    f_start_hz: float = 1.0,
    f_stop_hz: float = 100000.0,
) -> Dict[str, Any]:
    """Simulate a SPICE netlist and compute AC frequency response and -3dB cutoff.

    Args:
        netlist: Standard SPICE netlist text with components (R, C, L, sources).
        f_start_hz: Starting AC sweep frequency in Hertz.
        f_stop_hz: Stopping AC sweep frequency in Hertz.

    Returns:
        Extracted passband gain, -3dB bandwidth, roll-off (dB/dec), and ASCII plot.
    """
    sim_result = CircuitSimulator.simulate_netlist(
        netlist_text=netlist,
        f_start=f_start_hz,
        f_stop=f_stop_hz,
    )
    return sim_result.to_dict()


@mcp.tool()
def snap_component_to_standard(
    value: float,
    component_type: str = "resistor",
    series: str = "E24",
) -> Dict[str, Any]:
    """Snap an ideal calculated resistor or capacitor value to nearest commercial E-series value.

    Args:
        value: Ideal calculated floating-point value (Ohms or Farads).
        component_type: 'resistor', 'capacitor', or 'inductor'.
        series: IEC series: 'E12' (10%), 'E24' (5%), or 'E96' (1%).

    Returns:
        Exact nearest standard commercial value, relative error %, and SI formatted string.
    """
    return snap_component_value(value=value, series=series, component_type=component_type)


@mcp.tool()
def render_schematic_to_file(
    topology: str = "sallen_key",
    r1_formatted: str = "10 kΩ",
    r2_formatted: str = "10 kΩ",
    c1_formatted: str = "22 nF",
    c2_formatted: str = "10 nF",
    output_filepath: str = "circuit_schematic.svg",
) -> Dict[str, str]:
    """Render a clean publication-quality vector circuit diagram (SVG) to disk.

    Args:
        topology: 'sallen_key', 'twin_t_notch', or 'rc_lowpass'.
        r1_formatted: Formatted R1 value (e.g. '10 kΩ').
        r2_formatted: Formatted R2 value.
        c1_formatted: Formatted C1 value (e.g. '22 nF').
        c2_formatted: Formatted C2 value.
        output_filepath: Target filesystem path (e.g. 'schematic.svg').

    Returns:
        Status confirmation with absolute file path.
    """
    topo = topology.lower()
    if "sallen" in topo:
        svg_data = SchematicRenderer.render_sallen_key(
            r1_val=r1_formatted,
            r2_val=r2_formatted,
            c1_val=c1_formatted,
            c2_val=c2_formatted,
            output_path=output_filepath,
        )
    elif "notch" in topo or "twin" in topo:
        svg_data = SchematicRenderer.render_twin_t_notch(
            r_val=r1_formatted,
            c_val=c1_formatted,
            output_path=output_filepath,
        )
    else:
        svg_data = SchematicRenderer.render_rc_filter(
            r_val=r1_formatted,
            c_val=c1_formatted,
            output_path=output_filepath,
        )

    return {
        "status": "SUCCESS",
        "output_path": os.path.abspath(output_filepath),
        "file_size_bytes": str(len(svg_data)),
    }


@mcp.tool()
def run_monte_carlo(
    netlist: str,
    resistor_tolerance_pct: float = 1.0,
    capacitor_tolerance_pct: float = 5.0,
    num_runs: int = 100,
) -> Dict[str, Any]:
    """Runs Monte Carlo tolerance analysis on a circuit netlist.

    Evaluates real-world component tolerance distributions (Gaussian 3-sigma)
    and returns 95% confidence intervals, mean cutoff frequency, and std deviation.

    Args:
        netlist: SPICE netlist string.
        resistor_tolerance_pct: Resistor tolerance percentage (e.g. 1.0 for 1% E96).
        capacitor_tolerance_pct: Capacitor tolerance percentage (e.g. 5.0 for 5% ceramic).
        num_runs: Number of stochastic runs (default: 100).

    Returns:
        Dictionary containing nominal cutoff, mean cutoff, standard deviation,
        and 95% confidence interval bounds.
    """
    return CircuitSimulator.simulate_monte_carlo(
        netlist=netlist,
        resistor_tolerance=resistor_tolerance_pct / 100.0,
        capacitor_tolerance=capacitor_tolerance_pct / 100.0,
        num_runs=num_runs,
    )


def main():
    """Server entrypoint."""
    mcp.run()


if __name__ == "__main__":
    main()
