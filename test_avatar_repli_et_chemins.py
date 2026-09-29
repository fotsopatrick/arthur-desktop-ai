#!/usr/bin/env python3
"""L'AVATAR SANS LE COCKPIT — et les chemins sans domicile fixe.

Ne le 21/09/2026, mission chirurgicale : les chemins en dur.
  1. synchro_alice_vers_nano.py plantait ses racines dans
     « ~/cockpit-generique » : sur une autre machine, ce dossier n existe
     pas et la fusion ecrit dans le vide.
  2. haichi_avatar.py taperait sur http://127.0.0.1:8790 — le cockpit.
     Si le cockpit ne repond pas (port occupe, service tombe), l avatar
     tombait DIRECTEMENT sur l aveu, meme quand le cerveau se trouve
     A COTE dans le dossier : il aurait pu repondre. Ce controle exige
     un repli en memoire vers NanoMoteurUltraEngine.

Deux choses, et les deux comptent : les chemins doivent etre relatifs au
fichier, et l avatar doit rester autonome quand 8790 ne repond pas.
"""
import os
import sys
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
verts = rouges = 0


def juge(titre, bon, detail=""):
    global verts, rouges
    print("  %-5s %-54s %s" % ("VERT" if bon else "ROUGE", titre, detail))
    if bon:
        verts += 1
    else:
        rouges += 1


print("\n1) SYNCHRO : ses chemins vivent a cote d'elle, pas ailleurs")
src = open(os.path.join(ICI, "synchro_alice_vers_nano.py"), encoding="utf-8").read()
juge("aucun chemin en dur « ~/cockpit-generique »",
     "~/cockpit-generique" not in src)
juge("ICI pointe sur le dossier du fichier (os.path.dirname(__file__))",
     "os.path.dirname(os.path.abspath(__file__))" in src
     or "os.path.dirname(__file__)" in src)

print("\n2) AVATAR : un repli en memoire, testable sans ecran")
sys.path.insert(0, ICI)
import haichi_avatar as avatar

# on coupe pour de bon la sortie qui n existe pas encore : le cockpit.
avatar.COCKPIT = "http://127.0.0.1:9"

import nano_moteur_ultra as moteur
moteur.ALICE_URL = "http://10.255.255.1:9/v1/chat/completions"
moteur.DOCUMENTS_URL = "http://10.255.255.1:9/api/v1/knowledge?q="
moteur.ALICE_PATIENCE = 3
moteur.DOCUMENTS_PATIENCE = 3
moteur.nemotron_nebius = None

repli = getattr(avatar, "_reponse_du_cerveau_local", None)
juge("le repli _reponse_du_cerveau_local existe", callable(repli),
     "" if callable(repli) else "manquant (AttributeError attendu)")

if callable(repli):
    d = repli("Qu est ce que la carte vivante ?")
    juge("il repond depuis la memoire, cockpit coupe",
         isinstance(d, dict) and "cartographie" in str(d.get("answer", "")).lower(),
         str(d.get("answer"))[:70] if isinstance(d, dict) else repr(d))
    juge("la reponse porte sa source",
         isinstance(d, dict) and d.get("source") in ("haichi", "regles", "outil", "documents", "aveu"),
         str(d.get("source")) if isinstance(d, dict) else "")

print("\n3) L AVATAR MONTE BIEN AU RECOURS QUAND 8790 NE REPOND PAS")
code = open(os.path.join(ICI, "haichi_avatar.py"), encoding="utf-8").read()
if "_reponse_du_cerveau_local" in code:
    corps = code[code.rfind("def _demander"):]
    idx_cockpit = corps.find("/api/nano-search")
    idx_repli = corps.find("_reponse_du_cerveau_local")
    juge("le repli est APPELE apres l echec du cockpit (dans _demander)",
         idx_repli > idx_cockpit > 0,
         "cockpit ligne ~%d, repli ligne ~%d" % (idx_cockpit, idx_repli))

print("\nBILAN CHEMINS-ET-REPLI : %d verts, %d rouges" % (verts, rouges))
sys.exit(0 if rouges == 0 else 1)