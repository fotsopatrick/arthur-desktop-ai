#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE GRAPHE D'ARTHUR, SUITE — arthur_graphe.py.

Complete tests/test_rag_et_graphe.py. Aucun reseau : Qwen, morgan, Nemotron
et les cerveaux declares sont remplaces par des faux. On prouve :
  - nebius (avec clef) repond ; sans clef ou muet, on redescend a Qwen ;
  - local (morgan) repond ; muet, on redescend a Qwen ;
  - un cerveau declare qui dit « je ne sais pas » ne compte pas ;
  - un cerveau de repli APRES Qwen repond quand Qwen se tait ;
  - les documents de la maison (rag_maison) sont lus au noeud distant ;
  - une fiche « faux positif » sans document s'arrete sur l'aveu local ;
  - l'executant interne ne boucle jamais ; LangGraph est pris s'il est la ;
  - la ligne de commande.
"""
import importlib.util
import json
import os
import sys
import types

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import arthur_graphe as G  # noqa: E402
import nano_moteur_ultra as NM  # noqa: E402


class _FauxFournisseurs:
    """fournisseurs.py sans reseau : des fiches et des reponses ecrites."""

    def __init__(self, ordre, reponses):
        self._ordre, self.reponses, self.appels = ordre, reponses, []

    def fiche(self, nom):
        if nom in ("qwen", "local", "nebius"):
            return {"type": "interne"}
        return {"type": "openai", "modele": "m-" + nom} if nom in self.reponses else None

    def ordre(self, choix):
        return list(self._ordre.get(choix, ["qwen"]))

    def demander(self, nom, question, extraits=None, consigne=None):
        self.appels.append((nom, extraits))
        r = self.reponses.get(nom)
        return {"reponse": r, "panne": None if r else "muet", "modele": "m-" + nom}


class _FauxNemotron:
    def __init__(self, pret=True, reponse=None, panne=None):
        self.pret, self.reponse, self.panne, self.appels = pret, reponse, panne, []

    def est_pret(self):
        return self.pret

    def demander(self, q):
        self.appels.append(q)
        return {"reponse": self.reponse, "panne": self.panne}


@pytest.fixture
def graphe(tmp_path, monkeypatch):
    monkeypatch.setattr(NM, "LACUNES_PATH", str(tmp_path / "lacunes.json"))
    monkeypatch.setattr(NM, "RAG_MAISON", None)
    monkeypatch.setattr(NM, "rag_local", None)
    monkeypatch.setattr(NM, "_reglage_maison", lambda cle, defaut: defaut)
    monkeypatch.setattr(NM, "fournisseurs", _FauxFournisseurs({}, {}))
    monkeypatch.setattr(NM, "nemotron_nebius", _FauxNemotron(pret=False))
    alice = {"reponse": None, "appels": []}

    def faux_alice(question, extraits=None):
        alice["appels"].append((question, extraits))
        return alice["reponse"], (None if alice["reponse"] else "hors ligne")
    monkeypatch.setattr(G._MOTEUR, "demander_a_alice", faux_alice)
    monkeypatch.setattr(G._MOTEUR, "demander_a_morgan", lambda q: None)
    monkeypatch.setattr(G._MOTEUR, "_chercher_chez_alice", lambda q: (None, 0))
    monkeypatch.setattr(G, "_GRAPHE", G.construire(False))
    G.alice = alice
    return G


QUESTION = "quelle est la capitale du Cameroun ?"


def test_nebius_avec_clef_repond(graphe, monkeypatch):
    nemo = _FauxNemotron(reponse="Yaounde (Nemotron).")
    monkeypatch.setattr(NM, "nemotron_nebius", nemo)
    r = graphe.repondre(QUESTION, choix="nebius")
    assert r["source"] == "nemotron" and r["etapes"][-1] == "gros_cerveau : nemotron"
    assert nemo.appels == [QUESTION] and not graphe.alice["appels"]


def test_nebius_muet_redescend_a_qwen(graphe, monkeypatch):
    monkeypatch.setattr(NM, "nemotron_nebius", _FauxNemotron(panne="HTTP 402"))
    graphe.alice["reponse"] = "Yaounde."
    r = graphe.repondre(QUESTION, choix="nebius")
    assert r["source"] == "alice" and r["answer"] == "Yaounde."


def test_nebius_sans_clef_tout_se_tait_donne_un_aveu(graphe):
    r = graphe.repondre(QUESTION, choix="nebius")
    assert r["source"] == "aveu" and r["etapes"][-1] == "aveu"
    etape = r["etapes"][-2]
    assert "nebius : pas de clef" in etape and "qwen : hors ligne" in etape
    lacunes = json.load(open(NM.LACUNES_PATH, encoding="utf-8"))
    assert "nebius : pas de clef" in lacunes[0]["contexte_brut"]


def test_nebius_absent_du_tout(graphe, monkeypatch):
    monkeypatch.setattr(NM, "nemotron_nebius", None)
    r = graphe.repondre(QUESTION, choix="nebius")
    assert "nebius : pas de clef" in r["etapes"][-2]


def test_nebius_muet_sans_panne(graphe, monkeypatch):
    monkeypatch.setattr(NM, "nemotron_nebius", _FauxNemotron())
    r = graphe.repondre(QUESTION, choix="nebius")
    assert "nebius : rien" in r["etapes"][-2]


def test_local_morgan_repond(graphe, monkeypatch):
    monkeypatch.setattr(G._MOTEUR, "demander_a_morgan", lambda q: "Yaounde (morgan).")
    r = graphe.repondre(QUESTION, choix="local")
    assert r["source"] == "local" and r["etapes"][-1] == "gros_cerveau : morgan"


def test_local_morgan_muet(graphe):
    r = graphe.repondre(QUESTION, choix="local")
    assert "morgan : rien" in r["etapes"][-2]


def test_qwen_qui_ne_sait_pas_ne_compte_pas(graphe):
    graphe.alice["reponse"] = "Je ne sais pas."
    r = graphe.repondre(QUESTION)
    assert r["source"] == "aveu" and "qwen : « je ne sais pas »" in r["etapes"][-2]


def test_cerveau_declare_qui_ne_sait_pas_puis_repli_apres_qwen(graphe, monkeypatch):
    f = _FauxFournisseurs({"ds": ["ds", "qwen", "secours"]},
                          {"ds": "Je ne sais pas.", "secours": "Yaounde (secours)."})
    monkeypatch.setattr(NM, "fournisseurs", f)
    r = graphe.repondre(QUESTION, choix="ds")
    assert r["source"] == "secours" and r["etapes"][-1] == "gros_cerveau : secours"
    assert "m-secours" in r["thought"]
    assert [n for n, _ in f.appels] == ["ds", "secours"]
    assert len(graphe.alice["appels"]) == 1            # Qwen, entre les deux


def test_cerveau_declare_muet_la_panne_est_notee(graphe, monkeypatch):
    f = _FauxFournisseurs({"ds": ["ds", "qwen"]}, {"ds": None})
    monkeypatch.setattr(NM, "fournisseurs", f)
    r = graphe.repondre(QUESTION, choix="ds")
    assert r["source"] == "aveu" and "ds : muet" in r["etapes"][-2]


def test_documents_de_la_maison_lus_au_noeud_distant(graphe, monkeypatch):
    monkeypatch.setattr(NM, "RAG_MAISON", ["faux-rag"])
    vus = []

    def faux_rag(q):
        vus.append(q)
        return "[lecon.md] la capitale du cameroun est yaounde", 2
    monkeypatch.setattr(G._MOTEUR, "chercher_dans_la_maison", faux_rag)
    graphe.alice["reponse"] = "Yaounde, d'apres lecon.md."
    r = graphe.repondre(QUESTION)
    assert r["source"] == "documents" and "documents" in r["thought"]
    assert "2 mot(s) retrouve(s)" in r["etapes"][1]
    assert graphe.alice["appels"][-1][1].startswith("[lecon.md]")


def test_cerveau_declare_lit_les_documents(graphe, monkeypatch):
    monkeypatch.setattr(G._MOTEUR, "_chercher_chez_alice",
                        lambda q: ("[a.md] cameroun capitale yaounde", 2))
    f = _FauxFournisseurs({"ds": ["ds", "qwen"]}, {"ds": "Yaounde."})
    monkeypatch.setattr(NM, "fournisseurs", f)
    r = graphe.repondre(QUESTION, choix="ds")
    assert r["source"] == "ds" and "avec les documents" in r["thought"]
    assert f.appels[0][1].startswith("[a.md]")


def test_faux_positif_sans_document_s_arrete_sur_l_aveu_local(graphe):
    etat = {"extraits": None, "sortie": {"peut_monter": "documents"}}
    assert G.apres_documents(etat) == G.END
    etat["extraits"] = "[x] y"
    assert G.apres_documents(etat) == "gros_cerveau"
    assert G.apres_documents({"sortie": {"peut_monter": True}}) == "gros_cerveau"


def test_faux_positif_de_bout_en_bout(graphe, monkeypatch):
    """Une fiche gagne sur un mot banal, mais ne couvre pas « routeur » : en
    local, le moteur avoue et ne laisse monter QUE pour lire des documents.
    Sans document, le graphe s'arrete la, sans appeler le gros cerveau."""
    moteur = G._MOTEUR
    for attribut in ("index", "mots_simples"):          # remis en place apres
        monkeypatch.setattr(moteur, attribut, getattr(moteur, attribut))
    monkeypatch.setattr(moteur, "base", {"docker_infra": {
        "mots": ["docker"], "think": "t", "answer": "Docker isole."}})
    moteur.reconstruire_index()
    r = graphe.repondre("parle-moi du routeur docker ?")
    assert r["source"] == "aveu" and "ecartee" in r["thought"]
    assert [e.split(" :")[0] for e in r["etapes"]] == ["local", "documents_distants"]


