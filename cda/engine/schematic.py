"""Schematic Vector Rendering Engine using Schemdraw.

Generates high-definition vector (SVG) and raster (PNG) circuit schematics
directly compatible with AI agent chat interfaces and documentation pipelines.
"""

from __future__ import annotations
import io
import os
from pathlib import Path
from typing import Dict, Any, Optional
import schemdraw
import schemdraw.elements as elm


class SchematicRenderer:
    """Renders academic/industrial circuit schematics to SVG and image files."""

    @classmethod
    def render_rc_filter(
        cls,
        r_val: str = "10 kΩ",
        c_val: str = "100 nF",
        output_path: Optional[str] = None
    ) -> str:
        """Render 1st-order passive RC lowpass filter."""
        with schemdraw.Drawing(show=False) as d:
            d.config(inches_per_unit=0.6, unit=3.0, fontsize=11)
            d += elm.SourceSin().up().label("Vin", loc="left")
            d += elm.Resistor().right().label(f"R\n{r_val}")
            d += elm.Dot()
            d.push()
            d += elm.Capacitor().down().label(f"C\n{c_val}")
            d += elm.Ground()
            d.pop()
            d += elm.Line().right().length(1.5)
            d += elm.Dot(open=True).label("Vout", loc="right")

            if output_path:
                d.save(output_path)
            return d.get_imagedata("svg").decode("utf-8")

    @classmethod
    def render_sallen_key(
        cls,
        r1_val: str = "10 kΩ",
        r2_val: str = "10 kΩ",
        c1_val: str = "22 nF",
        c2_val: str = "10 nF",
        opamp_name: str = "U1 (TL072)",
        output_path: Optional[str] = None
    ) -> str:
        """Render 2nd-order Sallen-Key unity-gain active lowpass filter."""
        with schemdraw.Drawing(show=False) as d:
            d.config(inches_per_unit=0.6, unit=3.0, fontsize=10)

            # Input source
            d += elm.Line().right().length(1.0).label("Vin", loc="left")
            d += elm.Resistor().right().label(f"R1\n{r1_val}")
            node1 = d.add(elm.Dot())

            # Resistor R2 leading to non-inverting opamp input
            d += elm.Resistor().right().label(f"R2\n{r2_val}")
            node2 = d.add(elm.Dot())

            # Capacitor C2 to Ground
            d.push()
            d += elm.Capacitor().down().label(f"C2\n{c2_val}")
            d += elm.Ground()
            d.pop()

            # Op-Amp
            d += elm.Line().right().length(1.0)
            op = d.add(elm.Opamp(leads=True).anchor("in2").label(opamp_name, loc="center", ofst=(0, 0.8)))

            # Feedback path from output to node1 through C1
            d.push()
            d += elm.Line().up().at(node1.center).length(2.0)
            d += elm.Capacitor().tox(op.out).label(f"C1\n{c1_val}")
            d += elm.Line().toy(op.out)
            d.pop()

            # Unity gain feedback to inverting terminal
            d += elm.Line().left().at(op.in1).length(0.8)
            d += elm.Line().up().length(1.0)
            d += elm.Line().tox(op.out)
            d += elm.Line().toy(op.out)
            d += elm.Dot()

            # Output terminal
            d += elm.Line().right().at(op.out).length(1.5)
            d += elm.Dot(open=True).label("Vout", loc="right")

            if output_path:
                d.save(output_path)
            return d.get_imagedata("svg").decode("utf-8")

    @classmethod
    def render_twin_t_notch(
        cls,
        r_val: str = "15.9 kΩ",
        c_val: str = "200 nF",
        opamp_name: str = "U1 (OPA1612)",
        output_path: Optional[str] = None
    ) -> str:
        """Render active Twin-T Notch filter for powerline hum elimination (50/60Hz)."""
        with schemdraw.Drawing(show=False) as d:
            d.config(inches_per_unit=0.6, unit=3.0, fontsize=10)

            d += elm.Line().right().length(1.0).label("Vin", loc="left")
            vin_node = d.add(elm.Dot())

            # Upper branch: R - R with C/2 to ground
            d += elm.Resistor().right().label(f"R\n{r_val}")
            mid_r = d.add(elm.Dot())
            d += elm.Resistor().right().label(f"R\n{r_val}")
            out_node = d.add(elm.Dot())

            # Shunt C from mid_r
            d.push()
            d += elm.Capacitor().down().at(mid_r.center).label(f"2C")
            d += elm.Ground()
            d.pop()

            # Lower branch: C - C with R/2 to ground
            d.push()
            d += elm.Line().down().at(vin_node.center).length(2.5)
            d += elm.Capacitor().right().tox(mid_r.center).label(f"C\n{c_val}")
            mid_c = d.add(elm.Dot())
            d += elm.Capacitor().right().tox(out_node.center).label(f"C\n{c_val}")
            d += elm.Line().toy(out_node.center)
            d.pop()

            # Shunt R from mid_c
            d.push()
            d += elm.Resistor().down().at(mid_c.center).label("R/2")
            d += elm.Ground()
            d.pop()

            # Buffer Op-Amp
            d += elm.Line().right().at(out_node.center).length(1.0)
            op = d.add(elm.Opamp(leads=True).anchor("in2").label(opamp_name, loc="center", ofst=(0, 0.8)))

            # Unity gain buffer feedback
            d += elm.Line().left().at(op.in1).length(0.6)
            d += elm.Line().up().length(0.8)
            d += elm.Line().tox(op.out)
            d += elm.Line().toy(op.out)
            d += elm.Dot()

            # Output
            d += elm.Line().right().at(op.out).length(1.5)
            d += elm.Dot(open=True).label("Vout", loc="right")

            if output_path:
                d.save(output_path)
            return d.get_imagedata("svg").decode("utf-8")

