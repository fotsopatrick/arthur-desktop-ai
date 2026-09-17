#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARTHUR CHERCHE VRAIMENT, IL LE DIT, ET IL MONTRE COMMENT.

TROIS FAUTES MESUREES LE 17/09/2026.

1. IL COUPE LA ROUTE. Son premier serveur (porte 8796) repond
   {"erreur": "inconnu"} — il REPOND, il ne plante pas. L avatar prend donc
   « (rien) » et fait « return » : le cockpit, qui avait la reponse, n est
   jamais appele. Preuve : la meme question posee au cockpit rend
   « Oulan-Bator » en 3,8 secondes.
   C est la lecon connue : un code 200 ne veut pas dire que c est ouvert.
   Un repli qui ne se declenche QUE sur une panne ne se declenche jamais
   quand le serveur repond poliment « je ne sais pas ».

2. IL RESTE MUET 3,8 SECONDES. Patrick : « il doit dire je cherche et je te
   reponds ». Un silence de quatre secondes fait croire que c est casse.

3. IL NE MONTRE PAS SON TRAVAIL. Patrick : « son ecran doit montrer ce qu il
   a fait et comment ». Aujourd hui il rend la reponse nue. On veut savoir
   quel etage a repondu, combien de temps, et ce qu il a lu.

CE QUE CETTE EPREUVE NE PROUVE PAS, ET QUI EST DIT ICI : elle lit le code de
l avatar, elle ne regarde pas son ecran. Une bulle peut etre bien ecrite dans
le code et mal dessinee a l ecran. Seule une photo le dirait.
"""
import json
import os
import re
import sys
import time
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


AVATAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "haichi_avatar.py")
code = open(AVATAR, encoding="utf-8").read() if os.path.exists(AVATAR) else ""


def demander(port, route, question, delai=150):
    """Pose une question a un serveur, rend sa reponse et le temps mis."""
    corps = json.dumps({"prompt": question, "action": "parler"}).encode("utf-8")
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (port, route), data=corps,
                               headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        d = json.loads(urllib.request.urlopen(r, timeout=delai).read().decode("utf-8"))
    except Exception as e:
        d = {"_panne": str(e)[:60]}
    return d, int((time.time() - t0) * 1000)


QUESTION = "Quelle est la capitale de la Mongolie ?"

print("1) LA ROUTE VA-T-ELLE JUSQU AU BOUT ?")
a, ms_a = demander(8796, "/api/arthur-action", QUESTION, 30)
print("        le serveur d action dit : %s   (%d ms)" % (json.dumps(a, ensure_ascii=False)[:70], ms_a))
c, ms_c = demander(8790, "/api/nano-search", QUESTION)
rep_c = (c.get("answer") or "")[:60]
print("        le cockpit dit          : %s   (%d ms)" % (rep_c, ms_c))
juge("Oulan" in rep_c, "le cockpit, lui, CONNAIT la reponse")

# Le coeur : l avatar doit passer la main quand la reponse n est pas une vraie
# reponse — pas seulement quand le serveur plante.
passe_la_main = bool(re.search(
    r'(erreur|_panne|pas_de_reponse|sans_reponse|vraie_reponse|reponse_utile)', code, re.I))
juge(passe_la_main,
     "l avatar regarde si la reponse est VRAIE, pas seulement si ca plante")
# On verifie le GESTE, pas un mot. Premier jet du 17/09/2026 : l epreuve
# interdisait le mot « (rien) », alors qu il est legitime — il sert a
# reconnaitre une reponse creuse. Une epreuve qui interdit un mot mesure
# l orthographe, pas le comportement.
juge(code.count("nano-search") >= 1
     and code.index("_est_une_vraie_reponse(d)") < code.index("nano-search"),
     "il regarde si la premiere reponse est vraie AVANT de monter au cockpit")

print("2) DIT-IL QU IL CHERCHE, PENDANT QU IL CHERCHE ?")
juge(bool(re.search(r"je cherche", code, re.I)),
     "les mots « je cherche » sont dans son code")
juge(bool(re.search(r"un instant|je te r[ée]ponds", code, re.I)),
     "il promet de repondre, il ne laisse pas un silence nu")
juge(code.count("montrer_bulle") >= 3,
     "il parle AU MOINS deux fois : d abord « je cherche », puis la reponse")

print("3) MONTRE-T-IL CE QU IL A FAIT, ET COMMENT ?")
juge(bool(re.search(r"etage|montee|source", code, re.I)),
     "il dit QUEL etage a repondu")
juge(bool(re.search(r"%d ms|\bms\b.*time\.time|time\.time\(\).*1000", code)),
     "il compte les millisecondes de chaque etage et les affiche")
juge(bool(re.search(r"def _?(raconter_comment|montrer_travail|comment_j_ai_fait)", code)),
     "il a une fonction dediee qui raconte comment il a fait")

print("")
print("  %d verts, %d rouges" % (verts, rouges))
sys.exit(0 if rouges == 0 else 1)
