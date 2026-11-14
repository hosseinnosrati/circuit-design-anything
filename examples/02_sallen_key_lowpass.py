"""Example 02: Active Sallen-Key Butterworth Lowpass Filter Synthesis.

Demonstrates closed-loop 2nd-order active lowpass synthesis with SPICE
AC frequency simulation, -3dB bandwidth extraction, and ASCII Bode plot.
"""

from cda.templates import synthesize_sallen_key_lowpass

def main():
    print("=" * 70)
    print("CDA: Sallen-Key Active Lowpass Filter Synthesis (fc = 100 Hz)")
    print("=" * 70)

    result = synthesize_sallen_key_lowpass(fc_target_hz=100.0, q_factor=0.7071, series="E24")

    print(f"\n[+] Target Cutoff: {result['target_cutoff_hz']} Hz")
    print(f"[+] Actual Cutoff: {result['actual_cutoff_hz']} Hz (Error: {result['cutoff_error_percent']} %)")

    print("\n[+] SPICE Frequency Response Simulation:")
    print(result['simulation']['ascii_plot'])

    print("\n[+] Verification SPICE Netlist:")
    print(result['spice_netlist'])

    print("\n[+] Bill of Materials (BOM):")
    print(result['bom_table'])

    svg_filename = "sallen_key_lowpass_100hz.svg"
    with open(svg_filename, "w", encoding="utf-8") as f:
        f.write(result['schematic_svg'])
    print(f"\n[+] Vector Schematic saved to: {svg_filename}")


if __name__ == "__main__":
    main()

