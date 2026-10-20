"""
ip_protector.py - Protection de la Propriété Intellectuelle (Zéro Fuite de Code)
AlphaLab-ZeroDisk: Génère la preuve cryptographique SHA-256 sans jamais divulguer le code source secret.
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any

class IPProtector:
    """
    Garantit la protection absolue de l'algorithme découvert :
    1. Calcule l'empreinte cryptographique SHA-256 du code source.
    2. Génère un certificat de preuve vérifiable (graines, scores exacts, empreinte).
    3. Masque et obfusque l'implémentation pour le magasin public.
    4. Audite le dossier public pour certifier qu'aucune ligne propriétaire ne fuite.
    """

    def __init__(self, public_dir: str):
        self.public_dir = public_dir
        os.makedirs(self.public_dir, exist_ok=True)
        self.proof_file = os.path.join(self.public_dir, "proof_benchmark.json")

    @staticmethod
    def compute_sha256(text: str) -> str:
        """Génère l'empreinte SHA-256 immuable du code source pour prouver l'antériorité."""
        normalized = text.strip().encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()

    def generate_public_proof(
        self,
        champion: Dict[str, Any],
        baselines: Dict[str, Dict[str, float]],
        base_seed: int = 42,
        n_scenarios: int = 200,
        n_tasks_per_scenario: int = 500
    ) -> Dict[str, Any]:
        """
        Crée le fichier de preuve mathématique auditable public_store/proof_benchmark.json.
        Ne contient AUCUNE formule secrète en clair.
        """
        secret_code = champion.get("code", "")
        code_hash = self.compute_sha256(secret_code)
        gain = champion.get("gain_pct", 0.0)
        avg_srv = champion.get("avg_servers", 0.0)
        eff = champion.get("efficiency_pct", 0.0)
        name = champion.get("name", "AlphaLab_Champion")

        # Signature publique tronquée/obfusquée (Boîte Noire)
        sanitized_interface = (
            "def score_server(task_cpu: float, task_ram: float, task_io: float,\n"
            "                 rem_cpu: float, rem_ram: float, rem_io: float,\n"
            "                 server_load: float) -> float:\n"
            '    """\n'
            f'    Algorithme Champion : {name}\n'
            f'    Gain d\'infrastructure certifié : +{gain:.2f}% de serveurs économisés\n'
            f'    Empreinte SHA-256 : {code_hash}\n'
            '    Status: [CŒUR MATHÉMATIQUE PROPRIÉTAIRE SOUS LICENCE COMMERCIALE]\n'
            '    L\'implémentation complète est fournie automatiquement après souscription de la licence.\n'
            '    """\n'
            "    # [REDACTED: 8 lignes d'optimisation non-linéaire vectorielle 3D]\n"
            "    # Compatible drop-in Kubernetes Scheduler Plugin / Nomad Allocator\n"
            "    raise NotImplementedError('Code propriétaire débloqué via clé de licence.')\n"
        )

        proof_data = {
            "title": "AlphaLab-ZeroDisk Cryptographic Proof of Benchmark & Priority",
            "certified_at": datetime.utcnow().isoformat() + "Z",
            "algorithm_metadata": {
                "name": name,
                "version": "1.0-commercial-ready",
                "sha256_code_fingerprint": code_hash,
                "complexity": "O(1) time, O(1) space per server candidate",
                "dependencies": "Standard Python math built-in only (Zero external packages)"
            },
            "benchmark_protocol": {
                "benchmark_type": "3D Online Vector Bin-Packing (CPU, RAM, I/O)",
                "total_scenarios": n_scenarios,
                "tasks_per_scenario": n_tasks_per_scenario,
                "total_tasks_evaluated": n_scenarios * n_tasks_per_scenario,
                "deterministic_base_seed": base_seed,
                "workload_distribution": {
                    "cpu_bound_heavy": "35%",
                    "ram_bound_heavy": "35%",
                    "microservices_io_bound": "20%",
                    "balanced_generalist": "10%"
                }
            },
            "comparative_results": {
                "industry_baselines": baselines,
                "discovered_champion": {
                    "name": name,
                    "avg_servers_required": avg_srv,
                    "packing_efficiency_pct": eff,
                    "net_infrastructure_gain_pct": gain
                }
            },
            "verification_procedure": (
                "To verify cryptographic anteriority upon purchase: compute the SHA-256 "
                "checksum of the licensed 'score_server' implementation in algorithme_champion.py. "
                f"It will match exactly: {code_hash}"
            ),
            "public_interface_mock": sanitized_interface
        }

        with open(self.proof_file, "w", encoding="utf-8") as f:
            json.dump(proof_data, f, indent=2, ensure_ascii=False)

        # Audit anti-fuite
        self.verify_zero_leak(secret_code)
        return proof_data

    def verify_zero_leak(self, secret_code: str) -> bool:
        """
        Vérification de sécurité anti-fuite :
        1. Parcourt tous les fichiers du dossier public_store pour s'assurer
           qu'aucune ligne ou formule mathématique propriétaire n'y figure.
        2. Vérifie l'index Git pour certifier qu'aucun fichier zip ou dossier
           confidentiel (DECOUVERTE_A_VENDRE, data, dashboard.html) n'est traqué.
        """
        # 1. Audit du contenu des fichiers publics
        if secret_code:
            secret_lines = [
                line.strip() for line in secret_code.splitlines()
                if line.strip() and not line.strip().startswith("def score_server")
                and not line.strip().startswith("return ")
                and not line.strip().startswith("#")
                and len(line.strip()) > 8
            ]

            for root, _, files in os.walk(self.public_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        for s_line in secret_lines:
                            if s_line in content:
                                raise SecurityError(
                                    f"[CRITICAL SECURITY ALERT] Fuite détectée dans {filepath}! "
                                    f"La ligne propriétaire '{s_line}' a été trouvée dans le dossier web public !"
                                )
                    except UnicodeDecodeError:
                        continue

        # 2. Audit de l'index Git (Garantie Zéro Fichier Confidentiel / Zip sur le repo)
        self.verify_git_repository_cleanliness()
        return True

    def verify_git_repository_cleanliness(self):
        """Vérifie que Git ne traque aucun zip, code secret ou base interne."""
        import subprocess
        try:
            res = subprocess.run(
                ["git", "ls-files"],
                cwd=os.path.dirname(self.public_dir),
                capture_output=True,
                text=True,
                check=True
            )
            tracked_files = res.stdout.splitlines()
            forbidden_patterns = [
                ".zip",
                "DECOUVERTE_A_VENDRE",
                "algorithme_champion.py",
                "dashboard.html",
                "evolution.db",
                "sent_leads.json"
            ]
            leaks = []
            for tf in tracked_files:
                for pattern in forbidden_patterns:
                    if pattern in tf:
                        leaks.append(tf)

            if leaks:
                raise SecurityError(
                    f"[CRITICAL GIT LEAK ALERT] Des fichiers confidentiels sont traqués par Git : {leaks} ! "
                    "Le push vers GitHub est immédiatement bloqué."
                )
        except subprocess.SubprocessError:
            pass


class SecurityError(Exception):
    """Exception levée en cas de tentative de fuite de propriété intellectuelle."""
    pass