def test_l_executant_interne_ne_boucle_jamais():
    g = G._MiniGraphe()
    g.add_node("a", lambda e: {})
    g.add_edge(G.START, "a")
    g.add_edge("a", "a")
    with pytest.raises(RuntimeError, match="ne s'arrete pas"):
        g.compile().invoke({})


def test_le_graphe_se_construit_au_premier_appel(graphe, monkeypatch):
    monkeypatch.setattr(G, "_GRAPHE", None)
    monkeypatch.setattr(G, "AVEC_LANGGRAPH", False)
    monkeypatch.setattr(G.construire, "__defaults__", (False,))
    r = G.repondre("qui est Victor ?")
    assert G._GRAPHE is not None and r["etapes"] == ["local : haichi"]
    assert "peut_monter" not in r


# ── la ligne de commande ─────────────────────────────────────────────────────
def test_main_sans_question_montre_l_aide(capsys):
    assert G.main([]) == 0
    assert "arthur_graphe.py" in capsys.readouterr().out


def test_main_dessin_sans_langgraph(monkeypatch, capsys):
    monkeypatch.setattr(G, "AVEC_LANGGRAPH", False)
    assert G.main(["--dessin"]) == 1
    assert "pip install langgraph" in capsys.readouterr().out


def test_main_pose_une_question(graphe, capsys):
    graphe.alice["reponse"] = "Yaounde."
    assert G.main(["--rien", "quelle", "est", "la", "capitale", "du", "Cameroun", "?"]) == 0
    sortie = capsys.readouterr().out
    assert "Yaounde." in sortie and "(alice — local" in sortie


