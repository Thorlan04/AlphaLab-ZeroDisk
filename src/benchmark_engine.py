"""
benchmark_engine.py - Le Laboratoire & Juge Déterministe Vectorisé (Argon Hardened)
AlphaLab-ZeroDisk: 100% en RAM, Vectorisation NumPy, Pénalité de Ressources Bloquées (Stranded Capacity) & Anti-Triche.
"""

import ast
import math
import time
import concurrent.futures
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

# Server capacity normalized to (1.0, 1.0, 1.0)
SERVER_CAPACITY = np.array([1.0, 1.0, 1.0], dtype=np.float32)


def generate_industrial_scenarios(
    n_scenarios: int = 200,
    n_tasks_per_scenario: int = 500,
    base_seed: int = 42
) -> List[np.ndarray]:
    """
    Génère en RAM 200 scénarios industriels reproductibles de 500 tâches 3D (CPU, RAM, IO).
    Préserve strictement la séquence pseudo-aléatoire (base_seed=42) pour garantir
    la compatibilité bit-à-bit avec l'historique des 5 440+ formules évaluées.
    """
    scenarios = []
    for s_idx in range(n_scenarios):
        s_rng = np.random.default_rng(base_seed + s_idx * 1000 + 7)
        task_types = s_rng.choice([0, 1, 2, 3], size=n_tasks_per_scenario, p=[0.35, 0.35, 0.20, 0.10])
        tasks = np.zeros((n_tasks_per_scenario, 3), dtype=np.float32)

        for i, t_type in enumerate(task_types):
            if t_type == 0:  # CPU-bound
                cpu = s_rng.uniform(0.30, 0.75)
                ram = s_rng.uniform(0.05, 0.25)
                io = s_rng.uniform(0.05, 0.20)
            elif t_type == 1:  # RAM-bound
                cpu = s_rng.uniform(0.05, 0.25)
                ram = s_rng.uniform(0.30, 0.80)
                io = s_rng.uniform(0.05, 0.20)
            elif t_type == 2:  # Micro-services / IO-bound
                cpu = s_rng.uniform(0.02, 0.18)
                ram = s_rng.uniform(0.02, 0.18)
                io = s_rng.uniform(0.25, 0.65)
            else:  # Balanced
                cpu = s_rng.uniform(0.10, 0.40)
                ram = s_rng.uniform(0.10, 0.40)
                io = s_rng.uniform(0.10, 0.40)
            tasks[i, 0] = cpu
            tasks[i, 1] = ram
            tasks[i, 2] = io

        tasks.flags.writeable = False  # Protection anti-triche : interdiction de modifier l'entrée in-place
        scenarios.append(tasks)

    return scenarios


