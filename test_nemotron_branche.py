# -*- coding: utf-8 -*-
"""CONTROLE : arthur est bien branche sur Nebius + un modele NVIDIA Nemotron.
Exigence du concours : tourner sur Nebius, avec un modele open source NVIDIA.
"""
import sys, nemotron_nebius as N
vert=rouge=0
def dire(ok,t):
    global vert,rouge
    print(("  VERT   " if ok else "  ROUGE  ")+t)
    if ok: vert+=1
    else: rouge+=1
dire(N.ADRESSE.startswith("https://api.studio.nebius.com"), "l'adresse est bien Nebius (leurs serveurs)")
dire("nvidia/" in N.MODELE.lower() and "nemotron" in N.MODELE.lower(), "le modele est un NVIDIA Nemotron : "+N.MODELE)
dire(N.est_pret(), "la cle Nebius est presente")
if N.est_pret():
    r=N.demander("En un mot, quelle est la capitale du Cameroun ?")
    rep=(r.get("reponse") or "")
    dire("yaound" in rep.lower(), "reponse reelle et juste du cerveau : "+rep[:80])
    dire(r.get("duree_ms",0)>0, "la reponse vient bien de Nebius (%s ms)" % r.get("duree_ms"))
print("\n  %d vert, %d rouge" % (vert,rouge))
sys.exit(0 if rouge==0 else 1)
