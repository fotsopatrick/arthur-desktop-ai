#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LES PETITS MODULES — jeton, cerveau, plafond Nebius, savoir commun, garde.

Ce qu'on prouve, sans reseau, sans depenser un centime, et sans toucher au
vrai HOME ni au vrai savoir (COCKPIT_ENV, ARTHUR_REGLAGES,
BUDGET_NEBIUS_DOSSIER + budget_nebius.REGLAGE, HAICHI_SAVOIR_DIR jetables) :
  - le jeton du cockpit se lit dans la variable, puis dans le .env ;
  - le cerveau ne s'ecrit jamais par-dessus un reglage abime ;
  - un carnet Nebius abime BLOQUE (on ne depense pas a l'aveugle), et les
    trois plafonds (jour, total, euros) refusent l'appel ;
  - la confiance d'une URL ne regarde que le nom de domaine ;
  - le garde : ses portes, sa quarantaine, et sa ligne de commande.
"""
import importlib.util
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import arthur_cerveau  # noqa: E402
import budget_nebius  # noqa: E402
import fournisseurs  # noqa: E402
import jeton_cockpit  # noqa: E402
import savoir_commun  # noqa: E402
from ecriture_sure import FichierAbime  # noqa: E402


def _charger_garde(nom="garde_savoir_essai"):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(REPO, "garde-savoir.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GARDE = _charger_garde()


# ══════════════════════════════════════════════════════════════════════════
# JETON DU COCKPIT
# ══════════════════════════════════════════════════════════════════════════

class TestJeton:
    def test_variable_d_abord(self, monkeypatch):
        monkeypatch.setenv("COCKPIT_TOKEN", "  abc  ")
        assert jeton_cockpit.jeton() == "abc"
        assert jeton_cockpit.entetes() == {"Content-Type": "application/json",
                                           "X-Cockpit-Token": "abc"}

    def test_fichier_env(self, monkeypatch, tmp_path):
        """Le .env est lu ligne a ligne ; les guillemets sont retires."""
        env = tmp_path / ".env"
        env.write_text("AUTRE=1\n COCKPIT_TOKEN = \"xyz\" \n", encoding="utf-8")
        monkeypatch.delenv("COCKPIT_TOKEN", raising=False)
        monkeypatch.setenv("COCKPIT_ENV", str(env))
        assert jeton_cockpit.jeton() == "xyz"

    def test_sans_jeton(self, monkeypatch, tmp_path):
        """Ni variable ni .env (ou .env sans jeton) : pas d'en-tete."""
        monkeypatch.delenv("COCKPIT_TOKEN", raising=False)
        monkeypatch.setenv("COCKPIT_ENV", str(tmp_path / "absent"))
        assert jeton_cockpit.entetes() == {"Content-Type": "application/json"}
        (tmp_path / "vide.env").write_text("RIEN=1\n", encoding="utf-8")
        monkeypatch.setenv("COCKPIT_ENV", str(tmp_path / "vide.env"))
        assert jeton_cockpit.jeton() == ""


# ══════════════════════════════════════════════════════════════════════════
# LE CERVEAU
# ══════════════════════════════════════════════════════════════════════════

class TestCerveau:
    def test_reglage_abime_jamais_ecrase(self, monkeypatch, tmp_path):
        """Reglage illisible : lire() rend {}, mais choisir() refuse d'ecrire."""
        f = tmp_path / "reglages.json"
        f.write_text("{abime", encoding="utf-8")
        monkeypatch.setenv("ARTHUR_REGLAGES", str(f))
        assert arthur_cerveau.lire() == {}
        assert arthur_cerveau.actuel() == "qwen"
        ok, msg = arthur_cerveau.choisir("local")
        assert ok is False and msg.startswith("Je ne change rien")
        assert f.read_text(encoding="utf-8") == "{abime"

    def test_reglage_pas_un_objet(self, monkeypatch, tmp_path):
        f = tmp_path / "reglages.json"
        f.write_text("[1, 2]", encoding="utf-8")
        monkeypatch.setenv("ARTHUR_REGLAGES", str(f))
        ok, msg = arthur_cerveau.choisir("nebius")
        assert ok is False and "n'est pas un objet JSON" in msg
        assert f.read_text(encoding="utf-8") == "[1, 2]"

    def test_fournisseurs_en_panne(self, monkeypatch, tmp_path):
        """Si les cerveaux declares ne se lisent pas, les trois de base restent."""
        def boum():
            raise RuntimeError("fournisseurs casse")
        monkeypatch.setenv("ARTHUR_REGLAGES", str(tmp_path / "absent.json"))
        monkeypatch.setattr(fournisseurs, "cerveaux", boum)
        assert arthur_cerveau.choix_possibles() == arthur_cerveau.CHOIX_DE_BASE


# ══════════════════════════════════════════════════════════════════════════
# LE PLAFOND NEBIUS
# ══════════════════════════════════════════════════════════════════════════

JOUR = "2026-09-30"
OUVERT = {"paiement_autorise": 1, "euros_par_million": 1.0, "euros_max": 10.0}


@pytest.fixture
def carnet(tmp_path, monkeypatch):
    d = tmp_path / "carnet"
    monkeypatch.setenv("BUDGET_NEBIUS_DOSSIER", str(d))
    monkeypatch.setattr(budget_nebius, "REGLAGE", str(tmp_path / "budget-nebius.json"))
    budget_nebius._dossier()
    return d


class TestBudget:
    def test_carnet_du_jour_abime(self, carnet):
        (carnet / (JOUR + ".json")).write_text("[1]", encoding="utf-8")
        permis, raison, reste = budget_nebius.autoriser(10, jour=JOUR)
        assert permis is False and reste == 0
        assert "carnet des depenses Nebius est abime (AttributeError)" in raison

    def test_ancien_carnet_abime_bloque_le_total(self, carnet):
        """Sans total.json, un vieux carnet abime bloque tout."""
        (carnet / "2026-09-01.json").write_text("{", encoding="utf-8")
        (carnet / "notes.txt").write_text("ignore", encoding="utf-8")
        permis, raison, _ = budget_nebius.autoriser(10, jour=JOUR)
        assert permis is False and "abime (JSONDecodeError)" in raison

    def test_total_abime(self, carnet):
        (carnet / "total.json").write_text('{"jetons": "beaucoup"}', encoding="utf-8")
        permis, raison, _ = budget_nebius.autoriser(10, jour=JOUR)
        assert permis is False and "compteur total Nebius est abime (ValueError)" in raison
        assert budget_nebius.etat(JOUR)["erreur"].startswith("le compteur total")

    def test_plafond_total(self, carnet):
        (carnet / "total.json").write_text('{"jetons": 2999990}', encoding="utf-8")
        permis, raison, _ = budget_nebius.autoriser(100, jour=JOUR)
        assert permis is False and raison.startswith("Plafond TOTAL Nebius atteint (2999990")

    def test_plafond_euros(self, carnet):
        (carnet / "total.json").write_text('{"jetons": 9990000}', encoding="utf-8")
        r = dict(OUVERT, jetons_total_max=10 ** 8)
        permis, raison, _ = budget_nebius.autoriser(20000, reglages=r, jour=JOUR)
        assert permis is False and "Plafond en euros atteint (environ 9.99 EUR sur 10.0)" in raison

    def test_plafond_du_jour(self, carnet):
        (carnet / (JOUR + ".json")).write_text('{"jetons": 99990}', encoding="utf-8")
        (carnet / "total.json").write_text('{"jetons": 99990}', encoding="utf-8")
        permis, raison, reste = budget_nebius.autoriser(100, jour=JOUR)
        assert permis is False and reste == 10
        assert raison.startswith("Plafond Nebius du jour atteint (99990")

    def test_prix_absent_c_est_non(self, carnet):
        permis, raison = budget_nebius.paiement_autorise({"paiement_autorise": 1, "euros_max": 5})
        assert permis is False and "euros_par_million" in raison
        assert budget_nebius.paiement_autorise(OUVERT) == (True, "")

    def test_noter_sur_carnets_abimes(self, carnet):
        """Carnet du jour abime : la journee est bloquee. Total abime : tout l'est."""
        (carnet / (JOUR + ".json")).write_text("{abime", encoding="utf-8")
        (carnet / "total.json").write_text("{abime", encoding="utf-8")
        assert budget_nebius.noter({"total_tokens": 7}, "nemotron", "essai", jour=JOUR) == 7
        jour = json.loads((carnet / (JOUR + ".json")).read_text(encoding="utf-8"))
        total = json.loads((carnet / "total.json").read_text(encoding="utf-8"))
        assert jour["jetons"] == 10 ** 9 + 7 and jour["abime_avant"] == "{abime"
        assert total["jetons"] == 10 ** 12 + 7 and total["par_qui"] == {"essai": 7}

    def test_noter_ajoute_au_total_existant(self, carnet):
        (carnet / "total.json").write_text('{"jetons": 100, "appels": 2}', encoding="utf-8")
        budget_nebius.noter(None, "nemotron", "uatu", jour=JOUR, estimation=50)
        total = json.loads((carnet / "total.json").read_text(encoding="utf-8"))
        assert (total["jetons"], total["appels"]) == (150, 3)
        jour = json.loads((carnet / (JOUR + ".json")).read_text(encoding="utf-8"))
        assert jour["dernier"]["estime"] is True


# ══════════════════════════════════════════════════════════════════════════
# SAVOIR COMMUN
# ══════════════════════════════════════════════════════════════════════════

class TestSavoirCommun:
    def test_url_seul_le_domaine_compte(self):
        """data.gouv.fr vaut 1.0 ; « /gouv » dans le chemin ne triche pas."""
        assert savoir_commun.confiance_sur("https://www.data.gouv.fr/x", "1990-01-01") == 1.0
        assert savoir_commun.confiance_sur("http://evil.example/gouv", "1990-01-01") == 0.6
        assert savoir_commun.confiance_sur("https://fr.wikipedia.org/wiki/X", "1990-01-01") == 0.8


# ══════════════════════════════════════════════════════════════════════════
# LE GARDE DU SAVOIR
# ══════════════════════════════════════════════════════════════════════════

def _fiche(**kw):
    f = {"mots": ["capitale", "zimbabwe"], "think": "q", "answer": "Harare",
         "source": "ministere des affaires etrangeres", "date_capture": "2026-09-22",
         "_lacune": "capitale zimbabwe"}
    f.update(kw)
    return f


@pytest.fixture
def savoir(tmp_path, monkeypatch):
    monkeypatch.setenv("HAICHI_SAVOIR_DIR", str(tmp_path))
    return tmp_path


def _lire(chemin):
    return json.load(open(str(chemin), encoding="utf-8"))


class TestGarde:
    def test_chemin_par_defaut_le_depot(self, monkeypatch):
        monkeypatch.delenv("HAICHI_SAVOIR_DIR", raising=False)
        assert GARDE._chemin("x.json") == os.path.join(REPO, "x.json")

    def test_registre_absent(self, savoir):
        assert GARDE._charger_registre() == ({}, str(savoir / "registre_connaissances.json"))

    def test_import_sans_racine_dans_le_chemin(self, monkeypatch):
        """Lance d'ailleurs, le garde retrouve savoir_commun a cote de lui."""
        propre = [p for p in sys.path if p and os.path.realpath(p) != os.path.realpath(REPO)]
        monkeypatch.setattr(sys, "path", propre)
        monkeypatch.delitem(sys.modules, "savoir_commun")
        g = _charger_garde("garde_savoir_ailleurs")
        assert g.mots_depuis("Le chat") == ["chat"]
        assert sys.path[0] == REPO

    def test_quarantaine_pas_une_liste(self, savoir):
        (savoir / "quarantaine.json").write_text("{}", encoding="utf-8")
        with pytest.raises(FichierAbime):
            GARDE._ajouter_en_quarantaine([{"x": 1}])

    def test_fiche_vide_refusee_et_retiree_de_l_attente(self, savoir, capsys):
        """Porte 0 : sans reponse, refus ; la fiche quitte l'attente."""
        attente = [_fiche(answer=""), _fiche(_lacune="autre")]
        chemin_attente = str(savoir / "fiches-attente.json")
        code = GARDE.juger(attente[0], {}, (attente, chemin_attente), chemin_attente)
        assert code == 1
        assert [f["_lacune"] for f in _lire(chemin_attente)] == ["autre"]
        assert _lire(savoir / "quarantaine.json")[0]["motif_refus"] == "fiche sans reponse ou sans mots"
        assert "REFUS" in capsys.readouterr().out

    def test_meme_fiche_deux_fois_meme_cle(self, savoir):
        """Une fiche identique a une fiche connue reprend sa cle ; l'attente est videe."""
        registre = {"connue": {"mots": ["zimbabwe", "capitale"], "answer": "Harare", "think": "t"},
                    "meta": "pas une fiche"}
        chemin_attente = str(savoir / "fiches-attente.json")
        code = GARDE.juger(_fiche(), registre, ([_fiche()], chemin_attente), chemin_attente)
        assert code == 0
        r = _lire(savoir / "registre_connaissances.json")
        assert set(r) == {"connue", "meta"}
        assert r["connue"]["source"] == "ministere des affaires etrangeres"
        assert _lire(chemin_attente) == []

    @pytest.mark.xfail(strict=True, reason="bug: garde-savoir.py:112-113 — juger() tolere une "
                       "entree non-objet du registre (ligne 201) mais _valide() fait v.get() "
                       "dessus : AttributeError, la fiche saine n'est jamais ecrite")
    def test_entree_non_objet_avant_la_fiche(self, savoir):
        registre = {"_version": "2", "connue": {"mots": ["autre"], "answer": "x", "think": ""}}
        assert GARDE.juger(_fiche(), registre, None, None) == 0

    def test_cle_deja_prise(self, savoir, monkeypatch):
        """Deux validations dans la meme nanoseconde : pas d'ecrasement."""
        monkeypatch.setattr(GARDE.time, "time_ns", lambda: 42)
        registre = {"apprentissage_42": {"mots": ["autre", "chose"], "answer": "x", "think": ""}}
        GARDE._valide(registre, str(savoir / "r.json"), _fiche(), None, None)
        assert set(registre) == {"apprentissage_42", "apprentissage_42_"}

    def test_petits_juges(self):
        assert GARDE._mots_recoupent([], ["a"]) is False
        assert GARDE._reponses_se_contredisent({"answer": ""}, {"answer": "x"}) is False
        assert GARDE._reponses_se_contredisent({"answer": "Harare"}, {"answer": "harare"}) is False
        assert GARDE._reponses_se_contredisent({"answer": "le a"}, {"answer": "le b"}) is False

    def test_confiance_qui_plante(self, monkeypatch):
        def boum(*a):
            raise ValueError("date folle")
        monkeypatch.setattr(GARDE, "confiance_sur", boum)
        assert GARDE._confiance({"source": "x"}) == 0.5
        assert GARDE._confiance({"source": " "}) == 0.9


class TestGardeLigneDeCommande:
    def test_aide(self, capsys):
        assert GARDE.main(["-h"]) == 0
        assert "GARDE DU SAVOIR" in capsys.readouterr().out

    def test_sans_source(self, savoir, capsys):
        """--sans-source : refus, et la fiche d'essai quitte l'attente."""
        (savoir / "fiches-attente.json").write_text(json.dumps(
            [{"_lacune": "test-sans-source"}, {"_lacune": "garde"}]), encoding="utf-8")
        assert GARDE.main(["--sans-source"]) == 1
        assert _lire(savoir / "fiches-attente.json") == [{"_lacune": "garde"}]
        assert "REFUS : fiche sans source" in capsys.readouterr().out

    def test_attente_illisible_rien_a_juger(self, savoir, capsys):
        (savoir / "fiches-attente.json").write_text("{abime", encoding="utf-8")
        assert GARDE.main([]) == 0
        assert "rien a juger" in capsys.readouterr().out

    def test_premiere_fiche_en_attente(self, savoir):
        (savoir / "fiches-attente.json").write_text(json.dumps([_fiche()]), encoding="utf-8")
        assert GARDE.main([]) == 0
        r = _lire(savoir / "registre_connaissances.json")
        assert [v["answer"] for v in r.values()] == ["Harare"]
        assert _lire(savoir / "fiches-attente.json") == []

    def test_fiche_en_arguments(self, savoir):
        code = GARDE.main(["--question", "Quelle est la capitale du Ghana ?", "--reponse", "Accra",
                           "--source", "ministere", "--date", "2026-09-22"])
        assert code == 0
        r = _lire(savoir / "registre_connaissances.json")
        (fiche,) = r.values()
        assert fiche["answer"] == "Accra" and "ghana" in fiche["mots"]

    def test_fiche_en_arguments_sans_date(self, savoir):
        code = GARDE.main(["--question", "Capitale du Ghana ?", "--reponse", "Accra",
                           "--source", "ministere"])
        assert code == 1
        assert "date de capture" in _lire(savoir / "quarantaine.json")[0]["motif_refus"]


if __name__ == "__main__":
    sys.exit(pytest.main(["-q", __file__]))
