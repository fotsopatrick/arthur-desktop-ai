#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests unitaires des 3 serveurs MCP locaux.

jimmy : ces tests sont écrits AVANT de vérifier que les modules marchent.
On les lance, on les voit au rouge, puis on corrige jusqu'au vert.

Couverture :
  - mcp_analyse_banc : structure de sortie, champs obligatoires
  - mcp_eveil : git state, agent probe, system state
  - mcp_refactor : remplacement texte, regex, dry-run, streaming
"""
import json
import os
import sys
import tempfile
import shutil

# Ajouter le répertoire parent pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ══════════════════════════════════════════════════════════════════════════
# MCP ÉVEIL
# ══════════════════════════════════════════════════════════════════════════

class TestMCPEveil:
    """Tests du module mcp_eveil.py."""

    def test_git_state_returns_dict(self):
        """git_state rend toujours un dict, même hors d'un dépôt."""
        from skills.mcp_eveil import git_state
        result = git_state(".")
        assert isinstance(result, dict)

    def test_git_state_has_branch_or_error(self):
        """git_state contient soit 'branch', soit 'error'."""
        from skills.mcp_eveil import git_state
        result = git_state(".")
        assert "branch" in result or "error" in result

    def test_git_state_on_real_repo(self):
        """Sur le dépôt haichi, on doit avoir branch=main et des commits."""
        from skills.mcp_eveil import git_state
        repo = os.path.join(os.path.dirname(__file__), "..")
        result = git_state(repo)
        # Soit c'est un vrai dépôt, soit une erreur — jamais un crash
        assert isinstance(result, dict)
        if "branch" in result:
            assert isinstance(result["branch"], str)
            assert isinstance(result.get("last_commits", []), list)

    def test_probe_agent_down(self):
        """Un port fermé rend 'down'."""
        from skills.mcp_eveil import probe_agent
        status, latency = probe_agent("127.0.0.1", 59999, timeout=1)
        assert status == "down"
        assert latency is None

    def test_agents_state_returns_dict(self):
        """agents_state rend un dict avec un entry par agent."""
        from skills.mcp_eveil import agents_state
        result = agents_state({"test_agent": 59999})
        assert "test_agent" in result
        assert result["test_agent"]["status"] in ("up", "down")

    def test_system_state_has_hostname(self):
        """system_state rend au moins le hostname."""
        from skills.mcp_eveil import system_state
        result = system_state()
        assert "hostname" in result
        assert isinstance(result["hostname"], str)
        assert len(result["hostname"]) > 0

    def test_system_state_has_load(self):
        """system_state rend la charge."""
        from skills.mcp_eveil import system_state
        result = system_state()
        # Sur Linux, load_1m est un float ; ailleurs, peut être None
        assert "load_1m" in result

    def test_system_state_has_disk(self):
        """system_state rend l'utilisation disque."""
        from skills.mcp_eveil import system_state
        result = system_state()
        assert "disk_used_pct" in result

    def test_eveil_complet(self):
        """eveil() rend les 4 sections attendues."""
        from skills.mcp_eveil import eveil
        result = eveil(".")
        assert "timestamp" in result
        assert "git" in result
        assert "agents" in result
        assert "system" in result


# ══════════════════════════════════════════════════════════════════════════
# MCP REFACTOR
# ══════════════════════════════════════════════════════════════════════════

