#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arthur doit surveiller le videur de la tour.

Patrick, le 16/09/2026 : « comment le banisseur est mort et ca passe
inapercu 2 jours d'affilee ? »

La reponse : personne ne le regardait. Arthur regardait le site, le disque
et la memoire — pas le videur. Un garde que personne ne surveille peut
mourir en silence. Il est reste mort du 14/09 13h47 au 16/09 18h12.

Deux choses a verifier, pas une :
  · le videur est-il DEBOUT ?
  · garde-t-il VRAIMENT ? (un videur debout avec zero cellule ne garde rien —
    c'est la lecon « un port qui repond ne veut pas dire que ca marche »)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import haichi_outils_tour as T

reussi = rate = 0


def juge(attendu, vrai, montre=""):
    global reussi, rate
    if vrai:
        reussi += 1
        print("  OK    " + attendu)
    else:
        rate += 1
        print("  RATE  %-50s %s" % (attendu, str(montre)[:70]))


def verdict(videur):
    """Fait parler Arthur sur un videur fabrique, sans toucher au serveur."""
    T._memoire["sante"] = (T.time.time(), {
        "souci": "", "uptime": "up 2 days, 2 users, load average: 0.5, 0.5, 0.5",
        "disque": "/dev/sda1 72G 44G 29G 61% /", "memoire": "Mem: 7746 1573 6173",
        "conteneurs": "tour-caddy-1|Up 2 hours", "coeurs": 4,
        "portes": [("le site public", "https://x", 200, True, None)],
        "videur": videur,
    })
    return T.outil_serveur_va_bien()


print("\n1) IL DEMANDE DES NOUVELLES DU VIDEUR")
import inspect
source = inspect.getsource(T._releve_sante)
juge("il interroge fail2ban", "fail2ban" in source, source[:150])

print("\n2) UN VIDEUR DEBOUT ET QUI GARDE : RIEN A SIGNALER")
t = verdict({"debout": True, "cellules": 5, "bannis": 22})
juge("il ne crie pas", "Ca ne va PAS" not in t, t[-150:])
juge("il dit quand meme combien de cellules", "5" in t and "cellule" in t.lower(), t)

print("\n3) UN VIDEUR MORT : IL CRIE")
t = verdict({"debout": False, "cellules": 0, "bannis": 0})
juge("il dit que ca va mal", "Ca ne va PAS" in t, t[-160:])
juge("il nomme le videur", "videur" in t.lower(), t[-160:])

print("\n4) UN VIDEUR DEBOUT MAIS QUI NE GARDE RIEN : IL CRIE AUSSI")
# La lecon « un port qui repond ne veut pas dire que ca marche ».
t = verdict({"debout": True, "cellules": 0, "bannis": 0})
juge("zero cellule declenche l'alerte", "Ca ne va PAS" in t, t[-160:])

print("\n5) S'IL N'A PAS PU REGARDER, IL LE DIT — IL N'INVENTE PAS")
t = verdict(None)
juge("il ne declare pas une panne qu'il n'a pas vue",
     "Ca ne va PAS" not in t or "pas pu" in t.lower(), t[-200:])

print("\n6) IL COMPTE LES VRAIES CELLULES, PAS DES LIGNES DE TEXTE")
# Le videur ecrit « |- Number of jail:\t5 ». Compter les lignes qui commencent
# par « | » donnait 1 alors qu'il y en a 5. Un compteur qui compte la mauvaise
# chose ment avec aplomb.
T._memoire.clear()
vrai = T._releve_sante()
v = vrai.get("videur")
juge("il a pu regarder le vrai videur", v is not None, vrai.get("souci"))
if v:
    juge("il le voit debout", v["debout"] is True, v)
    juge("il compte plus d'une cellule", v["cellules"] > 1, v)
    juge("il voit des adresses bloquees", v["bannis"] > 0, v)

print("\n" + "=" * 72)
print("  %d epreuves passees, %d ratees" % (reussi, rate))
print("=" * 72)
sys.exit(1 if rate else 0)
