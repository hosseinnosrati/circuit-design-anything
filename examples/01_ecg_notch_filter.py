"""Example 01: Biomedical ECG Powerline Hum (50Hz) Notch Filter Synthesis.

Demonstrates closed-loop synthesis of an active Twin-T notch filter for
removing 50Hz mains interference from electrocardiogram (ECG) telemetry.
"""

import json
from cda.templates import synthesize_twin_t_notch

def main():
    print("=" * 70)
    print("CDA: Biomedical ECG 50Hz Notch Filter Synthesis")
    print("=" * 70)

    result = synthesize_twin_t_notch(f_notch_hz=50.0, series="E24")

    print(f"\n[+] Topology: {result['topology']}")
    print(f"[+] Target Notch Frequency: {result['target_notch_hz']} Hz")
    print(f"[+] Actual Synthesized Frequency: {result['actual_notch_hz']} Hz")
    print(f"[+] Frequency Deviation: {result['error_percent']} %\n")

    print("[+] Commercial Component Selection (E24 Standard):")
    for name, comp in result['components'].items():
        if isinstance(comp, dict):
            print(f"    - {name:16}: {comp['formatted']:>10} (Error: {comp['error_percent']:+.2f}%)")
        else:
            print(f"    - {name:16}: {comp}")

    print("\n[+] Bill of Materials (BOM):")
    print(result['bom_table'])

    # Save SVG schematic
    svg_filename = "ecg_notch_filter_50hz.svg"
    with open(svg_filename, "w", encoding="utf-8") as f:
        f.write(result['schematic_svg'])
    print(f"\n[+] Vector Schematic saved to: {svg_filename}")


if __name__ == "__main__":
    main()

