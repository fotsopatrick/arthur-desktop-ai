# --- TATOUAGE CRYPTOGRAPHIQUE INAMOVIBLE ---
# Signature: nominomi
# B64_PROOF = "bm9taW5vbWktcGF0cmljay1jcmVhdGlvbi1zb3V2ZXJhaW5lLTIwMjY="
# HASH_PROOF = "af6152e817c761ccf74e9430053b2bd172802a3df02fd8a9bc8a13a415d40433"

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L'ETAGE NEMOTRON — le gros cerveau d'Arthur, chez Nebius.

POURQUOI CET ETAGE EXISTE.
Le concours Nebius x NVIDIA exige deux choses, sans quoi la candidature est
refusee : tourner sur leur nuage, et utiliser au moins un modele open source
de NVIDIA. Arthur branche donc son quatrieme etage sur Nemotron, chez eux —
a la place de Qwen, qui tournait sur Alice, la machine de la maison.

CE QU'ARTHUR NE PERD PAS EN GAGNANT UN SPONSOR.
Cet etage est le DERNIER. Il ne se declenche que si les trois d'avant ont
echoue. Donc :
  - les faits de la maison restent gratuits et immediats (0,14 ms) ;
  - la sante reste refusee, avant meme d'arriver ici ;
  - et si Nemotron ne sait pas, Arthur AVOUE. Il ne recopie pas une invention.

