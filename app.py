"""Streamlit Web Application for Circuit Design Anything (CDA).

Interactive 24/7 Cloud EDA Studio:
- Dual Mode: Guided Parametric Synthesizer & Arbitrary SPICE Netlist Solver
- Real-time parametric circuit synthesis
- IEC 60063 E-series component snapping
- SPICE frequency response Bode plots (Magnitude & Phase)
- Schemdraw vector schematic display
- KiCad netlist & BOM export
"""

import io
import math
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from cda.templates import (
    synthesize_sallen_key_lowpass,
    synthesize_twin_t_notch,
    synthesize_rc_lowpass,
    synthesize_instrumentation_amp,
)
from cda.engine.spice import CircuitSimulator
from cda.engine.kicad import KiCadExporter

st.set_page_config(
    page_title="Circuit Design Anything (CDA) | Autonomous EDA Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Dark Theme CSS
st.markdown("""
<style>
    .main { background-color: #0b1120; }
    h1, h2, h3 { color: #f1f5f9; font-weight: 800; }
    .stMetric { background-color: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 10px; padding: 12px; }
    .metric-card { background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 12px; padding: 1.2rem; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Circuit Design Anything (CDA)")
st.caption("Autonomous EDA Studio: Closed-Loop SPICE Synthesis, IEC 60063 Snapping & KiCad PCB Generation | By Hossein Nosrati")

# Sidebar Controls
st.sidebar.header("🕹️ Studio Navigation")
studio_mode = st.sidebar.radio(
    "Choose Mode",
    options=["🎛️ Guided Filter Synthesizer", "⚡ Custom SPICE Netlist Engine"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.info("🤖 **Universal AI & IDE Integration**:\nThis web app is an interactive visual playground. CDA connects seamlessly via MCP to **Cursor**, **Claude Desktop**, **Windsurf**, standalone **CLI**, and native **Python** scripts (see GitHub README).")
st.sidebar.markdown("### 🔗 Open-Source Ecosystem")
st.sidebar.markdown("[GitHub Repository](https://github.com/hosseinnosrati/circuit-design-anything)")
st.sidebar.markdown("[Hardware Debug Anything (HDA)](https://github.com/hosseinnosrati/hardware-debug-anything)")
st.sidebar.markdown("[Author Portfolio](https://hosseinnosrati.github.io)")
st.sidebar.markdown("[X / Twitter: @MhosseinNosrati](https://x.com/MhosseinNosrati)")

if studio_mode == "🎛️ Guided Filter Synthesizer":
    st.sidebar.header("🛠️ Design Specifications")
    topology_choice = st.sidebar.selectbox(
        "Circuit Topology",
        options=[
            "Sallen-Key Active Lowpass (2nd Order)",
            "Active Twin-T Notch Filter (50/60 Hz)",
            "Precision Instrumentation Amplifier (AD620)",
            "1st-Order Passive RC Lowpass",
        ],
        index=0,
    )

    if "Instrumentation" in topology_choice:
        target_param = st.sidebar.slider("Voltage Gain (V/V)", min_value=2, max_value=1000, value=100, step=1)
        param_label = "Target Gain"
        param_unit = "x"
    else:
        target_param = st.sidebar.slider("Target Frequency (Hz)", min_value=10, max_value=5000, value=100, step=5)
        param_label = "Cutoff / Center Freq"
        param_unit = "Hz"

    series_choice = st.sidebar.selectbox(
        "IEC Component Tolerance Series",
        options=["E12 (10% Tolerance)", "E24 (5% Commercial Standard)", "E96 (1% Precision)"],
        index=1,
    )
    series_clean = series_choice[:3]

    # Run Synthesis Engine
    if "Sallen" in topology_choice:
        result = synthesize_sallen_key_lowpass(fc_target_hz=float(target_param), series=series_clean)
        f_actual = result["actual_cutoff_hz"]
        err_pct = result["cutoff_error_percent"]
    elif "Notch" in topology_choice:
        result = synthesize_twin_t_notch(f_notch_hz=float(target_param), series=series_clean)
        f_actual = result["actual_notch_hz"]
        err_pct = result["error_percent"]
    elif "Instrumentation" in topology_choice:
        result = synthesize_instrumentation_amp(gain=float(target_param), series=series_clean)
        f_actual = result["actual_gain"]
        err_pct = result["gain_error_percent"]
    else:
        result = synthesize_rc_lowpass(fc_hz=float(target_param), series=series_clean)
        f_actual = result["actual_cutoff_hz"]
        err_pct = result["error_percent"]

    # Top Metrics Bar
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Design Specification", f"{target_param} {param_unit}")
    col2.metric("Commercial Realization", f"{f_actual} {param_unit}")
    col3.metric("Tolerance Deviation", f"{err_pct:+.2f} %")
    col4.metric("Component Series", series_clean)

    st.markdown("---")

    # Main Content Tabs
    tab_schematic, tab_spice, tab_kicad = st.tabs(["📐 Vector Schematic", "📈 SPICE Frequency Response", "📋 KiCad Netlist & BOM"])

    with tab_schematic:
        st.subheader("Synthesized Vector Schematic (Schemdraw Engine)")
        if "schematic_svg" in result and result["schematic_svg"]:
            st.image(result["schematic_svg"], use_container_width=True)
        st.markdown("**Selected Commercial Components:**")
        for name, comp in result["components"].items():
            if isinstance(comp, dict):
                st.write(f"- **{name}**: `{comp['formatted']}` (Standard: {comp['standard_value']:.4g}, Error: {comp['error_percent']:+.2f}%)")
            else:
                st.write(f"- **{name}**: `{comp}`")

    with tab_spice:
        st.subheader("AC Frequency Sweep & -3dB Bandwidth Analysis")
        f_min = max(1.0, float(target_param) / 50.0)
        f_max = float(target_param) * 50.0
        f_axis = np.logspace(np.log10(f_min), np.log10(f_max), 400)
        w = 2.0 * np.pi * f_axis

        fig, ax = plt.subplots(figsize=(10, 3.8), dpi=130)
        fig.patch.set_facecolor("#0b1120")
        ax.set_facecolor("#0f172a")

        if "Sallen" in topology_choice:
            w_c = 2.0 * np.pi * f_actual
            mag_db = 20 * np.log10(1.0 / np.sqrt((1 - (w / w_c)**2)**2 + 2 * (w / w_c)**2))
        elif "Notch" in topology_choice:
            w_n = 2.0 * np.pi * f_actual
            mag_db = 20 * np.log10(np.maximum(1e-3, np.abs(1 - (w / w_n)**2)) / np.sqrt((1 - (w / w_n)**2)**2 + 4 * (w / w_n)**2))
        else:
            w_c = 2.0 * np.pi * f_actual
            mag_db = 20 * np.log10(1.0 / np.sqrt(1 + (w / w_c)**2))

        ax.semilogx(f_axis, mag_db, color="#38bdf8", lw=2.4, label="AC Magnitude (dB)")
        ax.axvline(f_actual, color="#22c55e", ls="--", lw=1.6, label=f"Corner: {f_actual:.1f} Hz")
        ax.set_xlabel("Frequency (Hz)", color="#94a3b8", fontsize=10)
        ax.set_ylabel("Gain (dB)", color="#94a3b8", fontsize=10)
        ax.grid(True, which="both", color="#1e293b", ls=":")
        ax.tick_params(colors="#94a3b8")
        for spine in ax.spines.values():
            spine.set_color("#334155")
        ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#f1f5f9")
        plt.tight_layout()
        st.pyplot(fig)

    with tab_kicad:
        st.subheader("Manufacturing Bill of Materials (BOM)")
        st.markdown(result["bom_table"])

        if "kicad_netlist" in result:
            st.subheader("KiCad S-Expression Netlist (.net)")
            st.code(result["kicad_netlist"], language="lisp")
            st.download_button(
                label="💾 Download KiCad Netlist (.net)",
                data=result["kicad_netlist"],
                file_name="circuit_design.net",
                mime="text/plain",
            )

else:
    # Mode 2: Custom SPICE Netlist Engine
    st.markdown("""
    > [!TIP]
    > **General-Purpose SPICE & Modified Nodal Analysis (MNA) Engine:**
    > Enter *any arbitrary SPICE netlist* (resistors, capacitors, inductors, active operational amplifiers) or transfer function. 
    > CDA deterministically solves the nodal admittance matrix, extracts the -3dB bandwidth, phase margin, and computes the complete AC frequency Bode plot.
    """)

    sample_netlists = {
        "2nd-Order Sallen-Key Active Lowpass": (
            "* 2nd-Order Sallen-Key Butterworth Lowpass Filter\n"
            "V1 in 0 AC 1.0\n"
            "R1 in n1 10k\n"
            "R2 n1 n2 10k\n"
            "C1 n1 out 22n\n"
            "C2 n2 0 10n\n"
            "X1 n2 out out OPAMP\n"
            ".AC DEC 50 1 100k\n"
            ".END"
        ),
        "RLC Resonant Bandpass Filter": (
            "* RLC Resonant Bandpass Network (Q=10)\n"
            "V1 in 0 AC 1.0 BANDPASS\n"
            "R1 in out 100\n"
            "L1 out n1 10m\n"
            "C1 n1 0 100n\n"
            ".AC DEC 50 10 100k\n"
            ".END"
        ),
        "1st-Order Passive RC Lowpass Filter": (
            "* Passive Lowpass Filter (Corner ~ 720 Hz)\n"
            "V1 in 0 AC 1.0\n"
            "R1 in out 4.7k\n"
            "C1 out 0 47n\n"
            ".AC DEC 50 1 100k\n"
            ".END"
        ),
        "Audio High-Frequency Notch Filter": (
            "* Twin-T Notch Filter (Corner ~ 1.0 kHz)\n"
            "V1 in 0 AC 1.0\n"
            "R1 in n1 1.5k\n"
            "R2 n1 out 1.5k\n"
            "C1 in n2 100n\n"
            "C2 n2 out 100n\n"
            ".AC DEC 50 10 100k\n"
            ".END"
        ),
    }

    selected_sample = st.selectbox("Load Example SPICE Netlist (or edit manually below):", list(sample_netlists.keys()))
    default_netlist = sample_netlists[selected_sample]

    col_nl1, col_nl2 = st.columns([3, 1])
    with col_nl1:
        netlist_input = st.text_area("SPICE Netlist (.cir / .sp)", value=default_netlist, height=190)
    with col_nl2:
        st.markdown("**Simulation Parameters:**")
        f_start_val = st.number_input("Start Frequency (Hz)", value=1.0, min_value=0.1, max_value=1000.0, step=1.0)
        f_stop_val = st.number_input("Stop Frequency (Hz)", value=100000.0, min_value=100.0, max_value=10000000.0, step=1000.0)
        run_sim = st.button("🚀 Run MNA Simulation", type="primary", use_container_width=True)

    # Execute deterministic SPICE simulation
    sim_res = CircuitSimulator.simulate_netlist(netlist_input, f_start=float(f_start_val), f_stop=float(f_stop_val))

    # Metrics Display
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Identified -3dB Cutoff", f"{sim_res.cutoff_freq_hz:.1f} Hz" if sim_res.cutoff_freq_hz else "N/A")
    m2.metric("Passband Gain", f"{sim_res.passband_gain_db:.2f} dB" if sim_res.passband_gain_db is not None else "0.00 dB")
    m3.metric("Roll-off Rate", f"{sim_res.rolloff_db_per_decade:+.1f} dB/dec" if sim_res.rolloff_db_per_decade is not None else "N/A")
    m4.metric("Phase Margin", f"{sim_res.phase_margin_deg:.1f}°" if sim_res.phase_margin_deg is not None else "Stable")

    st.markdown("---")

    tab_plot, tab_ascii, tab_json = st.tabs(["📊 Dual Bode Magnitude & Phase", "📟 ASCII Terminal Plot", "🔍 Telemetry Data"])

    with tab_plot:
        fig, (ax_mag, ax_phase) = plt.subplots(2, 1, figsize=(10, 5.0), dpi=130, sharex=True)
        fig.patch.set_facecolor("#0b1120")
        ax_mag.set_facecolor("#0f172a")
        ax_phase.set_facecolor("#0f172a")

        # Magnitude Plot
        ax_mag.semilogx(sim_res.frequencies, sim_res.magnitude_db, color="#38bdf8", lw=2.2, label="Magnitude (dB)")
        if sim_res.cutoff_freq_hz:
            ax_mag.axvline(sim_res.cutoff_freq_hz, color="#22c55e", ls="--", lw=1.5, label=f"fc = {sim_res.cutoff_freq_hz:.1f} Hz")
        ax_mag.set_ylabel("Magnitude (dB)", color="#94a3b8")
        ax_mag.grid(True, which="both", color="#1e293b", ls=":")
        ax_mag.tick_params(colors="#94a3b8")
        for s in ax_mag.spines.values():
            s.set_color("#334155")
        ax_mag.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#f1f5f9", loc="lower left")

        # Phase Plot
        ax_phase.semilogx(sim_res.frequencies, sim_res.phase_deg, color="#f59e0b", lw=2.0, label="Phase (deg)")
        ax_phase.set_xlabel("Frequency (Hz)", color="#94a3b8")
        ax_phase.set_ylabel("Phase (deg)", color="#94a3b8")
        ax_phase.grid(True, which="both", color="#1e293b", ls=":")
        ax_phase.tick_params(colors="#94a3b8")
        for s in ax_phase.spines.values():
            s.set_color("#334155")
        ax_phase.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#f1f5f9", loc="lower left")

        plt.tight_layout()
        st.pyplot(fig)

    with tab_ascii:
        st.markdown("**Terminal-Friendly ASCII Bode Plot:**")
        st.code(sim_res.ascii_bode_plot, language="text")

    with tab_json:
        st.markdown("**Detailed Diagnostic Notes:**")
        for note in sim_res.notes:
            st.write(f"- {note}")
        st.json(sim_res.to_dict())
