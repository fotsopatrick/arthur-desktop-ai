#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE SERVEUR MCP D'ARTHUR, DANS LE MEME PROCESSUS — chaque porte du JSON-RPC.

Ce qu'on prouve, sans reseau (faux urlopen) et sans toucher au vrai HOME :
  - chaque requete qui porte un id recoit une reponse, meme l'outil inconnu,
    la methode inconnue ou l'exception ; une notification ne recoit rien ;
  - arthur_parler envoie au cockpit AVEC son jeton ;
  - arthur_lire_dialogues lit la fin du journal, ou dit qu'il n'y a rien ;
  - arthur_cerveau montre puis change le cerveau (reglage jetable) ;
  - apprendre_savoir passe par le mur (savoir jetable).
"""
import io
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import mcp_arthur_server as serveur  # noqa: E402


def _dialoguer(monkeypatch, *requetes):
    """Envoie des lignes au serveur (dict -> JSON, str tel quel) ; rend les reponses."""
    lignes = "".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in requetes)
    sortie, avant = io.StringIO(), sys.stdout
    monkeypatch.setattr(sys, "stdin", io.StringIO(lignes))
    sys.stdout = sortie
    try:
        serveur.main()
    finally:
        sys.stdout = avant
    return [json.loads(l) for l in sortie.getvalue().splitlines() if l.strip()]


def _appel(msg_id, outil, **arguments):
    return {"jsonrpc": "2.0", "id": msg_id, "method": "tools/call",
            "params": {"name": outil, "arguments": arguments}}


def _texte(reponse):
    return reponse["result"]["content"][0]["text"]


class _FausseReponse:
    def __init__(self, corps):
        self.corps = corps

    def read(self):
        return self.corps

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestProtocole:
    def test_ping_et_methode_inconnue(self, monkeypatch):
        r = _dialoguer(monkeypatch,
                       {"jsonrpc": "2.0", "id": 1, "method": "ping"},
                       {"jsonrpc": "2.0", "id": 2, "method": "resources/list"},
                       {"jsonrpc": "2.0", "method": "notifications/initialized"})
        assert r[0] == {"jsonrpc": "2.0", "id": 1, "result": {}}
        assert r[1]["id"] == 2
        assert r[1]["error"]["code"] == -32601
        assert "resources/list" in r[1]["error"]["message"]
        assert len(r) == 2              # la notification ne recoit rien

    def test_outil_inconnu(self, monkeypatch):
        r = _dialoguer(monkeypatch, _appel(7, "outil_fantome"))
        assert r == [{"jsonrpc": "2.0", "id": 7,
                      "error": {"code": -32602, "message": "outil inconnu : outil_fantome"}}]

    def test_exception_recoit_une_reponse(self, monkeypatch):
        """Des params qui ne sont pas un objet : erreur interne, mais une reponse."""
        r = _dialoguer(monkeypatch, {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                                     "params": ["pas", "un", "objet"]})
        assert r[0]["id"] == 9
        assert r[0]["error"]["code"] == -32603
        assert r[0]["error"]["message"].startswith("erreur interne")

    def test_ligne_non_json_sans_reponse(self, monkeypatch, capsys):
        """Une ligne qui n'est meme pas du JSON n'a pas d'id : rien sur stdout,
        un mot sur stderr, et le serveur continue."""
        r = _dialoguer(monkeypatch, "{pas du json",
                       {"jsonrpc": "2.0", "id": 3, "method": "ping"})
        assert r == [{"jsonrpc": "2.0", "id": 3, "result": {}}]
        assert "Erreur MCP Arthur" in capsys.readouterr().err

    def test_erreur_sans_id_muette(self, monkeypatch):
        sortie = io.StringIO()
        monkeypatch.setattr(sys, "stdout", sortie)
        serveur._erreur(None, -1, "rien")
        assert sortie.getvalue() == ""


class TestParler:
    def test_envoi_avec_jeton(self, monkeypatch):
        """Le cockpit recoit la question avec le jeton X-Cockpit-Token."""
        vus = []

        def faux_urlopen(req, timeout=None):
            vus.append(req)
            return _FausseReponse(json.dumps({"succes": True, "reponse": "Bonjour"}).encode())
        monkeypatch.setenv("COCKPIT_TOKEN", "jeton-essai")
        monkeypatch.setattr(serveur.urllib.request, "urlopen", faux_urlopen)
        r = serveur.envoyer_vers_arthur("Salut Arthur")
        assert r == {"succes": True, "reponse": "Bonjour"}
        assert vus[0].full_url == "http://127.0.0.1:8790/api/nano-search"
        assert vus[0].get_header("X-cockpit-token") == "jeton-essai"
        assert json.loads(vus[0].data) == {"prompt": "Salut Arthur"}

    def test_outil_parler(self, monkeypatch):
        monkeypatch.setattr(serveur, "envoyer_vers_arthur",
                            lambda msg, action: {"dit": msg, "action": action})
        r = _dialoguer(monkeypatch, _appel(4, "arthur_parler", message="coucou"))
        assert _texte(r[0]) == 'Arthur a parlé : {"dit": "coucou", "action": "parler"}'


class TestDialogues:
    def test_pas_de_journal(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        r = _dialoguer(monkeypatch, _appel(1, "arthur_lire_dialogues"))
        assert _texte(r[0]) == "Aucun dialogue enregistré pour le moment."

    def test_fin_du_journal(self, monkeypatch, tmp_path):
        """Seules les N dernieres lignes sont rendues."""
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / "livrables").mkdir()
        (tmp_path / "livrables" / "arthur_dialogues.log").write_text(
            "".join("ligne %d\n" % i for i in range(10)), encoding="utf-8")
        r = _dialoguer(monkeypatch, _appel(1, "arthur_lire_dialogues", lignes=2))
        assert _texte(r[0]) == "ligne 8\nligne 9\n"

    def test_nombre_de_lignes_invalide(self, monkeypatch, tmp_path):
        """Un nombre de lignes qui n'est pas un entier : erreur dite, pas de plantage."""
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / "livrables").mkdir()
        (tmp_path / "livrables" / "arthur_dialogues.log").write_text("a\n", encoding="utf-8")
        r = _dialoguer(monkeypatch, _appel(1, "arthur_lire_dialogues", lignes="deux"))
        assert _texte(r[0]).startswith("Erreur de lecture")


