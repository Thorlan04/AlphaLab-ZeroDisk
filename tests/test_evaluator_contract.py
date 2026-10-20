"""
AlphaLab-ZeroDisk — Formal Evaluator Contract & Anti-Cheat Regression Suite
Covers 13 invalid subcases (probe-evasion runtime exceptions, NaN, +Inf, -Inf,
non-finite coercions, AST violations, constant/degenerate outputs) plus
finite-score controls across both fast and full benchmark modes.
"""

import unittest
from src.benchmark_engine import BenchmarkEngine


class TestEvaluatorContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Compact deterministic instance for fast unit testing
        cls.engine = BenchmarkEngine(n_scenarios=4, n_tasks=20, fast_eval_scenarios=2)

    def test_01_probe_evasion_runtime_exceptions_rejected(self):
        """
        Subcases 1-5: Candidates that pass initial probe points (or single-point server_load == 0.5)
        and raise ZeroDivisionError, ValueError, TypeError, OverflowError, or IndexError during placement
        MUST return valid=False in both fast and full modes (never silently substitute -1e9).
        """
        probe_loads = "(0.28, 0.24, 0.27, 0.70, 0.07, 0.31, 0.56, 0.66, 0.5)"
        subcases = [
            # 1. Classic Massimiliano reproducer (server_load == 0.5 probe evasion -> 1/0)
            """
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    if server_load == 0.5:
        return 1.0
    return 1.0 / 0.0
""",
            # 2. Evades all 8 initial probes, then triggers ZeroDivisionError during placement
            f"""
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    if round(server_load, 2) in {probe_loads}:
        return rem_cpu * 1.1 + rem_ram * 0.9 + rem_io * 0.5
    return 1.0 / 0.0
""",
            # 3. Evades all 8 initial probes, then triggers math.log(-1) ValueError during placement
            f"""
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    if round(server_load, 2) in {probe_loads}:
        return rem_cpu * 1.1 + rem_ram * 0.9 + rem_io * 0.5
    return math.log(-1.0)
""",
            # 4. Evades all 8 initial probes, then triggers TypeError (None conversion) during placement
            f"""
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    if round(server_load, 2) in {probe_loads}:
        return rem_cpu * 1.1 + rem_ram * 0.9 + rem_io * 0.5
    return None
""",
            # 5. Evades all 8 initial probes, then triggers OverflowError (math.exp(1000)) during placement
            f"""
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    if round(server_load, 2) in {probe_loads}:
        return rem_cpu * 1.1 + rem_ram * 0.9 + rem_io * 0.5
    return math.exp(1000.0)
""",
        ]

        for idx, code in enumerate(subcases, 1):
            for full_mode in (False, True):
                with self.subTest(subcase=idx, full_benchmark=full_mode):
                    res = self.engine.evaluate_code(code, full_benchmark=full_mode)
                    self.assertFalse(res["valid"], f"Subcase {idx} (full={full_mode}) must be invalid")

    def test_02_non_finite_scores_rejected_in_probes_and_placements(self):
        """
        Subcases 6-13: NaN, +Inf, -Inf (both at probe time and mid-simulation after passing probes),
        plus constant/degenerate and AST-illegal candidates MUST return valid=False.
        """
        probe_loads = "(0.28, 0.24, 0.27, 0.70, 0.07, 0.31, 0.56, 0.66)"
        subcases = [
            # 6. Direct NaN on probes
            """
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    return float('nan')
""",
            # 7. Direct +Inf on probes
            """
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    return float('inf')
""",
            # 8. Direct -Inf on probes
            """
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    return float('-inf')
""",
            # 9. Passes all 8 probes, returns NaN during placement
            f"""
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    if round(server_load, 2) in {probe_loads}:
        return rem_cpu * 1.2 + rem_ram * 0.8 + rem_io * 0.4
    return float('nan')
""",
            # 10. Passes all 8 probes, returns +Inf during placement
            f"""
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    if round(server_load, 2) in {probe_loads}:
        return rem_cpu * 1.2 + rem_ram * 0.8 + rem_io * 0.4
    return float('inf')
""",
            # 11. Passes all 8 probes, returns -Inf during placement
            f"""
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    if round(server_load, 2) in {probe_loads}:
        return rem_cpu * 1.2 + rem_ram * 0.8 + rem_io * 0.4
    return float('-inf')
""",
            # 12. Constant / degenerate output
            """
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    return 42.0
""",
            # 13. AST security violation (mutable default argument / state)
            """
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load, _cache=[]):
    return rem_cpu + rem_ram + rem_io
""",
        ]

        for idx, code in enumerate(subcases, 6):
            for full_mode in (False, True):
                with self.subTest(subcase=idx, full_benchmark=full_mode):
                    res = self.engine.evaluate_code(code, full_benchmark=full_mode)
                    self.assertFalse(res["valid"], f"Subcase {idx} (full={full_mode}) must be invalid")

    def test_03_valid_finite_score_controls_pass_fast_and_full(self):
        """
        Finite-score control candidates (Best-Fit L2 equivalent & Log-Barrier Cosine)
        must pass cleanly in both fast and full benchmark modes.
        """
        valid_controls = [
            """
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    dc = rem_cpu - task_cpu
    dr = rem_ram - task_ram
    di = rem_io - task_io
    return -(dc * dc + dr * dr + di * di)
""",
            """
def score_server(task_cpu, task_ram, task_io, rem_cpu, rem_ram, rem_io, server_load):
    dc = rem_cpu - task_cpu
    dr = rem_ram - task_ram
    di = rem_io - task_io
    barrier = math.log(dc + 1e-4) + math.log(dr + 1e-4) + math.log(di + 1e-4)
    dot = task_cpu * (1.0 - rem_cpu) + task_ram * (1.0 - rem_ram) + task_io * (1.0 - rem_io)
    return dot + 0.05 * barrier + 0.2 * server_load
""",
        ]

        for idx, code in enumerate(valid_controls, 1):
            for full_mode in (False, True):
                with self.subTest(control=idx, full_benchmark=full_mode):
                    res = self.engine.evaluate_code(code, full_benchmark=full_mode)
                    self.assertTrue(res["valid"], f"Control {idx} failed: {res.get('error')}")
                    self.assertLess(res["avg_servers"], 20.0)
                    self.assertGreater(res["efficiency_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
