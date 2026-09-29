#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TESTS D'INTÉGRATION MCP — nominal ET chaos, pour les 3 outils locaux.

jimmy : écrits AVANT le blindage, vus au ROUGE, puis le code a été corrigé
jusqu'au VERT. Complète test_mcp_tools.py (qui couvre déjà le nominal en
détail) en insistant sur ce qui manquait : les pannes PROVOQUÉES EXPRÈS,
et la règle absolue — zéro trace Python (stacktrace) rendue à l'agent,
toujours du JSON, même quand tout casse.
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ══════════════════════════════════════════════════════════════════════════
# ÉVEIL — nominal + chaos
# ══════════════════════════════════════════════════════════════════════════

class TestEveilNominal:
    def test_git_state_sur_vrai_depot(self):
        """Sur le dépôt haichi, on a bien un état git exploitable."""
        from skills.mcp_eveil import git_state
        repo = os.path.join(os.path.dirname(__file__), "..")
        result = git_state(repo)
        assert result.get("branch")
        assert isinstance(result.get("last_commits"), list)


class TestEveilChaos:
    def test_absence_de_depot_git(self):
        """Hors de tout dépôt git : JSON partiel structuré, jamais de crash."""
        from skills.mcp_eveil import git_state
        with tempfile.TemporaryDirectory() as td:
            result = git_state(td)
        assert isinstance(result, dict)
        assert "error" in result

    def test_timeout_reseau_sur_un_agent(self):
        """Un agent qui ne répond jamais (port fermé) : 'down', pas de crash."""
        from skills.mcp_eveil import probe_agent
        statut, latence = probe_agent("127.0.0.1", 59998, timeout=1)
        assert statut == "down"
        assert latence is None

    def test_eveil_complet_ne_plante_jamais_meme_hors_repo(self):
        """eveil() au complet, hors dépôt git : toujours les 4 sections."""
        from skills.mcp_eveil import eveil
        with tempfile.TemporaryDirectory() as td:
            result = eveil(td, agents={"fantome": 59997})
        for cle in ("timestamp", "git", "agents", "system"):
            assert cle in result

    def test_ligne_de_commande_rend_toujours_du_json(self):
        """Le CLI, sur un dossier bidon, rend du JSON valide sur stdout et
        AUCUNE trace Python sur stderr."""
        script = os.path.join(os.path.dirname(__file__), "..", "skills",
                              "mcp_eveil.py")
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run([sys.executable, script, "--repo", td, "--json"],
                               capture_output=True, text=True, timeout=15)
        json.loads(r.stdout)  # ne lève pas -> c'est du JSON valide
        assert "Traceback" not in r.stderr


# ══════════════════════════════════════════════════════════════════════════
# ANALYSE BANC — nominal + chaos
# ══════════════════════════════════════════════════════════════════════════

class TestAnalyseBancNominal:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mcp_int_analyse_")
        with open(os.path.join(self.tmpdir, "test_rapport.py"), "w") as f:
            f.write("def test_ok():\n    assert 1 == 1\n")
            f.write("def test_faux():\n    assert 1 == 2, 'attendu 1, recu 2'\n")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_parse_un_faux_rapport_pytest_json(self):
        """Un vrai rapport JSON pytest (fabriqué ici) est bien extrait."""
        from skills.mcp_analyse_banc import run_pytest
        result = run_pytest(self.tmpdir)
        assert result["total"] >= 2
        assert result["failed"] >= 1
        assert any("faux" in (f.get("test") or "") for f in result["failures"])


