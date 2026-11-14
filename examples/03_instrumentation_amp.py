"""Example 03: Precision Instrumentation Amplifier Synthesis (AD620 / INA128).

Demonstrates medical/sensor front-end gain stage synthesis with 0.1% E96 resistors.
"""

from cda.templates import synthesize_instrumentation_amp

def main():
    print("=" * 70)
    print("CDA: Precision Instrumentation Amplifier Synthesis (Gain = 100x)")
    print("=" * 70)

    result = synthesize_instrumentation_amp(gain=100.0, series="E96")

    print(f"\n[+] Target Gain: {result['target_gain']}x")
    print(f"[+] Actual Synthesized Gain: {result['actual_gain']}x")
    print(f"[+] Gain Error: {result['gain_error_percent']} %\n")

    print("[+] Gain-Setting Resistor (Rg):")
    rg = result['components']['Rg']
    print(f"    - Ideal Value: {rg['ideal_value']:.2f} Ω")
    print(f"    - Standard E96: {rg['formatted']} (Error: {rg['error_percent']:+.2f}%)")

    print("\n[+] Bill of Materials (BOM):")
    print(result['bom_table'])


if __name__ == "__main__":
    main()

