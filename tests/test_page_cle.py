#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA PAGE DE LA CLEF NEBIUS — page_cle_nebius.py.

Ce qu'on prouve, SANS reseau et SANS toucher a la vraie clef (le coffre est
un fichier jetable, Nebius est remplace par un faux) :
  - l'etat du coffre ne montre jamais la clef entiere ;
  - une clef vide, trop courte ou avec un espace est refusee, en clair ;
  - une bonne clef est rangee en droits 600 ;
  - « essayer » dit ce que Nebius a repondu, ou la panne ;
  - la serrure : Host inconnu -> 403 ; ecrire sans Origin/Referer de la page
    elle-meme -> 403 ; la page elle-meme -> accepte.
"""
import http.client
import json
import os
import runpy
import stat
import sys
import threading
from http.server import ThreadingHTTPServer

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import page_cle_nebius as page  # noqa: E402

CLE = "eyJ" + "a" * 37 + "WXYZ"


@pytest.fixture
def coffre(tmp_path, monkeypatch):
    chemin = tmp_path / "secrets" / "cle-nebius.txt"
    monkeypatch.setattr(page, "COFFRE", str(chemin))
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    return chemin


@pytest.fixture
def serveur(coffre):
    s = ThreadingHTTPServer(("127.0.0.1", 0), page.Poste)
    threading.Thread(target=s.serve_forever, args=(0.05,), daemon=True).start()
    yield s.server_address[1]
    s.shutdown()
    s.server_close()


def _appel(port, methode, chemin, corps=None, entetes=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    h = {"Host": "127.0.0.1:%d" % port}
    h.update(entetes or {})
    c.request(methode, chemin, body=corps, headers=h)
    r = c.getresponse()
    donnees = r.read()
    c.close()
    return r.status, r.getheader("Content-Type") or "", donnees


def _poster(port, chemin, corps=b"{}", origine=True, **entetes):
    h = {"Content-Type": "application/json"}
    if origine:
        h["Origin"] = "http://127.0.0.1:%d" % port
    h.update(entetes)
    return _appel(port, "POST", chemin, corps, h)


# ── le coffre ────────────────────────────────────────────────────────────────
def test_coffre_absent(coffre):
    assert page.etat_du_coffre() == {"posee": False, "apercu": "", "longueur": 0}


def test_coffre_vide(coffre):
    coffre.parent.mkdir()
    coffre.write_text("  \n")
    assert page.etat_du_coffre()["posee"] is False


def test_coffre_ne_montre_que_la_fin(coffre):
    coffre.parent.mkdir()
    coffre.write_text(CLE + "\n")
    e = page.etat_du_coffre()
    assert e == {"posee": True, "apercu": "…WXYZ", "longueur": len(CLE)}


@pytest.mark.parametrize("mauvaise, mot", [
    ("", "rien"), (None, "rien"), ("   ", "rien"),
    ("courte", "6 caracteres"),
    ("a" * 20 + " " + "b" * 5, "espace"),
    ("a" * 20 + "\n" + "b" * 5, "espace"),
])
def test_ranger_refuse_en_clair(coffre, mauvaise, mot):
    ok, texte = page.ranger(mauvaise)
    assert not ok and mot in texte
    assert not coffre.exists()


def test_ranger_une_bonne_clef_en_600(coffre):
    ok, texte = page.ranger("  " + CLE + "  ")
    assert ok and "rangee" in texte
    assert coffre.read_text() == CLE + "\n"
    assert stat.S_IMODE(os.stat(coffre).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(coffre.parent).st_mode) == 0o700


# ── essayer ──────────────────────────────────────────────────────────────────
def test_essayer_sans_clef(coffre, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "ancienne")      # ignoree : on teste le coffre
    monkeypatch.setattr(page.nemotron_nebius, "COFFRE", str(coffre))
    r = page.essayer()
    assert r == {"ok": False, "texte": "Aucune clef dans le coffre."}
    assert "NEBIUS_API_KEY" not in os.environ


def test_essayer_panne(coffre, monkeypatch):
    monkeypatch.setattr(page.nemotron_nebius, "est_pret", lambda: True)
    monkeypatch.setattr(page.nemotron_nebius, "demander",
                        lambda q: {"panne": "HTTP 401", "reponse": None})
    assert page.essayer() == {"ok": False, "texte": "HTTP 401"}


def test_essayer_reussi(coffre, monkeypatch):
    questions = []
    monkeypatch.setattr(page.nemotron_nebius, "est_pret", lambda: True)
    monkeypatch.setattr(page.nemotron_nebius, "demander",
                        lambda q: questions.append(q) or
                        {"panne": None, "reponse": "  bonjour \n", "duree_ms": 12.5})
    r = page.essayer()
    assert r["ok"] and "« bonjour »" in r["texte"] and "12.5" in r["texte"]
    assert "bonjour" in questions[0]


# ── la page, par HTTP ────────────────────────────────────────────────────────
def test_get_la_page_et_l_etat(serveur, coffre):
    code, typ, corps = _appel(serveur, "GET", "/")
    assert code == 200 and typ.startswith("text/html")
    assert "La clef de Nebius" in corps.decode("utf-8")
    assert _appel(serveur, "GET", "/index.html")[0] == 200
    code, typ, corps = _appel(serveur, "GET", "/etat")
    assert code == 200 and typ.startswith("application/json")
    assert json.loads(corps)["posee"] is False


def test_get_chemin_inconnu_404(serveur):
    assert _appel(serveur, "GET", "/rien")[0] == 404


def test_host_etranger_403_meme_en_lecture(serveur):
    code, _, _ = _appel(serveur, "GET", "/etat", entetes={"Host": "evil.example:%d" % serveur})
    assert code == 403
    code, _, _ = _appel(serveur, "GET", "/etat", entetes={"Host": "localhost:%d" % serveur})
    assert code == 200


def test_ranger_par_la_page(serveur, coffre):
    code, _, corps = _poster(serveur, "/ranger", json.dumps({"cle": CLE}).encode())
    assert code == 200 and json.loads(corps)["ok"]
    assert coffre.read_text().strip() == CLE
    etat = json.loads(_appel(serveur, "GET", "/etat")[2])
    assert etat["posee"] and CLE not in json.dumps(etat)


def test_ranger_json_illisible(serveur, coffre):
    code, _, corps = _poster(serveur, "/ranger", b"{pas du json")
    assert code == 200
    d = json.loads(corps)
    assert d["ok"] is False and "rien" in d["texte"]


def test_ranger_sans_corps(serveur, coffre):
    code, _, corps = _poster(serveur, "/ranger", None)
    assert json.loads(corps)["ok"] is False


@pytest.mark.parametrize("entetes", [
    {},                                                    # aucune origine
    {"Origin": "http://evil.example"},
    {"Referer": "http://evil.example/p"},
    {"Origin": "null"},                                    # pas de « :// »
    {"Origin": "https://127.0.0.1:{port}"},               # mauvais schema
])
def test_ecrire_sans_la_bonne_origine_403(serveur, coffre, entetes):
    coffre.parent.mkdir()
    coffre.write_text(CLE)
    h = {k: v.format(port=serveur) for k, v in entetes.items()}
    code, _, _ = _poster(serveur, "/effacer", origine=False, **h)
    assert code == 403
    assert coffre.exists()


def test_effacer_avec_referer_de_la_page(serveur, coffre):
    coffre.parent.mkdir()
    coffre.write_text(CLE)
    code, _, corps = _poster(serveur, "/effacer", origine=False,
                             Referer="http://127.0.0.1:%d/" % serveur)
    assert code == 200 and json.loads(corps) == {"ok": True, "texte": "Clef effacee."}
    assert not coffre.exists()
    code, _, corps = _poster(serveur, "/effacer")
    assert json.loads(corps) == {"ok": True, "texte": "Il n'y avait deja rien."}


def test_essayer_par_la_page(serveur, monkeypatch):
    monkeypatch.setattr(page, "essayer", lambda: {"ok": True, "texte": "Nebius a repondu"})
    code, _, corps = _poster(serveur, "/essayer")
    assert code == 200 and json.loads(corps)["ok"]


def test_post_chemin_inconnu_404(serveur):
    assert _poster(serveur, "/rien")[0] == 404


def test_lancement_direct_ecoute_sur_127(monkeypatch, capsys):
    """« python3 page_cle_nebius.py » : 127.0.0.1 et le port 8796, rien d'autre."""
    vus = []

    class FauxServeur:
        def __init__(self, adresse, poste):
            vus.append(adresse)

        def serve_forever(self):
            return None
    monkeypatch.setattr("http.server.ThreadingHTTPServer", FauxServeur)
    runpy.run_path(os.path.join(REPO, "page_cle_nebius.py"), run_name="__main__")
    assert vus == [("127.0.0.1", 8796)]
    assert "http://127.0.0.1:8796" in capsys.readouterr().out
