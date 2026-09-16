# -*- coding: utf-8 -*-
"""L'INTERFACE D'ARTHUR — simple au point de n'avoir rien a expliquer.

Elle pese 15 pour cent de la note du concours. Mais on ne note pas « c'est
joli » : on compte ce qui se compte.

DEUX HYPOTHESES, departagees le 16/09/2026 :
  (1) ajouter des explications a l'ecran ;
  (2) ENLEVER tout ce qui n'est pas indispensable.
Ce qui les separe : le nombre de choses a lire avant de comprendre quoi faire.
Mesure de depart : 2 boutons, 1 champ — deja sobre. Le probleme n'etait pas
le nombre d'elements, c'etaient LES MOTS.

CE QUE CE BANC EXIGE :
  - trois boutons au maximum ;
  - AUCUN mot de metier a l'ecran ;
  - le bon nom : Arthur, pas les anciens ;
  - aucun chiffre faux affiche ;
  - le texte d'invite DIT quoi faire ;
  - ca tient sur un petit ecran.
"""
import io, os, re, sys

ICI = os.path.dirname(os.path.abspath(__file__))
rouges = 0
def dire(ok, quoi):
    global rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    if not ok:
        rouges += 1

# Les mots qu'un inconnu ne comprend pas. Chacun a ete vu a l'ecran.
JARGON = ["nano-reasoner", "nano reasoner", "souverain", "reasoner", "api",
          "endpoint", "backend", "prompt", "token", "latence", "inference",
          "deterministe", "moteur", "transmettre"]

# Les anciens noms. Le produit s'appelle Arthur depuis le 16/09/2026.
ANCIENS = ["haichi flottant", "petit braignak", "compagnon souverain"]

for fichier, quoi in [("haichi_avatar.py", "sa fenetre du bureau"),
                      ("haichi_flottant.html", "sa page web")]:
    chemin = os.path.join(ICI, fichier)
    if not os.path.exists(chemin):
        dire(False, fichier + " est introuvable")
        continue
    s = io.open(chemin, encoding="utf-8").read()
    print("  --- " + quoi + " ---")

    # ce qui est VISIBLE : les libelles, les invites, les titres
    visibles = []
    visibles += re.findall(r'Gtk\.Button\(label="([^"]*)"\)', s)
    visibles += re.findall(r'set_placeholder_text\("([^"]*)"\)', s)
    visibles += re.findall(r'placeholder="([^"]*)"', s)
    visibles += re.findall(r'<title>([^<]*)</title>', s)
    visibles += re.findall(r'<button[^>]*>([^<]{2,40})</button>', s)
    visibles += re.findall(r'<b>([^<]{2,40})</b>', s)
    visibles += re.findall(r'<span>([^<]{2,60})</span>', s)
    vus = " | ".join(v.strip() for v in visibles if v.strip())

    nb = len(re.findall(r'Gtk\.Button\(', s)) + len(re.findall(r'<button', s))
    dire(nb <= 3, f"{nb} bouton(s) — on en veut trois au maximum")

    bas = vus.lower()
    trouves = [j for j in JARGON if j in bas]
    dire(not trouves, "aucun mot de metier a l'ecran" if not trouves
         else "mots de metier trouves : " + ", ".join(trouves))

    vieux = [a for a in ANCIENS if a in bas]
    dire(not vieux, "le bon nom est affiche" if not vieux
         else "ancien nom encore affiche : " + ", ".join(vieux))

    dire("arthur" in bas, "le nom Arthur apparait")

    # un chiffre affiche doit etre vrai. On a mesure 0,14 ms, pas 0,1.
    faux = re.findall(r"<\s*0[.,]1\s*ms", bas)
    dire(not faux, "aucun chiffre faux affiche" if not faux
         else "chiffre faux affiche : " + str(faux[0]))

    # le texte d'invite doit dire QUOI FAIRE
    invites = re.findall(r'set_placeholder_text\("([^"]*)"\)', s) + \
              re.findall(r'placeholder="([^"]*)"', s)
    if invites:
        inv = invites[0].lower()
        dire(len(invites[0]) <= 52, f"l'invite est courte ({len(invites[0])} lettres, on veut 52 au plus)")
        dire(any(m in inv for m in ["pose", "demande", "question", "ecris", "écris", "tape"]),
             "l'invite dit quoi faire : « " + invites[0] + " »")

print("\nBILAN INTERFACE : %d rouge(s) sur 14" % rouges)
raise SystemExit(1 if rouges else 0)
