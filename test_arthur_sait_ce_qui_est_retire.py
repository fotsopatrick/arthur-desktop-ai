#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arthur doit distinguer « en panne » de « retire expres ».

Ne le 16/09/2026 d'une faute reelle. Arthur annoncait :

    ⚠️ Ca ne va PAS tout a fait : l'accueil de la tour : INTROUVABLE.

Il a parle au serveur : sur les 8 programmes qui tournent, aucun n'est
l'accueil. La page n'est pas tombee — elle a ete ENLEVEE, volontairement.

Un detecteur qui ne connait qu'un seul « absent » crie au feu devant une
piece qu'on a demolie expres. Et une alerte qui se declenche toujours pour
rien finit par ne plus etre lue : c'est ainsi qu'on rate la vraie panne.

Il faut donc trois etats, pas deux :
  · la chose est la et repond          → rien a dire
  ✗ la chose est attendue et absente   → ALERTE
  — la chose n'est plus attendue       → on le dit calmement, PAS d'alerte

Ces epreuves sont ecrites AVANT la correction. Elles doivent d'abord
echouer, sinon elles ne prouvent rien.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import haichi_outils_tour as T

reussi = rate = 0


def juge(ce_qu_on_attend, vrai, montre=""):
    global reussi, rate
    if vrai:
        reussi += 1
        print("  OK    " + ce_qu_on_attend)
    else:
        rate += 1
        print("  RATE  %-52s %s" % (ce_qu_on_attend, str(montre)[:60]))


print("\n1) CHAQUE FACADE DIT SI ON L'ATTEND ENCORE")
for facade in T._FACADES:
    juge("« %s » porte sa raison d'etre" % facade[0], len(facade) >= 4, facade)

print("\n2) L'ACCUEIL EST MARQUE COMME RETIRE, PAS COMME CASSE")
accueil = [f for f in T._FACADES if "accueil" in f[0]]
juge("l'accueil est toujours dans la liste (on ne cache pas)", len(accueil) == 1)
if accueil:
    raison = accueil[0][3] if len(accueil[0]) >= 4 else ""
    juge("il est marque retire (4e case remplie)", bool(raison), accueil[0])
    if raison:
        juge("la raison dit que c'est volontaire",
             any(m in raison.lower() for m in ("expres", "volontaire", "supprim",
                                               "retir", "enlev")), raison)
        juge("la raison dit ou est passee la fonctionnalite",
             "sauvegarde" in raison.lower(), raison)

print("\n3) UNE CHOSE RETIREE NE DECLENCHE AUCUNE ALERTE")
# On fabrique un faux releve : une facade vivante, une retiree introuvable.
faux = {
    "souci": "", "uptime": "up 3 days, 1 user, load average: 0.20",
    "disque": "/dev/sda1 100G 40G 60G 40% /", "memoire": "Mem: 8000 4000 4000",
    "conteneurs": "tour-caddy-1|Up 2 hours",
    "portes": [
        ("le site public", "https://exemple", 200, True, None),
        ("la chose demolie", "https://exemple/parti", 404, False,
         "retiree expres le 14/09/2026 ; la fonctionnalite est dans la sauvegarde"),
    ],
}
T._memoire["sante"] = (T.time.time(), faux)
texte = T.outil_serveur_va_bien()
juge("il ne dit PAS que ca va mal", "Ca ne va PAS" not in texte, texte[-120:])
juge("il dit quand meme que la chose est partie",
     "retir" in texte.lower() or "demoli" in texte.lower(), texte[-200:])
juge("il ne la range pas dans les ennuis",
     "la chose demolie : INTROUVABLE" not in texte, texte[-200:])

print("\n4) UNE VRAIE PANNE CRIE TOUJOURS")
faux2 = dict(faux)
faux2["portes"] = [("le site public", "https://exemple", 502, False, None)]
T._memoire["sante"] = (T.time.time(), faux2)
texte2 = T.outil_serveur_va_bien()
juge("une facade attendue et tombee declenche l'alerte",
     "Ca ne va PAS" in texte2, texte2[-160:])
juge("elle est nommee dans l'alerte", "le site public" in texte2, texte2[-160:])

print("\n" + "=" * 72)
print("  %d epreuves passees, %d ratees" % (reussi, rate))
print("=" * 72)
sys.exit(1 if rate else 0)
