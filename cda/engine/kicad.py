"""KiCad S-Expression Netlist and Bill-of-Materials (BOM) Generator.

Exports circuit topologies into valid KiCad netlists (.net) ready for PCB layout,
along with manufacturing BOM tables (0805/0603 SMD and SOIC footprints).
"""

from __future__ import annotations
import csv
import io
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class ComponentItem:
    designator: str
    value: str
    footprint: str
    description: str
    manufacturer_pn: str = ""


class KiCadExporter:
    """Exports structured netlists and BOM for EDA manufacturing pipelines."""

    @classmethod
    def generate_bom_csv(cls, components: List[ComponentItem]) -> str:
        """Generate industry-standard CSV Bill of Materials (JLCPCB / PCBWay compatible)."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Designator", "Value", "Package/Footprint", "Description", "Manufacturer Part Number"])
        for comp in components:
            writer.writerow([
                comp.designator,
                comp.value,
                comp.footprint,
                comp.description,
                comp.manufacturer_pn or "Generic",
            ])
        return output.getvalue()

    @classmethod
    def generate_bom_markdown(cls, components: List[ComponentItem]) -> str:
        """Generate human-readable GitHub Markdown table."""
        lines = [
            "| Designator | Value | Footprint / Package | Description |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for c in components:
            lines.append(f"| **{c.designator}** | {c.value} | `{c.footprint}` | {c.description} |")
        return "\n".join(lines)

    @classmethod
    def generate_kicad_netlist(
        cls,
        project_name: str,
        components: List[ComponentItem],
        nets: Dict[str, List[str]]
    ) -> str:
        """Generate KiCad (v6/v7/v8) compatible S-expression netlist.

        Args:
            project_name: Name of the circuit project.
            components: List of ComponentItem objects.
            nets: Mapping of net names to list of 'Designator:Pin' (e.g. {'Vin': ['R1:1', 'J1:1']}).
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        s_expr = [
            f"(export (version D)",
            f'  (design',
            f'    (source "{project_name}.kicad_sch")',
            f'    (date "{timestamp}")',
            f'    (tool "Circuit Design Anything (CDA) EDA Agent")',
            f'  )',
            f'  (components',
        ]

        for c in components:
            s_expr.extend([
                f'    (comp (ref "{c.designator}")',
                f'      (value "{c.value}")',
                f'      (footprint "{c.footprint}")',
                f'      (fields (field (name "Description") "{c.description}"))',
                f'    )',
            ])
        s_expr.append('  )')

        s_expr.append('  (nets')
        for code, (net_name, pins) in enumerate(nets.items(), start=1):
            s_expr.append(f'    (net (code {code}) (name "{net_name}")')
            for pin_desc in pins:
                parts = pin_desc.split(":")
                ref = parts[0]
                pin = parts[1] if len(parts) > 1 else "1"
                s_expr.append(f'      (node (ref "{ref}") (pin "{pin}"))')
            s_expr.append('    )')
        s_expr.append('  )')
        s_expr.append(')')

        return "\n".join(s_expr)
