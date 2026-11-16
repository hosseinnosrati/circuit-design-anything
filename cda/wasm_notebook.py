import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo
    import numpy as np
    import matplotlib.pyplot as plt
    import math

    # IEC 60063 Standard E24 Base Values
    E24_BASE = [
        1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
        3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1
    ]

    def snap_e24(val):
        if val <= 0:
            return val
        dec = math.floor(math.log10(val))
        mant = val / (10 ** dec)
        best = min(E24_BASE, key=lambda b: abs(b - mant))
        return best * (10 ** dec)

    def format_unit(val, comp="res"):
        if "res" in comp:
            if val >= 1e6:
                return f"{val/1e6:.3g} MΩ"
            elif val >= 1e3:
                return f"{val/1e3:.3g} kΩ"
            return f"{val:.3g} Ω"
        elif "cap" in comp:
            if val >= 1e-6:
                return f"{val*1e6:.3g} µF"
            elif val >= 1e-9:
                return f"{val*1e9:.3g} nF"
            elif val >= 1e-12:
                return f"{val*1e12:.3g} pF"
            return f"{val:.3g} F"
        return f"{val:.3g}"

    return E24_BASE, format_unit, math, mo, np, plt, snap_e24


@app.cell
def __(mo):
    mo.md(
        """
        # ⚡ Circuit Design Anything (CDA) — WebAssembly Studio
        ### *100% Client-Side In-Browser EDA Simulation powered by Pyodide & Marimo WASM*
        **Zero Server Dependencies &bull; Runs entirely inside your browser CPU**
        """
    )
    return


@app.cell
def __(mo):
    topo_choice = mo.ui.dropdown(
        options=[
            "Sallen-Key Active Lowpass (2nd Order)",
            "Active Twin-T Notch Filter (50/60 Hz)",
            "Precision Instrumentation Amplifier (AD620)",
            "1st-Order Passive RC Lowpass",
        ],
        value="Sallen-Key Active Lowpass (2nd Order)",
        label="Circuit Topology",
    )

    freq_in = mo.ui.slider(
        start=10,
        stop=5000,
        step=5,
        value=100,
        label="Target Frequency / Gain",
    )

    mo.hstack([topo_choice, freq_in], justify="start", gap=2)
    return freq_in, topo_choice


