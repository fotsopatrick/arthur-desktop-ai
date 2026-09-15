# -*- coding: utf-8 -*-
"""Les TROIS etages de Haichi, et qui doit repondre a quoi.

  etage 1 — ses regles ecrites          : la maison, en moins d une milliseconde
  etage 2 — les documents avales        : l actualite technique, environ 300 ms
  etage 3 — Qwen qui reflechit          : le reste du monde, quelques secondes
  et l aveu, quand aucun des trois ne sait.
"""
import json, time, urllib.request, unicodedata

ADRESSE = "http://127.0.0.1:8790/api/nano-search"

def propre(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    for a in ("'", "’", "`"): t = t.replace(a, " ")
    return " ".join(t.split())

CAS = [
    # question, qui doit repondre, mots attendus
    ("Qui est Victor dans l equipe de la tour ?",            "haichi",     ["victor"]),
    ("Qu est ce que la carte vivante ?",                     "haichi",     ["cartographie"]),
    ("Qu est ce que le circuit Zorglub de la tour ?",        "aveu",       ["je ne sais pas"]),
    ("comment marche la prep",                               "aveu",       ["sante", "medecins"]),
    # celle-ci DOIT passer par les documents : sinon Qwen invente une vieille reference
    ("Quelle faille touche le noyau Linux de Debian ?",      "documents",  ["debian"]),
    ("Quelle est la capitale du Cameroun ?",                 "alice",      ["yaound"]),
    ("Combien font 17 multiplie par 4 ?",                    "alice",      ["68"]),
]

rouges = 0
for question, qui, attendus in CAS:
    corps = json.dumps({"prompt": question}).encode("utf-8")
    req = urllib.request.Request(ADRESSE, data=corps, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=180).read().decode("utf-8"))
    except Exception as e:
        print("  ROUGE " + question[:46] + " -> PANNE : " + str(e)[:50]); rouges += 1; continue
    duree = (time.perf_counter() - t0) * 1000
    rep, source = d.get("answer", ""), d.get("source", "(aucune)")
    bas = propre(rep)
    bon_texte = any(propre(a) in bas for a in attendus)
    bon_qui = (source == qui)
    bon = bon_texte and bon_qui
    rouges += 0 if bon else 1
    print(("  VERT  " if bon else "  ROUGE ") + f"({duree:8.0f} ms, {source:<9}) {question[:44]}")
    print("         " + rep[:100].replace("\n", " "))
    if not bon_texte: print("         -> mots attendus : " + str(attendus))
    if not bon_qui:   print(f"         -> devait venir de '{qui}', est venu de '{source}'")

print("\nBILAN : %d rouge(s) sur %d" % (rouges, len(CAS)))
raise SystemExit(1 if rouges else 0)
