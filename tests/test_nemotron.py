#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'ETAGE NEMOTRON — nemotron_nebius.py.

Ce qu'on prouve, SANS reseau et SANS depenser un centime (un faux Nebius sur
cette machine, un carnet de depenses jetable, un HOME jetable) :
  - la clef se cherche dans l'appel, puis NEBIUS_API_KEY, puis le coffre ;
  - sans clef, rien ne part, et Arthur le dit ;
  - l'interrupteur de budget_nebius coupe tout appel « vrai Nebius » ;
  - 402 = plus de credit, dit en clair ; une autre erreur HTTP aussi ;
  - une reponse vide ne rend JAMAIS la reflexion (reasoning_content) ;
  - chat() (les agents du jeu) obeit aux memes regles.
"""
import json
import os
import runpy
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import budget_nebius  # noqa: E402
import nemotron_nebius as N  # noqa: E402


class _Faux(BaseHTTPRequestHandler):
    reponse, code, recus = {}, 200, []

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        _Faux.recus.append((self.headers.get("Authorization"), json.loads(self.rfile.read(n))))
        corps = json.dumps(_Faux.reponse).encode()
        self.send_response(_Faux.code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *a):
        pass


def _repond(texte, fin="stop", **message):
    _Faux.reponse = {"choices": [{"message": dict(content=texte, **message),
                                  "finish_reason": fin}],
                     "usage": {"total_tokens": 50}}


@pytest.fixture
def nebius(tmp_path, monkeypatch):
    """Un faux Nebius, un coffre vide, un carnet jetable, l'interrupteur ferme."""
    _Faux.code, _Faux.recus = 200, []
    _repond("Yaounde.")
    s = HTTPServer(("127.0.0.1", 0), _Faux)
    threading.Thread(target=s.serve_forever, args=(0.05,), daemon=True).start()
    monkeypatch.setattr(N, "ADRESSE", "http://127.0.0.1:%d/v1/chat/completions" % s.server_address[1])
    monkeypatch.setattr(N, "COFFRE", str(tmp_path / "coffre.txt"))
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("BUDGET_NEBIUS_DOSSIER", str(tmp_path / "carnet"))
    monkeypatch.setattr(budget_nebius, "REGLAGE", str(tmp_path / "budget.json"))
    yield tmp_path
    s.shutdown()
    s.server_close()


def _ouvrir(tmp):
    (tmp / "budget.json").write_text(json.dumps(
        {"paiement_autorise": 1, "euros_par_million": 1.0, "euros_max": 5}))


# ── la clef ──────────────────────────────────────────────────────────────────
def test_clef_dans_l_ordre(nebius, monkeypatch):
    assert N.cle_du_moment() == "" and not N.est_pret()
    (nebius / "coffre.txt").write_text("  du-coffre \n")
    assert N.cle_du_moment() == "du-coffre" and N.est_pret()
    monkeypatch.setenv("NEBIUS_API_KEY", " de-l-env ")
    assert N.cle_du_moment() == "de-l-env"
    assert N.cle_du_moment(" tendue ") == "tendue"


def test_sans_clef_rien_ne_part(nebius):
    d = N.demander("capitale du Cameroun ?")
    assert d["reponse"] is None and "cle de Nebius" in d["panne"]
    assert _Faux.recus == []


def test_essai_ne_part_pas(nebius):
    d = N.demander("?", cle="x", essai=True)
    assert d["essai"] and d["reponse"] is None and d["panne"] is None
    assert _Faux.recus == []


# ── un faux Nebius (ne coute rien) ──────────────────────────────────────────
def test_faux_nebius_repond_sans_rien_noter(nebius):
    d = N.demander("capitale du Cameroun ?", cle="cle-test")
    assert d["reponse"] == "Yaounde." and d["panne"] is None and not d["avoue"]
    auth, corps = _Faux.recus[0]
    assert auth == "Bearer cle-test" and corps["model"] == N.MODELE
    assert corps["max_tokens"] <= budget_nebius.reglages()["jetons_max_par_appel"]
    assert budget_nebius.etat()["total"] == 0          # pas de fausse depense
    journal = (nebius / "livrables" / "arthur_dialogues.log").read_text()
    assert "capitale du Cameroun" in journal and "Yaounde." in journal


def test_l_aveu_est_reconnu(nebius):
    _repond("Je ne suis pas sûr de ça.")
    assert N.demander("?", cle="x")["avoue"] is True


def test_journal_impossible_n_empeche_pas_la_reponse(nebius):
    (nebius / "livrables").write_text("un fichier, pas un dossier")
    d = N.demander("?", cle="x")
    assert d["reponse"] == "Yaounde."


