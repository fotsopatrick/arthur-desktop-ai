# -*- coding: utf-8 -*-
"""GREFFON VEILLE — la veille d'Uatu (page Observatoire du cockpit) entre dans Arthur.

Ne le 27/09/2026, d'une demande de Patrick : « complete les projets des
hackathons en faisant en sorte que nos projets IA utilisent les parties d'Uatu
qui peuvent entrer ». Pour Arthur (concours Nebius), trois morceaux entrent :
la matrice Beelzebuth & Sage, les grands actionnaires, les medias.

Ce que ce banc exige :
  1. « a quoi Nvidia est expose » -> les crises de la matrice ou Nvidia figure ;
  2. « qui detient Apple »        -> les actionnaires qui citent Apple ;
  3. « ou lire les nouvelles de bourse » -> des medias en acces libre ;
  4. une entreprise absente -> « aucune trace », jamais une invention ;
  5. chaque reponse dit que les fiches sont ecrites a la main ;
  6. le greffon est trouve et ALLUME par le vrai mecanisme des greffons.
"""
import os, sys
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
rouges = 0
def dire(ok, quoi):
    global rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    if not ok:
        rouges += 1

import haichi_greffons as G
r = G.essayer("a quoi Nvidia est exposé ?", dossier=os.path.join(ICI, "greffons"))
dire(bool(r) and r["greffon"] == "veille", "le greffon veille repond a « a quoi Nvidia est exposé »")
t = (r or {}).get("reponse") or ""
dire("Goulet" in t and "Taïwan" in t.replace("Taiwan", "Taïwan"), "il cite l'energie des datacenters et le verrou taiwanais")
dire("main" in t, "il dit que les fiches sont ecrites a la main")

r = G.essayer("qui détient Apple ?", dossier=os.path.join(ICI, "greffons"))
t = (r or {}).get("reponse") or ""
dire("BlackRock" in t, "« qui détient Apple » cite BlackRock")

r = G.essayer("où lire les nouvelles de la bourse ?", dossier=os.path.join(ICI, "greffons"))
t = (r or {}).get("reponse") or ""
dire("Reuters" in t, "« où lire les nouvelles de la bourse » cite Reuters")

r = G.essayer("a quoi Zorglub Industries est exposé ?", dossier=os.path.join(ICI, "greffons"))
t = (r or {}).get("reponse") or ""
dire("aucune trace" in t.lower(), "une entreprise absente -> « aucune trace », pas d'invention")

r = G.essayer("quelle heure est-il ?", dossier=os.path.join(ICI, "greffons"))
dire(not r or r.get("greffon") != "veille", "une question sans rapport ne reveille pas le greffon")

# --- le VRAI chemin : le cockpit demande a haichi_outils.chercher_un_outil ---
import haichi_outils
qn = "a quoi nvidia est expose ?"          # le cockpit enleve accents et majuscules
f = haichi_outils.chercher_un_outil(qn)
t = f() if f else ""
dire(bool(f) and "Goulet" in str(t), "le vrai chemin (chercher_un_outil, celui du cockpit) passe par le greffon")
f = haichi_outils.chercher_un_outil("quelle heure est-il")
dire(bool(f) and "Goulet" not in str(f()), "les outils d'Arthur passent avant les greffons (l'heure reste l'heure)")

print(f"\nBILAN GREFFON VEILLE : {9 - rouges} verts, {rouges} rouges")
raise SystemExit(1 if rouges else 0)