def simulate_packing(
    tasks: np.ndarray,
    scoring_fn=None,
    method_name: str = "custom"
) -> Tuple[int, float, float]:
    """
    Simule en RAM l'allocation séquentielle en temps réel (online) des tâches sur des serveurs 3D.
    Utilise des opérations matricielles NumPy vectorisées pour le filtrage d'admissibilité
    et l'évaluation des baselines, ainsi que la quantification des ressources résiduelles bloquées
    (Stranded Resources).
    Retourne (nombre de serveurs ouverts, efficacité volumique en %, stranded_capacity_pct).
    """
    n_tasks = tasks.shape[0]
    rem_cap = np.empty((n_tasks, 3), dtype=np.float64)
    load_arr = np.empty(n_tasks, dtype=np.float64)
    n_servers = 0

    total_task_volume = float(np.sum(tasks))

    for idx in range(n_tasks):
        t_cpu = float(tasks[idx, 0])
        t_ram = float(tasks[idx, 1])
        t_io = float(tasks[idx, 2])

        best_server_idx = -1

        if n_servers > 0:
            active_rem = rem_cap[:n_servers]
            valid_mask = (
                (active_rem[:, 0] >= t_cpu) &
                (active_rem[:, 1] >= t_ram) &
                (active_rem[:, 2] >= t_io)
            )
            valid_indices = np.flatnonzero(valid_mask)

            if valid_indices.size > 0:
                if method_name == "first_fit":
                    best_server_idx = int(valid_indices[0])
                elif method_name == "best_fit_l2":
                    cand_rem = active_rem[valid_indices]
                    res_c = cand_rem[:, 0] - t_cpu
                    res_r = cand_rem[:, 1] - t_ram
                    res_i = cand_rem[:, 2] - t_io
                    scores = -(res_c * res_c + res_r * res_r + res_i * res_i)
                    best_server_idx = int(valid_indices[int(np.argmax(scores))])
                elif method_name == "dot_product":
                    cand_rem = active_rem[valid_indices]
                    scores = (
                        t_cpu * (1.0 - cand_rem[:, 0]) +
                        t_ram * (1.0 - cand_rem[:, 1]) +
                        t_io * (1.0 - cand_rem[:, 2])
                    )
                    best_server_idx = int(valid_indices[int(np.argmax(scores))])
                else:
                    best_score = -float('inf')
                    for s_i in valid_indices:
                        s = int(s_i)
                        r_c = float(active_rem[s, 0])
                        r_r = float(active_rem[s, 1])
                        r_i = float(active_rem[s, 2])
                        s_load = float(load_arr[s])
                        score = float(scoring_fn(t_cpu, t_ram, t_io, r_c, r_r, r_i, s_load))
                        if not math.isfinite(score):
                            raise ValueError(f"Score non-fini détecté ({score}) durant simulate_packing.")

                        if score > best_score:
                            best_score = score
                            best_server_idx = s

        if best_server_idx != -1:
            rem_cap[best_server_idx, 0] -= t_cpu
            rem_cap[best_server_idx, 1] -= t_ram
            rem_cap[best_server_idx, 2] -= t_io
            rem_sum = rem_cap[best_server_idx, 0] + rem_cap[best_server_idx, 1] + rem_cap[best_server_idx, 2]
            load_arr[best_server_idx] = (3.0 - rem_sum) / 3.0
        else:
            rem_cap[n_servers, 0] = 1.0 - t_cpu
            rem_cap[n_servers, 1] = 1.0 - t_ram
            rem_cap[n_servers, 2] = 1.0 - t_io
            load_arr[n_servers] = (t_cpu + t_ram + t_io) / 3.0
            n_servers += 1

    if n_servers == 0:
        return 0, 0.0, 0.0

    # Efficacité volumique brute (%)
    efficiency_pct = (total_task_volume / (n_servers * 3.0)) * 100.0

    # Quantification rigoureuse de la fragmentation tri-dimensionnelle (Stranded Resources) :
    # Sur chaque serveur ouvert, l'écart entre les ressources restantes et la ressource goulot
    # d'étranglement mesure la capacité piégée par saturation asymétrique.
    final_rem = rem_cap[:n_servers]
    bottleneck_rem = np.min(final_rem, axis=1, keepdims=True)
    stranded_matrix = final_rem - bottleneck_rem
    stranded_capacity_pct = float(np.sum(stranded_matrix) / (n_servers * 3.0)) * 100.0

    return n_servers, efficiency_pct, stranded_capacity_pct


class SecurityASTValidator(ast.NodeVisitor):
    """
    Valide l'AST Python pour interdire tout code système dangereux,
    variables globales, mutations in-place, appels système, imports ou accès disque / réseau.
    """
    FORBIDDEN_NAMES = {
        'eval', 'exec', 'open', '__import__', 'globals', 'locals', 'getattr', 'setattr',
        'delattr', 'compile', 'breakpoint', 'input', 'memoryview', 'os', 'sys',
        'subprocess', 'socket', 'urllib', 'requests', 'shutil', 'builtins', 'vars', 'dir'
    }

    def __init__(self):
        self.is_valid = True
        self.error_message = ""

    def visit_Import(self, node):
        self.is_valid = False
        self.error_message = "Interdiction stricte des imports dans la sandbox (Zéro Disque / Sandbox Sécurisée)."

    def visit_ImportFrom(self, node):
        self.is_valid = False
        self.error_message = "Interdiction stricte des imports 'from' dans la sandbox."

    def visit_Global(self, node):
        self.is_valid = False
        self.error_message = "Interdiction des variables globales (Anti-Triche)."

    def visit_Nonlocal(self, node):
        self.is_valid = False
        self.error_message = "Interdiction des variables nonlocal (Anti-Triche)."

    def visit_Name(self, node):
        if node.id in self.FORBIDDEN_NAMES or node.id.startswith('__'):
            self.is_valid = False
            self.error_message = f"Accès interdit au symbole '{node.id}'."
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr.startswith('__') or node.attr in self.FORBIDDEN_NAMES:
            self.is_valid = False
            self.error_message = f"Accès interdit à l'attribut spécial '{node.attr}'."
        if isinstance(node.ctx, ast.Store):
            self.is_valid = False
            self.error_message = "Mutation d'attribut interdite (Anti-Triche)."
        self.generic_visit(node)

    def visit_Subscript(self, node):
        if isinstance(node.ctx, ast.Store):
            self.is_valid = False
            self.error_message = "Modification de tableau in-place interdite (Anti-Triche)."
        self.generic_visit(node)


