"""Unit and Integration Tests for Circuit Design Anything (CDA)."""

import os
import unittest
from cda.engine.components import snap_component_value, ESeries
from cda.engine.spice import CircuitSimulator
from cda.engine.schematic import SchematicRenderer
from cda.engine.kicad import KiCadExporter, ComponentItem
from cda.templates import (
    synthesize_sallen_key_lowpass,
    synthesize_twin_t_notch,
    synthesize_rc_lowpass,
    synthesize_instrumentation_amp,
)


class TestCDAComponents(unittest.TestCase):
    def test_e24_resistor_snapping(self):
        res = snap_component_value(4821.0, series=ESeries.E24, component_type="resistor")
        self.assertIn("4.7", res["formatted"])
        self.assertAlmostEqual(res["standard_value"], 4700.0)

    def test_e96_precision_snapping(self):
        res = snap_component_value(4821.0, series=ESeries.E96, component_type="resistor")
        self.assertAlmostEqual(res["standard_value"], 4870.0)
        self.assertLess(abs(res["error_percent"]), 1.5)

    def test_capacitor_snapping(self):
        cap = snap_component_value(102e-9, series=ESeries.E24, component_type="capacitor")
        self.assertEqual(cap["standard_value"], 100e-9)
        self.assertIn("100 nF", cap["formatted"])


class TestCDASpice(unittest.TestCase):
    def test_rc_transfer_function(self):
        # H(s) = 1 / (1e-3 * s + 1) -> fc = 1 / (2*pi*1e-3) ~= 159.15 Hz
        res = CircuitSimulator.simulate_transfer_function(
            num_coeffs=[1.0],
            den_coeffs=[1e-3, 1.0],
            f_start=1.0,
            f_stop=10000.0,
        )
        self.assertEqual(res.status, "SUCCESS")
        self.assertIsNotNone(res.cutoff_freq_hz)
        self.assertAlmostEqual(res.cutoff_freq_hz, 159.15, delta=15.0)

    def test_netlist_simulation(self):
        netlist = """
        R1 in out 10k
        C1 out 0 100n
        """
        res = CircuitSimulator.simulate_netlist(netlist)
        self.assertEqual(res.status, "SUCCESS")
        self.assertIsNotNone(res.cutoff_freq_hz)
        self.assertTrue(len(res.ascii_bode_plot) > 50)


class TestCDASchematic(unittest.TestCase):
    def test_render_rc_filter_svg(self):
        svg = SchematicRenderer.render_rc_filter(r_val="10 kΩ", c_val="100 nF")
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)

    def test_render_sallen_key_svg(self):
        svg = SchematicRenderer.render_sallen_key(r1_val="10 kΩ", r2_val="10 kΩ", c1_val="22 nF", c2_val="10 nF")
        self.assertIn("<svg", svg)


class TestCDAKiCad(unittest.TestCase):
    def test_bom_generation(self):
        items = [
            ComponentItem("R1", "10 kΩ", "Resistor_SMD:R_0805", "1% Thick Film"),
            ComponentItem("C1", "100 nF", "Capacitor_SMD:C_0805", "5% C0G"),
        ]
        csv_data = KiCadExporter.generate_bom_csv(items)
        self.assertIn("Designator,Value,Package/Footprint", csv_data)
        self.assertIn("R1,10 kΩ", csv_data)

    def test_kicad_netlist(self):
        items = [ComponentItem("R1", "10 kΩ", "R_0805", "1%")]
        nets = {"Vin": ["R1:1"]}
        net_text = KiCadExporter.generate_kicad_netlist("TestProj", items, nets)
        self.assertIn("(export (version D)", net_text)
        self.assertIn('(comp (ref "R1")', net_text)


class TestCDATemplates(unittest.TestCase):
    def test_sallen_key_synthesis(self):
        synth = synthesize_sallen_key_lowpass(fc_target_hz=50.0)
        self.assertIn("Sallen-Key", synth["topology"])
        self.assertLess(abs(synth["cutoff_error_percent"]), 10.0)
        self.assertIn("R1", synth["components"])

    def test_twin_t_notch_synthesis(self):
        synth = synthesize_twin_t_notch(f_notch_hz=50.0)
        self.assertIn("Twin-T Notch", synth["topology"])
        self.assertLess(abs(synth["error_percent"]), 10.0)

    def test_instrumentation_amp_synthesis(self):
        synth = synthesize_instrumentation_amp(gain=100.0)
        self.assertAlmostEqual(synth["target_gain"], 100.0)
        self.assertLess(abs(synth["gain_error_percent"]), 2.0)


if __name__ == "__main__":
    unittest.main()
