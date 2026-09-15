# -*- coding: utf-8 -*-
"""Les OUTILS de Haichi : lire les choses vivantes du cockpit.

Une regle ecrite ne change jamais. Un OUTIL va voir, maintenant, l etat reel :
l heure qu il est, les modules allumes, le reseau, la veille du matin.
Ce test verifie que Haichi va VRAIMENT voir, au lieu de reciter.
"""
import json, time, urllib.request, unicodedata, datetime, re

ADRESSE = "http://127.0.0.1:8790/api/nano-search"

def propre(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.replace("'", " ").split())

maintenant = datetime.datetime.now()
heure_du_moment = maintenant.strftime("%H:%M")[:4]   # on tolere la minute qui tourne

CAS = [
    # question, d ou doit venir la reponse, ce qu elle doit contenir
    ("Quelle heure est-il ?",                 "outil", [heure_du_moment]),
    ("Quels modules du cockpit sont eteints ?", "outil", ["eteint"]),
    ("Combien de modules sont allumes ?",     "outil", ["allum"]),
    ("Ou en est la veille IA du matin ?",     "outil", ["veille"]),
    ("Combien de sujets connais-tu ?",        "outil", ["230", "sujets"]),
    # et les anciens devoirs ne doivent pas casser
    ("Qui est Victor dans l equipe de la tour ?", "haichi", ["victor"]),
    ("Qu est ce que le circuit Zorglub ?",    "aveu",   ["je ne sais pas"]),
]

rouges = 0
for question, qui, attendus in CAS:
    corps = json.dumps({"prompt": question}).encode("utf-8")
    req = urllib.request.Request(ADRESSE, data=corps, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=120).read().decode("utf-8"))
    except Exception as e:
        print("  ROUGE " + question[:44] + " -> PANNE : " + str(e)[:50]); rouges += 1; continue
    duree = (time.perf_counter() - t0) * 1000
    rep, source = d.get("answer", ""), d.get("source", "(aucune)")
    bas = propre(rep)
    bon_texte = any(propre(a) in bas for a in attendus)
    bon_qui = (source == qui)
    bon = bon_texte and bon_qui
    rouges += 0 if bon else 1
    print(("  VERT  " if bon else "  ROUGE ") + f"({duree:7.0f} ms, {source:<7}) {question[:42]}")
    print("         " + rep[:100].replace("\n", " "))
    if not bon_texte: print("         -> on attendait : " + str(attendus))
    if not bon_qui:   print(f"         -> devait venir de '{qui}', est venu de '{source}'")

print("\nBILAN OUTILS : %d rouge(s) sur %d" % (rouges, len(CAS)))
raise SystemExit(1 if rouges else 0)
