#!/usr/bin/env python3
"""Les yeux d'Arthur sur la tour — cas par cas, refus compris.

Un outil qui repond toujours « tout va bien » ne sert a rien. La moitie des
epreuves ici verifient qu'Arthur DIT quand il ne voit pas, et qu'il refuse
de se declencher sur une question qui n'a rien a voir.
"""
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/haichi"))
import haichi_outils as H
import haichi_outils_tour as T
import nano_moteur_ultra as NM

verts, rouges = [], []


def juge(titre, verif, obtenu):
    bon = verif(obtenu) if callable(verif) else verif == obtenu
    (verts if bon else rouges).append((titre, obtenu))
    apercu = str(obtenu).replace("\n", " ⏎ ")[:74]
    print("  %s %-46s %s" % ("OK  " if bon else "RATE", titre, apercu))


print("\n1) « QUI EST EN LIGNE ? » — il mesure vraiment")
texte = H.outil_qui_est_en_ligne()
juge("il repond quelque chose (plus de 60 lettres)",
     lambda n: n > 60, len(texte))
juge("il nomme la tour", lambda t: t, "Sur la tour" in texte)
juge("il nomme la maison", lambda t: t, "A la maison" in texte)
juge("il cite un conteneur reel de la tour",
     lambda t: t, any(n in texte for n in ("tour-caddy-1", "petit-braignak",
                                           "pandemonium", "tour-embed")))
juge("il compte ce qu'il a vu", lambda t: t, "en marche" in texte)
juge("il ne promet rien sans avoir regarde",
     lambda t: t, "mesure a l'instant" in texte)

print("\n2) IL EST RAPIDE LA DEUXIEME FOIS")
t0 = time.perf_counter(); H.outil_qui_est_en_ligne()
ms = (time.perf_counter() - t0) * 1000
juge("deuxieme appel sous 50 millisecondes", lambda x: x < 50, round(ms, 1))

print("\n3) « LE SERVEUR VA BIEN ? » — il voit les vrais ennuis")
sante = H.outil_serveur_va_bien()
juge("il donne depuis quand la machine tourne",
     lambda t: t, "Allume depuis" in sante)
juge("il donne la place sur le disque", lambda t: t, "Disque :" in sante)
juge("il regarde les portes du site", lambda t: t, "Les portes du site" in sante)
juge("il tranche : ca va ou ca ne va pas",
     lambda t: t, ("Tout va bien" in sante) or ("Ca ne va PAS" in sante))
juge("il VOIT que l'accueil de la tour est introuvable",
     lambda t: t, "INTROUVABLE" in sante)

print("\n4) IL DIT QUAND IL NE VOIT PAS — on casse expres")
vrai_ssh = T._SSH[:]
try:
    T._SSH[:] = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2",
                 "machine-qui-nexiste-pas.invalide"]
    T._memoire.clear()
    casse = T.outil_qui_est_en_ligne()
    juge("il avoue ne pas avoir pu regarder",
         lambda t: t, "Je n'ai pas pu regarder" in casse)
    juge("il n'invente aucun agent",
         lambda t: t, "tour-caddy-1" not in casse)
    juge("il continue a voir la maison", lambda t: t, "A la maison" in casse)

    T._memoire.clear()
    casse2 = T.outil_serveur_va_bien()
    juge("sante : il avoue aussi",
         lambda t: t, "Je n'ai pas pu regarder la machine" in casse2)
    juge("sante : il ne dit surtout pas « tout va bien »",
         lambda t: t, "Tout va bien" not in casse2)
finally:
    T._SSH[:] = vrai_ssh
    T._memoire.clear()

print("\n5) ARTHUR ENTIER — la bonne question trouve le bon outil")
m = NM.NanoMoteurUltraEngine()
for question, mot_attendu in [
    ("qui est en ligne ?",              "QUI EST EN LIGNE"),
    ("qui est la en ce moment ?",       "QUI EST EN LIGNE"),
    ("quels agents sont la ?",          "QUI EST EN LIGNE"),
    ("le serveur va bien ?",            "LE SERVEUR"),
    ("est-ce que la tour va bien ?",    "LE SERVEUR"),
    ("y a t il une panne ?",            "LE SERVEUR"),
]:
    r = m.repondre(question)
    juge("%-34s" % question, lambda _: (r.get("source") == "outil" and
                                        mot_attendu in str(r.get("answer", ""))),
         r.get("source"))

print("\n6) IL NE SE DECLENCHE PAS N'IMPORTE QUAND")
for question, ce_qui_ne_doit_pas_sortir in [
    ("qui est Victor ?",               "QUI EST EN LIGNE"),
    ("c'est quoi la tour ?",           "LE SERVEUR VA"),
    ("combien font 17 fois 23 ?",      "QUI EST EN LIGNE"),
    ("c'est quoi la PrEP ?",           "LE SERVEUR VA"),
]:
    r = m.repondre(question)
    juge("%-34s ne sort pas les yeux" % question,
         lambda _: ce_qui_ne_doit_pas_sortir not in str(r.get("answer", "")),
         r.get("source"))

print("\n" + "=" * 74)
print("  %d epreuves passees, %d ratees" % (len(verts), len(rouges)))
for t, o in rouges:
    print("   RATE : %s  (obtenu : %s)" % (t, str(o)[:70]))
print("=" * 74)
sys.exit(1 if rouges else 0)
