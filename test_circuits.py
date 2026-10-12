"""Check each simulated lab against hand calculations. Run: python -m unittest -v"""
import unittest

import analyze

analyze.simulate()
M = analyze.analyse()


class Lab1Diode(unittest.TestCase):
    def test_silicon_forward_drop(self):
        self.assertTrue(0.5 < M["lab1_forward_voltage_at_1mA_V"] < 0.75)

    def test_reverse_leakage_is_tiny(self):
        self.assertLess(M["lab1_reverse_current_at_-5V_uA"], 1)

    def test_half_wave_loses_one_diode_drop(self):
        self.assertTrue(0.5 < M["lab1_halfwave_drop_V"] < 0.9)

    def test_half_wave_average_close_to_vp_over_pi(self):
        self.assertAlmostEqual(M["lab1_halfwave_dc_out_V"], M["lab1_halfwave_dc_theory_V"], delta=0.3)


class Lab2Bridge(unittest.TestCase):
    def test_two_diode_drops(self):
        self.assertTrue(1.0 < M["lab2_bridge_drop_V"] < 1.7)

    def test_ripple_at_twice_mains_frequency(self):
        self.assertEqual(M["lab2_ripple_frequency_Hz"], 100)

    def test_capacitor_raises_dc_and_cuts_ripple(self):
        self.assertGreater(M["lab2_filtered_dc_V"], M["lab2_unfiltered_dc_V"] + 2)
        self.assertLess(M["lab2_filtered_ripple_Vpp"], 0.2 * M["lab2_unfiltered_ripple_Vpp"])

    def test_ripple_within_textbook_estimate(self):
        # Vr ≈ Vp / (2 f R C) is a slight overestimate, so the simulated ripple should sit below it
        self.assertTrue(0.5 * M["lab2_filtered_ripple_theory_Vpp"] < M["lab2_filtered_ripple_Vpp"] <= M["lab2_filtered_ripple_theory_Vpp"])


class Lab3Zener(unittest.TestCase):
    def test_regulates_near_5v1(self):
        self.assertAlmostEqual(M["lab3_regulated_V_at_12V_in"], 5.1, delta=0.15)

    def test_line_regulation_under_20mV_per_V(self):
        self.assertLess(M["lab3_line_regulation_mV_per_V"], 20)

    def test_load_regulation_under_2_percent(self):
        self.assertLess(M["lab3_load_regulation_pct_0_to_20mA"], 2)

    def test_dropout_matches_series_resistor_limit(self):
        self.assertAlmostEqual(M["lab3_dropout_load_current_mA"], M["lab3_dropout_theory_mA"], delta=3)


if __name__ == "__main__":
    unittest.main()
