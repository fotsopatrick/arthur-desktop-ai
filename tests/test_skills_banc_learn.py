#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP ANALYSE BANC et MCP APPRENDRE — les chemins que le banc ne voyait pas.

Ce qu'on prouve, SANS reseau et sans toucher au vrai savoir :
  - analyse_banc lit un vrai petit banc jetable (repli JUnit) ;
  - le rapport JSON de pytest-json-report est lu, resume, et un rapport
    corrompu est REMONTE (jamais cache derriere le repli) ;
  - pytest absent, pytest trop long, XML absent ou illisible : un JSON
    propre, jamais une trace Python ;
  - main() rend 0 / 1 / 2 selon le verdict ;
  - mcp_learn : chargement rate, mur qui tombe, quarantaine illisible,
    et la ligne de commande (aide, arguments manquants, valide, refus).
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import types

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from skills import mcp_analyse_banc as banc  # noqa: E402
from skills import mcp_learn  # noqa: E402

_VRAI_UNLINK = os.unlink


# ══════════════════════════════════════════════════════════════════════════
# outils : un faux subprocess.run qui joue le role de pytest
# ══════════════════════════════════════════════════════════════════════════

def _apres(cmd, option):
    return cmd[cmd.index(option) + 1] if option in cmd else None


class FauxPytest:
    """Remplace subprocess.run : ecrit ce qu'on lui dit dans le rapport
    demande (JSON ou XML), ou leve l'exception choisie."""

    def __init__(self, json_contenu=None, xml_contenu=None, lever_json=None,
                 lever_xml=None, effacer_json=False, effacer_xml=False):
        self.json_contenu = json_contenu
        self.xml_contenu = xml_contenu
        self.lever_json = lever_json
        self.lever_xml = lever_xml
        self.effacer_json = effacer_json
        self.effacer_xml = effacer_xml
        self.commandes = []
        self.fichiers = []

    def __call__(self, cmd, **kw):
        self.commandes.append(list(cmd))
        chemin_json = _apres(cmd, "--json-report-file")
        chemin_xml = _apres(cmd, "--junitxml")
        for c in (chemin_json, chemin_xml):
            if c:
                self.fichiers.append(c)
        if chemin_json:
            if self.lever_json:
                raise self.lever_json
            if self.effacer_json:
                _VRAI_UNLINK(chemin_json)
            elif self.json_contenu is not None:
                with open(chemin_json, "w", encoding="utf-8") as f:
                    f.write(self.json_contenu)
        if chemin_xml:
            if self.lever_xml:
                raise self.lever_xml
            if self.effacer_xml:
                _VRAI_UNLINK(chemin_xml)
            elif self.xml_contenu is not None:
                with open(chemin_xml, "w", encoding="utf-8") as f:
                    f.write(self.xml_contenu)
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boum")

    def nettoyer(self):
        for c in self.fichiers:
            try:
                _VRAI_UNLINK(c)
            except OSError:
                pass


@pytest.fixture
def faux(monkeypatch):
    crees = []

    def fabriquer(**kw):
        f = FauxPytest(**kw)
        monkeypatch.setattr(banc.subprocess, "run", f)
        crees.append(f)
        return f
    yield fabriquer
    for f in crees:
        f.nettoyer()


RAPPORT_JSON = {
    "summary": {"total": 3, "passed": 1, "failed": 1, "error": 1, "duration": 0.12345},
    "tests": [
        {"nodeid": "t/test_a.py::test_ok", "outcome": "passed"},
        {"nodeid": "t/test_a.py::test_ko", "outcome": "failed",
         "call": {"crash": {"path": "t/test_a.py", "lineno": 7,
                            "message": "assert 4 == 5"}}},
        {"nodeid": "t/test_b.py::test_err", "outcome": "error",
         "call": {"longrepr": "ImportError: x" * 50}},
    ],
}

XML_UN_ECHEC = (
    '<?xml version="1.0"?><testsuites><testsuite tests="2" failures="1" '
    'errors="0" time="0.5"><testcase classname="t.test_a" name="test_ok"/>'
    '<testcase classname="t.test_a" name="test_ko"><failure message="assert 1 == 2">'
    'trace</failure></testcase></testsuite></testsuites>')


# ══════════════════════════════════════════════════════════════════════════
# ANALYSE BANC — un vrai banc jetable
# ══════════════════════════════════════════════════════════════════════════

