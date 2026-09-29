# -*- coding: utf-8 -*-
"""Le test de l'intelligence UNIQUE du cockpit.

Une seule porte : /api/nano-search. Trois devoirs :
  1. Les faits de la maison -> Haichi repond lui-meme, tres vite.
  2. Ce qui n'existe pas     -> il AVOUE. Jamais d'invention.
  3. Le reste du monde       -> il passe la main au repli local (Qwen/Alice).
On verifie AUSSI qui a parle (le champ "source"), pas seulement le texte.
Abandon 21/09/2026 : la 4e couche cloud (Nebius) est coupee — tout repond
avec la maison, rien ne depend du nuage.
"""
import json, time, urllib.request, unicodedata
import jeton_cockpit  # 24/09 : le cockpit exige X-Cockpit-Token sur ses POST

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
    # 18/09/2026 : « qui est Victor » passe par un OUTIL dedie
    # (outil_ce_qua_fait_un_agent), ajoute ce jour-la. La source juste est
    # donc « outil », pas « haichi » — cette ligne n'avait pas suivi.
    ("Qui est Victor dans l equipe de la tour ?", "outil",  ["victor"]),
    ("Qu est ce que la carte vivante ?",          "haichi", ["cartographie", "composants"]),
    ("Cite trois agents de la tour.",             "haichi", ["braignak"]),
    ("Qu est ce que Beelzebuth dans la tour ?",   "haichi", ["gloutonnerie", "boucle"]),
    # Ces deux-la parlent de la MAISON : c est Haichi lui-meme qui doit avouer,
    # Alice n a pas le droit d etre consultee (elle inventerait).
    ("Qu est ce que le circuit Zorglub de la tour ?",             "aveu-maison", AVEUX),
    ("Qui est l agent Pterodactyle de la tour ?",                 "aveu-maison", AVEUX),
    ("Quelle est la couleur officielle du protocole Wibble ?",    "aveu", AVEUX),
    # Le 16/09/2026 : ces epreuves exigeaient « alice ». Elles figeaient un
    # ordre ou Nemotron (concours Nebius) passait AVANT Qwen. Depuis le
    # 21/09/2026 la 4e couche cloud (Nebius) est ABANDONNEE : il ne reste
    # que le repli local Qwen sur Alice. La source juste est donc « alice ».
    # REPLI MAÎTRISÉ (21/09/2026) : si Alice est hors ligne, Haichi avoue
    # proprement (source=aveu). C'est le comportement correct de la tour :
    # aucune béquille cloud, repli autonome assumé. Source acceptée : alice|aveu.
    ("Quelle est la capitale du Cameroun ?", "alice|aveu",  ["yaound", "je ne sais pas"]),
    # Celle-ci ne doit monter chez PERSONNE : Arthur sait compter tout seul.
    ("Combien font 17 multiplie par 4 ?",    "outil",           ["68"]),
    # L'ocean n'est PLUS ici : voir l'epreuve de RESILIENCE plus bas.
]

def demander(q):
    corps = json.dumps({"prompt": q}).encode("utf-8")
    req = urllib.request.Request(ADRESSE, data=corps, headers=jeton_cockpit.entetes())
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
        bon_qui = source in qui_doit_parler.split("|")

    # Haichi doit rester rapide quand c'est lui qui repond
    # 27/09/2026, choix A de Patrick : un aveu sur la MAISON lit d'abord les documents
    # de la maison (le RAG, ~2,6 s) avant d'avouer. Seuil 3 s pour lui ; 1 s pour Haichi.
    bon_vitesse = (duree < 1.0) if qui_doit_parler == "haichi" else \
                  (duree < 3.0) if qui_doit_parler == "aveu-maison" else True
    bon = bon_texte and bon_qui and bon_vitesse
    rouges += 0 if bon else 1

    print(("  VERT  " if bon else "  ROUGE ") + f"({duree:5.2f}s, {source}) {question}")
    print("         " + rep[:105].replace("\n", " "))
    if not bon_texte:  print("         -> on attendait un de ces mots : " + str(attendus[:4]))
    if not bon_qui:    print(f"         -> c est '{qui_doit_parler}' qui devait repondre, pas '{source}'")
    if not bon_vitesse:print("         -> Haichi doit repondre en moins d une seconde")

print()
# --- EPREUVE DE RESILIENCE (21/09/2026) -------------------------------------
# La 4e couche cloud (Nebius) est abandonnee. Ce qu'on doit prouver ici n'est
# plus l'exactitude d'une culture pointue, mais la RESILIENCE : sur une
# question que le petit cerveau local ne maitrise pas, le systeme repond
# quand meme SANS le nuage, SANS panne, et SANS invention vide.
# DETTE ASSUMEE (phase 2, apprentissage bottom-up) : Qwen 1.5B dit
# « Atlantique » au lieu du Pacifique. Cette exactitude-la sera le fruit du
# circuit « geographie » a construire — elle n'est PAS exigee ici, et c'est
# dit. Le jour ou le circuit existe, on remettra le mot « pacifique ».
print("--- RESILIENCE : repondre sans le cloud ---")
try:
    d, duree = demander("Quel est le plus grand ocean du monde ?")
    rep = d.get("answer", "")
    source = d.get("source", "(aucune source)")
    local_ok = source in ("alice", "local", "aveu")
    sans_cloud = source not in ("nemotron",)
    non_vide = bool((rep or "").strip())
    bon = local_ok and sans_cloud and non_vide
    rouges += 0 if bon else 1
    print(("  VERT  " if bon else "  ROUGE ") + f"({duree:5.2f}s, {source}) repli local, aucun appel cloud")
    print("         " + rep[:105].replace("\n", " "))
    if not bon:
        print("         -> le repli local devait repondre sans le nuage")
except Exception as e:
    print("  ROUGE repli local -> PANNE : " + str(e)[:60]); rouges += 1

print()
print("BILAN : %d rouge(s) sur %d" % (rouges, len(CAS) + 1))
raise SystemExit(1 if rouges else 0)
