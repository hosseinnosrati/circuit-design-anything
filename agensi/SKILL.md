---
name: circuit-design-anything
description: Autonomous Electronic Design Automation (EDA) and SPICE simulation engine for AI agents. Solves Modified Nodal Analysis (MNA) frequency sweeps, maps theoretical parts to IEC 60063 standards (E12, E24, E96 1%), and exports KiCad PCB netlists.
tags: [eda, spice, kicad, electronics, hardware, circuit-simulation, mcp]
version: 0.1.0
---

# Circuit Design Anything (CDA) — Agent Skill

This skill equips AI agents (Claude Code, Cursor, Copilot, Windsurf) with a deterministic electronic design automation (EDA) toolchain. Instead of hallucinating theoretical component values (e.g. 4.821kΩ) or producing unverifiable circuit schematics, the agent uses CDA to simulate, mathematically verify, and manufacture physical hardware.

## When to Invoke This Skill
Trigger this skill whenever the user asks to:
1. Design or analyze an analog filter (passive RC/RLC or active op-amp Sallen-Key lowpass, highpass, bandpass, notch).
2. Simulate frequency response, calculate -3dB bandwidth, cutoff frequency, or check phase margins of an analog circuit.
3. Convert theoretical component values into commercially purchasable parts according to IEC 60063 (E12, E24, E96 1% tolerance).
4. Generate a KiCad schematic netlist, Schemdraw vector diagram, or Bill of Materials (BOM) for fabrication.

## Deterministic Tool APIs

### 1. `simulate_ac`
Executes a Modified Nodal Analysis (MNA) AC frequency sweep on an RLC circuit.
* **Parameters**:
  - `netlist`: List of component branch definitions (e.g., `R1 1 2 10k`, `C1 2 0 100n`).
  - `f_start`: Starting frequency in Hz (e.g., `1.0`).
  - `f_stop`: Ending frequency in Hz (e.g., `1e6`).
  - `points`: Number of logarithmic sweep points (default: `100`).
* **Returns**: Magnitude in dB, Phase in degrees, -3dB cutoff frequency, and passband attenuation.

### 2. `pick_standard_parts`
Snaps unmanufacturable floating-point component values to the nearest real-world IEC 60063 decade.
* **Parameters**:
  - `target_value`: Floating point nominal value (e.g., `4821.3`).
  - `component_type`: `"resistor"` or `"capacitor"`.
  - `series`: `"E12"` (10%), `"E24"` (5%), or `"E96"` (1% precision standard).
* **Returns**: Standard commercial value, percentage tolerance deviation, and standard component part code.

### 3. `export_kicad`
Generates a complete KiCad-compatible netlist file and Schemdraw Python vector script.
* **Parameters**:
  - `circuit_name`: Unique string identifier for the design.
  - `components`: Formatted list of parts with assigned standard commercial values and footprints (e.g. `0805`, `0603`, `Through-Hole`).
* **Returns**: KiCad `.net` content, Bill of Materials (BOM) table, and vector schematic SVG.

## Standard Agent Workflow

When asked to design a circuit, follow this 4-step loop:
1. **Analytical Synthesis**: Derive the transfer function $H(s)$ and calculate nominal values $R, C, L$.
2. **Commercial Quantization**: Call `pick_standard_parts` using the `E96` series (1% tolerance) to select realistic market components.
3. **MNA Verification**: Call `simulate_ac` with the quantized components to verify that the cutoff frequency, passband ripple, and roll-off rate adhere strictly to user specifications.
4. **Manufacturing Export**: Call `export_kicad` to provide the ready-to-fabricate PCB netlist and Bill of Materials to the user.