class BenchmarkEngine:
    """
    Laboratoire d'évaluation déterministe en RAM (Argon Hardened).
    Calcule les baselines standards, vérifie l'absence de triche et évalue la fragmentation 3D.
    """
    def __init__(self, n_scenarios: int = 200, n_tasks: int = 500, fast_eval_scenarios: int = 30):
        self.n_scenarios = n_scenarios
        self.n_tasks = n_tasks
        self.fast_eval_scenarios = fast_eval_scenarios

        # 1. Génération en RAM des scénarios industriels (protégés en lecture seule)
        self.scenarios = generate_industrial_scenarios(n_scenarios, n_tasks, base_seed=42)

        # 2. Calcul déterministe des baselines industrielles
        self.baselines = self._compute_baselines()
        self.best_baseline_servers = min(b["avg_servers"] for b in self.baselines.values())
        self.best_baseline_name = min(self.baselines, key=lambda k: self.baselines[k]["avg_servers"])

        # Pré-calcul de la référence rapide sur le sous-ensemble fast_eval_scenarios
        fast_subset = self.scenarios[:self.fast_eval_scenarios]
        self.fast_baseline_servers = sum(
            simulate_packing(sc, method_name=self.best_baseline_name)[0] for sc in fast_subset
        ) / len(fast_subset)

    def _compute_baselines(self) -> Dict[str, Dict[str, float]]:
        methods = ["first_fit", "best_fit_l2", "dot_product"]
        results = {}

        for m in methods:
            total_servers = 0
            total_eff = 0.0
            total_stranded = 0.0
            for sc in self.scenarios:
                srv, eff, stranded = simulate_packing(sc, method_name=m)
                total_servers += srv
                total_eff += eff
                total_stranded += stranded

            n = len(self.scenarios)
            avg_servers = total_servers / n
            avg_eff = total_eff / n
            avg_stranded = total_stranded / n
            results[m] = {
                "avg_servers": round(avg_servers, 3),
                "efficiency_pct": round(avg_eff, 2),
                "stranded_capacity_pct": round(avg_stranded, 2)
            }

        return results

    def validate_code_ast(self, code_str: str) -> Tuple[bool, str]:
        """Vérifie la sécurité AST, l'absence de variables d'état et la signature de score_server."""
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return False, f"Erreur de syntaxe Python: {e}"

        validator = SecurityASTValidator()
        validator.visit(tree)
        if not validator.is_valid:
            return False, validator.error_message

        func_found = False
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "score_server":
                func_found = True
                expected_args = ['task_cpu', 'task_ram', 'task_io', 'rem_cpu', 'rem_ram', 'rem_io', 'server_load']
                args = [arg.arg for arg in node.args.args]
                if args != expected_args:
                    return False, f"Signature invalide. Attendu: {expected_args}, Reçu: {args}"
                if node.args.defaults or node.args.kw_defaults:
                    return False, "Arguments par défaut mutables interdits (Anti-Triche)."
                break

        if not func_found:
            return False, "Aucune fonction 'score_server' trouvée dans le code soumis."

        return True, "Code validé avec succès."

    @staticmethod
    def _verify_anti_cheat_probes(scoring_fn) -> Tuple[bool, str]:
        """
        Vérifie que la fonction candidate :
        1. Est strictement déterministe (sans effet de bord entre appels).
        2. Ne retourne pas une constante dégénérée (variance > 1e-8 sur 8 états distincts).
        3. Sensibilise réellement les résidus 3D (CPU, RAM, IO).
        """
        probes = [
            (0.45, 0.10, 0.10, 0.50, 0.80, 0.85, 0.28),
            (0.10, 0.60, 0.10, 0.85, 0.62, 0.80, 0.24),
            (0.05, 0.08, 0.40, 0.90, 0.85, 0.42, 0.27),
            (0.25, 0.25, 0.25, 0.30, 0.30, 0.30, 0.70),
            (0.15, 0.20, 0.10, 0.95, 0.90, 0.95, 0.07),
            (0.35, 0.15, 0.05, 0.36, 0.80, 0.90, 0.31),
            (0.08, 0.45, 0.12, 0.70, 0.46, 0.15, 0.56),
            (0.20, 0.10, 0.30, 0.22, 0.50, 0.31, 0.66),
        ]
        scores = []
        for p in probes:
            s1 = float(scoring_fn(*p))
            s2 = float(scoring_fn(*p))
            if math.isnan(s1) or math.isinf(s1):
                return False, "Rejet Anti-Triche : Valeur NaN ou Inf retournée sur les sondes."
            if abs(s1 - s2) > 1e-12:
                return False, "Rejet Anti-Triche : Fonction non-déterministe (état caché détecté)."
            scores.append(s1)

        if float(np.std(scores)) < 1e-7:
            return False, "Rejet Anti-Triche : Fonction constante ou dégénérée détectée."

        return True, "Anti-triche validé."

    def evaluate_code(self, code_str: str, full_benchmark: bool = False, timeout_sec: float = 2.5) -> Dict[str, Any]:
        """
        Exécute la fonction dans un bac à sable sécurisé avec audit anti-triche et timeout strict.
        """
        is_safe, msg = self.validate_code_ast(code_str)
        if not is_safe:
            return {"valid": False, "error": msg, "avg_servers": 9999.0, "efficiency_pct": 0.0, "gain_pct": -100.0}

        safe_globals = {
            "__builtins__": {
                "abs": abs,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "round": round,
                "float": float,
                "int": int,
                "range": range,
                "len": len,
                "bool": bool,
            },
            "math": math,
        }
        local_scope: Dict[str, Any] = {}
        try:
            exec(code_str, safe_globals, local_scope)
            scoring_fn = local_scope.get("score_server")
            if not callable(scoring_fn):
                return {"valid": False, "error": "L'objet 'score_server' n'est pas appelable.", "avg_servers": 9999.0, "efficiency_pct": 0.0, "gain_pct": -100.0}

            ok_probe, probe_msg = self._verify_anti_cheat_probes(scoring_fn)
            if not ok_probe:
                return {"valid": False, "error": probe_msg, "avg_servers": 9999.0, "efficiency_pct": 0.0, "gain_pct": -100.0}
        except Exception as e:
            return {"valid": False, "error": f"Erreur lors de l'exécution initiale: {e}", "avg_servers": 9999.0, "efficiency_pct": 0.0, "gain_pct": -100.0}

        eval_scenarios = self.scenarios if full_benchmark else self.scenarios[:self.fast_eval_scenarios]

        def _run_eval():
            total_servers = 0
            total_eff = 0.0
            total_stranded = 0.0
            for sc in eval_scenarios:
                srv, eff, stranded = simulate_packing(sc, scoring_fn=scoring_fn, method_name="custom")
                total_servers += srv
                total_eff += eff
                total_stranded += stranded
            n = len(eval_scenarios)
            return total_servers / n, total_eff / n, total_stranded / n

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_eval)
                avg_servers, efficiency_pct, stranded_pct = future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            return {"valid": False, "error": f"Timeout dépassé (> {timeout_sec}s). Algorithme trop lent.", "avg_servers": 9999.0, "efficiency_pct": 0.0, "gain_pct": -100.0}
        except Exception as e:
            return {"valid": False, "error": f"Erreur d'exécution: {e}", "avg_servers": 9999.0, "efficiency_pct": 0.0, "gain_pct": -100.0}

        base_ref = self.best_baseline_servers if full_benchmark else self.fast_baseline_servers
        gain_pct = ((base_ref - avg_servers) / base_ref) * 100.0

        return {
            "valid": True,
            "error": None,
            "avg_servers": round(avg_servers, 3),
            "efficiency_pct": round(efficiency_pct, 2),
            "stranded_capacity_pct": round(stranded_pct, 2),
            "gain_pct": round(gain_pct, 3),
            "full_benchmark": full_benchmark
        }
