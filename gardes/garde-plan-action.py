#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GARDE DU PLAN D'ACTION — un problème sans plan ne sert à rien.

POURQUOI CE GARDE EXISTE
Né d'une faute réelle le 16/09/2026. Ses mots : « ta réponse est inutile ;
une réponse sans plan d'action ne me sert à rien ». J'annonçais un blocage
(le harnais refuse, la liste est cassée…) et je m'arrêtais là, sans dire quoi
faire ni quels étaient ses choix.

CE QUE LE GARDE EXIGE, ET RIEN D'AUTRE
Dès que la réponse SIGNALE un problème, un blocage, un refus, une panne, une
régression — elle doit contenir, dans le MÊME message, QUATRE choses :

  1. L'ANALYSE. La cause nommée, OU deux hypothèses et ce qui les sépare.
     (méthode scientifique — voir la compétence « analyse »).
  2. LA SUITE. La prochaine action concrète, précise.
  3. TES POSSIBILITÉS. Les choix offerts à Patrick (au moins deux, ou « une
     seule voie » dit clairement).
  4. LES COMPÉTENCES nécessaires pour la suite (détection de compétence) :
     nommer la ou les compétences/outils qu'il faudra (ex. « analyse »,
     « publier-etude », « beelzebuth »…), ou dire « aucune compétence à part ».

QUAND IL SE TAIT
- La réponse ne signale AUCUN problème (un succès net, une question simple,
  une mesure, une recherche).
- Le même texte a déjà été jugé (empreinte), on ne le juge pas deux fois.

