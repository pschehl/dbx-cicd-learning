import json
from pathlib import Path
import subprocess
import sys
import unittest

from src.sales_job import run_demo, summarize_orders


class SalesTests(unittest.TestCase):
    def test_paid_orders_only_and_exact_cents(self):
        self.assertEqual(summarize_orders([
            {"id": 1, "amount_cents": 101, "status": "paid"},
            {"id": 2, "amount_cents": 202, "status": "paid"},
            {"id": 3, "amount_cents": 999, "status": "cancelled"},
        ]), {"paid_orders": 2, "total_cents": 303})

    def test_empty_input(self):
        self.assertEqual(summarize_orders([]), {"paid_orders": 0, "total_cents": 0})

    def test_duplicate_order_rejected(self):
        order = {"id": 1, "amount_cents": 100, "status": "paid"}
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            summarize_orders([order, order])

    def test_invalid_amounts_rejected(self):
        for amount in [-1, 1.5, True, "100"]:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                summarize_orders([{"id": 1, "amount_cents": amount, "status": "paid"}])

    def test_unknown_status_rejected(self):
        with self.assertRaisesRegex(ValueError, "status"):
            summarize_orders([{"id": 1, "amount_cents": 100, "status": "pending"}])

    def test_environment_examples(self):
        for env, size, total in [("dev", 10, 2000), ("staging", 100, 20000), ("prod", 1000, 200000)]:
            with self.subTest(env=env):
                result = run_demo(env, size, total, "example-sha")
                self.assertEqual(result["total_cents"], total)
                self.assertEqual(result["environment"], env)
                self.assertEqual(result["release_sha"], "example-sha")

    def test_incomplete_group(self):
        self.assertEqual(run_demo("dev", 6, 0)["paid_orders"], 5)

    def test_threshold_blocks_bad_run(self):
        with self.assertRaisesRegex(ValueError, "Quality check failed"):
            run_demo("staging", 100, 20001)

    def test_invalid_configuration(self):
        for args in [("unknown", 10, 0), ("dev", 0, 0), ("dev", 100001, 0), ("dev", 10, -1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                run_demo(*args)

    def test_cli_output_and_failure_exit(self):
        script = Path(__file__).resolve().parents[1] / "src" / "sales_job.py"
        command = [sys.executable, str(script), "--environment", "dev", "--batch-size", "10"]
        passed = subprocess.run(command + ["--min-total-cents", "2000"], capture_output=True, text=True)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertEqual(json.loads(passed.stdout)["quality_check"], "passed")
        failed = subprocess.run(command + ["--min-total-cents", "2001"], capture_output=True, text=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("Quality check failed", failed.stderr)


if __name__ == "__main__":
    unittest.main()
