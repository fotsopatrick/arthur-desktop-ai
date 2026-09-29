#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests du serveur stdio MCP (mcp_arthur_server.py).

jimmy : au ROUGE d'abord — on prouve que les handlers tools/call des
3 nouveaux outils locaux n'existent pas encore (le serveur ne répond
pas), puis on les implémente jusqu'au vert.

Couverture :
  - initialize / tools/list répondent et exposent les 5 outils
  - tools/call répond pour arthur_parler (hors ligne inclus)
  - tools/call répond pour eveil_systeme (JSON avec clé "git")
  - tools/call répond pour analyse_banc (JSON avec clé "total")
  - tools/call répond pour refactor (dry_run sur un fichier temp)
"""
import json
import os
import select
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVEUR = os.path.join(REPO, "mcp_arthur_server.py")


def _lire_ligne(proc, timeout=30):
    """Lit une ligne JSON-RPC du serveur stdio, avec timeout réel."""
    fd = proc.stdout.fileno()
    buf = b""
    fin = time.time() + timeout
    while time.time() < fin:
        r, _, _ = select.select([fd], [], [], 0.5)
        if fd in r:
            bloc = os.read(fd, 4096)
            if not bloc:
                break
            buf += bloc
            if b"\n" in buf:
                ligne, _ = buf.split(b"\n", 1)
                return json.loads(ligne.decode("utf-8"))
    raise TimeoutError("le serveur stdio n'a pas répondu")


class Serveur:
    """Un serveur stdio lancé pour toute une session de tests."""

    def __init__(self, argv=None, env=None):
        environnement = dict(os.environ)
        if env:
            environnement.update(env)
        self.proc = subprocess.Popen(
            [sys.executable, SERVEUR] + (argv or []),
            cwd=REPO,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=environnement,
        )
        self.appel("initialize")

    def appel(self, method, params=None):
        msg = {"jsonrpc": "2.0", "id": 11, "method": method}
        if params:
            msg["params"] = params
        self.proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
        self.proc.stdin.flush()
        return _lire_ligne(self.proc)

    def appeler_outil(self, nom, arguments=None):
        rep = self.appel("tools/call", {"name": nom, "arguments": arguments or {}})
        assert rep.get("result") is not None, \
            f"{nom} n'a pas rendu de résultat : {rep}"
        blocs = rep["result"].get("content") or []
        texte = "".join(b.get("text", "") for b in blocs if isinstance(b, dict))
        return texte

    def fermer(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


# ══════════════════════════════════════════════════════════════════════════
# 1. Annonce de capacités
# ══════════════════════════════════════════════════════════════════════════

class TestAnnonce:
    def test_initialize_repond(self):
        s = Serveur()
        try:
            rep = s.appel("tools/list")
            outils = [t.get("name") for t in rep["result"]["tools"]]
            assert "arthur_parler" in outils
            assert "arthur_lire_dialogues" in outils
        finally:
            s.fermer()

    def test_trois_outils_locaux_annonces(self):
        s = Serveur()
        try:
            rep = s.appel("tools/list")
            noms = [t.get("name") for t in rep["result"]["tools"]]
            for nom in ("eveil_systeme", "analyse_banc", "refactor",
                        "apprendre_savoir"):
                assert nom in noms, f"{nom} manque dans tools/list"
        finally:
            s.fermer()


# ══════════════════════════════════════════════════════════════════════════
# 2. Outils Arthur
# ══════════════════════════════════════════════════════════════════════════

class TestOutilsArthur:
    def test_arthur_parler_repond(self):
        s = Serveur()
        try:
            texte = s.appeler_outil("arthur_parler", {"message": "test"})
            assert "Arthur" in texte or "succes" in texte
        finally:
            s.fermer()


# ══════════════════════════════════════════════════════════════════════════
# 3. Les 3 outils locaux — le cœur du manque
# ══════════════════════════════════════════════════════════════════════════

class TestOutilsLocaux:
    def test_eveil_systeme_repond_avec_git(self):
        s = Serveur()
        try:
            texte = s.appeler_outil("eveil_systeme", {})
            data = json.loads(texte)
            assert "git" in data
            assert "system" in data
        finally:
            s.fermer()

    def test_analyse_banc_repond_avec_total(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "test_ok.py"), "w") as f:
                f.write("def test_ok():\n    assert 1 + 1 == 2\n")
            s = Serveur()
            try:
                texte = s.appeler_outil("analyse_banc", {"path": td})
                data = json.loads(texte)
                assert data.get("total", -1) >= 1
                assert "passed" in data
            finally:
                s.fermer()

    def test_refactor_repond_avec_modifications(self):
        with tempfile.TemporaryDirectory() as td:
            fiche = os.path.join(td, "source.txt")
            with open(fiche, "w") as f:
                f.write("Bonjour le monde.\n")
            cible = os.path.join(td, "source.txt")
            s = Serveur()
            try:
                texte = s.appeler_outil("refactor", {
                    "glob": cible,
                    "target": "monde",
                    "replace": "univers",
                    "dry_run": True,
                })
                data = json.loads(texte)
                assert data.get("total_replacements", 0) == 1
                assert data.get("files_modified", 0) == 1
            finally:
                s.fermer()

    def test_apprendre_savoir_repond_en_bac_a_sable(self):
        with tempfile.TemporaryDirectory() as bac:
            shutil.copy(os.path.join(REPO, "registre_exemple.json"),
                        os.path.join(bac, "registre_connaissances.json"))
            s = Serveur(env={"HAICHI_SAVOIR_DIR": bac})
            try:
                texte = s.appeler_outil("apprendre_savoir", {
                    "question": "Quelle est la capitale du Zimbabwe ?",
                    "reponse": "Harare est la capitale du Zimbabwe.",
                    "source": "ministere des affaires etrangeres",
                    "date": "2026-09-22",
                })
                data = json.loads(texte)
                assert data.get("verdict") == "valide"
            finally:
                s.fermer()

    def test_apprendre_savoir_refuse_sans_source(self):
        with tempfile.TemporaryDirectory() as bac:
            shutil.copy(os.path.join(REPO, "registre_exemple.json"),
                        os.path.join(bac, "registre_connaissances.json"))
            s = Serveur(env={"HAICHI_SAVOIR_DIR": bac})
            try:
                texte = s.appeler_outil("apprendre_savoir", {
                    "question": "Quelle est la capitale du Zimbabwe ?",
                    "reponse": "Harare est la capitale du Zimbabwe.",
                    "source": "sans source",
                    "date": "2026-09-22",
                })
                data = json.loads(texte)
                assert data.get("verdict") == "refuse"
            finally:
                s.fermer()


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))