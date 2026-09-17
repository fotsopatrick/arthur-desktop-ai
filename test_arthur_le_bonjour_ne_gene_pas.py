#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DIRE BONJOUR NE DOIT PAS EFFACER LA QUESTION.

FAUTE DITE PAR PATRICK LE 17/09/2026 : « Arthur dit automatiquement salut,
meme si mon premier message a une demande il l ignore dans sa premiere
reponse ».

CE QUE J AI MESURE, AVANT DE TOUCHER :

    « quelle est la capitale de la Mongolie ? »          -> Oulan-Bator
    « salut, quelle est la capitale de la Mongolie ? »   -> « Je ne sais pas »

Le mot « salut » traine la question vers ses documents, qui n ont rien, et il
s arrete la. Il ne monte plus jamais au grand modele.

C EST EXACTEMENT LA MEME FAUTE QUE « explique en une phrase ». Ces mots-la
ne disent pas DE QUOI on parle, ils disent A QUI on parle. Ils ne doivent
jamais servir a choisir la reponse. Trente-trois mots de consigne avaient
deja ete retires pour cette raison ; les mots de politesse avaient ete
oublies.

CE QUE CETTE EPREUVE VERIFIE, ET SES DEUX DEVOIRS :
  · un bonjour COLLE a une question ne change plus la reponse ;
  · un bonjour TOUT SEUL reste un bonjour — on ne casse pas l accueil.
"""
import json
import sys
import urllib.request

verts = 0
rouges = 0


def juge(ok, quoi):
    global verts, rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    if ok:
        verts += 1
    else:
        rouges += 1


def demander(question, delai=140):
    corps = json.dumps({"prompt": question}).encode("utf-8")
    r = urllib.request.Request("http://127.0.0.1:8790/api/nano-search",
                               data=corps,
                               headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(r, timeout=delai).read().decode("utf-8"))
    except Exception as e:
        d = {"answer": "", "cle": None, "_panne": str(e)[:60]}
    return d


print("1) LE BONJOUR COLLE A UNE QUESTION LA LAISSE-T-IL PASSER ?")
paires = [
    ("Quelle est la capitale de la Mongolie ?",
     "salut, quelle est la capitale de la Mongolie ?", "Oulan"),
    ("Combien font 17 fois 23 ?",
     "bonjour, combien font 17 fois 23 ?", "391"),
]
for nue, polie, attendu in paires:
    a = demander(nue)
    b = demander(polie)
    ra = (a.get("answer") or "")[:70].replace("\n", " ")
    rb = (b.get("answer") or "")[:70].replace("\n", " ")
    print("        sans bonjour : " + ra)
    print("        avec bonjour : " + rb)
    juge(attendu.lower() in rb.lower(),
         "« %s » rend toujours la bonne reponse" % polie[:44])

print("2) UN BONJOUR TOUT SEUL RESTE-T-IL UN BONJOUR ?")
d = demander("salut")
print("        cle trouvee : " + str(d.get("cle")))
juge(d.get("cle") == "salutations",
     "« salut » tout seul tombe encore sur l accueil")

print("3) ET LES AUTRES FORMULES DE POLITESSE ?")
for q, attendu in [("bonjour, merci de me dire la capitale de la Mongolie", "Oulan"),
                   ("coucou, combien font 17 fois 23 ?", "391")]:
    r = (demander(q).get("answer") or "")[:70].replace("\n", " ")
    print("        " + q[:46] + " -> " + r[:46])
    juge(attendu.lower() in r.lower(), "« %s » passe aussi" % q[:40])

print("")
print("  %d verts, %d rouges" % (verts, rouges))
sys.exit(0 if rouges == 0 else 1)
