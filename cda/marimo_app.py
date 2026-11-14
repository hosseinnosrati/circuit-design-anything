import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo
    import numpy as np
    import matplotlib.pyplot as plt
    from cda.templates import (
        synthesize_sallen_key_lowpass,
        synthesize_twin_t_notch,
        synthesize_rc_lowpass,
        synthesize_instrumentation_amp,
    )
    return (
        mo,
        np,
        plt,
        synthesize_sallen_key_lowpass,
        synthesize_twin_t_notch,
        synthesize_rc_lowpass,
        synthesize_instrumentation_amp,
    )


@app.cell
def __(mo):
    mo.md(
        """
        # ⚡ Circuit Design Anything (CDA) — Interactive EDA Lab
        ### *Autonomous AI-Powered Circuit Synthesis, SPICE Simulation & KiCad Export*
        **Hardware Acceleration:** NVIDIA RTX Pro 6000 &bull; **Framework:** Model Context Protocol (MCP)
        """
    )
    return


@app.cell
def __(mo):
    topology_selector = mo.ui.dropdown(
        options=[
            "Sallen-Key Active Lowpass (2nd Order)",
            "Active Twin-T Notch Filter (50/60 Hz)",
            "Precision Instrumentation Amplifier (AD620)",
            "1st-Order Passive RC Lowpass",
        ],
        value="Sallen-Key Active Lowpass (2nd Order)",
        label="Select Circuit Topology",
    )

    freq_slider = mo.ui.slider(
        start=10,
        stop=5000,
        step=5,
        value=100,
        label="Target Frequency / Cutoff (Hz)",
    )

    series_selector = mo.ui.dropdown(
        options=["E12", "E24", "E96"],
        value="E24",
        label="IEC 60063 Component Series",
    )

    mo.hstack([topology_selector, freq_slider, series_selector], justify="start", gap=2)
    return freq_slider, series_selector, topology_selector


@app.cell
def __(
    freq_slider,
    mo,
    np,
    plt,
    series_selector,
    synthesize_instrumentation_amp,
    synthesize_rc_lowpass,
    synthesize_sallen_key_lowpass,
    synthesize_twin_t_notch,
    topology_selector,
):
    topo = topology_selector.value
    target_f = freq_slider.value
    series = series_selector.value

    if "Sallen" in topo:
        result = synthesize_sallen_key_lowpass(fc_target_hz=float(target_f), series=series)
        f_actual = result["actual_cutoff_hz"]
        err_pct = result["cutoff_error_percent"]
    elif "Notch" in topo:
        result = synthesize_twin_t_notch(f_notch_hz=float(target_f), series=series)
        f_actual = result["actual_notch_hz"]
        err_pct = result["error_percent"]
    elif "Instrumentation" in topo:
        result = synthesize_instrumentation_amp(gain=float(target_f), series=series)
        f_actual = result["actual_gain"]
        err_pct = result["gain_error_percent"]
    else:
        result = synthesize_rc_lowpass(fc_hz=float(target_f), series=series)
        f_actual = result["actual_cutoff_hz"]
        err_pct = result["error_percent"]

    # Metrics display
    metric_cols = mo.hstack(
        [
            mo.stat(value=f"{target_f} Hz", label="Design Target"),
            mo.stat(value=f"{f_actual} Hz", label="Commercial Synthesized"),
            mo.stat(
                value=f"{err_pct:+.2f}%",
                label="Tolerance Error",
                caption="IEC Snapped E-Series",
            ),
        ],
        justify="space-between",
    )

    # Plot Bode curve
    f_axis = np.logspace(np.log10(max(1.0, target_f / 50.0)), np.log10(target_f * 50.0), 300)
    w = 2.0 * np.pi * f_axis

    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=130)
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")

    if "Sallen" in topo:
        w_c = 2.0 * np.pi * f_actual
        mag_db = 20 * np.log10(1.0 / np.sqrt((1 - (w / w_c)**2)**2 + 2 * (w / w_c)**2))
    elif "Notch" in topo:
        w_n = 2.0 * np.pi * f_actual
        mag_db = 20 * np.log10(np.abs(1 - (w / w_n)**2) / np.sqrt((1 - (w / w_n)**2)**2 + 4 * (w / w_n)**2))
    else:
        w_c = 2.0 * np.pi * f_actual
        mag_db = 20 * np.log10(1.0 / np.sqrt(1 + (w / w_c)**2))

    ax.semilogx(f_axis, mag_db, color="#38bdf8", lw=2.2, label="AC Magnitude (dB)")
    ax.axvline(f_actual, color="#22c55e", ls="--", lw=1.5, label=f"Corner: {f_actual:.1f} Hz")
    ax.set_title(f"AC Frequency Response: {topo}", color="#f1f5f9", fontsize=11, fontweight="bold")
    ax.set_xlabel("Frequency (Hz)", color="#94a3b8")
    ax.set_ylabel("Gain (dB)", color="#94a3b8")
    ax.grid(True, which="both", color="#1e293b", ls=":")
    ax.tick_params(colors="#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#334155")
    ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#f1f5f9")
    plt.tight_layout()

    # Schemdraw Vector Graphic
    svg_html = mo.Html(result.get("schematic_svg", ""))

    # BOM Table
    bom_md = mo.md(f"### Bill of Materials (BOM)\n{result['bom_table']}")

    mo.vstack([metric_cols, mo.ui.tabs({"📈 SPICE Frequency Response": fig, "📐 Vector Schematic": svg_html, "📋 KiCad BOM": bom_md})])
    return (
        ax,
        bom_md,
        err_pct,
        f_actual,
        f_axis,
        fig,
        mag_db,
        metric_cols,
        result,
        series,
        spine,
        svg_html,
        target_f,
        topo,
        w,
        w_c,
        w_n,
    )


if __name__ == "__main__":
    app.run()
