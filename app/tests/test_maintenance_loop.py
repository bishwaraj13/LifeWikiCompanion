import unittest

from app.services.maintenance_loop import run_maintenance_loop


class MaintenanceLoopTests(unittest.TestCase):
    def test_loop_runs_maintenance_periodically_until_max_runs(self):
        runs = []
        sleeps = []

        result = run_maintenance_loop(
            maintain_once=lambda: runs.append("ran"),
            interval_seconds=15,
            sleep=sleeps.append,
            max_runs=3,
        )

        self.assertEqual(result.runs_completed, 3)
        self.assertEqual(runs, ["ran", "ran", "ran"])
        self.assertEqual(sleeps, [15, 15])

    def test_loop_requires_positive_interval(self):
        with self.assertRaises(ValueError):
            run_maintenance_loop(
                maintain_once=lambda: None,
                interval_seconds=0,
                sleep=lambda seconds: None,
                max_runs=1,
            )


if __name__ == "__main__":
    unittest.main()