@app.cell
def __(format_unit, freq_in, math, mo, np, plt, snap_e24, topo_choice):
    target_f = freq_in.value
    topo = topo_choice.value

    if "Sallen" in topo:
        C2_ideal = 10e-9
        C1_ideal = 20e-9
        w_c = 2.0 * math.pi * target_f
        R_ideal = 1.0 / (w_c * math.sqrt(C1_ideal * C2_ideal))
        R_act = snap_e24(R_ideal)
        fc_act = 1.0 / (2.0 * math.pi * R_act * math.sqrt(C1_ideal * C2_ideal))
        err = ((fc_act - target_f) / target_f) * 100.0

        bom_rows = [
            ("R1", format_unit(R_act, "res"), "R_0805", "1% Thin-Film"),
            ("R2", format_unit(R_act, "res"), "R_0805", "1% Thin-Film"),
            ("C1", "20 nF", "C_0805", "5% C0G/NP0 Ceramic"),
            ("C2", "10 nF", "C_0805", "5% C0G/NP0 Ceramic"),
            ("U1", "TL072", "SOIC-8", "Dual Low-Noise JFET Op-Amp"),
        ]

    elif "Notch" in topo:
        C_ideal = 100e-9
        R_ideal = 1.0 / (2.0 * math.pi * target_f * C_ideal)
        R_act = snap_e24(R_ideal)
        R_shunt = snap_e24(R_act / 2.0)
        fc_act = 1.0 / (2.0 * math.pi * R_act * C_ideal)
        err = ((fc_act - target_f) / target_f) * 100.0

        bom_rows = [
            ("R1, R2", format_unit(R_act, "res"), "R_0805", "0.1% Precision Thin-Film"),
            ("R3 (R/2)", format_unit(R_shunt, "res"), "R_0805", "0.1% Precision Thin-Film"),
            ("C1, C2", "100 nF", "C_0805", "1% Film Capacitor"),
            ("C3 (2C)", "200 nF", "C_0805", "1% Film Capacitor"),
            ("U1", "OPA1612", "SOIC-8", "Ultra-Low Distortion Audio Op-Amp"),
        ]

    elif "Instrumentation" in topo:
        rg_ideal = 49400.0 / (target_f - 1.0)
        rg_act = snap_e24(rg_ideal)
        gain_act = 1.0 + (49400.0 / rg_act)
        fc_act = gain_act
        err = ((gain_act - target_f) / target_f) * 100.0

        bom_rows = [
            ("U1", "AD620ARZ", "SOIC-8", "Precision Instrumentation Amp"),
            ("Rg", format_unit(rg_act, "res"), "R_0805", "0.1% 25ppm Thin-Film"),
            ("C1, C2", "100 nF", "C_0603", "Decoupling X7R"),
        ]

    else:
        C_ideal = 100e-9
        R_ideal = 1.0 / (2.0 * math.pi * target_f * C_ideal)
        R_act = snap_e24(R_ideal)
        fc_act = 1.0 / (2.0 * math.pi * R_act * C_ideal)
        err = ((fc_act - target_f) / target_f) * 100.0

        bom_rows = [
            ("R1", format_unit(R_act, "res"), "R_0603", "1% Thick Film"),
            ("C1", "100 nF", "C_0603", "5% X7R Ceramic"),
        ]

    # Metrics
    unit_str = "x" if "Instrumentation" in topo else "Hz"
    metrics = mo.hstack(
        [
            mo.stat(value=f"{target_f} {unit_str}", label="Design Target"),
            mo.stat(value=f"{fc_act:.2f} {unit_str}", label="Synthesized with E24"),
            mo.stat(value=f"{err:+.2f}%", label="Tolerance Deviation"),
        ],
        justify="space-between",
    )

    # Plot
    f_axis = np.logspace(np.log10(max(1.0, target_f / 50.0)), np.log10(target_f * 50.0), 300)
    w = 2.0 * np.pi * f_axis

    fig, ax = plt.subplots(figsize=(8.5, 3.2), dpi=120)
    fig.patch.set_facecolor("#0b1120")
    ax.set_facecolor("#0f172a")

    if "Sallen" in topo:
        w_c = 2.0 * np.pi * fc_act
        mag_db = 20 * np.log10(1.0 / np.sqrt((1 - (w / w_c)**2)**2 + 2 * (w / w_c)**2))
    elif "Notch" in topo:
        w_n = 2.0 * np.pi * fc_act
        mag_db = 20 * np.log10(np.maximum(1e-3, np.abs(1 - (w / w_n)**2)) / np.sqrt((1 - (w / w_n)**2)**2 + 4 * (w / w_n)**2))
    else:
        w_c = 2.0 * np.pi * fc_act
        mag_db = 20 * np.log10(1.0 / np.sqrt(1 + (w / w_c)**2))

    ax.semilogx(f_axis, mag_db, color="#38bdf8", lw=2.2, label="AC Magnitude (dB)")
    ax.axvline(fc_act, color="#22c55e", ls="--", lw=1.5, label=f"Corner: {fc_act:.1f} {unit_str}")
    ax.set_title(f"Client-Side WASM Frequency Analysis: {topo}", color="#f1f5f9", fontsize=11, fontweight="bold")
    ax.set_xlabel("Frequency (Hz)", color="#94a3b8")
    ax.set_ylabel("Gain (dB)", color="#94a3b8")
    ax.grid(True, which="both", color="#1e293b", ls=":")
    ax.tick_params(colors="#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#334155")
    ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#f1f5f9")
    plt.tight_layout()

    # Markdown BOM
    bom_md_lines = ["| Designator | Commercial Value | Package | Description |", "| :--- | :--- | :--- | :--- |"]
    for row in bom_rows:
        bom_md_lines.append(f"| **{row[0]}** | `{row[1]}` | `{row[2]}` | {row[3]} |")
    bom_table = mo.md("\n".join(bom_md_lines))

    mo.vstack([metrics, fig, mo.md("### Bill of Materials (BOM)"), bom_table])
    return (
        C1_ideal,
        C2_ideal,
        C_ideal,
        R_act,
        R_ideal,
        R_shunt,
        ax,
        bom_md_lines,
        bom_rows,
        bom_table,
        err,
        f_axis,
        fc_act,
        fig,
        gain_act,
        mag_db,
        metrics,
        rg_act,
        rg_ideal,
        row,
        spine,
        unit_str,
        w,
        w_c,
        w_n,
    )


if __name__ == "__main__":
    app.run()