SANS CLE, IL LE DIT.
Mesure du 15/09/2026 qui justifie tout ce projet : questionne sur une faille
recente de Debian, un modele courant a repondu « CVE-2023-2687 » — une
reference fabriquee, datee de 2023. Un modele qui invente est pire qu'un
modele muet. Alors ici, quand quelque chose manque, on le dit.
"""
import json
import os
import re
import time
import urllib.request

# Le modele NVIDIA, chez Nebius. Les deux sont exiges par le concours.
# Le modele demande jusqu'au 16/09/2026 (Llama-3_3-Nemotron-Super-49B-v1_5)
# n'existe plus chez Nebius : il repondait « 404 », c'est-a-dire « ca n'existe
# pas ». Sa liste du jour donne quatre Nemotron. Celui-ci a repondu juste aux
# trois epreuves d'essai, en 891 millisecondes en moyenne.
MODELE = "nvidia/Nemotron-3-Ultra-550b-a55b"

# Les Nemotron REFLECHISSENT d'abord, et leur reflexion mange la place.
# Avec 220 jetons, toute la place partait dans la reflexion et la vraie
# reponse arrivait VIDE. Il leur en faut largement assez.
JETONS = 900
ADRESSE = "https://api.studio.nebius.com/v1/chat/completions"
PATIENCE = 90

# La consigne qui compte : mieux vaut se taire que mentir.
CONSIGNE = (
    "Tu es Arthur, compagnon flottant de La Tour de Controle. "
    "Reponds en francais. N ecris JAMAIS de phrases d assistant du type Je ne peux pas generer une application. "
    "Si la demande necessite du code, transmets-la a la salle des agents. Si tu ne sais pas, dis Je ne sais pas."
)

# Les mots qui trahissent un aveu, dans la reponse du gros cerveau.
AVEUX = ["je ne sais pas", "je ne connais pas", "je n ai pas d information",
         "aucune information", "n existe pas", "je ne suis pas sur"]


def _sans_accent(t):
    import unicodedata
    t = unicodedata.normalize("NFD", str(t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"['’`]", " ", t)


COFFRE = os.path.expanduser("~/.secrets/cle-nebius.txt")


def cle_du_moment(cle=None):
    """Ou Arthur va chercher sa cle, dans cet ordre.

    1. Celle qu'on lui tend dans l'appel (sert aux tests).
    2. La variable d'environnement NEBIUS_API_KEY.
    3. Le coffre : ~/.secrets/cle-nebius.txt, lisible par Patrick seul.

    Le coffre existe parce qu'une variable d'environnement meurt quand on
    ferme le terminal. Patrick devait la retaper a chaque fois.
    Le fichier, lui, reste. Il est en droits 600 : personne d'autre ne le lit.
    """
    if cle is not None:
        return str(cle).strip()

    depuis_env = os.environ.get("NEBIUS_API_KEY", "").strip()
    if depuis_env:
        return depuis_env

    try:
        with open(COFFRE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def demander(question, cle=None, essai=False, patience=PATIENCE):
    """Pose la question au gros cerveau. Rend toujours un dictionnaire.

    Les cles du dictionnaire :
      reponse  — le texte, ou None si rien ;
      panne    — ce qui a manque, en clair, ou None ;
      modele   — quel modele a ete appele ;
      avoue    — vrai si le modele a dit qu'il ne savait pas ;
      essai    — vrai si rien n'est parti pour de vrai ;
      duree_ms — combien de temps ca a pris.
    """
    t0 = time.perf_counter()
    la_cle = cle_du_moment(cle)

    base = {"reponse": None, "panne": None, "modele": MODELE,
            "avoue": False, "essai": bool(essai), "duree_ms": 0.0,
            "question_envoyee": question}

    if not la_cle:
        base["panne"] = ("Il me manque la cle de Nebius. Elle se met dans la "
                         "page http://127.0.0.1:8796 du cockpit. Je prefere te le dire "
                         "plutot que d'inventer une reponse.")
        base["duree_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return base

    if essai:
        base["panne"] = None
        base["reponse"] = None
        base["duree_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return base

    charge = json.dumps({
        "model": MODELE,
        "messages": [{"role": "system", "content": CONSIGNE},
                     {"role": "user", "content": question}],
        "max_tokens": JETONS,
        "temperature": 0,
    }).encode("utf-8")
    req = urllib.request.Request(ADRESSE, data=charge, headers={
        "Authorization": "Bearer " + la_cle,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=patience) as r:
            d = json.loads(r.read().decode("utf-8"))
        choix = d["choices"][0]
        message = choix.get("message") or {}
        texte = (message.get("content") or "").strip()

        if not texte:
            # Le modele a tout depense en reflexion. Sa reflexion est dans
            # "reasoning_content" — on ne la rend JAMAIS comme si c'etait une
            # reponse : ce sont ses brouillons, pas ce qu'il affirme.
            pourquoi = choix.get("finish_reason")
            if pourquoi == "length":
                base["panne"] = ("Le gros cerveau a reflechi si longtemps qu'il "
                                 "n'a plus eu la place de repondre. Je prefere "
                                 "te le dire plutot que de te donner ses "
                                 "brouillons.")
            else:
                base["panne"] = ("Le gros cerveau a rendu une reponse vide "
                                 "(raison donnee : %s)." % pourquoi)
        else:
            plat = _sans_accent(texte)
            base["reponse"] = texte
            base["avoue"] = any(a in plat for a in AVEUX)
            
            # Consignation miroir pour que le grand agent et Patrick voient tout en direct
            try:
                os.makedirs("~/livrables", exist_ok=True)
                with open("~/livrables/arthur_dialogues.log", "a", encoding="utf-8") as f_dialogue:
                    f_dialogue.write(f"[{time.ctime()}] PATRICK ➔ ARTHUR : {question}\n[{time.ctime()}] ARTHUR ➔ PATRICK :\n{texte}\n----------------------------------------\n")
            except Exception:
                pass
    except Exception as e:
        base["panne"] = "Le gros cerveau n'a pas repondu : " + str(e)[:130]

    base["duree_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return base


def chat(messages, max_tokens=220, temperature=0.5, patience=PATIENCE):
    """Un ECHANGE libre avec Nemotron : on donne une liste de messages
    (systeme + histoire de la discussion) et il repond. Sert aux agents du
    jeu qui discutent entre eux. Rend {reponse, panne}."""
    la_cle = cle_du_moment()
    if not la_cle:
        return {"reponse": None, "panne": "cle Nebius absente"}
    charge = json.dumps({"model": MODELE, "messages": messages,
                         "max_tokens": max_tokens,
                         "temperature": temperature}).encode("utf-8")
    req = urllib.request.Request(ADRESSE, data=charge, headers={
        "Authorization": "Bearer " + la_cle, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=patience) as r:
            d = json.loads(r.read().decode("utf-8"))
        txt = (d["choices"][0]["message"].get("content") or "").strip()
        return {"reponse": txt or None,
                "panne": None if txt else "reponse vide (trop de reflexion)"}
    except Exception as e:
        return {"reponse": None, "panne": str(e)[:130]}


def est_pret():
    """Vrai si la cle est la. Sert au cockpit pour allumer un voyant."""
    return bool(cle_du_moment())


if __name__ == "__main__":
    print("  modele  :", MODELE)
    print("  adresse :", ADRESSE)
    print("  cle     :", "presente" if est_pret() else "ABSENTE")
    r = demander("Quelle est la capitale du Cameroun ?")
    print("  essai   :", r.get("reponse") or r.get("panne"))
