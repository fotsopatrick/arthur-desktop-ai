#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ne jamais reposer a Patrick une question qu il a deja tranchee.

POURQUOI (17/09/2026). Ses mots, excede :
  « j ai deja dit oui... ceci plein de fois »
  « pourquoi tu me reposes la question mille fois »
  « tu sais pas faire une sauvegarde tes questions => mes reponses »

Chaque question reposee lui coute du temps, et dit toujours la meme chose :
je n ai pas garde sa reponse. Ce garde lit le carnet avant de laisser passer
une question.
"""
import importlib.util, json, pathlib, re, sys

REFUS = 2
CARNET = pathlib.Path.home()/"outils"/"carnet-des-reponses.py"


def _carnet():
    if not CARNET.exists():
        return None
    spec = importlib.util.spec_from_file_location("carnet", CARNET)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    texte = ""
    for champ in ("last_message", "message", "assistant_message"):
        if d.get(champ):
            texte += str(d[champ]) + "\n"
    if not texte:
        return 0

    # On ne regarde que les questions posees dans un bloc « demandes ».
    blocs = re.findall(r"```demandes(.*?)```", texte, re.S)
    if not blocs:
        return 0
    questions = []
    for b in blocs:
        for l in b.splitlines():
            m = re.match(r"\s*quoi\s*:\s*(.+)", l)
            if m:
                questions.append(m.group(1).strip())
    if not questions:
        return 0

    c = _carnet()
    if c is None:
        return 0

    deja = [(q, c.deja_repondu(q)) for q in questions]
    deja = [(q, r) for q, r in deja if r]
    if not deja:
        return 0

    print("GARDE DE LA QUESTION DEJA TRANCHEE — REFUS.\n", file=sys.stderr)
    print("Tu reposes une question a laquelle Patrick a deja repondu :\n",
          file=sys.stderr)
    for q, r in deja[:3]:
        print("  Tu demandes : %s" % q[:88], file=sys.stderr)
        print("  Il a repondu : %s\n" % r, file=sys.stderr)
    print("Ses mots, le 17/09/2026 : « pourquoi tu me reposes la question "
          "mille fois ».", file=sys.stderr)
    print("\nFAIS CE QU IL A DIT, et enleve la question de ton message.",
          file=sys.stderr)
    print("Si la situation a vraiment change, dis en quoi — puis agis.",
          file=sys.stderr)
    return REFUS


if __name__ == "__main__":
    sys.exit(main())
