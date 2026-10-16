import unittest

import numpy as np

import simulate_itrusst_bm1 as bm1


class ItrusstBm1SimulationTests(unittest.TestCase):
    def test_nominal_contract_and_resource_gate(self):
        config = bm1.config_for_preset("benchmark-nominal")
        gate = bm1.resource_gate(config)
        self.assertEqual((config.nx, config.ny), (481, 281))
        self.assertEqual(config.expanded_shape, (521, 305))
        self.assertEqual(config.ppw, 12.0)
        self.assertAlmostEqual(config.cfl, 0.48)
        self.assertEqual(config.nt, 1500)
        self.assertEqual(config.recorded_samples, 100)
        self.assertEqual(
            gate["derived"]["comparison_shape_lateral_axial"], [141, 241]
        )
        self.assertEqual(gate["derived"]["sensor_points"], 141 * 241)
        self.assertEqual(gate["status"], "passed")

    def test_source_is_before_official_exit_plane(self):
        config = bm1.config_for_preset("benchmark-nominal")
        mask = bm1.build_source_mask(config)
        geometry = bm1.source_geometry(config, mask)
        self.assertGreater(geometry["source_points"], 0)
        self.assertEqual(geometry["axial_index_min"], 0)
        self.assertLessEqual(geometry["source_exit_comparison_index"], 19)
        self.assertAlmostEqual(geometry["geometric_focus_axial_mm"], 64.0)

    def test_sensor_grid_and_orientation(self):
        config = bm1.config_for_preset("benchmark-nominal")
        mask = bm1.build_sensor_mask(config)
        self.assertEqual(np.count_nonzero(mask), 141 * 241)
        values = np.arange(np.count_nonzero(mask))
        reshaped = bm1.reshape_comparison_values(values, config)
        self.assertEqual(reshaped.shape, (141, 241))
        self.assertEqual(reshaped[0, 0], 0)
        self.assertEqual(reshaped[1, 0], 1)
        self.assertEqual(reshaped[0, 1], 141)

    def test_harmonic_extraction_recovers_amplitude_and_phase(self):
        frequency = 500_000.0
        points_per_period = 25
        dt = 1.0 / (frequency * points_per_period)
        sample_count = 4 * points_per_period
        time_values = np.arange(sample_count) * dt
        amplitudes = np.array([2.0, 5.0])
        phases = np.array([0.0, 0.7])
        signals = amplitudes[:, None] * np.sin(
            2 * np.pi * frequency * time_values[None, :] + phases[:, None]
        )
        recovered_amplitude, recovered_phase = bm1.extract_harmonic(
            signals, dt, frequency
        )
        np.testing.assert_allclose(recovered_amplitude, amplitudes, rtol=1e-12)
        np.testing.assert_allclose(recovered_phase, phases, atol=1e-12)

    def test_pressure_orientation_accepts_cpp_time_by_sensor(self):
        raw = np.arange(15, dtype=float).reshape(3, 5)
        oriented = bm1.orient_pressure_time_series(
            raw,
            sensor_points=5,
            recorded_samples=3,
        )
        self.assertEqual(oriented.shape, (5, 3))
        np.testing.assert_array_equal(oriented, raw.T)

    def test_smoke_is_explicitly_not_benchmark_evidence(self):
        gate = bm1.resource_gate(bm1.config_for_preset("smoke"))
        self.assertEqual(gate["claim_level"], "workflow_smoke_only")
        self.assertEqual(gate["status"], "passed")
        self.assertEqual(
            gate["derived"]["comparison_shape_lateral_axial"], [71, 121]
        )

    def test_axisymmetric_grid_and_mirroring(self):
        config = bm1.config_for_preset(
            "benchmark-nominal", coordinate_system="axisymmetric"
        )
        self.assertEqual(config.expanded_shape, (521, 153))
        source = bm1.build_axisymmetric_source_mask(config)
        sensor = bm1.build_axisymmetric_sensor_mask(config)
        self.assertEqual(source.shape, (481, 141))
        self.assertEqual(np.count_nonzero(sensor), 71 * 241)
        values = np.arange(np.count_nonzero(sensor))
        mirrored = bm1.reshape_axisymmetric_comparison_values(values, config)
        self.assertEqual(mirrored.shape, (141, 241))
        np.testing.assert_array_equal(mirrored[:70], mirrored[:70:-1])

    def test_bm3_nominal_material_and_time_contract(self):
        config = bm1.config_for_preset(
            "benchmark-nominal",
            coordinate_system="axisymmetric",
            benchmark="BM3",
        )
        gate = bm1.resource_gate(config)
        self.assertEqual(config.points_per_period, 96)
        self.assertAlmostEqual(config.cfl, 0.125)
        self.assertEqual(config.nt, 5760)
        self.assertEqual(config.recorded_samples, 384)
        self.assertEqual(gate["status"], "passed")
        self.assertLessEqual(
            config.dt_s,
            gate["derived"]["stability_dt_limit_s"],
        )
        self.assertLess(
            gate["derived"]["dt_to_stability_limit_ratio"],
            1.0,
        )
        material = gate["derived"]["material"]["bone"]
        self.assertEqual(material["axial_index_start"], 120)
        self.assertEqual(material["axial_index_stop_exclusive"], 146)
        self.assertEqual(material["front_mm"], 30.0)
        self.assertEqual(material["represented_thickness_mm"], 6.5)
        self.assertEqual(material["sound_speed_m_per_s"], 2800.0)
        self.assertEqual(material["density_kg_per_m3"], 1850.0)
        self.assertEqual(material["alpha_coeff_db_per_mhz_power_cm"], 16.0)
        self.assertEqual(material["alpha_power"], 2.0)
        self.assertIsNone(material["alpha_mode"])

    def test_bm3_medium_arrays_are_radially_uniform(self):
        config = bm1.config_for_preset(
            "benchmark-nominal",
            coordinate_system="axisymmetric",
            benchmark="BM3",
        )
        shape = (config.nx, (config.ny + 1) // 2)
        sound_speed, density, alpha_coeff = bm1.build_medium_arrays(config, shape)
        self.assertEqual(sound_speed.shape, (481, 141))
        np.testing.assert_array_equal(sound_speed[120:146], 2800.0)
        np.testing.assert_array_equal(density[120:146], 1850.0)
        np.testing.assert_array_equal(alpha_coeff[120:146], 16.0)
        np.testing.assert_array_equal(sound_speed[:120], 1500.0)
        np.testing.assert_array_equal(alpha_coeff[:120], 0.0)

    def test_bm3_cartesian_execution_gate_is_blocked(self):
        config = bm1.config_for_preset(
            "benchmark-nominal",
            coordinate_system="cartesian_2d",
            benchmark="BM3",
        )
        gate = bm1.resource_gate(config)
        self.assertEqual(gate["status"], "failed")
        self.assertFalse(gate["checks"]["bm3_axisymmetric_only"])

    def test_bm3_smoke_gate_preserves_material_and_safe_cfl(self):
        config = bm1.config_for_preset(
            "smoke",
            coordinate_system="axisymmetric",
            benchmark="BM3",
        )
        gate = bm1.resource_gate(config)
        self.assertEqual(config.ppw, 6.0)
        self.assertEqual(config.points_per_period, 48)
        self.assertLessEqual(config.cfl, 0.25)
        self.assertEqual(
            gate["derived"]["material"]["bone"]["represented_thickness_mm"],
            6.5,
        )
        self.assertEqual(gate["status"], "passed")

    def test_bm4_nominal_multilayer_contract_and_stability_probe(self):
        config = bm1.config_for_preset(
            "benchmark-nominal",
            coordinate_system="axisymmetric",
            benchmark="BM4",
        )
        gate = bm1.resource_gate(config)
        self.assertEqual(config.points_per_period, 144)
        self.assertEqual(config.nt, 8640)
        self.assertEqual(config.recorded_samples, 576)
        self.assertEqual(config.omp_threads, 6)
        self.assertLessEqual(
            gate["derived"]["omp_thread_fraction"],
            0.5,
        )
        self.assertTrue(gate["checks"]["omp_threads_leave_device_headroom"])
        self.assertEqual(
            gate["derived"]["grid_axes_internal"],
            ["axial", "radial"],
        )
        self.assertEqual(gate["derived"]["grid_shape_internal"], [481, 141])
        self.assertEqual(gate["derived"]["grid_shape_expanded"], [521, 153])
        self.assertEqual(
            gate["derived"]["comparison_domain_grid_shape_axial_lateral"],
            [481, 281],
        )
        self.assertEqual(gate["status"], "passed")
        self.assertLessEqual(
            config.dt_s,
            gate["derived"]["stability_dt_limit_s"],
        )
        material = gate["derived"]["material"]
        self.assertEqual(
            material["bone"]["aggregate_semantics"],
            "cortical_material_only_legacy_compatibility",
        )
        self.assertEqual(
            material["bone"]["represented_thickness_mm"],
            2.5,
        )
        self.assertEqual(
            material["osseous_compartment"],
            {
                "axial_index_start": 120,
                "axial_index_stop_exclusive": 146,
                "front_mm": 30.0,
                "stop_mm": 36.5,
                "represented_thickness_mm": 6.5,
                "heterogeneous": True,
                "authoritative_properties": "layers",
            },
        )
        layers = {
            layer["name"]: layer
            for layer in material["layers"]
        }
        expected = {
            "water": (0, 104, 0.0, 1500.0, 1000.0),
            "skin": (104, 120, 0.8, 1610.0, 1090.0),
            "outer_cortical_bone": (120, 126, 16.0, 2800.0, 1850.0),
            "trabecular_bone": (126, 142, 32.0, 2300.0, 1700.0),
            "inner_cortical_bone": (142, 146, 16.0, 2800.0, 1850.0),
            "brain": (146, 481, 1.2, 1560.0, 1040.0),
        }
        self.assertEqual(set(layers), set(expected))
        for name, (
            start,
            stop,
            alpha,
            sound_speed,
            density,
        ) in expected.items():
            layer = layers[name]
            self.assertEqual(layer["axial_index_start"], start)
            self.assertEqual(layer["axial_index_stop_exclusive"], stop)
            self.assertAlmostEqual(
                layer["alpha_coeff_db_per_mhz_power_cm"],
                alpha,
            )
            self.assertEqual(layer["sound_speed_m_per_s"], sound_speed)
            self.assertEqual(layer["density_kg_per_m3"], density)

    def test_bm4_medium_arrays_are_radially_uniform(self):
        config = bm1.config_for_preset(
            "benchmark-nominal",
            coordinate_system="axisymmetric",
            benchmark="BM4",
        )
        shape = (config.nx, (config.ny + 1) // 2)
        sound_speed, density, alpha_coeff = bm1.build_medium_arrays(config, shape)
        expected_rows = [
            (0, 104, 1500.0, 1000.0, 0.0),
            (104, 120, 1610.0, 1090.0, 0.8),
            (120, 126, 2800.0, 1850.0, 16.0),
            (126, 142, 2300.0, 1700.0, 32.0),
            (142, 146, 2800.0, 1850.0, 16.0),
            (146, 481, 1560.0, 1040.0, 1.2),
        ]
        for start, stop, sound_speed_value, density_value, alpha_value in expected_rows:
            np.testing.assert_allclose(
                sound_speed[start:stop],
                sound_speed_value,
            )
            np.testing.assert_allclose(density[start:stop], density_value)
            np.testing.assert_allclose(alpha_coeff[start:stop], alpha_value)

    def test_bm4_cartesian_execution_gate_is_blocked(self):
        config = bm1.config_for_preset(
            "benchmark-nominal",
            coordinate_system="cartesian_2d",
            benchmark="BM4",
        )
        gate = bm1.resource_gate(config)
        self.assertEqual(gate["status"], "failed")
        self.assertFalse(gate["checks"]["bm4_axisymmetric_only"])

    def test_device_gate_rejects_more_than_half_the_logical_cpus(self):
        logical = bm1.os.cpu_count() or 1
        excessive = max(1, logical // 2 + 1)
        config = bm1.config_for_preset(
            "benchmark-nominal",
            coordinate_system="axisymmetric",
            benchmark="BM4",
            omp_threads=excessive,
        )
        gate = bm1.resource_gate(config)
        self.assertEqual(gate["status"], "failed")
        self.assertFalse(gate["checks"]["omp_threads_leave_device_headroom"])

    def test_bm4_transmitted_region_is_strictly_after_brain_interface(self):
        config = bm1.config_for_preset(
            "benchmark-nominal",
            coordinate_system="axisymmetric",
            benchmark="BM4",
        )
        field = np.zeros((141, 241), dtype=float)
        field[70, 74] = 3.0
        metrics = bm1.transmitted_region_metrics(field, config)
        self.assertEqual(metrics["axial_index_start"], 74)
        self.assertEqual(metrics["axial_mm_start"], 37.0)
        self.assertEqual(metrics["positive_voxels"], 1)
        self.assertEqual(metrics["peak_pa"], 3.0)
        self.assertTrue(metrics["passed"])

    def test_bm4_transmitted_region_rejects_interface_only_pressure(self):
        config = bm1.config_for_preset(
            "benchmark-nominal",
            coordinate_system="axisymmetric",
            benchmark="BM4",
        )
        field = np.zeros((141, 241), dtype=float)
        field[70, 73] = 3.0
        metrics = bm1.transmitted_region_metrics(field, config)
        self.assertFalse(metrics["passed"])


if __name__ == "__main__":
    unittest.main()