class TestAnalyseBancChaos:
    def test_rapport_json_corrompu_rend_fatal(self):
        """Texte brut corrompu au lieu de JSON : JSON {'fatal': true, 'error': ...},
        jamais une exception qui remonte."""
        from skills.mcp_analyse_banc import parse_pytest_json_report
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False) as f:
            f.write("ceci n'est pas du JSON du tout {{{")
            chemin = f.name
        try:
            result = parse_pytest_json_report(chemin)
        finally:
            os.unlink(chemin)
        assert result.get("fatal") is True
        assert "error" in result

    def test_fichier_rapport_absent(self):
        """Chemin de rapport inexistant : fatal structuré, pas de crash."""
        from skills.mcp_analyse_banc import parse_pytest_json_report
        result = parse_pytest_json_report("/chemin/qui/n/existe/pas.json")
        assert result.get("fatal") is True

    def test_dossier_de_tests_inexistant_ne_plante_pas(self):
        """pytest pointé sur un dossier fantôme : JSON quand même."""
        from skills.mcp_analyse_banc import run_pytest
        result = run_pytest("/chemin/totalement/fantome/xyz")
        assert isinstance(result, dict)

    def test_ligne_de_commande_rend_toujours_du_json(self):
        script = os.path.join(os.path.dirname(__file__), "..", "skills",
                              "mcp_analyse_banc.py")
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run([sys.executable, script, "--path", td, "--json"],
                               capture_output=True, text=True, timeout=30)
        json.loads(r.stdout)
        assert "Traceback" not in r.stderr


# ══════════════════════════════════════════════════════════════════════════
# REFACTOR AST — nominal + chaos
# ══════════════════════════════════════════════════════════════════════════

class TestRefactorNominal:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mcp_int_refactor_")
        with open(os.path.join(self.tmpdir, "cible.py"), "w") as f:
            f.write("nom_ancien = 1\nprint(nom_ancien)\n")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_remplacement_reussi_dit_success_true(self):
        from skills.mcp_refactor import refactor
        result = refactor("*.py", "nom_ancien", "nom_nouveau",
                          base_dir=self.tmpdir)
        assert result["success"] is True
        assert result["reason"] is None
        assert result["total_replacements"] == 2


class TestRefactorChaos:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mcp_int_refactor_chaos_")
        with open(os.path.join(self.tmpdir, "cible.py"), "w") as f:
            f.write("x = 1\n")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_chaine_inexistante_rend_target_not_found(self):
        from skills.mcp_refactor import refactor
        result = refactor("*.py", "mot_qui_n_existe_nulle_part", "rien",
                          base_dir=self.tmpdir)
        assert result["success"] is False
        assert result["reason"] == "target_not_found"

    @pytest.mark.skipif(os.geteuid() == 0, reason="root ignore les permissions")
    def test_fichier_protege_ne_plante_pas(self):
        """Remplacer un fichier passe par un dossier (fichier temporaire +
        remplacement atomique) : c'est le DOSSIER qui doit être protégé
        pour vraiment empêcher l'écriture, pas le fichier lui-même (chmod
        sur le fichier seul ne bloque pas os.replace). Pas de crash, pas
        de remplacement compté comme réussi."""
        dossier_protege = os.path.join(self.tmpdir, "protege")
        os.makedirs(dossier_protege)
        cible = os.path.join(dossier_protege, "secret.py")
        with open(cible, "w") as f:
            f.write("secret = 'x'\n")
        os.chmod(dossier_protege, stat.S_IRUSR | stat.S_IXUSR)  # pas d'écriture
        try:
            from skills.mcp_refactor import refactor
            result = refactor("secret.py", "secret", "public",
                              base_dir=dossier_protege)
            assert result["success"] is False
        finally:
            os.chmod(dossier_protege, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def test_regex_invalide_ne_plante_pas(self):
        from skills.mcp_refactor import refactor_file
        cible = os.path.join(self.tmpdir, "cible.py")
        count, lignes, erreur = refactor_file(cible, "([", "x", use_regex=True)
        assert count == 0
        assert erreur is not None
        assert "regex" in erreur.lower()

    def test_ligne_de_commande_rend_toujours_du_json(self):
        script = os.path.join(os.path.dirname(__file__), "..", "skills",
                              "mcp_refactor.py")
        r = subprocess.run(
            [sys.executable, script, "--glob", "*.py",
             "--target", "rien_trouve_ici", "--replace", "x",
             "--base-dir", self.tmpdir, "--json"],
            capture_output=True, text=True, timeout=15)
        data = json.loads(r.stdout)
        assert data["success"] is False
        assert "Traceback" not in r.stderr


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