class TestVraiBanc:
    def test_petit_banc_jetable(self, tmp_path):
        """Un vrai pytest sur un dossier jetable : un vert, un rouge nomme."""
        (tmp_path / "test_jetable.py").write_text(
            "def test_vert():\n    assert 1 + 1 == 2\n\n"
            "def test_rouge():\n    assert 2 + 2 == 5, 'calcul faux'\n",
            encoding="utf-8")
        r = banc.run_pytest(str(tmp_path))
        assert (r["total"], r["passed"], r["failed"], r["errors"]) == (2, 1, 1, 0)
        assert [f["test"] for f in r["failures"]] == ["test_rouge"]
        assert "calcul faux" in r["failures"][0]["message"]
        assert r["failures"][0]["file"].endswith(".py")


# ══════════════════════════════════════════════════════════════════════════
# ANALYSE BANC — le rapport JSON (pytest-json-report present)
# ══════════════════════════════════════════════════════════════════════════

class TestRapportJson:
    def test_rapport_json_resume(self, faux):
        """Le rapport JSON est lu et resume : compteurs, echecs, duree arrondie."""
        f = faux(json_contenu=json.dumps(RAPPORT_JSON))
        r = banc.run_pytest("t", "test_a*.py")
        assert (r["total"], r["passed"], r["failed"], r["errors"]) == (3, 1, 1, 1)
        assert r["duration_s"] == 0.123
        ko, err = r["failures"]
        assert ko == {"file": "t/test_a.py", "line": 7, "test": "test_ko",
                      "expected": "", "received": "", "message": "assert 4 == 5"}
        assert err["file"] == "t/test_b.py::test_err" and err["line"] == 0
        assert len(err["message"]) == 300
        # un seul lancement : le repli JUnit n'a pas servi
        assert len(f.commandes) == 1
        # le motif non standard devient un filtre -k
        assert f.commandes[0][f.commandes[0].index("-k") + 1] == "a*"
        assert not os.path.exists(f.fichiers[0])

    def test_rapport_json_corrompu_remonte(self, faux):
        """Un rapport NON vide mais illisible est une vraie panne : on la dit."""
        f = faux(json_contenu="ceci n'est pas du JSON")
        r = banc.run_pytest("t")
        assert r["fatal"] is True
        assert "illisible" in r["error"]
        assert len(f.commandes) == 1

    def test_parse_rapport_absent(self, tmp_path):
        """parse_pytest_json_report ne leve jamais : fichier absent -> fatal."""
        r = banc.parse_pytest_json_report(str(tmp_path / "rien.json"))
        assert r["fatal"] is True

    def test_nettoyage_rate_ne_casse_rien(self, faux, monkeypatch):
        """Un rapport qu'on n'arrive pas a effacer ne change pas le resultat."""
        faux(json_contenu=json.dumps(RAPPORT_JSON))

        def refuse(chemin):
            raise OSError("occupe")
        monkeypatch.setattr(banc.os, "unlink", refuse)
        r = banc.run_pytest("t")
        assert r["total"] == 3

    def test_rapport_vide_nettoyage_rate(self, faux, monkeypatch):
        """Rapport vide (greffon absent) + effacement rate : repli JUnit quand meme."""
        faux(json_contenu="", xml_contenu=XML_UN_ECHEC)
        monkeypatch.setattr(banc.os, "unlink", lambda c: (_ for _ in ()).throw(OSError("x")))
        r = banc.run_pytest("t")
        assert r["total"] == 2 and r["failed"] == 1

    def test_rapport_json_disparu(self, faux):
        """Le fichier JSON a disparu : on passe au repli JUnit."""
        f = faux(effacer_json=True, xml_contenu=XML_UN_ECHEC)
        r = banc.run_pytest("t")
        assert r["failed"] == 1 and len(f.commandes) == 2

    def test_json_timeout(self, faux):
        """pytest trop long : un JSON qui le dit, pas d'exception."""
        faux(lever_json=subprocess.TimeoutExpired("pytest", 120))
        r = banc.run_pytest("t")
        assert r["error_message"] == "pytest timeout (120s)"
        assert r["duration_s"] == 120.0

    @pytest.mark.xfail(strict=True, reason="bug: mcp_analyse_banc.py:74-81 — le motif par "
                       "defaut laisse un '-k' orphelin, qui avale '--json-report'")
    def test_pas_de_k_orphelin(self, faux):
        """Motif par defaut : aucun filtre -k ne doit partir vers pytest."""
        f = faux(json_contenu=json.dumps(RAPPORT_JSON))
        banc.run_pytest("t")
        assert "-k" not in f.commandes[0]


