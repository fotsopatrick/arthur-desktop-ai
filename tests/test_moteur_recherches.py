#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE MOTEUR, SES SOURCES — nano_moteur_ultra.py (les recherches et les appels).

Ce qu'on prouve, SANS reseau (faux Alice sur 127.0.0.1, faux RAG, faux
fournisseurs) et SANS ecrire dans le depot (lacunes et savoir en bac a sable) :
  - le savoir se trouve (bac a sable d'abord), s'abime sans tout casser, et
    les sujets ecartes (sante) ne sont jamais charges ;
  - chaque recherche (documents d'Alice, rag_maison, documents locaux) exige
    MOTS_RETROUVES_MINIMUM mots de la question, et une panne se dit ;
  - Alice muette est retenue 30 s ; les documents muets n'y touchent pas ;
  - le cerveau choisi, puis Qwen, puis les replis : les pannes s'additionnent ;
  - la file des lacunes : pas de doublon, bornee, jamais ecrasee si abimee ;
  - sans ses modules facultatifs, le moteur demarre quand meme.
"""
import importlib.util
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import nano_moteur_ultra as _NM  # noqa: E402

_VRAI_REGLAGE_MAISON = _NM._reglage_maison


def _port_mort():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class FauxRag:
    def __init__(self, morceaux=None, erreur=None):
        self.morceaux, self.erreur, self.questions = morceaux or [], erreur, []

    def chercher(self, question, k=3):
        self.questions.append((question, k))
        if self.erreur:
            raise self.erreur
        return self.morceaux


class FauxFournisseurs:
    def __init__(self, ordre=None, reponses=None):
        self._ordre, self.reponses, self.appels = ordre or {}, reponses or {}, []

    def fiche(self, nom):
        if nom in ("qwen", "local", "nebius"):
            return {"type": "interne"}
        return {"type": "openai"} if nom in self.reponses else None

    def ordre(self, choix):
        return list(self._ordre.get(choix, [choix, "qwen"]))

    def demander(self, nom, question, extraits=None, consigne=None):
        self.appels.append((nom, extraits))
        r = self.reponses.get(nom)
        return {"reponse": r, "panne": None if r else "%s muet" % nom, "modele": "m"}


class _Alice(BaseHTTPRequestHandler):
    """La memoire (GET) et le modele (POST) d'Alice, pour de faux."""
    documents, reponse, code, recus = {}, {}, 200, []

    def _repondre(self, objet):
        corps = json.dumps(objet).encode()
        self.send_response(_Alice.code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        _Alice.recus.append(("GET", self.path, None))
        self._repondre(_Alice.documents)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        _Alice.recus.append(("POST", self.path, json.loads(self.rfile.read(n))))
        self._repondre(_Alice.reponse)

    def log_message(self, *a):
        pass


@pytest.fixture
def NM(tmp_path, monkeypatch):
    port = _port_mort()
    monkeypatch.setattr(_NM, "LACUNES_PATH", str(tmp_path / "lacunes.json"))
    monkeypatch.setattr(_NM, "RAG_MAISON", None)
    monkeypatch.setattr(_NM, "ALICE_URL", "http://127.0.0.1:%d/v1/chat/completions" % port)
    monkeypatch.setattr(_NM, "DOCUMENTS_URL", "http://127.0.0.1:%d/k?q=" % port)
    monkeypatch.setattr(_NM, "ALICE_MUETTE_JUSQUA", [0.0])
    monkeypatch.setattr(_NM, "DOCUMENTS_MUETS_JUSQUA", [0.0])
    monkeypatch.setattr(_NM, "_reglage_maison", lambda cle, defaut: defaut)
    monkeypatch.setattr(_NM, "haichi_outils", None)
    monkeypatch.setattr(_NM, "rag_local", FauxRag())
    monkeypatch.setattr(_NM, "fournisseurs", FauxFournisseurs())
    monkeypatch.setattr(_NM, "nemotron_nebius", None)
    return _NM


@pytest.fixture
def alice(NM, monkeypatch):
    _Alice.documents, _Alice.code, _Alice.recus = {}, 200, []
    _Alice.reponse = {"choices": [{"message": {"content": "  Yaounde.  "}}]}
    s = HTTPServer(("127.0.0.1", 0), _Alice)
    threading.Thread(target=s.serve_forever, args=(0.05,), daemon=True).start()
    base = "http://127.0.0.1:%d" % s.server_address[1]
    monkeypatch.setattr(NM, "ALICE_URL", base + "/v1/chat/completions")
    monkeypatch.setattr(NM, "DOCUMENTS_URL", base + "/api/v1/knowledge?q=")
    yield _Alice
    s.shutdown()
    s.server_close()


# ── ou est le savoir ─────────────────────────────────────────────────────────
def test_le_bac_a_sable_prime(NM, tmp_path, monkeypatch):
    (tmp_path / "registre_connaissances.json").write_text("{}")
    monkeypatch.setenv("HAICHI_SAVOIR_DIR", str(tmp_path))
    assert NM._trouver_le_savoir() == str(tmp_path / "registre_connaissances.json")


def test_bac_vide_on_prend_le_depot(NM, tmp_path, monkeypatch):
    monkeypatch.setenv("HAICHI_SAVOIR_DIR", str(tmp_path))
    assert os.path.basename(NM._trouver_le_savoir()).startswith("registre_")


def test_aucun_savoir_nulle_part(NM, tmp_path, monkeypatch):
    monkeypatch.delenv("HAICHI_SAVOIR_DIR", raising=False)
    monkeypatch.setattr(NM, "ICI", str(tmp_path))
    assert NM._trouver_le_savoir() is None


def test_reglage_maison_lu_a_cote_du_moteur(NM, tmp_path, monkeypatch):
    monkeypatch.setattr(NM, "__file__", str(tmp_path / "nano_moteur_ultra.py"))
    assert _VRAI_REGLAGE_MAISON("cerveau_gros", "qwen") == "qwen"       # pas de fichier
    (tmp_path / "reglages-maison.json").write_text(json.dumps({"cerveau_gros": "local"}))
    assert _VRAI_REGLAGE_MAISON("cerveau_gros", "qwen") == "local"
    assert _VRAI_REGLAGE_MAISON("absent", 7) == 7
    (tmp_path / "reglages-maison.json").write_text("{abime")
    assert _VRAI_REGLAGE_MAISON("cerveau_gros", "qwen") == "qwen"


def test_charger_ecarte_la_sante_et_fusionne_la_base(NM, tmp_path, monkeypatch):
    registre = {
        "labo_vih_docking": {"mots": ["docking"], "answer": "medical"},
        "docker_infra": {"mots": ["moby"], "answer": "ecrasee par la base"},
        "sans_reponse": {"mots": ["rien"]},
        "pas_un_dict": ["x"],
        "odoo_sauvegarde": {"mots": ["sauvegarde odoo"], "answer": "chaque nuit"},
    }
    (tmp_path / "r.json").write_text(json.dumps(registre))
    monkeypatch.setattr(NM, "REGISTRE_PATH", str(tmp_path / "r.json"))
    e = NM.NanoMoteurUltraEngine()
    assert "labo_vih_docking" not in e.base and "sans_reponse" not in e.base
    assert "pas_un_dict" not in e.base and "odoo_sauvegarde" in e.base
    assert e.base["docker_infra"]["answer"] == NM.BASE_INITIALE["docker_infra"]["answer"]
    assert "moby" in e.base["docker_infra"]["mots"]            # les mots s'ajoutent
    assert e.index["moby"] == {"docker_infra"}


def test_registre_abime_la_base_reste(NM, tmp_path, monkeypatch):
    (tmp_path / "r.json").write_text("{abime")
    monkeypatch.setattr(NM, "REGISTRE_PATH", str(tmp_path / "r.json"))
    e = NM.NanoMoteurUltraEngine()
    assert set(e.base) == set(NM.BASE_INITIALE)


def test_un_mot_de_trois_circuits_ne_designe_plus_rien(NM):
    e = NM.NanoMoteurUltraEngine()
    e.base = {"circuit_1": {"mots": ["marche"], "answer": "1"},
              "circuit_2": {"mots": ["marche"], "answer": "2"},
              "circuit_3": {"mots": ["marche", "deploiement"], "answer": "3"},
              "docker_infra": {"mots": ["marche"], "answer": "d"}}
    e.reconstruire_index()
    assert e.index["marche"] == {"docker_infra"}
    assert e.index["deploiement"] == {"circuit_3"}


# ── sans ses modules facultatifs ─────────────────────────────────────────────
def test_le_moteur_demarre_sans_ses_modules_facultatifs(monkeypatch, tmp_path):
    for nom in ("haichi_outils", "skills.prompt_caching", "nemotron_nebius",
                "fournisseurs", "rag_local"):
        monkeypatch.setitem(sys.modules, nom, None)      # import -> ImportError
    monkeypatch.setenv("HAICHI_SAVOIR_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(
        "nano_moteur_copie", os.path.join(REPO, "nano_moteur_ultra.py"))
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)
    assert M.haichi_outils is None and M._cache_mgr is None
    assert M.nemotron_nebius is None and M.fournisseurs is None and M.rag_local is None
    assert M.LACUNES_PATH == str(tmp_path / "lacunes.json")
    e = M.ENGINE
    assert e._chercher_localement("sauvegarde odoo") == (None, 0)
    assert e._cerveau_externe("deepseek") is None
    assert e._cerveaux_externes("deepseek") == []
    # Alice, sans cache de consigne : injoignable ici, mais sans planter
    monkeypatch.setattr(M, "ALICE_URL", "http://127.0.0.1:%d/v1" % _port_mort())
    monkeypatch.setattr(M, "ALICE_MUETTE_JUSQUA", [0.0])
    reponse, panne = e.demander_a_alice("?")
    assert reponse is None and panne
    r = e.repondre("quelle est la capitale du Cameroun ?", choisir="aucun")
    assert r["source"] == "aveu" and r["peut_monter"] is True
    assert M.nano_moteur_ultra("docker ?")["cle"] == "docker_infra"


# ── les documents de cette machine (rag_local) ───────────────────────────────
def test_local_rien_ou_en_panne(NM, monkeypatch):
    e = NM.NanoMoteurUltraEngine()
    assert e._chercher_localement("sauvegarde odoo") == (None, 0)
    monkeypatch.setattr(NM, "rag_local", FauxRag(erreur=OSError("disque")))
    assert e._chercher_localement("sauvegarde odoo") == (None, 0)


def test_local_un_seul_mot_ne_suffit_pas(NM, monkeypatch):
    monkeypatch.setattr(NM, "rag_local", FauxRag(
        [{"source": "a.md", "texte": "la sauvegarde du salon"}]))
    e = NM.NanoMoteurUltraEngine()
    e._citation = None
    assert e._chercher_localement("sauvegarde odoo retention") == (None, 0)
    assert e._citation is None


def test_local_retient_la_citation(NM, monkeypatch):
    rag = FauxRag([{"source": "odoo.md", "texte": "La sauvegarde odoo : retention 14 jours."},
                   {"source": "b.md", "texte": "x" * 900}])
    monkeypatch.setattr(NM, "rag_local", rag)
    e = NM.NanoMoteurUltraEngine()
    extraits, combien = e._chercher_localement("q" * 400 + " sauvegarde odoo retention")
    assert combien == 2 and extraits.startswith("[odoo.md] La sauvegarde")   # « odoo » : trop court
    assert "[b.md] " + "x" * 700 in extraits and "x" * 701 not in extraits
    assert e._citation == ("odoo.md", "La sauvegarde odoo : retention 14 jours.")
    assert len(rag.questions[0][0]) == 300 and rag.questions[0][1] == 3


# ── les documents d'Alice ────────────────────────────────────────────────────
def test_alice_documents_pertinents(alice, NM):
    fin = "x" * 800 + " cameroun"                   # le mot est APRES les 700 affiches
    alice.documents = {"resultats": [{"contenu": "La capitale du " + fin},
                                     "pas un dict", {"contenu": None}]}
    e = NM.NanoMoteurUltraEngine()
    extraits, combien = e._chercher_chez_alice("capitale cameroun")
    assert combien == 2 and "cameroun" not in extraits          # affichage tronque
    assert alice.recus[0][1].endswith("knowledge?q=capitale%20cameroun")


@pytest.mark.parametrize("documents", [
    [1, 2],                                            # pas un objet
    {"resultats": []},
    {"resultats": None},
    {"resultats": [{"contenu": "rien a voir"}]},
])
def test_alice_documents_inutiles(alice, NM, documents):
    alice.documents = documents
    assert NM.NanoMoteurUltraEngine()._chercher_chez_alice("capitale cameroun") == (None, 0)
    assert NM.DOCUMENTS_MUETS_JUSQUA[0] == 0.0          # ce n'est pas une panne


def test_alice_documents_en_panne_se_taisent_30_s(NM):
    e = NM.NanoMoteurUltraEngine()
    assert e._chercher_chez_alice("capitale cameroun") == (None, 0)
    assert NM.DOCUMENTS_MUETS_JUSQUA[0] > time.time() + 20
    assert NM.ALICE_MUETTE_JUSQUA[0] == 0.0             # Qwen, lui, n'est pas puni
    assert e._chercher_chez_alice("capitale cameroun") == (None, 0)


def test_documents_alice_d_abord_puis_local(NM, monkeypatch):
    e = NM.NanoMoteurUltraEngine()
    monkeypatch.setattr(e, "_chercher_chez_alice", lambda q: ("[alice] oui", 2))
    assert e.chercher_dans_les_documents("q") == ("[alice] oui", 2)
    e._sans_reseau = True                                 # mode local : pas d'Alice
    assert e.chercher_dans_les_documents("q") == (None, 0)


# ── les documents de la maison (rag_maison) ──────────────────────────────────
class _Resultat:
    def __init__(self, code=0, sortie="", erreur=""):
        self.returncode, self.stdout, self.stderr = code, sortie, erreur


def _rag_maison(NM, monkeypatch, resultat=None, erreur=None):
    appels = []

    def faux_run(commande, **kw):
        appels.append((commande, kw))
        if erreur:
            raise erreur
        return resultat
    monkeypatch.setattr(NM, "RAG_MAISON", ["python3", "rag.py"])
    monkeypatch.setattr(subprocess, "run", faux_run)
    return appels


def test_maison_sans_reglage_lit_les_documents_locaux(NM, monkeypatch):
    monkeypatch.setattr(NM, "rag_local", FauxRag(
        [{"source": "odoo.md", "texte": "sauvegarde odoo, retention 14 jours"}]))
    e = NM.NanoMoteurUltraEngine()
    extraits, combien = e.chercher_dans_la_maison("retention sauvegarde odoo")
    assert combien == 2 and "[odoo.md]" in extraits and e._panne_maison == ""


def test_maison_repond(NM, monkeypatch):
    morceaux = [{"texte": "La sauvegarde nocturne part a 3 h."},
                {"source": "b.md", "texte": ""}, "bizarre", {"source": "c.md", "texte": 5}]
    appels = _rag_maison(NM, monkeypatch, _Resultat(0, json.dumps(morceaux)))
    e = NM.NanoMoteurUltraEngine()
    extraits, combien = e.chercher_dans_la_maison("sauvegarde nocturne")
    assert combien == 2 and extraits == "[?] La sauvegarde nocturne part a 3 h."
    assert e._citation == ("?", "La sauvegarde nocturne part a 3 h.")
    commande, kw = appels[0]
    assert commande == ["python3", "rag.py", "--json-chercher", "sauvegarde nocturne"]
    assert kw["timeout"] == NM.RAG_MAISON_PATIENCE


def test_maison_code_d_erreur_est_une_panne(NM, monkeypatch):
    _rag_maison(NM, monkeypatch, _Resultat(2, "", "Traceback\npgvector absent\n"))
    e = NM.NanoMoteurUltraEngine()
    assert e.chercher_dans_la_maison("sauvegarde odoo") == (None, 0)
    assert e._panne_maison == "recherche maison en panne (code 2) : Traceback\npgvector absent"


@pytest.mark.parametrize("erreur, mot", [
    (OSError("introuvable"), "introuvable"),
    (subprocess.TimeoutExpired("rag", 30), "timed out"),
])
def test_maison_exception_est_une_panne(NM, monkeypatch, erreur, mot):
    _rag_maison(NM, monkeypatch, erreur=erreur)
    e = NM.NanoMoteurUltraEngine()
    assert e.chercher_dans_la_maison("sauvegarde odoo") == (None, 0)
    assert e._panne_maison.startswith("recherche maison en panne : ") and mot in e._panne_maison


@pytest.mark.parametrize("sortie, panne", [
    ("pas du json", True),
    (json.dumps({"texte": "pas une liste"}), False),
    (json.dumps([]), False),
    (json.dumps([{"texte": "la sauvegarde du salon"}]), False),   # un seul mot
])
def test_maison_sortie_inutile(NM, monkeypatch, sortie, panne):
    _rag_maison(NM, monkeypatch, _Resultat(0, sortie))
    e = NM.NanoMoteurUltraEngine()
    assert e.chercher_dans_la_maison("sauvegarde odoo") == (None, 0)
    assert bool(e._panne_maison) is panne


# ── Qwen sur Alice ───────────────────────────────────────────────────────────
def test_alice_repond_avec_les_extraits(alice, NM):
    e = NM.NanoMoteurUltraEngine()
    reponse, panne = e.demander_a_alice("capitale ?", extraits="[a.md] " + "y" * 3000)
    assert reponse == "Yaounde." and panne is None
    corps = alice.recus[-1][2]
    assert corps["model"] == "qwen" and corps["temperature"] == 0
    systeme = corps["messages"][0]["content"]
    assert systeme.startswith(NM.CONSIGNE_ALICE) and "[a.md]" in systeme
    assert len(systeme) < len(NM.CONSIGNE_ALICE) + 2800        # extraits bornes


def test_alice_sans_reseau_ou_muette(NM):
    e = NM.NanoMoteurUltraEngine()
    e._sans_reseau = True
    assert e.demander_a_alice("?") == (None, "mode sans cerveau : aucun appel reseau")
    e._sans_reseau = False
    NM.NanoMoteurUltraEngine.noter_alice_muette()
    assert e.alice_est_injoignable()
    assert "injoignable" in e.demander_a_alice("?")[1]


def test_alice_en_panne_est_retenue(alice, NM):
    alice.reponse = {"pas": "de choices"}
    e = NM.NanoMoteurUltraEngine()
    reponse, panne = e.demander_a_alice("?")
    assert reponse is None and "choices" in panne
    assert e.alice_est_injoignable()
    avant = len(alice.recus)
    e.demander_a_alice("?")
    assert len(alice.recus) == avant                     # on ne retente pas


# ── morgan (ollama, sur cette machine) ───────────────────────────────────────
def test_morgan_repond_et_reste_local(NM, monkeypatch):
    vus = []

    class _R:
        def read(self):
            return json.dumps({"message": {"content": " Yaounde. "}}).encode()

    def faux_urlopen(req, timeout=None):
        vus.append((req.full_url, json.loads(req.data)))
        return _R()
    monkeypatch.setattr(urllib.request, "urlopen", faux_urlopen)
    assert NM.NanoMoteurUltraEngine().demander_a_morgan("capitale ?") == "Yaounde."
    url, corps = vus[0]
    assert url == "http://127.0.0.1:11434/api/chat"
    assert corps["model"] == "morgan" and corps["stream"] is False


def test_morgan_muet(NM, monkeypatch):
    def refus(req, timeout=None):
        raise OSError("ollama eteint")
    monkeypatch.setattr(urllib.request, "urlopen", refus)
    assert NM.NanoMoteurUltraEngine().demander_a_morgan("?") is None


# ── le cerveau choisi, puis Qwen, puis les replis ────────────────────────────
def _moteur_et_alice(NM, monkeypatch, reponse_alice):
    e = NM.NanoMoteurUltraEngine()
    e._sans_reseau = False
    monkeypatch.setattr(e, "demander_a_alice",
                        lambda q, x=None: (reponse_alice, None if reponse_alice else "hors ligne"))
    return e


def test_cerveau_sans_reseau(NM):
    e = NM.NanoMoteurUltraEngine()
    e._sans_reseau = True
    assert e.demander_au_cerveau("?")[0] is None


def test_cerveau_declare_avant_qwen(NM, monkeypatch):
    f = FauxFournisseurs({"ds": ["ds", "qwen"]}, {"ds": "D'apres a.md."})
    monkeypatch.setattr(NM, "fournisseurs", f)
    e = _moteur_et_alice(NM, monkeypatch, "Qwen")
    e._choix = "ds"
    assert e.demander_au_cerveau("?", "[a.md] x") == ("D'apres a.md.", None)
    assert f.appels == [("ds", "[a.md] x")]


def test_cerveau_declare_muet_puis_qwen(NM, monkeypatch):
    f = FauxFournisseurs({"ds": ["ds", "qwen"]}, {"ds": None})
    monkeypatch.setattr(NM, "fournisseurs", f)
    e = _moteur_et_alice(NM, monkeypatch, "Qwen repond.")
    e._choix = "ds"
    assert e.demander_au_cerveau("?") == ("Qwen repond.", None)


def test_qwen_muet_puis_repli_apres_qwen(NM, monkeypatch):
    f = FauxFournisseurs({"ds": ["ds", "qwen", "secours"]}, {"ds": None, "secours": "Secours."})
    monkeypatch.setattr(NM, "fournisseurs", f)
    e = _moteur_et_alice(NM, monkeypatch, None)
    e._choix = "ds"
    assert e.demander_au_cerveau("?") == ("Secours.", None)
    assert [n for n, _ in f.appels] == ["ds", "secours"]


def test_tout_le_monde_muet_les_pannes_s_additionnent(NM, monkeypatch):
    f = FauxFournisseurs({"ds": ["ds", "qwen", "secours"]}, {"ds": None, "secours": None})
    monkeypatch.setattr(NM, "fournisseurs", f)
    e = _moteur_et_alice(NM, monkeypatch, None)
    e._choix = "ds"
    reponse, panne = e.demander_au_cerveau("?")
    assert reponse is None and panne == "ds : ds muet ; hors ligne ; secours : secours muet"


def test_qwen_seul_muet_une_seule_panne(NM, monkeypatch):
    e = _moteur_et_alice(NM, monkeypatch, None)
    e._choix = "qwen"
    assert e.demander_au_cerveau("?") == (None, "hors ligne")


def test_cerveau_externe_seulement_s_il_est_declare(NM, monkeypatch):
    monkeypatch.setattr(NM, "fournisseurs", FauxFournisseurs({}, {"ds": "x"}))
    e = NM.NanoMoteurUltraEngine()
    e._choix = None
    assert e._cerveau_externe("ds") == "ds"
    assert e._cerveau_externe("qwen") is None             # interne
    assert e._cerveau_externe("inconnu") is None
    assert e._cerveau_externe("aucun") is None
    assert e._cerveau_externe() is None
    assert e._cerveaux_externes("aucun") == []


# ── la file des lacunes ──────────────────────────────────────────────────────
def test_lacune_notee_une_seule_fois(NM):
    e = NM.NanoMoteurUltraEngine()
    e._consigner_lacune("capitale du cameroun", "rien")
    e._consigner_lacune("capitale du cameroun", "encore rien")
    lignes = json.load(open(NM.LACUNES_PATH, encoding="utf-8"))
    assert len(lignes) == 1 and lignes[0]["contexte_brut"] == "rien"
    assert lignes[0]["horodatage"]


def test_lacunes_bornees(NM, monkeypatch):
    monkeypatch.setattr(NM, "LACUNES_MAX", 3)
    e = NM.NanoMoteurUltraEngine()
    for i in range(5):
        e._consigner_lacune("question %d" % i, "r")
    lignes = json.load(open(NM.LACUNES_PATH, encoding="utf-8"))
    assert [l["question"] for l in lignes] == ["question 2", "question 3", "question 4"]


@pytest.mark.parametrize("contenu", ['{"pas": "une liste"}', "[abime"])
def test_lacunes_abimees_jamais_ecrasees(NM, contenu):
    with open(NM.LACUNES_PATH, "w", encoding="utf-8") as f:
        f.write(contenu)
    NM.NanoMoteurUltraEngine()._consigner_lacune("q", "r")    # ne plante pas
    assert open(NM.LACUNES_PATH, encoding="utf-8").read() == contenu


def test_la_fonction_du_module_repond(NM, monkeypatch):
    e = NM.NanoMoteurUltraEngine()
    monkeypatch.setattr(NM, "ENGINE", e)
    r = NM.nano_moteur_ultra("c'est quoi docker ?")
    assert r["cle"] == "docker_infra" and r["matched"] and r["source"] == "haichi"
    assert r["raw_output"].startswith("<think>") and r["latency_ms"] >= 0
