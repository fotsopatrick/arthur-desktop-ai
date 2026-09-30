#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LES CERVEAUX INTERCHANGEABLES, SUITE — fournisseurs.py.

Complete tests/test_fournisseurs.py. SANS reseau et SANS depenser un centime :
  - un cerveau inconnu ou interne ne part pas chez un fournisseur ;
  - ollama (sur cette machine) repond, ou dit sa panne ;
  - chaque erreur HTTP (401, 403, 500, injoignable) est dite en clair ;
  - une fiche incomplete, une reponse illisible, une reponse vide : en clair ;
  - Claude : SDK absent, modele sans repli, et chaque erreur du SDK ;
  - la ligne de commande liste les cerveaux et pose une question.
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
    reponse, code, recus, brut = {}, 200, [], None

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        _Faux.recus.append((self.path, json.loads(self.rfile.read(n))))
        corps = _Faux.brut if _Faux.brut is not None else json.dumps(_Faux.reponse).encode()
        self.send_response(_Faux.code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *a):
        pass


@pytest.fixture
def maison(tmp_path, monkeypatch):
    _Faux.code, _Faux.recus, _Faux.brut = 200, [], None
    _Faux.reponse = {"choices": [{"message": {"content": "Yaounde."}, "finish_reason": "stop"}],
                     "usage": {"total_tokens": 42}}
    s = HTTPServer(("127.0.0.1", 0), _Faux)
    threading.Thread(target=s.serve_forever, args=(0.05,), daemon=True).start()
    base = "http://127.0.0.1:%d" % s.server_address[1]
    reglages = {
        "cerveaux": {
            "gratuit": {"type": "openai", "url": base + "/v1/chat/completions", "modele": "m"},
            "sans_url": {"type": "openai", "modele": "m", "payant": False},
            "ollama": {"type": "ollama", "url": base + "/api/chat", "modele": "morgan"},
            "ollama_defaut": {"type": "ollama", "payant": False},
            "claude": {"type": "anthropic", "modele": "claude-opus-5-5", "cle_env": "FAUSSE_CLE"},
            "claude_ancien": {"type": "anthropic", "modele": "claude-ancien", "payant": True,
                              "effort": "high"},
            42: "pas une fiche",
        },
        "cerveau_repli": "pas une liste",
    }
    chemin = tmp_path / "reglages-maison.json"
    chemin.write_text(json.dumps(reglages))
    monkeypatch.setenv("ARTHUR_REGLAGES", str(chemin))
    monkeypatch.setenv("BUDGET_NEBIUS_DOSSIER", str(tmp_path / "carnet"))
    monkeypatch.setenv("FAUSSE_CLE", "cle-de-test")
    monkeypatch.setattr(budget_nebius, "REGLAGE", str(tmp_path / "budget.json"))
    (tmp_path / "budget.json").write_text(json.dumps(
        {"paiement_autorise": 1, "euros_par_million": 1.0, "euros_max": 5}))
    yield tmp_path
    s.shutdown()
    s.server_close()