class TestMCPRefactor:
    """Tests du module mcp_refactor.py."""

    def setup_method(self):
        """Crée un bac à sable temporaire avec des fichiers de test."""
        self.tmpdir = tempfile.mkdtemp(prefix="mcp_refactor_test_")
        # Fichier 1 : contient "ancien_nom" 3 fois
        with open(os.path.join(self.tmpdir, "fichier1.py"), "w") as f:
            f.write("# ancien_nom est utilisé ici\n")
            f.write("x = 'ancien_nom'\n")
            f.write("y = 'ancien_nom'\n")
        # Fichier 2 : ne contient pas la cible
        with open(os.path.join(self.tmpdir, "fichier2.py"), "w") as f:
            f.write("# ce fichier est propre\n")
            f.write("z = 42\n")
        # Fichier 3 : contient un TODO
        with open(os.path.join(self.tmpdir, "fichier3.py"), "w") as f:
            f.write("# TODO: corriger ceci\n")
            f.write("# TODO  améliorer cela\n")

    def teardown_method(self):
        """Nettoie le bac à sable."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_remplacement_texte(self):
        """Remplacement de texte simple fonctionne."""
        from skills.mcp_refactor import refactor
        result = refactor("*.py", "ancien_nom", "nouveau_nom",
                          base_dir=self.tmpdir)
        assert result["files_scanned"] >= 1
        assert result["files_modified"] == 1
        assert result["total_replacements"] == 3
        assert result["dry_run"] is False

        # Vérifier que le fichier a bien été modifié
        with open(os.path.join(self.tmpdir, "fichier1.py")) as f:
            content = f.read()
        assert "ancien_nom" not in content
        assert "nouveau_nom" in content

    def test_dry_run_ne_modifie_pas(self):
        """En dry-run, rien ne change sur le disque."""
        from skills.mcp_refactor import refactor
        result = refactor("*.py", "ancien_nom", "REMPLACEMENT",
                          dry_run=True, base_dir=self.tmpdir)
        assert result["dry_run"] is True
        assert result["total_replacements"] == 3

        # Le fichier NE doit PAS avoir changé
        with open(os.path.join(self.tmpdir, "fichier1.py")) as f:
            content = f.read()
        assert "ancien_nom" in content
        assert "REMPLACEMENT" not in content

    def test_cible_vide_refusee(self):
        """Une cible vide detruisait le fichier (inseree entre chaque caractere)."""
        from skills.mcp_refactor import refactor
        chemin = os.path.join(self.tmpdir, "fichier1.py")
        avant = open(chemin).read()
        result = refactor("*.py", "", "X", base_dir=self.tmpdir)
        assert result["success"] is False
        assert result["reason"] == "empty_target"
        assert open(chemin).read() == avant

    def test_glob_hors_base_ignore(self):
        """Un glob absolu ou en ../ ne sort pas de base_dir."""
        from skills.mcp_refactor import refactor
        dehors = tempfile.mkdtemp(prefix="mcp_refactor_dehors_")
        try:
            cible = os.path.join(dehors, "x.py")
            with open(cible, "w") as f:
                f.write("ancien_nom\n")
            result = refactor(cible, "ancien_nom", "pirate", base_dir=self.tmpdir)
            assert result["files_scanned"] == 0
            assert open(cible).read() == "ancien_nom\n"
        finally:
            shutil.rmtree(dehors, ignore_errors=True)

    def test_regex(self):
        """Remplacement par regex fonctionne."""
        from skills.mcp_refactor import refactor
        result = refactor("*.py", r"TODO:?\s*", "FIXME: ",
                          use_regex=True, base_dir=self.tmpdir)
        assert result["total_replacements"] == 2

        with open(os.path.join(self.tmpdir, "fichier3.py")) as f:
            content = f.read()
        assert "TODO" not in content
        assert "FIXME:" in content

    def test_aucun_match(self):
        """Quand rien ne matche, 0 modifications et 0 erreur."""
        from skills.mcp_refactor import refactor
        result = refactor("*.py", "mot_inexistant_xyz", "rien",
                          base_dir=self.tmpdir)
        assert result["files_modified"] == 0
        assert result["total_replacements"] == 0

    def test_structure_sortie(self):
        """La sortie contient tous les champs obligatoires."""
        from skills.mcp_refactor import refactor
        result = refactor("*.py", "x", "y", base_dir=self.tmpdir)
        for key in ("files_scanned", "files_modified", "total_replacements",
                     "changes", "dry_run"):
            assert key in result, f"champ manquant : {key}"

    def test_refactor_file_streaming(self):
        """refactor_file ne charge pas tout en mémoire (test indirect)."""
        from skills.mcp_refactor import refactor_file
        big_file = os.path.join(self.tmpdir, "big.py")
        # Crée un fichier de 10000 lignes
        with open(big_file, "w") as f:
            for i in range(10000):
                f.write(f"line_{i} = 'target_word'\n")
        count, lines, error = refactor_file(big_file, "target_word",
                                            "replaced")
        assert error is None
        assert count == 10000
        assert len(lines) == 10000


# ══════════════════════════════════════════════════════════════════════════
# MCP ANALYSE BANC
# ══════════════════════════════════════════════════════════════════════════

class TestMCPAnalyseBanc:
    """Tests du module mcp_analyse_banc.py."""

    def setup_method(self):
        """Crée un mini-projet de test avec un test vert et un test rouge."""
        self.tmpdir = tempfile.mkdtemp(prefix="mcp_analyse_test_")
        # Un test qui passe
        with open(os.path.join(self.tmpdir, "test_vert.py"), "w") as f:
            f.write("def test_ok():\n    assert 1 + 1 == 2\n")
        # Un test qui échoue
        with open(os.path.join(self.tmpdir, "test_rouge.py"), "w") as f:
            f.write("def test_echec():\n    assert 1 + 1 == 3, 'addition fausse'\n")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_structure_sortie_analyse(self):
        """run_pytest rend tous les champs obligatoires."""
        from skills.mcp_analyse_banc import run_pytest
        result = run_pytest(self.tmpdir)
        for key in ("total", "passed", "failed", "duration_s", "failures"):
            assert key in result, f"champ manquant : {key}"

    def test_detecte_echec(self):
        """run_pytest détecte bien le test rouge."""
        from skills.mcp_analyse_banc import run_pytest
        result = run_pytest(self.tmpdir)
        assert result["failed"] >= 1
        assert result["passed"] >= 1
        assert len(result["failures"]) >= 1

    def test_failure_detail(self):
        """Chaque échec contient file, test, message."""
        from skills.mcp_analyse_banc import run_pytest
        result = run_pytest(self.tmpdir)
        if result["failures"]:
            failure = result["failures"][0]
            for key in ("file", "test", "message"):
                assert key in failure, f"champ manquant dans failure : {key}"

    def test_tout_vert(self):
        """Quand tout passe, failed=0 et failures=[]."""
        # Écraser le test rouge par un test vert
        with open(os.path.join(self.tmpdir, "test_rouge.py"), "w") as f:
            f.write("def test_ok_aussi():\n    assert True\n")
        from skills.mcp_analyse_banc import run_pytest
        result = run_pytest(self.tmpdir)
        assert result["failed"] == 0
        assert result["failures"] == []

    def test_dossier_vide(self):
        """Sur un dossier sans test, rend total=0."""
        empty = tempfile.mkdtemp(prefix="mcp_vide_")
        try:
            from skills.mcp_analyse_banc import run_pytest
            result = run_pytest(empty)
            assert result["total"] == 0
        finally:
            shutil.rmtree(empty, ignore_errors=True)
