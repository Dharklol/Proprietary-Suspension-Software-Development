from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import unittest

from pssd_measurements import (
    SteeringPoint,
    incrementalize_points,
    summarize_repeatability,
    validate_measurement_package,
)


CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "measurement_data_contract.toml"
)


class MeasurementContractTests(unittest.TestCase):
    def _write_package(self, root: Path, *, unknown_channel: bool = False) -> None:
        (root / "session.toml").write_text(
            textwrap.dedent(
                """
                [session]
                session_id = "WUFR26-STEER-LF-TEST-001"
                vehicle_revision = "WUFR-26"
                test_type = "steering_level_f"
                data_role = "validation"
                started_at_utc = "2026-07-21T12:00:00Z"
                operator = "test operator"
                test_location = "shop"
                configuration_id = "WUFR26_INSTALLED_TEST_V0"
                registry_commit = "0123456789abcdef"
                time_base = "logger_monotonic_seconds"
                setup_record = "setup.md"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        (root / "channels.csv").write_text(
            "channel_id,sensor_id,quantity_id,acquisition_device,acquisition_channel,raw_unit,canonical_unit,sample_rate_hz,clock_id,calibration_id,polarity,zero_reference,status\n"
            "CH-STEER-0001,SNS-STEER-0001,QTY-STEER-0004,logger,A0,V,m,100,LOGGER-1,CAL-STEER-0001,positive_is_canonical_plus_y,measured_rack_center,active\n",
            encoding="utf-8",
        )
        (root / "calibrations.csv").write_text(
            "calibration_id,sensor_id,quantity_id,method,input_unit,output_unit,performed_at_utc,valid_from_utc,valid_to_utc,coefficients_json,fit_rmse,uncertainty_1sigma,status,source_sha256\n"
            'CAL-STEER-0001,SNS-STEER-0001,QTY-STEER-0004,linear,V,m,2026-07-21T11:00:00Z,2026-07-21T11:00:00Z,2026-08-21T11:00:00Z,"{""slope"":0.01,""intercept"":-0.005}",0.0001,0.0002,active,\n',
            encoding="utf-8",
        )
        channel = "CH-STEER-9999" if unknown_channel else "CH-STEER-0001"
        (root / "raw_samples.csv").write_text(
            "time_s,sequence,channel_id,raw_value,quality_flag\n"
            f"0.0,0,{channel},0.5,ok\n"
            f"0.01,1,{channel},0.6,ok\n",
            encoding="utf-8",
        )
        (root / "steering_points.csv").write_text(
            "point_id,repeat_index,approach_direction,target_fraction,measured_rack_m,primary_shaft_rad,steering_wheel_rad,steering_wheel_torque_nm,left_heading_rad,right_heading_rad,hold_start_s,hold_end_s,quality_flag\n"
            "P1,1,increasing,0.0,0.0001,,,,0.010,-0.010,0.0,1.0,ok\n"
            "P2,1,increasing,0.5,0.0126,,,,0.110,-0.140,2.0,3.0,ok\n",
            encoding="utf-8",
        )

    def test_valid_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_package(root)
            self.assertEqual(
                [],
                validate_measurement_package(root, contract_path=CONTRACT),
            )

    def test_undeclared_raw_channel_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_package(root, unknown_channel=True)
            messages = [
                str(issue)
                for issue in validate_measurement_package(root, contract_path=CONTRACT)
            ]
            self.assertTrue(any("unknown channel_id" in message for message in messages))

    def test_incrementalize_uses_approach_specific_center(self) -> None:
        points = [
            SteeringPoint("c_inc", 1, "increasing", 0.0, 0.001, None, None, None, 0.10, -0.10, 0, 1, "ok"),
            SteeringPoint("p_inc", 1, "increasing", 0.5, 0.011, None, None, None, 0.20, -0.25, 2, 3, "ok"),
            SteeringPoint("c_dec", 1, "decreasing", 0.0, -0.001, None, None, None, 0.11, -0.09, 4, 5, "ok"),
            SteeringPoint("p_dec", 1, "decreasing", 0.5, 0.009, None, None, None, 0.19, -0.23, 6, 7, "ok"),
        ]
        incremental = incrementalize_points(points)
        by_id = {item.point.point_id: item for item in incremental}
        self.assertAlmostEqual(0.010, by_id["p_inc"].rack_from_center_m)
        self.assertAlmostEqual(0.010, by_id["p_dec"].rack_from_center_m)
        self.assertAlmostEqual(0.10, by_id["p_inc"].left_incremental_rad)
        self.assertAlmostEqual(0.08, by_id["p_dec"].left_incremental_rad)
        self.assertEqual(4, len(summarize_repeatability(incremental)))


if __name__ == "__main__":
    unittest.main()