# ── la liste ─────────────────────────────────────────────────────────────────
def test_reglages_absents_ou_bizarres(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTHUR_REGLAGES", str(tmp_path / "absent.json"))
    assert set(fournisseurs.cerveaux()) == {"qwen", "local", "nebius"}
    (tmp_path / "liste.json").write_text("[1, 2]")
    monkeypatch.setenv("ARTHUR_REGLAGES", str(tmp_path / "liste.json"))
    assert set(fournisseurs.cerveaux()) == {"qwen", "local", "nebius"}
    (tmp_path / "abime.json").write_text("{")
    monkeypatch.setenv("ARTHUR_REGLAGES", str(tmp_path / "abime.json"))
    assert fournisseurs.ordre("qwen") == ["qwen"]


def test_les_cerveaux_de_base_sont_internes(maison):
    assert fournisseurs.est_interne("qwen") and fournisseurs.est_interne("NEBIUS")
    assert not fournisseurs.est_interne("gratuit")
    assert not fournisseurs.est_interne("inconnu")
    assert fournisseurs.fiche(None) is None


def test_repli_qui_n_est_pas_une_liste_redevient_qwen(maison):
    assert fournisseurs.ordre("Gratuit") == ["gratuit", "qwen"]
    assert fournisseurs.ordre("qwen") == ["qwen"]           # sans doublon


def test_local_ou_pas(maison):
    assert fournisseurs._local("http://localhost:8080/x")
    assert fournisseurs._local("http://[::1]:8080/x")
    assert not fournisseurs._local(None)
    assert not fournisseurs.est_payant({"type": "ollama", "url": "http://127.0.0.1:11434"})


# ── ce qui ne part pas ───────────────────────────────────────────────────────
def test_cerveau_inconnu(maison):
    d = fournisseurs.demander("telepathe", "?")
    assert d == {"reponse": None, "panne": "cerveau inconnu : telepathe",
                 "cerveau": "telepathe", "modele": None}


def test_cerveau_interne(maison):
    d = fournisseurs.demander("qwen", "?")
    assert d["reponse"] is None and "interne" in d["panne"]
    assert _Faux.recus == []


def test_fiche_incomplete(maison):
    d = fournisseurs.demander("sans_url", "?")
    assert d["reponse"] is None and "url" in d["panne"]


# ── openai : les pannes en clair ─────────────────────────────────────────────
@pytest.mark.parametrize("code, mot", [(401, "cle refusee (HTTP 401)"),
                                       (403, "cle refusee (HTTP 403)"),
                                       (500, "HTTP 500")])
def test_erreurs_http_en_clair(maison, code, mot):
    _Faux.code = code
    d = fournisseurs.demander("gratuit", "?")
    assert d["reponse"] is None and d["panne"] == mot


def test_injoignable(maison, monkeypatch):
    reglages = json.load(open(os.environ["ARTHUR_REGLAGES"]))
    reglages["cerveaux"]["gratuit"]["url"] = "http://127.0.0.1:1/v1"
    open(os.environ["ARTHUR_REGLAGES"], "w").write(json.dumps(reglages))
    d = fournisseurs.demander("gratuit", "?", patience=2)
    assert d["reponse"] is None and d["panne"].startswith("injoignable")


def test_json_illisible_est_injoignable(maison):
    _Faux.brut = b"<html>pas du json</html>"
    d = fournisseurs.demander("gratuit", "?")
    assert d["panne"].startswith("injoignable")


def test_reponse_sans_choices(maison):
    _Faux.reponse = {"usage": {"total_tokens": 7}}
    d = fournisseurs.demander("gratuit", "?")
    assert d["reponse"] is None and d["panne"] == "reponse illisible"


def test_usage_bizarre_ne_plante_pas(maison):
    _Faux.reponse = {"choices": [{"message": {"content": " ok "}}], "usage": {"total_tokens": "beaucoup"}}
    assert fournisseurs.demander("gratuit", "?")["reponse"] == "ok"
    _Faux.reponse = {"choices": [{"message": {"content": "ok"}}], "usage": ["pas", "un", "dict"]}
    assert fournisseurs.demander("gratuit", "?")["reponse"] == "ok"


def test_reponse_vide_sans_manque_de_place(maison):
    _Faux.reponse = {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]}
    d = fournisseurs.demander("gratuit", "?")
    assert d["reponse"] is None and d["panne"] == "gratuit a rendu une reponse vide"


def test_erreur_imprevue_jamais_de_plantage(maison, monkeypatch):
    def boum(*a, **k):
        raise RuntimeError("imprevu")
    monkeypatch.setattr(fournisseurs, "_openai", boum)
    d = fournisseurs.demander("gratuit", "?")
    assert d["reponse"] is None and d["panne"] == "gratuit en panne : imprevu"

    def muet(*a, **k):
        raise RuntimeError()
    monkeypatch.setattr(fournisseurs, "_openai", muet)
    assert fournisseurs.demander("gratuit", "?")["panne"] == "gratuit en panne : RuntimeError"


# ── ollama, sur cette machine ────────────────────────────────────────────────
def test_ollama_repond_gratuitement(maison):
    _Faux.reponse = {"message": {"content": " Yaounde. "}}
    d = fournisseurs.demander("ollama", "capitale ?", extraits="[x.md] bla")
    assert d["reponse"] == "Yaounde." and d["modele"] == "morgan"
    chemin, corps = _Faux.recus[0]
    assert chemin == "/api/chat" and corps["stream"] is False and corps["model"] == "morgan"
    assert "x.md" in corps["messages"][0]["content"]
    assert budget_nebius.etat()["total"] == 0