class TestCerveau:
    def test_voir_puis_changer(self, monkeypatch, tmp_path):
        """Sans argument : l'etat ; avec un nom : le reglage jetable change."""
        reglage = tmp_path / "reglages-maison.json"
        reglage.write_text(json.dumps({"alice": "10.0.0.2"}), encoding="utf-8")
        monkeypatch.setenv("ARTHUR_REGLAGES", str(reglage))
        r = _dialoguer(monkeypatch, _appel(1, "arthur_cerveau"),
                       _appel(2, "arthur_cerveau", cerveau="local"))
        assert "Gros cerveau d'Arthur (couche 3) : qwen" in _texte(r[0])
        assert "qwen → local" in _texte(r[1])
        d = json.loads(reglage.read_text(encoding="utf-8"))
        assert d == {"alice": "10.0.0.2", "cerveau_gros": "local"}


class TestApprendre:
    def test_fiche_refusee_par_le_mur(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HAICHI_SAVOIR_DIR", str(tmp_path))
        r = _dialoguer(monkeypatch, _appel(5, "apprendre_savoir", question="Capitale ?",
                                           reponse="Harare", source="sans source",
                                           date="2026-09-22"))
        verdict = json.loads(_texte(r[0]))
        assert verdict["verdict"] == "refuse"
        assert verdict["raison"] == "fiche sans source"
        assert os.path.exists(str(tmp_path / "quarantaine.json"))


if __name__ == "__main__":
    sys.exit(pytest.main(["-q", __file__]))