# ══════════════════════════════════════════════════════════════════════════
# ANALYSE BANC — le repli JUnit et ses pannes
# ══════════════════════════════════════════════════════════════════════════

class TestReplisJunit:
    def test_pytest_introuvable(self, faux):
        """pytest introuvable aux deux essais : un JSON clair."""
        faux(lever_json=FileNotFoundError("pytest"), lever_xml=FileNotFoundError("pytest"))
        r = banc.run_pytest("t")
        assert r["error_message"] == "pytest introuvable"
        assert r["total"] == 0

    def test_junit_timeout(self, faux):
        faux(json_contenu="", lever_xml=subprocess.TimeoutExpired("pytest", 120))
        r = banc.run_pytest("t")
        assert r["error_message"] == "pytest timeout (120s)"

    def test_junit_non_cree(self, faux):
        """Le XML n'existe pas : on le dit, avec le debut de stderr."""
        faux(json_contenu="", effacer_xml=True)
        r = banc.run_pytest("t")
        assert r["error_message"] == "junitxml non créé"
        assert r["stderr"] == "boum"

    def test_junit_illisible(self, faux):
        """Un XML vide ne se lit pas : message clair, pas de trace."""
        faux(json_contenu="", xml_contenu="")
        r = banc.run_pytest("t")
        assert r["error_message"].startswith("XML illisible")

    def test_junit_racine_inconnue(self, faux):
        """Une racine sans <testsuite> est lue elle-meme comme la suite."""
        faux(json_contenu="",
             xml_contenu='<rapport tests="4" failures="0" errors="1" time="2.5">'
                         '<testcase classname="a.b" name="t1"><error>plante</error>'
                         '</testcase></rapport>')
        r = banc.run_pytest("t")
        assert (r["total"], r["passed"], r["errors"]) == (4, 3, 1)
        assert r["failures"][0] == {"file": "a/b.py", "line": 0, "test": "t1",
                                    "expected": "", "received": "", "message": "plante"}

    def test_junit_testsuite_racine(self, faux):
        faux(json_contenu="",
             xml_contenu='<testsuite tests="1" failures="0" errors="0" time="0.1">'
                         '<testcase classname="x" name="t"/></testsuite>')
        r = banc.run_pytest("t")
        assert r == {"total": 1, "passed": 1, "failed": 0, "errors": 0,
                     "duration_s": 0.1, "failures": []}


# ══════════════════════════════════════════════════════════════════════════
# ANALYSE BANC — main()
# ══════════════════════════════════════════════════════════════════════════

class TestMainBanc:
    def _main(self, monkeypatch, capsys, argv, resultat=None, lever=None):
        vus = []

        def faux_run(chemin, motif):
            vus.append((chemin, motif))
            if lever:
                raise lever
            return resultat
        monkeypatch.setattr(banc, "run_pytest", faux_run)
        monkeypatch.setattr(sys, "argv", ["mcp_analyse_banc.py"] + argv)
        code = banc.main()
        return code, capsys.readouterr().out, vus

    def test_tout_vert_json(self, monkeypatch, capsys):
        code, out, vus = self._main(monkeypatch, capsys, ["--json", "--path", "x", "--pattern", "test_y.py"],
                                    {"failed": 0, "errors": 0, "total": 2})
        assert code == 0
        assert vus == [("x", "test_y.py")]
        assert json.loads(out) == {"failed": 0, "errors": 0, "total": 2}
        assert "\n  " not in out            # JSON pur, sur une ligne

    def test_rouge_lisible(self, monkeypatch, capsys):
        code, out, _ = self._main(monkeypatch, capsys, [], {"failed": 1, "errors": 0})
        assert code == 1
        assert '\n  "failed": 1' in out     # indente pour un humain

    def test_exception_devient_json(self, monkeypatch, capsys):
        """Regle absolue : zero trace Python rendue a l'agent."""
        code, out, _ = self._main(monkeypatch, capsys, ["--json"], lever=RuntimeError("panne"))
        assert code == 2
        r = json.loads(out)
        assert r["fatal"] is True and "panne" in r["error"]
        assert "Traceback" not in out


# ══════════════════════════════════════════════════════════════════════════
# MCP APPRENDRE
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def bac(tmp_path, monkeypatch):
    shutil.copy(os.path.join(REPO, "registre_exemple.json"),
                str(tmp_path / "registre_connaissances.json"))
    monkeypatch.setenv("HAICHI_SAVOIR_DIR", str(tmp_path))
    return tmp_path


