#!/usr/bin/env python3
"""Le calculateur d'Arthur, cas par cas — y compris ce qu'il doit REFUSER.

Ne le 16/09/2026 : a « combien font 17 fois 23 ? », Arthur sortait un circuit
sur les rappels. Une porte qui n'a jamais refuse ne garde rien : la moitie des
epreuves ici verifient qu'il se TAIT quand ce n'est pas un calcul.
"""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/haichi"))
import haichi_outils as H
import nano_moteur_ultra as NM

verts, rouges = [], []


def juge(titre, attendu, obtenu):
    bon = attendu(obtenu) if callable(attendu) else attendu == obtenu
    (verts if bon else rouges).append((titre, attendu, obtenu))
    print("  %s %-52s %s" % ("OK  " if bon else "RATE", titre, obtenu))


print("\n1) IL CALCULE JUSTE")
for question, attendu in [
    ("combien font 17 fois 23 ?",        "17 fois 23 = 391"),
    ("combien font 2 plus 2",            "2 plus 2 = 4"),
    ("100 moins 37",                     "100 moins 37 = 63"),
    ("144 divise par 12",                "144 divise par 12 = 12"),
    ("9 x 9",                            "9 fois 9 = 81"),
    ("7 * 8",                            "7 fois 8 = 56"),
    ("2.5 fois 4",                       "2.5 fois 4 = 10"),
    ("2,5 plus 1,5",                     "2.5 plus 1.5 = 4"),
    ("multiplie 12 par 12",              "12 fois 12 = 144"),
    # Le 16/09/2026 : « multiplié » avec son accent rendait None. Arthur
    # savait compter, mais seulement si on ecrivait mal. Patrick, lui,
    # ecrit avec les accents.
    ("Combien font 17 multiplié par 4 ?", "17 fois 4 = 68"),
    ("144 divisé par 12",                "144 divise par 12 = 12"),
    ("15 enlève 6",                      "15 moins 6 = 9"),
    ("144 divise par 12",                "144 divise par 12 = 12"),
]:
    juge(question, attendu, H.outil_calcul(question))

print("\n2) IL REFUSE CE QUI N'EST PAS UN CALCUL")
for question in [
    "qui est Victor ?",
    "c'est quoi la tour ?",
    "combien de modules sont allumes ?",
    "quelle heure est-il ?",
    "raconte moi 3 choses",                 # un seul nombre
    "les 3 agents et les 4 circuits et 5 portes",   # trop de nombres
    "parle moi des circuits",
]:
    juge(question, None, H.outil_calcul(question))

print("\n3) LES PIEGES")
juge("division par zero", lambda t: t and "zero" in t, H.outil_calcul("10 divise par 0"))
juge("il n'execute pas le texte de la question", None,
     H.outil_calcul("__import__('os').system('echo danger') plus 1"))
juge("un nombre negatif", "-5 plus 3 = -2", H.outil_calcul("-5 plus 3"))

print("\n4) ARTHUR EN ENTIER — le calcul passe AVANT les circuits")
m = NM.NanoMoteurUltraEngine()
for question, verif, ce_quon_veut in [
    ("combien font 17 fois 23 ?",
     lambda r: "391" in str(r.get("answer", "")), "il dit 391"),
    ("combien font 17 fois 23 ?",
     lambda r: "CIRCUIT" not in str(r.get("answer", "")).upper(),
     "il ne sort PAS un circuit"),
    ("combien font 17 fois 23 ?",
     lambda r: r.get("source") == "outil", "la reponse vient d'un outil"),
    ("qui est Victor ?",
     lambda r: "Victor" in str(r.get("answer", "")), "il parle encore de Victor"),
    ("c'est quoi la PrEP ?",
     lambda r: r.get("source") == "aveu", "il refuse encore la sante"),
]:
    r = m.repondre(question)
    juge("%s -> %s" % (question[:30], ce_quon_veut), True, verif(r))

print("\n" + "=" * 72)
print("  %d epreuves passees, %d ratees" % (len(verts), len(rouges)))
for t, a, o in rouges:
    print("   RATE : %s\n          attendu %r, obtenu %r" % (t, a, o))
print("=" * 72)
sys.exit(1 if rouges else 0)
