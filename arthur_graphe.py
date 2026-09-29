#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arthur_graphe.py — le chemin d'une question, dessine comme un graphe.

Ne le 29/09/2026. Le moteur (nano_moteur_ultra.py) enchaine ses etages dans
une seule longue fonction : on ne voyait pas, de l'exterieur, par ou passait
une question. Ici, chaque etage est un NOEUD, et chaque choix une ARETE :

    local ──(il sait, ou il refuse)──────────────────────────► fin
      │
      └─(il ne sait pas, et il a le droit de demander)─► documents_distants
                                                              │
                                                              ▼
                                                        gros_cerveau ──► fin
                                                              │
                                                              └─(rien)─► aveu ─► fin

  local              garde-fous, outils, regles ecrites, documents de cette
                     machine (rag_local) — AUCUN appel reseau ;
  documents_distants la memoire d'Alice (8000) et « rag_maison », s'ils sont la ;
  gros_cerveau       le cerveau choisi (reglages-maison.json -> cerveau_gros) :
                     Nemotron chez Nebius, Qwen sur Alice, ou morgan (ollama) ;
  aveu               « je ne sais pas », et la lacune est notee.

Ce qui ne monte JAMAIS au gros cerveau : la sante, les pieges (mots de passe,
clefs...), le charabia sans question, et une question sur la maison sans
regle ecrite — le moteur les tranche au noeud « local » (peut_monter absent).

LangGraph (pip install langgraph) orchestre le graphe s'il est installe. Sinon
un petit executant interne suit EXACTEMENT les memes noeuds et aretes : Arthur
ne depend toujours d'aucun paquet.

    python3 arthur_graphe.py "quelle est la capitale du Cameroun ?"
    python3 arthur_graphe.py --dessin        # le graphe, en Mermaid
