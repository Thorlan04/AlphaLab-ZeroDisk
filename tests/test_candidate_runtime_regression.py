"""Regression tests of the public evaluator; no agents or commercial code."""
import unittest

import numpy as np

from src.benchmark_engine import BenchmarkEngine, simulate_packing


SIGNATURE = (
    "def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):\n"
)
FINITE_SCORE = "    return rem_cpu + rem_ram + rem_io\n"


class CandidateContract(unittest.TestCase):
    def engine(self):
        engine = BenchmarkEngine(n_scenarios=2, n_tasks=3, fast_eval_scenarios=1)
        # The second task fits the first server, forcing a candidate score call.
        # task_cpu ~= .4 occurs here, but not in any of the eight Argon probes.
        tasks = np.array([[.4, .1, .1], [.4, .1, .1], [.3, .2, .2]], dtype=np.float32)
        tasks.flags.writeable = False
        engine.scenarios = [tasks, tasks]
        engine.baselines = engine._compute_baselines()
        engine.best_baseline_name = min(
            engine.baselines, key=lambda key: engine.baselines[key]["avg_servers"]
        )
        engine.best_baseline_servers = engine.baselines[engine.best_baseline_name]["avg_servers"]
        engine.fast_baseline_servers = float(
            simulate_packing(tasks, method_name=engine.best_baseline_name)[0]
        )
        return engine

    def test_runtime_failures_invalidate_fast_and_full(self):
        for result in ("1 / 0", "float('nan')", "float('inf')", "-float('inf')", "'bad-score'"):
            for full in (False, True):
                with self.subTest(result=result, full=full):
                    code = (
                        SIGNATURE
                        + "    if 0.399 < task_cpu < 0.401:\n"
                        + f"        return {result}\n"
                        + FINITE_SCORE
                    )
                    answer = self.engine().evaluate_code(code, full_benchmark=full)
                    self.assertFalse(answer["valid"])
                    # A probe rejection would not exercise simulate_packing.
                    self.assertIn("Erreur d'exécution", answer["error"])

    def test_probe_nonfinite_scores_are_rejected(self):
        for result in ("float('nan')", "float('inf')", "-float('inf')"):
            with self.subTest(result=result):
                answer = self.engine().evaluate_code(SIGNATURE + f"    return {result}\n")
                self.assertFalse(answer["valid"])
                self.assertIsNotNone(answer["error"])
                self.assertNotIn("Erreur d'exécution", answer["error"])

    def test_finite_candidate_preserves_fixture_packing(self):
        engine = self.engine()
        for full in (False, True):
            with self.subTest(full=full):
                answer = engine.evaluate_code(SIGNATURE + FINITE_SCORE, full_benchmark=full)
                self.assertTrue(answer["valid"], answer["error"])
                self.assertEqual(answer["avg_servers"], 2.0)
                self.assertEqual(answer["gain_pct"], 0.0)
        tasks = engine.scenarios[0]
        self.assertEqual(
            simulate_packing(tasks, lambda tc, tr, ti, rc, rr, ri, load: rc + rr + ri),
            simulate_packing(tasks, method_name="first_fit"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