# ── avec LangGraph (un faux, pour ne rien installer) ─────────────────────────
def _charger_une_copie(monkeypatch, faux_langgraph):
    """Charge arthur_graphe.py sous un autre nom, avec un « langgraph » factice
    et sans le depot dans sys.path (pour voir le module l'y remettre)."""
    paquet = types.ModuleType("langgraph")
    graph = types.ModuleType("langgraph.graph")
    for k, v in faux_langgraph.items():
        setattr(graph, k, v)
    paquet.graph = graph
    monkeypatch.setitem(sys.modules, "langgraph", paquet)
    monkeypatch.setitem(sys.modules, "langgraph.graph", graph)
    monkeypatch.setattr(sys, "path", [p for p in sys.path
                                      if os.path.abspath(p or ".") != REPO])
    spec = importlib.util.spec_from_file_location(
        "arthur_graphe_copie", os.path.join(REPO, "arthur_graphe.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert REPO in sys.path
    return module


def test_avec_langgraph_le_meme_graphe_et_le_dessin(monkeypatch, capsys):
    class _Dessin:
        def draw_mermaid(self):
            return "graph TD; local-->documents_distants"

    class FauxStateGraph(G._MiniGraphe):
        def get_graph(self):
            return _Dessin()
    copie = _charger_une_copie(monkeypatch, {"StateGraph": FauxStateGraph,
                                             "START": "__start__", "END": "__end__"})
    assert copie.AVEC_LANGGRAPH is True
    g = copie.construire()
    assert isinstance(g, FauxStateGraph)
    assert set(g.noeuds) == {"local", "documents_distants", "gros_cerveau", "aveu"}
    assert copie.main(["--dessin"]) == 0
    assert "local-->documents_distants" in capsys.readouterr().out
