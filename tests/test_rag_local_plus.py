#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE RAG LOCAL — les cas limites de la recherche BM25 sur cette machine.

Ce qu'on prouve, dans des dossiers jetables (ARTHUR_DOCUMENTS, ICI deplace) :
  - le reglage « rag_dossiers » est lu, et un reglage abime est ignore ;
  - un dossier absent, un lien casse, un fichier non UTF-8 ne cassent rien ;
  - le decoupage respecte les paragraphes et coupe les tres longs ;
  - un morceau fait seulement de mots vides n'entre pas dans l'index ;
  - taille() et la ligne de commande (--etat, --json-chercher, aide).
"""
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import rag_local  # noqa: E402


class TestDossiers:
    def test_reglage_rag_dossiers(self, tmp_path, monkeypatch):
        """Sans ARTHUR_DOCUMENTS, la liste du reglage est suivie (~ deplie)."""
        monkeypatch.delenv("ARTHUR_DOCUMENTS", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr(rag_local, "ICI", str(tmp_path))
        (tmp_path / "reglages-maison.json").write_text(
            json.dumps({"rag_dossiers": ["~/notes", "/srv/docs"]}), encoding="utf-8")
        assert rag_local.dossiers() == [str(tmp_path / "notes"), "/srv/docs"]

    @pytest.mark.parametrize("contenu", ["{abime", "[1, 2]", '{"rag_dossiers": []}'])
    def test_reglage_inutilisable(self, tmp_path, monkeypatch, contenu):
        """Reglage abime, pas un objet, ou liste vide : documents/ par defaut."""
        monkeypatch.delenv("ARTHUR_DOCUMENTS", raising=False)
        monkeypatch.setattr(rag_local, "ICI", str(tmp_path))
        (tmp_path / "reglages-maison.json").write_text(contenu, encoding="utf-8")
        assert rag_local.dossiers() == [rag_local.DOSSIER_PAR_DEFAUT]

    def test_variable_prioritaire(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARTHUR_DOCUMENTS", "%s::%s" % (tmp_path / "a", tmp_path / "b"))
        assert rag_local.dossiers() == [str(tmp_path / "a"), str(tmp_path / "b")]


class TestDecoupage:
    def test_paragraphes_regroupes_puis_coupes(self):
        """Deux paragraphes trop gros ensemble : deux morceaux."""
        a, b = "a" * 400, "b" * 400
        assert rag_local._decouper("\n\n\n" + a + "\n\n   \n\n" + b) == [a, b]

    def test_tres_long_paragraphe(self):
        long = "x" * (rag_local.TAILLE_MORCEAU * 2 + 10)
        morceaux = rag_local._decouper(long)
        assert [len(m) for m in morceaux] == [700, 700, 10]
        assert "".join(morceaux) == long


class TestIndex:
    def test_fichiers_difficiles(self, tmp_path):
        """Dossier absent, lien casse, Latin-1, mots vides : l'index tient."""
        d = tmp_path / "docs"
        d.mkdir()
        (d / "bon.md").write_text("Le volcan Kilimandjaro domine la Tanzanie.",
                                  encoding="utf-8")
        (d / "latin.txt").write_bytes("volcan \xe9teint".encode("latin-1"))
        (d / "vide.md").write_text("le la les de du", encoding="utf-8")
        (d / "LISEZ-MOI.md").write_text("volcan volcan volcan", encoding="utf-8")
        (d / "image.png").write_bytes(b"\x89PNG")
        os.symlink(str(d / "disparu.md"), str(d / "casse.md"))
        idx = rag_local.Index([str(tmp_path / "absent"), str(d)])
        assert idx.taille() == {"fichiers": 3, "morceaux": 1}
        r = idx.chercher("Quel volcan domine la Tanzanie ?")
        assert len(r) == 1
        assert r[0]["source"] == str(d / "bon.md")
        assert r[0]["score"] > 0
        # sans mot utile, rien
        assert idx.chercher("le la les") == []

    def test_reindexe_quand_un_fichier_change(self, tmp_path):
        d = tmp_path / "docs"
        d.mkdir()
        f = d / "a.md"
        f.write_text("baobab", encoding="utf-8")
        idx = rag_local.Index([str(d)])
        assert idx.chercher("baobab")
        f.write_text("manguier et papayer", encoding="utf-8")
        os.utime(str(f), ns=(1, 1))
        assert idx.chercher("baobab") == []
        assert idx.chercher("papayer")[0]["texte"] == "manguier et papayer"


class TestLigneDeCommande:
    def _docs(self, tmp_path, monkeypatch):
        d = tmp_path / "docs"
        d.mkdir()
        (d / "savoir.md").write_text("Le fleuve Congo traverse Kinshasa.", encoding="utf-8")
        monkeypatch.setenv("ARTHUR_DOCUMENTS", str(d))
        monkeypatch.setattr(rag_local, "_INDEX", None)
        return d

    def test_etat(self, tmp_path, monkeypatch, capsys):
        d = self._docs(tmp_path, monkeypatch)
        assert rag_local.main(["--etat"]) == 0
        r = json.loads(capsys.readouterr().out)
        assert r == {"dossiers": [str(d)], "fichiers": 1, "morceaux": 1}

    def test_json_chercher(self, tmp_path, monkeypatch, capsys):
        self._docs(tmp_path, monkeypatch)
        assert rag_local.main(["--json-chercher", "fleuve Congo"]) == 0
        r = json.loads(capsys.readouterr().out)
        assert r[0]["texte"] == "Le fleuve Congo traverse Kinshasa."
        # question absente : liste vide, pas d'erreur
        assert rag_local.main(["--json-chercher"]) == 0
        assert json.loads(capsys.readouterr().out) == []

    def test_aide(self, capsys):
        assert rag_local.main([]) == 0
        assert "rag_local.py" in capsys.readouterr().out


if __name__ == "__main__":
    sys.exit(pytest.main(["-q", __file__]))
