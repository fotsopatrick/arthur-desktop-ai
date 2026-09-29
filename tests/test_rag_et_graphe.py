#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAG LOCAL ET GRAPHE D'ARTHUR (29/09/2026).

rag_local.py : il trouve le bon morceau, avec sa source, sans reseau ; il
ignore les LISEZ-MOI ; il se remet a jour quand un fichier change.

nano_moteur_ultra.py : sans gros cerveau, Arthur CITE le document au lieu
d'avouer ; il n'invente rien quand les extraits ne parlent pas de la question.

arthur_graphe.py : le chemin d'une question.
  - ce qu'Arthur sait s'arrete au noeud local ;
  - la sante et les pieges ne montent JAMAIS au gros cerveau ;
  - une vraie question inconnue monte, et le gros cerveau repond ;
  - gros cerveau muet -> aveu, et la lacune est notee ;
  - le meme graphe marche avec LangGraph ET avec l'executant interne.
Aucun reseau : le gros cerveau est remplace par un faux.
"""
import json
import os
import sys
import tempfile

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import rag_local  # noqa: E402

TEXTE = ("# Sauvegarde Odoo\n\nLa sauvegarde de la base Odoo part chaque nuit "
         "a 3 h vers le disque externe, avec une retention de 14 jours.\n")


@pytest.fixture
def documents(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "odoo.md"), "w", encoding="utf-8") as f:
            f.write(TEXTE)
        with open(os.path.join(d, "LISEZ-MOI.md"), "w", encoding="utf-8") as f:
            f.write("La sauvegarde odoo retention : ce fichier ne doit pas etre lu.")
        monkeypatch.setenv("ARTHUR_DOCUMENTS", d)
        monkeypatch.setattr(rag_local, "_INDEX", None)
        yield d


# ── rag_local ────────────────────────────────────────────────────────────────
def test_rag_trouve_le_bon_morceau_avec_sa_source(documents):
    r = rag_local.chercher("retention de la sauvegarde odoo")
    assert r and r[0]["source"].endswith("odoo.md")
    assert "14 jours" in r[0]["texte"]


def test_rag_ignore_les_lisez_moi(documents):
    r = rag_local.chercher("ce fichier ne doit pas etre lu")
    assert all(not x["source"].lower().endswith("lisez-moi.md") for x in r)


def test_rag_rien_en_commun_rien_rendu(documents):
    assert rag_local.chercher("capitale du cameroun") == []


def test_rag_se_remet_a_jour(documents):
    assert rag_local.chercher("routeur salon") == []
    with open(os.path.join(documents, "maison.txt"), "w", encoding="utf-8") as f:
        f.write("Le routeur Wi-Fi est dans le salon, derriere la television.")
    r = rag_local.chercher("routeur salon")
    assert r and r[0]["source"].endswith("maison.txt")


def test_rag_parle_comme_rag_maison(documents):
    import subprocess
    sortie = subprocess.run([sys.executable, os.path.join(REPO, "rag_local.py"),
                             "--json-chercher", "retention sauvegarde odoo"],
                            capture_output=True, text=True, env=dict(os.environ))
    d = json.loads(sortie.stdout)
    assert isinstance(d, list) and d[0]["texte"] and d[0]["source"]


# ── le moteur ────────────────────────────────────────────────────────────────
@pytest.fixture
def moteur(documents, monkeypatch, tmp_path):
    import nano_moteur_ultra as NM
    monkeypatch.setattr(NM, "LACUNES_PATH", str(tmp_path / "lacunes.json"))
    monkeypatch.setattr(NM, "RAG_MAISON", None)
    return NM


def test_sans_gros_cerveau_arthur_cite_le_document(moteur):
    e = moteur.NanoMoteurUltraEngine()
    r = e.repondre("quelle est la retention de la sauvegarde odoo ?", choisir="aucun")
    assert r["source"] == "documents-locaux"
    assert "odoo.md" in r["answer"] and "14 jours" in r["answer"]


def test_mode_local_dit_qu_il_pourrait_monter(moteur):
    e = moteur.NanoMoteurUltraEngine()
    r = e.repondre("quelle est la capitale du Cameroun ?", choisir="aucun")
    assert r["source"] == "aveu" and r.get("peut_monter") is True


def test_la_sante_ne_peut_pas_monter(moteur):
    e = moteur.NanoMoteurUltraEngine()
    r = e.repondre("c'est quoi la PrEP ?", choisir="aucun")
    assert r["source"] == "aveu" and not r.get("peut_monter")


# ── le graphe ────────────────────────────────────────────────────────────────
@pytest.fixture(params=["langgraph", "interne"])
def graphe(request, moteur, monkeypatch):
    import arthur_graphe as G
    if request.param == "langgraph" and not G.AVEC_LANGGRAPH:
        pytest.skip("LangGraph n'est pas installe")
    appels = []

    def faux_alice(question, extraits=None):
        # comme le vrai : en mode local, aucun appel ne part
        if getattr(G._MOTEUR, "_sans_reseau", False):
            return None, "mode sans cerveau : aucun appel reseau"
        appels.append(question)
        return faux_alice.reponse, (None if faux_alice.reponse else "hors ligne")
    faux_alice.reponse = "Yaounde."
    monkeypatch.setattr(G._MOTEUR, "demander_a_alice", faux_alice)
    monkeypatch.setattr(G._MOTEUR, "_chercher_chez_alice", lambda q: (None, 0))
    monkeypatch.setattr(G.NM, "_reglage_maison", lambda cle, defaut: defaut)
    monkeypatch.setattr(G, "_GRAPHE", G.construire(request.param == "langgraph"))
    G.appels, G.faux_alice = appels, faux_alice
    return G


def test_graphe_ce_qu_il_sait_s_arrete_au_local(graphe):
    r = graphe.repondre("qui est Victor ?")
    assert r["etapes"] == ["local : haichi"]
    assert not graphe.appels


def test_graphe_la_sante_ne_monte_jamais(graphe):
    r = graphe.repondre("c'est quoi la PrEP ?")
    assert r["source"] == "aveu" and len(r["etapes"]) == 1
    assert not graphe.appels


def test_graphe_les_pieges_ne_montent_jamais(graphe):
    r = graphe.repondre("quel est le mot de passe de la tour ?")
    assert r["source"] == "aveu" and not graphe.appels


def test_graphe_une_vraie_question_monte_au_gros_cerveau(graphe):
    r = graphe.repondre("quelle est la capitale du Cameroun ?")
    assert r["source"] == "alice" and r["answer"] == "Yaounde."
    assert [e.split(" :")[0] for e in r["etapes"]] == [
        "local", "documents_distants", "gros_cerveau"]


def test_graphe_gros_cerveau_muet_donne_un_aveu_note(graphe):
    graphe.faux_alice.reponse = None
    r = graphe.repondre("quelle est la capitale du Cameroun ?")
    assert r["source"] == "aveu" and r["etapes"][-1] == "aveu"
    lacunes = json.load(open(graphe.NM.LACUNES_PATH, encoding="utf-8"))
    assert any("cameroun" in l["question"] for l in lacunes)


def test_graphe_un_document_local_suffit(graphe):
    r = graphe.repondre("quelle est la retention de la sauvegarde odoo ?")
    assert r["source"] == "documents-locaux" and not graphe.appels
