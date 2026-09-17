#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arthur doit distinguer une pointe passagere d'une vraie surcharge.

Ne le 16/09/2026, juste apres la fausse alerte de l'accueil. Arthur disait :

    ⚠️ Ca ne va PAS tout a fait : il peine, il a trop de travail.

On a regarde : la tour a 4 coeurs, et la charge etait « 5.71, 2.07, 1.56 ».
Le gros mangeur tournait depuis 34 SECONDES — une tache planifiee qui
demarre. Une minute plus tard il n'y a plus rien.

Deux fautes dans le meme jugement :
  · le seuil etait ecrit en dur (4). Une machine a 16 coeurs ne peine pas
    a 4 ; une machine a 2 coeurs peine bien avant. Le seuil, c'est le
    NOMBRE DE COEURS, et il se demande a la machine.
  · il lisait la moyenne d'UNE MINUTE, celle que la moindre tache planifiee
    fait sauter. Pour dire « il peine », il faut l'etat de fond : la
    moyenne de QUINZE minutes.

C'est la meme faute que l'accueil : un detecteur qui crie pour rien finit
par ne plus etre lu, et c'est comme ca qu'on rate la vraie panne.
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


def verdict(charges, coeurs):
    """Fait parler Arthur sur une charge fabriquee, sans toucher au serveur."""
    T._memoire["sante"] = (T.time.time(), {
        "souci": "",
        "uptime": "up 2 days,  3:43,  2 users, load average: %s" % charges,
        "disque": "/dev/sda1 72G 44G 29G 61% /",
        "memoire": "Mem: 7746 1573 6173",
        "conteneurs": "tour-caddy-1|Up 2 hours",
        "coeurs": coeurs,
        "portes": [("le site public", "https://x", 200, True, None)],
    })
    return T.outil_serveur_va_bien()


print("\n1) IL DEMANDE COMBIEN DE COEURS A LA MACHINE")
import inspect
source_du_releve = inspect.getsource(T._releve_sante)
juge("il demande « nproc » a la machine", "nproc" in source_du_releve,
     source_du_releve[:200])

print("\n2) UNE POINTE PASSAGERE N'EST PAS UNE PANNE")
# 4 coeurs. La minute est haute, le quart d'heure est calme : un cron.
t = verdict("5.71, 2.07, 1.56", 4)
juge("il ne dit pas que ca va mal", "Ca ne va PAS" not in t, t[-150:])
juge("il ne dit pas « il peine »", "il peine" not in t, t[-150:])
juge("il signale quand meme la pointe",
     "pointe" in t.lower() or "passag" in t.lower(), t[:400])

print("\n3) UNE VRAIE SURCHARGE DE FOND CRIE")
# 4 coeurs, et le quart d'heure est a 9 : la machine est vraiment noyee.
t = verdict("9.10, 9.00, 9.30", 4)
juge("il dit que ca va mal", "Ca ne va PAS" in t, t[-150:])
juge("il dit qu'il peine", "peine" in t, t[-150:])

print("\n4) LE SEUIL SUIT LA MACHINE, IL N'EST PAS ECRIT EN DUR")
# Meme charge de 6, deux machines differentes.
petite = verdict("6.00, 6.00, 6.00", 2)   # 2 coeurs : noyee
grosse = verdict("6.00, 6.00, 6.00", 16)  # 16 coeurs : tranquille
juge("charge 6 sur 2 coeurs : ca va mal", "Ca ne va PAS" in petite, petite[-120:])
juge("charge 6 sur 16 coeurs : ca va bien", "Ca ne va PAS" not in grosse, grosse[-120:])
juge("il dit sur combien de coeurs il juge",
     "coeur" in grosse.lower(), grosse[:400])

print("\n5) SANS LE NOMBRE DE COEURS, IL NE DEVINE PAS")
t = verdict("6.00, 6.00, 6.00", 0)
juge("il ne declare pas une panne qu'il ne peut pas mesurer",
     "Ca ne va PAS" not in t or "coeur" in t.lower(), t[-200:])

print("\n" + "=" * 72)
print("  %d epreuves passees, %d ratees" % (reussi, rate))
print("=" * 72)
sys.exit(1 if rate else 0)
