#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests du module MCP apprendre (skills/mcp_learn.py) — les deux garanties.

1. une fiche NON sourcée est bloquée (verdict refuse, rien dans le registre) ;
2. une fiche sourcéee et datée passe (verdict valide, registre mis à jour).
Bac à sable : HAICHI_SAVOIR_DIR pointe vers un dossier jetable.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import pytest

from skills.mcp_learn import apprendre


@pytest.fixture()
def bac():
    dossier = tempfile.mkdtemp(prefix="mcp-learn-bac-")
    shutil.copy(os.path.join(REPO, "registre_exemple.json"),
                os.path.join(dossier, "registre_connaissances.json"))
    os.environ["HAICHI_SAVOIR_DIR"] = dossier
    yield dossier
    os.environ.pop("HAICHI_SAVOIR_DIR", None)
    shutil.rmtree(dossier, ignore_errors=True)


def _resumes(bac):
    return json.load(open(os.path.join(bac, "registre_connaissances.json"),
                          encoding="utf-8"))


class TestGaranties:
    def test_fiche_non_sourcee_bloquee(self, bac):
        r = apprendre("Quelle est la capitale du Zimbabwe ?",
                      "Harare", "sans source", "2026-09-22")
        assert r["verdict"] == "refuse"
        registre = _resumes(bac)
        assert not any("harare" in str(v.get("answer", "")).lower() or
                       "zimbabwe" in " ".join(v.get("mots", [])).lower()
                       for v in registre.values())

    def test_fiche_sourcee_datee_passe(self, bac):
        r = apprendre("Quelle est la capitale du Zimbabwe ?",
                      "Harare est la capitale du Zimbabwe.",
                      "ministere des affaires etrangeres", "2026-09-22")
        assert r["verdict"] == "valide"
        assert 0.0 <= r["confiance"] <= 1.0
        registre = _resumes(bac)
        assert any("Harare" in str(v.get("answer", ""))
                   for v in registre.values())

    def test_fiche_source_non_datee_bloquee(self, bac):
        r = apprendre("Quelle est la capitale du Zimbabwe ?",
                      "Harare est la capitale du Zimbabwe.",
                      "ministere des affaires etrangeres", "")
        assert r["verdict"] == "refuse"


if __name__ == "__main__":
    sys.exit(pytest.main(["-q", __file__]))