"""
import os
import sys
from typing import List, Optional, TypedDict

ICI = os.path.dirname(os.path.abspath(__file__))
if ICI not in sys.path:
    sys.path.insert(0, ICI)

import nano_moteur_ultra as NM

try:
    from langgraph.graph import StateGraph, START, END
    AVEC_LANGGRAPH = True
except Exception:                       # pas installe : l'executant interne
    StateGraph, START, END = None, "__start__", "__end__"
    AVEC_LANGGRAPH = False


class Etat(TypedDict, total=False):
    question: str
    choix: Optional[str]          # force un cerveau ; sinon le reglage
    sortie: dict                  # la reponse, au format du moteur
    extraits: Optional[str]       # ce que les documents distants ont rendu
    etapes: List[str]             # le chemin suivi, noeud par noeud


# Un moteur a part : le graphe ne touche pas a l'etat du moteur partage.
_MOTEUR = NM.NanoMoteurUltraEngine()


def _pas(etat, texte):
    return list(etat.get("etapes") or []) + [texte]


# ── LES NOEUDS ───────────────────────────────────────────────────────────────
def noeud_local(etat: Etat) -> Etat:
    s = _MOTEUR.repondre(etat["question"], choisir="aucun")
    return {"sortie": s,
            "etapes": _pas(etat, "local : %s" % (s.get("source") or "?"))}


def noeud_documents_distants(etat: Etat) -> Etat:
    q = _MOTEUR._sans_la_politesse(_MOTEUR.normaliser(etat["question"]))
    _MOTEUR._sans_reseau = False
    extraits, combien = _MOTEUR._chercher_chez_alice(q)
    if not extraits and NM.RAG_MAISON:
        extraits, combien = _MOTEUR.chercher_dans_la_maison(q)
    return {"extraits": extraits,
            "etapes": _pas(etat, "documents_distants : %s" % (
                "%d mot(s) retrouve(s)" % combien if extraits else "rien"))}


def noeud_gros_cerveau(etat: Etat) -> Etat:
    """Le meme ordre que le moteur : nebius (si la clef est la) puis qwen ;
    local (morgan) puis qwen. Rend une sortie au format du moteur."""
    q, extraits = etat["question"], etat.get("extraits")
    choix = etat.get("choix") or NM._reglage_maison("cerveau_gros", "qwen")
    t0 = NM.time.perf_counter_ns()
    _MOTEUR._sans_reseau = False
    essais = []

    if choix == "nebius" and not extraits:
        if NM.nemotron_nebius is not None and NM.nemotron_nebius.est_pret():
            d = NM.nemotron_nebius.demander(q)
            if d.get("reponse"):
                return {"sortie": NM.NanoMoteurUltraEngine._sortie(
                            True, "Passe a Nemotron, chez Nebius.", d["reponse"],
                            "nemotron", 0.0, t0, source="nemotron"),
                        "etapes": _pas(etat, "gros_cerveau : nemotron")}
            essais.append("nebius : %s" % (d.get("panne") or "rien"))
        else:
            essais.append("nebius : pas de clef")
        choix = "qwen"

    if choix == "local" and not extraits:
        r = _MOTEUR.demander_a_morgan(q)
        if r:
            return {"sortie": NM.NanoMoteurUltraEngine._sortie(
                        True, "Passe a morgan (ollama, local).", r,
                        "local", 0.0, t0, source="local"),
                    "etapes": _pas(etat, "gros_cerveau : morgan")}
        essais.append("morgan : rien")

    r, panne = _MOTEUR.demander_a_alice(q, extraits)
    if r and "je ne sais pas" not in r.lower():
        source = "documents" if extraits else "alice"
        return {"sortie": NM.NanoMoteurUltraEngine._sortie(
                    True, "Passe a Qwen sur Alice%s." % (
                        ", avec les documents" if extraits else ""),
                    r, source, 0.0, t0, source=source),
                "etapes": _pas(etat, "gros_cerveau : qwen")}
    essais.append("qwen : %s" % (panne or ("« je ne sais pas »" if r else "rien")))
    return {"sortie": None,
            "etapes": _pas(etat, "gros_cerveau : " + " ; ".join(essais))}


def noeud_aveu(etat: Etat) -> Etat:
    t0 = NM.time.perf_counter_ns()
    q = _MOTEUR._sans_la_politesse(_MOTEUR.normaliser(etat["question"]))
    raison = " ; ".join((etat.get("etapes") or [])[1:]) or "personne n'a su"
    _MOTEUR._consigner_lacune(q, "Graphe : " + raison)
    return {"sortie": NM.NanoMoteurUltraEngine._sortie(
                False, "Aucun etage n'a su : " + raison, NM.REPLI,
                None, 0.0, t0, source="aveu"),
            "etapes": _pas(etat, "aveu")}


# ── LES ARETES ───────────────────────────────────────────────────────────────
def apres_local(etat: Etat) -> str:
    return "documents_distants" if (etat.get("sortie") or {}).get("peut_monter") else END


def apres_gros_cerveau(etat: Etat) -> str:
    return END if etat.get("sortie") else "aveu"


# ── L'EXECUTANT INTERNE (sans LangGraph) ─────────────────────────────────────
class _MiniGraphe:
    """Juste ce qu'il faut de l'API de LangGraph pour ce graphe-ci."""

    def __init__(self, _type_etat=None):
        self.noeuds, self.aretes, self.conditions = {}, {}, {}

    def add_node(self, nom, fonction):
        self.noeuds[nom] = fonction

    def add_edge(self, de, vers):
        self.aretes[de] = vers

    def add_conditional_edges(self, de, choisir, destinations=None):
        self.conditions[de] = choisir

    def compile(self):
        return self

    def invoke(self, etat):
        etat = dict(etat)
        courant = self.aretes[START]
        for _ in range(20):                     # garde contre une boucle
            if courant == END:
                return etat
            etat.update(self.noeuds[courant](etat))
            courant = (self.conditions[courant](etat) if courant in self.conditions
                       else self.aretes[courant])
        raise RuntimeError("le graphe ne s'arrete pas")


def construire(avec_langgraph=AVEC_LANGGRAPH):
    g = StateGraph(Etat) if avec_langgraph else _MiniGraphe(Etat)
    g.add_node("local", noeud_local)
    g.add_node("documents_distants", noeud_documents_distants)
    g.add_node("gros_cerveau", noeud_gros_cerveau)
    g.add_node("aveu", noeud_aveu)
    g.add_edge(START, "local")
    g.add_conditional_edges("local", apres_local, ["documents_distants", END])
    g.add_edge("documents_distants", "gros_cerveau")
    g.add_conditional_edges("gros_cerveau", apres_gros_cerveau, ["aveu", END])
    g.add_edge("aveu", END)
    return g.compile()


_GRAPHE = None


def repondre(question, choix=None):
    """La reponse d'Arthur, au format du moteur, plus « etapes » : le chemin
    suivi dans le graphe."""
    global _GRAPHE
    if _GRAPHE is None:
        _GRAPHE = construire()
    fin = _GRAPHE.invoke({"question": question, "choix": choix, "etapes": []})
    sortie = dict(fin["sortie"])
    sortie.pop("peut_monter", None)
    sortie["etapes"] = fin.get("etapes", [])
    return sortie


def main(argv):
    if "--dessin" in argv:
        if not AVEC_LANGGRAPH:
            print("Le dessin demande LangGraph : pip install langgraph")
            return 1
        print(construire().get_graph().draw_mermaid())
        return 0
    question = " ".join(a for a in argv if not a.startswith("--"))
    if not question:
        print(__doc__)
        return 0
    r = repondre(question)
    print(r["answer"])
    print("\n(%s — %s)" % (r["source"], " -> ".join(r["etapes"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
