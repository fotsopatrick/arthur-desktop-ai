#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARTHUR LIT LES DOCUMENTS DE LA MAISON AVANT D'AVOUER (27/09/2026).

CE QUE LE BANC A MESURE, LE 27/09/2026 A 17:00 (~/rag-apprentissage) :
  sur 10 vraies questions de la maison, 4 n'arrivaient JAMAIS aux documents.
  Une regle avouait avant : « question sur la maison, aucune regle ecrite,
  Alice ne connait pas la maison : on n'invente pas ».
  La regle avait raison pour la memoire d'Alice (elle ne connait pas la
  maison). Elle a tort pour le RAG de la maison (les 33 lecons + les articles).

LES QUATRE DEVOIRS
  · une question de la maison, sans regle ecrite, dont la reponse EST dans
    les documents de la maison : il repond, et dit ou il a lu ;
  · les documents de la maison n'ont rien : il avoue, comme avant, et note
    la lacune (le bottom-up continue de la recevoir) ;
  · sans le reglage « rag_maison », rien ne change : il n'appelle rien ;
  · la memoire d'Alice (qui ne connait pas la maison) n'est JAMAIS lue pour
    une question de la maison.
Le vrai fichier lacunes.json n'est pas touche : la note est interceptee.
"""
import importlib.util
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
verts = 0
rouges = 0


def juge(ok, quoi):
    global verts, rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    if ok:
        verts += 1
    else:
        rouges += 1


s = importlib.util.spec_from_file_location("moteur", os.path.join(ICI, "nano_moteur_ultra.py"))
M = importlib.util.module_from_spec(s)
s.loader.exec_module(M)
E = M.NanoMoteurUltraEngine
QUESTION = "Ou est rangee la sauvegarde de l'ancienne tour Odoo avec les souvenirs de Clark ?"

notes = []
appels_alice_docs = []
E._consigner_lacune = lambda self, p, r: notes.append(r)
E.chercher_dans_les_documents = lambda self, q: (appels_alice_docs.append(q), (None, 0))[1]
E.demander_a_alice = lambda self, q, extraits=None: (
    ("La sauvegarde est sur Alice, dans ~/sauvegarde-tour." if extraits else None), None)

a = E()

print("1) LES DOCUMENTS DE LA MAISON ONT LA REPONSE")
E.chercher_dans_la_maison = lambda self, q: (
    "[lecon/ou-vit-la-memoire-de-la-tour] l'ancienne tour Odoo : sauvegarde sur Alice, "
    "~/sauvegarde-tour/dump-tour-20260913-0007.sql", 3)
r = a.repondre(QUESTION, choisir="qwen")
juge(r.get("source") == "documents-maison", "il repond depuis la maison (source=%s)" % r.get("source"))
juge("sauvegarde" in str(r.get("answer", "")).lower(), "la reponse contient le fait")
juge(not appels_alice_docs, "la memoire d'Alice n'a pas ete lue pour une question de la maison")

print("2) LES DOCUMENTS DE LA MAISON N'ONT RIEN")
notes.clear()
E.chercher_dans_la_maison = lambda self, q: (None, 0)
r = a.repondre(QUESTION, choisir="qwen")
juge(r.get("source") == "aveu", "il avoue, comme avant (source=%s)" % r.get("source"))
juge(bool(notes), "la lacune est notee pour le bottom-up")

print("3) SANS LE REGLAGE, RIEN NE CHANGE")
del E.chercher_dans_la_maison
s2 = importlib.util.spec_from_file_location("moteur2", os.path.join(ICI, "nano_moteur_ultra.py"))
M2 = importlib.util.module_from_spec(s2)
s2.loader.exec_module(M2)
M2.RAG_MAISON = None
juge(M2.NanoMoteurUltraEngine.chercher_dans_la_maison(a, "sauvegarde odoo") == (None, 0),
     "sans reglage « rag_maison », la recherche maison ne fait rien")

print("4) UNE COMMANDE CASSEE NE FAIT PAS PLANTER ARTHUR")
M2.RAG_MAISON = ["/bin/false"]
juge(M2.NanoMoteurUltraEngine.chercher_dans_la_maison(a, "sauvegarde odoo") == (None, 0),
     "une recherche maison en panne rend (None, 0)")

print("5) LA REVUE DE CODE DU 27/09 : REPONSES BIZARRES DU RAG, PANNES")
import json as _json
import tempfile as _tmp
def _faux_rag(sortie, code=0):
    f = os.path.join(_tmp.mkdtemp(), "faux_rag.sh")
    open(f, "w").write("#!/bin/sh\ncat <<'FIN'\n%s\nFIN\nexit %d\n" % (sortie, code))
    os.chmod(f, 0o755)
    return [f]
for bizarre in ['{"erreur": "base vide"}', '[null, 3, "x"]', '[{"source": "l", "texte": 42}]', 'pas du json']:
    M2.RAG_MAISON = _faux_rag(bizarre)
    try:
        ok = M2.NanoMoteurUltraEngine.chercher_dans_la_maison(a, "sauvegarde ancienne tour odoo") == (None, 0)
    except Exception as e:
        ok = False
    juge(ok, "reponse bizarre du RAG (%s) : pas de plantage, (None, 0)" % bizarre[:25])
M2.RAG_MAISON = _faux_rag("", 1)
M2.NanoMoteurUltraEngine.chercher_dans_la_maison(a, "sauvegarde ancienne tour odoo")
juge(bool(getattr(a, "_panne_maison", "")), "le RAG en panne laisse une TRACE (pas un silence)")

notes.clear()
E.chercher_dans_la_maison = lambda self, q: ("[lecon/x] l'ancienne tour Odoo : sauvegarde sur Alice", 3)
E.demander_a_alice = lambda self, q, extraits=None: (None, "Alice ne repond pas (temps depasse)")
r = a.repondre(QUESTION, choisir="qwen")
juge(r.get("source") == "aveu" and "panne" in (r.get("thought", "") + r.get("answer", "")).lower(),
     "documents trouves mais Alice en panne : l'aveu DIT la panne")
juge(not notes, "... et aucune « regle manquante » n'est notee pour le bottom-up (%d note(s))" % len(notes))

appels = []
E.chercher_dans_la_maison = lambda self, q: (appels.append(q), (None, 0))[1]
E.alice_est_injoignable = staticmethod(lambda: True)
# (30/09) Le cas protege : une commande « rag_maison » (lente, jusqu'a 30 s)
# dont seule Alice lirait les extraits. On le dit explicitement.
M.RAG_MAISON = ["faux-rag-maison"]
r = a.repondre(QUESTION, choisir="qwen")
juge(not appels, "Alice deja connue injoignable : on ne cherche pas pour rien (pas 30 s d'attente)")
# Sans « rag_maison », la recherche est le RAG local : instantane, et citable
# sans Alice. La lire vaut mieux qu'avouer (revue de code du 30/09).
M.RAG_MAISON = None
appels.clear()
r = a.repondre(QUESTION, choisir="qwen")
juge(bool(appels), "sans rag_maison, les documents locaux sont lus meme Alice muette")
E.alice_est_injoignable = staticmethod(lambda: False)

print("")
print("  %d verts, %d rouges" % (verts, rouges))
sys.exit(0 if rouges == 0 else 1)