Contrat du crochet Stop : refus en JSON sur la sortie standard, ou rien.
Code 0 dans les deux cas.
"""
import hashlib
import json
import os
import re
import sys
import time

MAISON = os.path.expanduser("~")
ETAT = os.environ.get("GARDE_PLAN_ETAT",
                      os.path.join(MAISON, ".claude/portes/.dernier-juge-plan"))
ATTENTE_MAX = 2.0
PAS = 0.2

# 1. La réponse SIGNALE-T-ELLE un problème / blocage ?
PROBLEME = re.compile(
    r"(\bbloqu[ée]\b|\bblocage\b|\bun mur\b|\ble mur\b|\brefus[ée]?\b|\brefuse\b|"
    r"\béchec\b|\béchou[ée]\b|\bimpossible\b|\bje ne peux pas\b|\bn[’' ]arrive pas\b|"
    r"\bne marche pas\b|\bne fonctionne pas\b|\bpanne\b|\brégression\b|\bregression\b|"
    r"\bclassifier\b|\bclassificateur\b|\bharnais (refuse|bloque|m[’' ]interdit)\b|"
    r"\bcass[ée]\b|\bcoinc[ée]\b|\bça coince\b|\bplante\b|\ba plant[ée]\b|"
    r"\bn[’' ]a pas march[ée]\b|\bne s[’' ]affiche pas\b|\berreur\b)", re.I)

# Exemptions : ces mots disent que le "problème" est déjà résolu -> pas besoin de plan.
RESOLU = re.compile(
    r"(\bc[’' ]est réglé\b|\bc[’' ]est répar[ée]\b|\brésolu\b|\btout est vert\b|"
    r"\bplus de (problème|blocage|souci)\b|\bfausse alerte\b)", re.I)

# 2. L'ANALYSE (cause OU deux hypothèses + ce qui les sépare)
ANALYSE = re.compile(
    r"(\bla cause\b|\bles causes\b|\bcause\s*:|\bla vraie cause\b|\bl[’' ]origine\b|"
    r"\bparce que\b|\bvient de\b|\bvenait de\b|\bhypothèse\b|\bdeux (causes|pistes|"
    r"hypothèses)\b|\bce qui les sépare\b|\bj[’' ]ai analys[ée]\b|\bce qui tranche\b|"
    r"\bd[’' ]où\b)", re.I)

# 3. LA SUITE (prochaine action)
SUITE = re.compile(
    r"(\bla suite\s*:|\bprochaine action\b|\bprochaine étape\b|\bplan d[’' ]action\b|"
    r"\ble plan\s*:|\bce que je fais ensuite\b|\bà faire ensuite\b|\bétape suivante\b)",
    re.I)

# 4. TES POSSIBILITÉS (choix offerts) — lettres (A)(B) ou chiffres 1) 2) acceptés
POSSIBILITES = re.compile(
    r"(\btes possibilités\b|\btes options\b|\bton choix\b|\bau choix\b|\boption\s*1\b|"
    r"\bvoie\s*1\b|\bdeux voies\b|\btrois voies\b|\btu peux\s*:?\s*1\b|"
    r"\bsoit\b.*\bsoit\b|\bchoix\s*:|\b1\).*\b2\)|\b1\.\s.*\b2\.\s|"
    r"\(\s*[aAbB]\s*\).*\(\s*[bBcC]\s*\)|\bune seule voie\b)", re.I | re.S)

# 4bis. Chaque choix doit être EXPLIQUÉ en mots simples, pas juste « (A) (B) ».
# On exige un signe d'explication (un tiret —, une flèche →, « car », « sinon »,
# « = », deux points suivis de mots) DANS la zone des choix. Sans explication,
# un choix comme « (A) je bloque » ne dit pas CE QUI SE PASSE si on le prend.
EXPLICATION = re.compile(
    r"(—|–|→|\bcar\b|\bsinon\b|\bdonc\b|\bpour que\b|\bveut dire\b|"
    r"\bça (coupe|bloque|rallume|protège|évite|permet)\b)", re.I)

# 5. LES COMPÉTENCES nécessaires
COMPETENCES = re.compile(
    r"(\bcompétences?\b|\bla compétence\b|\bil faudra la compétence\b|"
    r"\baucune compétence\b|\boutil nécessaire\b|\bskill\b)", re.I)


def dernier_message(chemin):
    if not chemin or not os.path.exists(chemin):
        return ""
    dernier = ""
    try:
        with open(chemin, encoding="utf-8", errors="replace") as f:
            for ligne in f:
                try:
                    o = json.loads(ligne)
                except Exception:
                    continue
                if o.get("type") != "assistant":
                    continue
                c = (o.get("message") or {}).get("content")
                if isinstance(c, str):
                    dernier = c
                elif isinstance(c, list):
                    bouts = [b.get("text", "") for b in c
                             if isinstance(b, dict) and b.get("type") == "text"]
                    if any(b.strip() for b in bouts):
                        dernier = " ".join(bouts)
    except OSError:
        return ""
    return dernier


def texte_juge(donnees):
    for cle in ("last_assistant_message", "assistant_message", "message"):
        v = donnees.get(cle)
        if isinstance(v, str) and v.strip():
            return v
    return dernier_message(donnees.get("transcript_path"))


def fautes(texte):
    """Rend la liste de ce qui manque, vide si la réponse passe."""
    if not PROBLEME.search(texte):
        return []
    if RESOLU.search(texte):
        return []
    manque = []
    if not ANALYSE.search(texte):
        manque.append("L'ANALYSE MANQUE (la cause, ou deux hypothèses + ce qui les sépare)")
    if not SUITE.search(texte):
        manque.append("LA SUITE MANQUE (la prochaine action)")
    if not POSSIBILITES.search(texte):
        manque.append("TES POSSIBILITÉS MANQUENT (ses choix, au moins deux)")
    elif not EXPLICATION.search(texte):
        manque.append("TES POSSIBILITÉS NE SONT PAS EXPLIQUÉES (chaque choix "
                      "doit dire, en mots simples, CE QUI SE PASSE si on le prend)")
    if not COMPETENCES.search(texte):
        manque.append("LES COMPÉTENCES NÉCESSAIRES MANQUENT (nomme-les, ou « aucune »)")
    return manque


def main():
    try:
        donnees = json.load(sys.stdin)
    except Exception:
        return 0
    texte = texte_juge(donnees)
    tp = donnees.get("transcript_path")
    vu = ""
    try:
        with open(ETAT, encoding="utf-8") as f:
            vu = f.read().strip()
    except OSError:
        pass
    empreinte = hashlib.sha1(texte.encode("utf-8")).hexdigest()
    fin = time.time() + ATTENTE_MAX
    while empreinte == vu and time.time() < fin and tp:
        time.sleep(PAS)
        texte = dernier_message(tp)
        empreinte = hashlib.sha1(texte.encode("utf-8")).hexdigest()
    if empreinte == vu or not texte.strip():
        return 0
    try:
        os.makedirs(os.path.dirname(ETAT), exist_ok=True)
        with open(ETAT, "w", encoding="utf-8") as f:
            f.write(empreinte)
    except OSError:
        pass
    f = fautes(texte)
    if not f:
        return 0
    print(json.dumps({
        "decision": "block",
        "reason": (
            "GARDE DU PLAN D'ACTION — refuse. " + " | ".join(f) + ".\n\n"
            "Tu signales un problème. Un problème sans plan ne sert à rien.\n"
            "Refais ta réponse avec, dans le même message, ces quatre choses :\n"
            "  1. L'ANALYSE — la cause nommée, ou deux hypothèses et ce qui\n"
            "     les sépare (méthode scientifique).\n"
            "  2. LA SUITE — écris « La suite : » PUIS la prochaine action\n"
            "     concrète (les deux points comptent).\n"
            "  3. TES POSSIBILITÉS — au moins deux choix, et CHAQUE choix\n"
            "     EXPLIQUÉ en mots simples : ce qu'il veut dire ET ce qui se\n"
            "     passe si Patrick le prend. Un tiret « — » relie le choix à\n"
            "     son explication.\n"
            "     Exemple clair :\n"
            "       (A) Je bloque Antigravity — il ne pourra plus se lancer,\n"
            "           donc il ne gaspillera plus tes jetons.\n"
            "       (B) Je le laisse tourner — pratique, mais il peut brûler\n"
            "           des jetons s'il boucle.\n"
            "     Mauvais (refusé) : « (A) bloquer (B) laisser » — on ne\n"
            "     comprend pas ce que ça change.\n"
            "  4. LES COMPÉTENCES nécessaires pour la suite — nomme-les, ou\n"
            "     dis « aucune compétence à part ».\n\n"
            "Si tu n'as pas encore la cause, dis « je ne sais pas encore, voilà\n"
            "ce qui trancherait » — mais donne quand même la suite et ses choix."),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
