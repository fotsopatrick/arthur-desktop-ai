# -*- coding: utf-8 -*-
"""Le test de l'intelligence UNIQUE du cockpit.

Une seule porte : /api/nano-search. Trois devoirs :
  1. Les faits de la maison -> Haichi repond lui-meme, tres vite.
  2. Ce qui n'existe pas     -> il AVOUE. Jamais d'invention.
  3. Le reste du monde       -> il passe la main a Qwen sur Alice.
On verifie AUSSI qui a parle (le champ "source"), pas seulement le texte.
"""
import json, time, urllib.request, unicodedata

ADRESSE = "http://127.0.0.1:8790/api/nano-search"

def sans_accent(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    for a in ("'", "’", "`"):
        t = t.replace(a, " ")
    return " ".join(t.split())

AVEUX = ["je ne sais pas", "je ne connais pas", "n existe pas", "aucune information",
         "pas d information", "je n ai pas d information", "ne figure pas",
         "je ne suis pas au courant", "aucune regle ecrite"]

# question, qui doit repondre, mots attendus (au moins un)
CAS = [
    ("Qui est Victor dans l equipe de la tour ?", "haichi", ["victor"]),
    ("Qu est ce que la carte vivante ?",          "haichi", ["cartographie", "composants"]),
    ("Cite trois agents de la tour.",             "haichi", ["braignak"]),
    ("Qu est ce que Beelzebuth dans la tour ?",   "haichi", ["gloutonnerie", "boucle"]),
    # Ces deux-la parlent de la MAISON : c est Haichi lui-meme qui doit avouer,
    # Alice n a pas le droit d etre consultee (elle inventerait).
    ("Qu est ce que le circuit Zorglub de la tour ?",             "aveu-maison", AVEUX),
    ("Qui est l agent Pterodactyle de la tour ?",                 "aveu-maison", AVEUX),
    ("Quelle est la couleur officielle du protocole Wibble ?",    "aveu", AVEUX),
    ("Quelle est la capitale du Cameroun ?",      "alice",  ["yaound"]),
    ("Combien font 17 multiplie par 4 ?",         "alice",  ["68"]),
    ("Quel est le plus grand ocean du monde ?",   "alice",  ["pacifique"]),
]

def demander(q):
    corps = json.dumps({"prompt": q}).encode("utf-8")
    req = urllib.request.Request(ADRESSE, data=corps, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    d = json.loads(urllib.request.urlopen(req, timeout=120).read().decode("utf-8"))
    return d, time.perf_counter() - t0

rouges = 0
for question, qui_doit_parler, attendus in CAS:
    try:
        d, duree = demander(question)
    except Exception as e:
        print("  ROUGE " + question + "  -> PANNE : " + str(e)[:60]); rouges += 1; continue

    rep = d.get("answer", "")
    source = d.get("source", "(aucune source indiquee)")
    bas = sans_accent(rep)

    if qui_doit_parler == "aveu-maison":
        bon_texte = any(sans_accent(a) in bas for a in attendus)
        bon_qui = (source == "aveu")          # Haichi lui-meme, pas Alice
    elif qui_doit_parler == "aveu":
        bon_texte = any(sans_accent(a) in bas for a in attendus)
        bon_qui = True
    else:
        bon_texte = any(sans_accent(a) in bas for a in attendus)
        bon_qui = (source == qui_doit_parler)

    # Haichi doit rester rapide quand c'est lui qui repond
    bon_vitesse = (duree < 1.0) if qui_doit_parler in ("haichi", "aveu-maison") else True
    bon = bon_texte and bon_qui and bon_vitesse
    rouges += 0 if bon else 1

    print(("  VERT  " if bon else "  ROUGE ") + f"({duree:5.2f}s, {source}) {question}")
    print("         " + rep[:105].replace("\n", " "))
    if not bon_texte:  print("         -> on attendait un de ces mots : " + str(attendus[:4]))
    if not bon_qui:    print(f"         -> c est '{qui_doit_parler}' qui devait repondre, pas '{source}'")
    if not bon_vitesse:print("         -> Haichi doit repondre en moins d une seconde")

print()
print("BILAN : %d rouge(s) sur %d" % (rouges, len(CAS)))
raise SystemExit(1 if rouges else 0)