class TestApprendrePannes:
    def test_chargement_rate(self, monkeypatch):
        """Veilleur introuvable : verdict « erreur », jamais une exception."""
        def casse():
            raise ImportError("veilleur absent")
        monkeypatch.setattr(mcp_learn, "_charger_veilleur", casse)
        r = mcp_learn.apprendre("q ?", "r", "s", "2026-09-22")
        assert r["verdict"] == "erreur"
        assert "veilleur absent" in r["raison"]
        assert r["confiance"] is None

    def test_mur_qui_tombe(self, monkeypatch):
        """Le mur plante : verdict « erreur », et stdout est bien rendu."""
        def registre():
            raise RuntimeError("registre en feu")
        faux_garde = types.SimpleNamespace(_charger_registre=registre)
        monkeypatch.setattr(mcp_learn, "_charger_garde", lambda: faux_garde)
        avant = sys.stdout
        r = mcp_learn.apprendre("Capitale du Zimbabwe ?", "Harare", "ministere", "2026-09-22")
        assert sys.stdout is avant
        assert r["verdict"] == "erreur"
        assert "registre en feu" in r["raison"]
        assert r["confiance"] is not None

    def test_quarantaine_illisible(self, monkeypatch, tmp_path):
        """Refus + quarantaine illisible : raison generique, pas de plantage."""
        (tmp_path / "quarantaine.json").write_text("{pas du json", encoding="utf-8")
        faux_garde = types.SimpleNamespace(
            _charger_registre=lambda: ({}, "x"),
            _chemin=lambda nom: str(tmp_path / nom),
            juger=lambda *a: 1)
        monkeypatch.setattr(mcp_learn, "_charger_garde", lambda: faux_garde)
        r = mcp_learn.apprendre("  Question ?  ", "R", "S", "2026-09-22")
        assert r["verdict"] == "refuse"
        assert r["raison"] == "refuse par le mur de confiance"
        assert r["question"] == "Question ?"

    def test_raison_lue_dans_la_quarantaine(self, bac):
        """Le motif du refus vient du mur lui-meme (quarantaine.json)."""
        r = mcp_learn.apprendre("Capitale du Zimbabwe ?", "", "ministere", "2026-09-22")
        assert r["verdict"] == "refuse"
        assert r["raison"] == "fiche sans reponse ou sans mots"

    def test_import_sans_racine_dans_le_chemin(self, monkeypatch):
        """Importe d'ailleurs, le module ajoute la racine du depot a sys.path."""
        propre = [p for p in sys.path if p and os.path.realpath(p) != os.path.realpath(REPO)]
        monkeypatch.setattr(sys, "path", propre)
        spec = importlib.util.spec_from_file_location(
            "mcp_learn_copie", os.path.join(REPO, "skills", "mcp_learn.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert sys.path[0] == mod.RACINE


class TestApprendreLigneDeCommande:
    def test_aide(self, capsys):
        assert mcp_learn.main(["--help"]) == 0
        assert "MCP APPRENDRE" in capsys.readouterr().out

    def test_arguments_manquants(self, capsys):
        assert mcp_learn.main(["--question", "q ?", "--reponse"]) == 2
        r = json.loads(capsys.readouterr().out)
        assert r["verdict"] == "erreur" and "obligatoires" in r["raison"]

    def test_fiche_valide(self, bac, capsys):
        code = mcp_learn.main(["--question", "Quelle est la capitale du Zimbabwe ?",
                               "--reponse", "Harare est la capitale du Zimbabwe.",
                               "--source", "ministere des affaires etrangeres",
                               "--date", "2026-09-22"])
        r = json.loads(capsys.readouterr().out)
        assert code == 0 and r["verdict"] == "valide"
        registre = json.load(open(str(bac / "registre_connaissances.json"), encoding="utf-8"))
        assert any("Harare" in str(v.get("answer")) for v in registre.values())

    def test_fiche_refusee(self, bac, capsys):
        code = mcp_learn.main(["--question", "Quelle est la capitale du Zimbabwe ?",
                               "--reponse", "Harare", "--source", "sans source",
                               "--date", "2026-09-22"])
        r = json.loads(capsys.readouterr().out)
        assert code == 1 and r["verdict"] == "refuse"
        assert r["raison"] == "fiche sans source"


if __name__ == "__main__":
    sys.exit(pytest.main(["-q", __file__]))