def test_reflexion_trop_longue_jamais_le_brouillon(nebius):
    _repond(None, fin="length", reasoning_content="mon brouillon secret")
    d = N.demander("?", cle="x")
    assert d["reponse"] is None and "place" in d["panne"]
    assert "brouillon secret" not in json.dumps(d)


def test_reponse_vide_pour_une_autre_raison(nebius):
    _repond("   ", fin="content_filter")
    d = N.demander("?", cle="x")
    assert d["reponse"] is None and "content_filter" in d["panne"]


def test_402_plus_de_credit(nebius):
    _Faux.code = 402
    d = N.demander("?", cle="x")
    assert d["credit_epuise"] is True and "crédit" in d["panne"]


def test_autre_erreur_http(nebius):
    _Faux.code = 500
    d = N.demander("?", cle="x")
    assert d["panne"].endswith("HTTP 500") and not d.get("credit_epuise")


def test_reponse_illisible(nebius):
    _Faux.reponse = {"rien": "du tout"}
    d = N.demander("?", cle="x")
    assert d["reponse"] is None and d["panne"].startswith("Le gros cerveau n'a pas repondu")


def test_serveur_injoignable(nebius, monkeypatch):
    monkeypatch.setattr(N, "ADRESSE", "http://127.0.0.1:1/v1")
    d = N.demander("?", cle="x", patience=2)
    assert d["reponse"] is None and "n'a pas repondu" in d["panne"]


# ── le vrai Nebius : l'argent ────────────────────────────────────────────────
def test_vrai_nebius_seulement_pour_nebius_com(monkeypatch):
    monkeypatch.setattr(N, "ADRESSE", "https://api.studio.nebius.com/v1/chat/completions")
    assert N._vrai_nebius()
    monkeypatch.setattr(N, "ADRESSE", "http://127.0.0.1:9/v1")
    assert not N._vrai_nebius()


def test_vrai_nebius_interrupteur_ferme_rien_ne_part(nebius, monkeypatch):
    monkeypatch.setattr(N, "_vrai_nebius", lambda: True)
    d = N.demander("?", cle="x")
    assert d["plafond"] is True and "coupe" in d["panne"]
    assert _Faux.recus == []


def test_vrai_nebius_ouvert_la_depense_est_notee(nebius, monkeypatch):
    monkeypatch.setattr(N, "_vrai_nebius", lambda: True)
    _ouvrir(nebius)
    d = N.demander("?", cle="x")
    assert d["reponse"] == "Yaounde."
    assert budget_nebius.etat()["total"] == 50


def test_plafond_du_jour_meme_pour_un_faux(nebius):
    (nebius / "budget.json").write_text(json.dumps({"jetons_par_jour": 10}))
    d = N.demander("?", cle="x")
    assert d["plafond"] and "jour" in d["panne"] and _Faux.recus == []


# ── chat : les agents du jeu ─────────────────────────────────────────────────
MESSAGES = [{"role": "system", "content": "tu es un agent"},
            {"role": "user", "content": "bonjour"}]


def test_chat_sans_clef(nebius):
    assert N.chat(MESSAGES) == {"reponse": None, "panne": "cle Nebius absente"}


def test_chat_faux_nebius(nebius, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "k")
    r = N.chat(MESSAGES, max_tokens=50, temperature=0.1)
    assert r == {"reponse": "Yaounde.", "panne": None}
    corps = _Faux.recus[0][1]
    assert corps["messages"] == MESSAGES and corps["max_tokens"] == 50
    assert corps["temperature"] == 0.1


def test_chat_reponse_vide(nebius, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "k")
    _repond(None, fin="length")
    assert N.chat(MESSAGES) == {"reponse": None, "panne": "reponse vide (trop de reflexion)"}


def test_chat_erreur_http(nebius, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "k")
    _Faux.code = 402
    r = N.chat(MESSAGES)
    assert r["reponse"] is None and "402" in r["panne"]


def test_chat_vrai_nebius_ferme(nebius, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "k")
    monkeypatch.setattr(N, "_vrai_nebius", lambda: True)
    r = N.chat(MESSAGES)
    assert r["reponse"] is None and "coupe" in r["panne"] and _Faux.recus == []


def test_chat_vrai_nebius_ouvert_note(nebius, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "k")
    monkeypatch.setattr(N, "_vrai_nebius", lambda: True)
    _ouvrir(nebius)
    assert N.chat(MESSAGES)["reponse"] == "Yaounde."
    assert budget_nebius.etat()["total"] == 50


def test_lancement_direct_sans_clef(nebius, capsys):
    """« python3 nemotron_nebius.py » sans clef : il le dit, rien ne part."""
    runpy.run_path(os.path.join(REPO, "nemotron_nebius.py"), run_name="__main__")
    sortie = capsys.readouterr().out
    assert "ABSENTE" in sortie and "cle de Nebius" in sortie