def test_ollama_reponse_illisible(maison):
    _Faux.reponse = {"rien": 1}
    d = fournisseurs.demander("ollama", "?")
    assert d["reponse"] is None and d["panne"] == "reponse illisible"


def test_ollama_adresse_par_defaut(maison, monkeypatch):
    vus = []

    def faux_poster(url, charge, entetes, patience):
        vus.append((url, charge["model"]))
        return {"message": {"content": "ok"}}
    monkeypatch.setattr(fournisseurs, "_poster", faux_poster)
    assert fournisseurs.demander("ollama_defaut", "?")["reponse"] == "ok"
    assert vus == [("http://127.0.0.1:11434/api/chat", "morgan")]


# ── Claude, par le SDK officiel ──────────────────────────────────────────────
def _faux_client(anthropic, comportement, appels):
    class _R:
        class usage:
            input_tokens, output_tokens = 3, None
        stop_reason = "end_turn"

        class _B:
            type, text = "text", "Bonjour."

        class _T:
            type, text = "thinking", "brouillon"
        content = [_T(), _B()]

    class _M:
        def create(self, **params):
            appels.append(params)
            if comportement:
                raise comportement
            return _R()

    class Client:
        def __init__(self, **kw):
            appels.append(kw)
            self.messages = _M()

            class _Beta:
                messages = _M()
            self.beta = _Beta()
    return Client


def test_claude_sans_repli_ni_effort_pour_un_autre_modele(maison, monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    appels = []
    monkeypatch.setattr(anthropic, "Anthropic", _faux_client(anthropic, None, appels))
    d = fournisseurs.demander("claude_ancien", "?")
    assert d["reponse"] == "Bonjour."                     # le brouillon n'est pas rendu
    kw, params = appels
    assert kw["api_key"] is None and kw["max_retries"] == 1
    assert "betas" not in params and "output_config" not in params
    assert params["max_tokens"] == 2000                  # plafonne par le budget
    assert budget_nebius.etat()["total"] == 3


def _erreurs(anthropic):
    import httpx
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    def rep(code):
        return httpx.Response(code, request=req)
    return [
        (anthropic.AuthenticationError("non", response=rep(401), body=None), "cle Claude refusee"),
        (anthropic.RateLimitError("trop", response=rep(429), body=None), "trop de demandes"),
        (anthropic.InternalServerError("oups", response=rep(529), body=None), "Claude : HTTP 529"),
        (anthropic.APIConnectionError(request=req), "Claude injoignable"),
    ]


def test_claude_chaque_erreur_du_sdk_en_clair(maison, monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    for erreur, attendu in _erreurs(anthropic):
        appels = []
        monkeypatch.setattr(anthropic, "Anthropic", _faux_client(anthropic, erreur, appels))
        d = fournisseurs.demander("claude", "?")
        assert d["reponse"] is None and attendu in d["panne"], (erreur, d)
    assert budget_nebius.etat()["total"] == 0            # rien de facture


def test_claude_sdk_absent(maison, monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic", None)
    d = fournisseurs.demander("claude", "?")
    assert d["reponse"] is None and "pip install anthropic" in d["panne"]


# ── la ligne de commande ─────────────────────────────────────────────────────
def test_main_liste_les_cerveaux(maison, capsys):
    assert fournisseurs.main([]) == 0
    sortie = capsys.readouterr().out
    assert "qwen" in sortie and "gratuit" in sortie and "payant" in sortie


def test_main_pose_une_question(maison, capsys):
    assert fournisseurs.main(["gratuit", "capitale", "?"]) == 0
    assert "Yaounde." in capsys.readouterr().out
    assert _Faux.recus[-1][1]["messages"][-1]["content"] == "capitale ?"


def test_main_question_par_defaut_et_panne(maison, capsys):
    assert fournisseurs.main(["inconnu"]) == 1
    assert "PANNE : cerveau inconnu" in capsys.readouterr().out


def test_lancement_direct(maison, monkeypatch, capsys):
    """« python3 fournisseurs.py » : la liste, et le code de sortie 0."""
    import runpy
    monkeypatch.setattr(sys, "argv", ["fournisseurs.py"])
    with pytest.raises(SystemExit) as fin:
        runpy.run_path(os.path.join(REPO, "fournisseurs.py"), run_name="__main__")
    assert fin.value.code == 0 and "qwen" in capsys.readouterr().out
