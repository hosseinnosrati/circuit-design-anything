# Circuit Design Anything (CDA) — Agensi.io Listing

> **Autonomous Electronic Design Automation (EDA) and Deterministic SPICE Simulation Engine for AI Agents**

## Overview
**Circuit Design Anything (CDA)** empowers Claude Code, Cursor, GitHub Copilot, and modern agentic coding environments to design, verify, and manufacture physical electronic circuits.

Large Language Models typically struggle with physical electronics: they recommend nonexistent component values (e.g. 4.821kΩ resistors), fail to simulate dynamic circuit stability, and cannot export manufacturable PCB netlists. CDA closes this loop by providing AI agents with real mathematical solvers and industry standards.

## Key Capabilities
* **Modified Nodal Analysis (MNA) AC Solver:** Real-time frequency response sweeps, -3dB bandwidth extraction, and Bode plot synthesis without external SPICE binaries.
* **IEC 60063 Standard Parts Picker:** Automatically maps arbitrary theoretical values to commercial decades (E12, E24, and 1% precision E96).
* **KiCad & Schemdraw Synthesis:** Generates production-ready KiCad PCB netlists and Schemdraw vector schematics.
* **100% Deterministic & Tested:** 12/12 unit tests passing in ~1.0 second with strictly zero external cloud API dependencies.

## Installation for AI Agents
Users can install CDA directly into their Claude Desktop or agent configuration:

```json
{
  "mcpServers": {
    "circuit-design-anything": {
      "command": "python",
      "args": ["-m", "cda.server"]
    }
  }
}
```

## Developer Information
* **Author:** Mohammad Hossein Nosrati
* **Affiliation:** Iran University of Science and Technology (IUST)
* **GitHub Repository:** [github.com/hosseinnosrati/circuit-design-anything](https://github.com/hosseinnosrati/circuit-design-anything)
* **Interactive Cloud Studio:** [circuit-design-anything.streamlit.app](https://circuit-design-anything-sgsl7u3hcr76gy96xsltgg.streamlit.app/)
* **License:** Apache 2.0 (Free & Open Source)
