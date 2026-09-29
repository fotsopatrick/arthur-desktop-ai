#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LES CERVEAUX INTERCHANGEABLES (29/09/2026) — fournisseurs.py.

Ce qu'on prouve, SANS reseau et SANS depenser un centime (faux serveurs sur
cette machine, faux client Claude) :
  - un cerveau se declare dans reglages-maison.json et se choisit par son nom ;
  - payant ou gratuit : dans le doute, payant ;
  - un cerveau payant ne part JAMAIS sans l'interrupteur de budget_nebius ;
  - la depense d'un cerveau payant est notee dans le carnet commun ;
  - les pannes (402, reponse vide, cle absente) sont dites en clair ;
  - Claude passe par le SDK officiel, avec effort et repli cote serveur ;
  - le moteur, le graphe et arthur_cerveau savent s'en servir, et
    redescendent a Qwen quand le cerveau choisi se tait.
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import budget_nebius  # noqa: E402
import fournisseurs  # noqa: E402


class _Faux(BaseHTTPRequestHandler):
    reponse = {"choices": [{"message": {"content": "Yaounde."}, "finish_reason": "stop"}],
               "usage": {"total_tokens": 42}}
    code = 200
    recus = []

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


@pytest.fixture
def serveur():
    _Faux.code, _Faux.recus = 200, []
    _Faux.reponse = {"choices": [{"message": {"content": "Yaounde."}, "finish_reason": "stop"}],
                     "usage": {"total_tokens": 42}}
    s = HTTPServer(("127.0.0.1", 0), _Faux)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d/v1/chat/completions" % s.server_address[1]
    s.shutdown()


@pytest.fixture
def maison(tmp_path, monkeypatch, serveur):
    """Un reglages-maison.json de bac a sable, un carnet de depenses jetable,
    et l'interrupteur FERME (comme par defaut)."""
    reglages = {
        "cerveaux": {
            "gratuit": {"type": "openai", "url": serveur, "modele": "m-local"},
            "payant": {"type": "openai", "url": serveur, "modele": "m-payant",
                       "cle_env": "FAUSSE_CLE", "payant": True},
            "distant": {"type": "openai", "url": "https://exemple.invalid/v1", "modele": "x"},
            "claude": {"type": "anthropic", "modele": "claude-opus-5-5", "cle_env": "FAUSSE_CLE"},
            "bizarre": {"type": "telepathie"},
        },
        "cerveau_repli": ["qwen"],
    }
    chemin = tmp_path / "reglages-maison.json"
    chemin.write_text(json.dumps(reglages))
    monkeypatch.setenv("ARTHUR_REGLAGES", str(chemin))
    monkeypatch.setenv("BUDGET_NEBIUS_DOSSIER", str(tmp_path / "carnet"))
    monkeypatch.setenv("FAUSSE_CLE", "cle-de-test")
    monkeypatch.setattr(budget_nebius, "REGLAGE", str(tmp_path / "budget.json"))
    return tmp_path


def _ouvrir_le_porte_monnaie(maison):
    (maison / "budget.json").write_text(json.dumps(
        {"paiement_autorise": 1, "euros_par_million": 1.0, "euros_max": 5}))


# ── la liste ─────────────────────────────────────────────────────────────────
def test_les_cerveaux_declares_s_ajoutent_aux_trois_de_base(maison):
    tous = fournisseurs.cerveaux()
    for nom in ("qwen", "local", "nebius", "gratuit", "payant", "claude"):
        assert nom in tous
    assert "bizarre" not in tous              # type inconnu : ignore


def test_dans_le_doute_c_est_payant(maison):
    tous = fournisseurs.cerveaux()
    assert fournisseurs.est_payant(tous["payant"])
    assert fournisseurs.est_payant(tous["distant"])      # adresse hors de la machine
    assert fournisseurs.est_payant(tous["claude"])
    assert not fournisseurs.est_payant(tous["gratuit"])   # 127.0.0.1


def test_ordre_le_choisi_puis_le_repli(maison):
    assert fournisseurs.ordre("gratuit") == ["gratuit", "qwen"]
    assert fournisseurs.ordre("inconnu") == ["qwen"]


# ── l'argent ─────────────────────────────────────────────────────────────────
def test_payant_interrupteur_ferme_rien_ne_part(maison):
    d = fournisseurs.demander("payant", "capitale du Cameroun ?")
    assert d["reponse"] is None and "coupe" in d["panne"]
    assert _Faux.recus == []


def test_payant_interrupteur_ouvert_part_et_se_note(maison):
    _ouvrir_le_porte_monnaie(maison)
    d = fournisseurs.demander("payant", "capitale du Cameroun ?")
    assert d["reponse"] == "Yaounde."
    auth, corps = _Faux.recus[0]
    assert auth == "Bearer cle-de-test" and corps["model"] == "m-payant"
    assert budget_nebius.etat()["total"] == 42


def test_gratuit_part_sans_interrupteur_et_ne_coute_rien(maison):
    d = fournisseurs.demander("gratuit", "capitale du Cameroun ?")
    assert d["reponse"] == "Yaounde."
    assert budget_nebius.etat()["total"] == 0


