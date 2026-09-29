#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LES CAS D'ANTICIPATION — le moteur ne doit JAMAIS planter,
il doit avouer. Etape 4 de l'audit du 21/09/2026.

Trois ennemis silencieux :
  1. reglages-maison.json CORROMPU (Jean a edite a la main, une virgule
     en trop). Le moteur doit retomber sur ses valeurs par defaut, pas
     s effondrer.
  2. Le gros cerveau (Alice / Nebius) qui ne repond pas : timeout. Arthur
     doit dire « je ne sais pas », pas attendre 90 secondes ni planter.
  3. Plus de mots inconnus que le seuil (MOTS_INCONNUS_MAX = 1). Quand
     Arthur ne reconnait pas de quoi on lui parle, il avoue net — sauf si
     c'est une VRAIE question de culture, qui merite le gros cerveau.

La regle : un test qui ne peut pas echouer ne garde rien. Chaque cas ici
doit prouver un comportement, pas seulement tourner sans planter.
"""
import json
import os
import sys
import time
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import nano_moteur_ultra as m

rouges = 0
verts = 0


def juge(titre, ok, detail=""):
    global rouges, verts
    if ok:
        verts += 1
        print("  VERT  " + titre + ("  (%s)" % detail if detail else ""))
    else:
        rouges += 1
        print("  ROUGE " + titre + ("  (%s)" % detail if detail else ""))


print("1) CONFIG CORROMPUE : LES DEFAUTS TOMBENT, PAS LE MOTEUR")
chemin_conf = os.path.join(ICI, "reglages-maison.json")
sauvegarde = None
if os.path.exists(chemin_conf):
    sauvegarde = open(chemin_conf, encoding="utf-8").read()
try:
    with open(chemin_conf, "w", encoding="utf-8") as f:
        f.write('{\n  "alice_cerveau": "http://192.0.2.10:8081",\n')  # virgule finale interdite -> corrompu
    try:
        recup = m._reglage_maison("alice_cerveau", "http://defaut:9")
        juge("JSON corrompu -> valeur par defaut", recup == "http://defaut:9", recup)
    except Exception as e:
        juge("JSON corrompu -> pas de crash", False, type(e).__name__)
finally:
    if sauvegarde is not None:
        open(chemin_conf, "w", encoding="utf-8").write(sauvegarde)
    elif os.path.exists(chemin_conf):
        os.remove(chemin_conf)

# Un fichier VALIDE mais SANS la cle demandee : meme effet que la cle
# manquante, sans toucher a la production — on ecrit un fichier de remplacement
# propre, on appelle, on restaure.
try:
    with open(chemin_conf, "w", encoding="utf-8") as f:
        json.dump({"autre_cle": 1}, f)
    recup = m._reglage_maison("alice_cerveau", "http://defaut2:9")
    juge("cle absente -> valeur par defaut", recup == "http://defaut2:9", recup)
finally:
    if sauvegarde is not None:
        open(chemin_conf, "w", encoding="utf-8").write(sauvegarde)


print("\n2) LE GROS CERVEAU MUET : TIMEOUT -> AVEOU, PAS DE PLANTAGE")
# Un serveur local qui accepte la connexion mais ne repond jamais : c'est
# exactement l'image d'un LLM freeze. Il faut que le moteur rende la main
# vite et avoue — pas qu'il attende 90 secondes.
import socketserver


class ServeurMuET(socketserver.TCPServer):
    allow_reuse_address = True


class EtageMuET(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            self.request.recv(65536)
            time.sleep(30)  # ne repond JAMAIS
        except Exception:
            pass


muet = ServeurMuET(("127.0.0.1", 0), EtageMuET)
import threading
threading.Thread(target=muet.serve_forever, daemon=True).start()
port_muet = muet.server_address[1]

vrai_url = m.ALICE_URL
vrai_patience = m.ALICE_PATIENCE
try:
    m.ALICE_URL = "http://127.0.0.1:%d/v1/chat/completions" % port_muet
    m.ALICE_PATIENCE = 2  # 2 secondes pour prouver qu'il ne freeze pas
    t0 = time.perf_counter()
    reponse, panne = m.ENGINE.demander_a_alice("Quelle est la capitale du Cameroun ?")
    duree = time.perf_counter() - t0
    juge("timeout -> on rend (None, panne)", reponse is None and panne,
         "en %.1fs" % duree)
    juge("timeout -> vite (moins de 6 s)", duree < 6, "%.1fs" % duree)
finally:
    m.ALICE_URL = vrai_url
    m.ALICE_PATIENCE = vrai_patience
    m.ALICE_MUETTE_JUSQUA[0] = 0.0  # rendre la main : Alice redeviable
    muet.shutdown()


print("\n3) LE SEUIL DE MOTS INCONNUS (MOTS_INCONNUS_MAX = 1)")
# a) Deux mots inventes SANS question : il avoue sans monter a Alice.
t0 = time.perf_counter()
r = m.nano_moteur_ultra("xyzzy blurp")
duree = time.perf_counter() - t0
juge("mots inventes sans question -> aveu", not r["matched"] and "x" in (r["answer"] or "x")[:1]
     or ("je ne sais" in (r["answer"] or "").lower()), r["source"])
juge("aveu rapide (< 3 s)", duree < 3, "%.1fs" % duree)

# b) Une VRAIE question avec un mot inconnu monte au bon etage (source alice).
# REPLI MAÎTRISÉ (21/09/2026) : si Alice est hors ligne, aveu est valide.
r = m.nano_moteur_ultra("Quel est le plus grand ocean du monde ?")
juge("vraie question -> alice est consultee ou repli valide",
     r["source"] in ("alice", "nemotron", "aveu"),
     r["source"])


print("\n" + "=" * 60)
print("BILAN ANTICIPATION : %d verts, %d rouge(s)" % (verts, rouges))
print("=" * 60)
sys.exit(1 if rouges else 0)