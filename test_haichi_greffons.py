# -*- coding: utf-8 -*-
"""LES GREFFONS DE HACHI.

Un greffon, c'est une capacite qu'on AJOUTE a Hachi sans toucher a son cerveau.
Chacun vit dans son propre dossier, avec sa fiche et son programme.

Ne le 16/09/2026, d'une demande de Patrick : « les gens doivent pouvoir le
customiser ». Et d'un exemple concret : connecter Hachi a WhatsApp.

Ce que ce banc exige :
  1. Hachi trouve les greffons poses dans son dossier ;
  2. un greffon ETEINT n'est jamais utilise ;
  3. un greffon ALLUME repond quand ses mots apparaissent ;
  4. un greffon qui PLANTE ne casse pas Hachi — il avoue et continue ;
  5. un greffon ne peut PAS voler la place des regles quand Hachi sait deja ;
  6. on peut allumer et eteindre sans redemarrer.
"""
import json, os, shutil, sys, tempfile, time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

rouges = 0
def dire(ok, quoi):
    global rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    if not ok:
        rouges += 1

try:
    import haichi_greffons as G
except Exception as e:
    print("  ROUGE  le module des greffons n'existe pas encore : " + str(e)[:70])
    print("\nBILAN GREFFONS : 1 rouge — rien n'est encore ecrit")
    raise SystemExit(1)

# --- on fabrique un faux greffon, dans un dossier jetable ---------------
bac = tempfile.mkdtemp(prefix="greffons-essai-")
def poser_greffon(nom, mots, allume=True, plante=False):
    d = os.path.join(bac, nom)
    os.makedirs(d, exist_ok=True)
    json.dump({
        "nom": nom,
        "titre": "Greffon d'essai " + nom,
        "mots": mots,
        "allume": allume,
        "auteur": "le banc",
    }, open(os.path.join(d, "greffon.json"), "w", encoding="utf-8"), ensure_ascii=False)
    corps = ('def repondre(question, reglages):\n'
             '    raise RuntimeError("je plante expres")\n' if plante else
             'def repondre(question, reglages):\n'
             '    return "reponse du greffon ' + nom + '"\n')
    open(os.path.join(d, "greffon.py"), "w", encoding="utf-8").write(corps)
    return d

poser_greffon("essai_allume", ["banane", "fruit jaune"], allume=True)
poser_greffon("essai_eteint", ["poireau"], allume=False)
poser_greffon("essai_casse", ["grenade"], allume=True, plante=True)

# 1. il les trouve
liste = G.lister(bac)
dire(len(liste) == 3, "il trouve les 3 greffons poses (trouve : %d)" % len(liste))
noms = sorted(g["nom"] for g in liste)
dire(noms == ["essai_allume", "essai_casse", "essai_eteint"], "il les nomme tous : " + ", ".join(noms))

# 2. un greffon eteint n'est jamais utilise
r = G.essayer("le poireau est un legume", bac)
dire(r is None, "un greffon ETEINT ne repond pas")

# 3. un greffon allume repond
r = G.essayer("parle-moi de la banane", bac)
dire(r is not None and "essai_allume" in str(r.get("reponse", "")),
     "un greffon ALLUME repond : " + str(r.get("reponse") if r else "rien")[:46])
dire(r is not None and r.get("greffon") == "essai_allume", "il dit QUEL greffon a repondu")

# 4. un greffon qui plante ne casse pas Hachi
try:
    r = G.essayer("une grenade explose", bac)
    dire(r is not None and r.get("panne"), "un greffon qui PLANTE est attrape, et il le dit")
except Exception as e:
    dire(False, "un greffon qui plante a casse Hachi : " + str(e)[:50])

# 5. il ne repond pas quand aucun mot ne correspond
r = G.essayer("qu est ce que la tour de controle", bac)
dire(r is None, "aucun greffon ne se declenche sur une question de la maison")

# 6. on peut allumer et eteindre
G.basculer("essai_eteint", True, bac)
r = G.essayer("le poireau est un legume", bac)
dire(r is not None, "apres l'avoir ALLUME, il repond")
G.basculer("essai_eteint", False, bac)
r = G.essayer("le poireau est un legume", bac)
dire(r is None, "apres l'avoir ETEINT, il se tait de nouveau")

# 7. la vitesse : un greffon ne doit pas ralentir Hachi quand il ne sert pas
t0 = time.perf_counter()
for _ in range(200):
    G.essayer("qu est ce que la tour", bac)
ms = (time.perf_counter() - t0) * 1000 / 200
dire(ms < 5, "quand aucun greffon ne sert : %.3f ms perdues (limite 5 ms)" % ms)

shutil.rmtree(bac, ignore_errors=True)
print("\nBILAN GREFFONS : %d rouge(s) sur 10" % rouges)
raise SystemExit(1 if rouges else 0)