def test_les_extraits_vont_dans_la_consigne(maison):
    fournisseurs.demander("gratuit", "retention ?", extraits="[odoo.md] 14 jours")
    systeme = _Faux.recus[0][1]["messages"][0]["content"]
    assert "odoo.md" in systeme and "14 jours" in systeme


# ── les pannes, dites en clair ───────────────────────────────────────────────
def test_402_plus_de_credit(maison):
    _Faux.code = 402
    d = fournisseurs.demander("gratuit", "?")
    assert d["reponse"] is None and "credit" in d["panne"]


def test_reflexion_trop_longue_pas_de_brouillon(maison):
    _Faux.reponse = {"choices": [{"message": {"content": None, "reasoning_content": "brouillon"},
                                  "finish_reason": "length"}]}
    d = fournisseurs.demander("gratuit", "?")
    assert d["reponse"] is None and "place" in d["panne"]


def test_cle_absente(maison, monkeypatch):
    _ouvrir_le_porte_monnaie(maison)
    monkeypatch.delenv("FAUSSE_CLE")
    d = fournisseurs.demander("payant", "?")
    assert d["reponse"] is None and "FAUSSE_CLE" in d["panne"]
    assert _Faux.recus == []


# ── Claude, par le SDK officiel ──────────────────────────────────────────────
class _FauxClaude:
    appels = []
    stop = "end_turn"

    def __init__(self, **kw):
        self.kw = kw
        outer = self

        class _M:
            def create(self_inner, **params):
                _FauxClaude.appels.append(params)

                class _B:
                    type, text = "text", "Yaounde."

                class _U:
                    input_tokens, output_tokens = 10, 5

                class _R:
                    content, stop_reason, usage = [_B()], _FauxClaude.stop, _U()
                return _R()

        class _Beta:
            messages = _M()
        self.beta = _Beta()
        self.messages = _M()


def test_claude_par_le_sdk_avec_effort_et_repli(maison, monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    _ouvrir_le_porte_monnaie(maison)
    _FauxClaude.appels, _FauxClaude.stop = [], "end_turn"
    monkeypatch.setattr(anthropic, "Anthropic", _FauxClaude)
    d = fournisseurs.demander("claude", "capitale du Cameroun ?")
    assert d["reponse"] == "Yaounde."
    p = _FauxClaude.appels[0]
    assert p["model"] == "claude-opus-5-5"
    assert p["fallbacks"] == "default" and "server-side-fallback-2026-07-01" in p["betas"]
    assert p["output_config"]["effort"] == "low"
    assert budget_nebius.etat()["total"] == 15


def test_claude_qui_decline_est_une_panne(maison, monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    _ouvrir_le_porte_monnaie(maison)
    _FauxClaude.stop = "refusal"
    monkeypatch.setattr(anthropic, "Anthropic", _FauxClaude)
    d = fournisseurs.demander("claude", "?")
    assert d["reponse"] is None and "decline" in d["panne"]


def test_claude_interrupteur_ferme(maison, monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    _FauxClaude.appels = []
    monkeypatch.setattr(anthropic, "Anthropic", _FauxClaude)
    d = fournisseurs.demander("claude", "?")
    assert d["reponse"] is None and _FauxClaude.appels == []


# ── le moteur, le graphe, arthur_cerveau ─────────────────────────────────────
@pytest.fixture
def moteur(maison, monkeypatch):
    import nano_moteur_ultra as NM
    monkeypatch.setattr(NM, "LACUNES_PATH", str(maison / "lacunes.json"))
    monkeypatch.setattr(NM, "RAG_MAISON", None)
    return NM


def test_moteur_repond_avec_le_cerveau_choisi(moteur):
    e = moteur.NanoMoteurUltraEngine()
    r = e.repondre("quelle est la capitale du Cameroun ?", choisir="gratuit")
    assert r["source"] == "gratuit" and r["answer"] == "Yaounde."


def test_moteur_cerveau_muet_redescend_a_qwen(moteur, monkeypatch):
    e = moteur.NanoMoteurUltraEngine()
    monkeypatch.setattr(e, "demander_a_alice", lambda q, x=None: ("Yaounde (Qwen).", None))
    r = e.repondre("quelle est la capitale du Cameroun ?", choisir="payant")  # interrupteur ferme
    assert r["source"] == "alice" and "Qwen" in r["answer"]
    assert "coupe" in r["thought"]


def test_graphe_avec_le_cerveau_choisi(moteur):
    import arthur_graphe as G
    G._GRAPHE = G.construire(False)
    r = G.repondre("quelle est la capitale du Cameroun ?", choix="gratuit")
    assert r["source"] == "gratuit" and r["etapes"][-1] == "gros_cerveau : gratuit"


def test_arthur_cerveau_connait_les_cerveaux_declares(maison):
    import arthur_cerveau
    ok, texte = arthur_cerveau.choisir("gratuit")
    assert ok, texte
    assert json.load(open(os.environ["ARTHUR_REGLAGES"]))["cerveau_gros"] == "gratuit"
    assert "gratuit" in arthur_cerveau.etat()
    assert not arthur_cerveau.choisir("inconnu")[0]
