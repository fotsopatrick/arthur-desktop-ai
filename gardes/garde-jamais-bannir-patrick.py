#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""On ne bannit jamais une adresse sans avoir verifie celle de Patrick d abord.

POURQUOI (17/09/2026). Patrick : « verifier mon ip actuelle avant tout
bannissement », « oui me bloque pas », « faut que ce soit une regle de base ».

Ce jour-la, son adresse maison apparaissait dans les traces de plusieurs
robots — parce que mes propres essais partaient de chez lui. Bannir la liste
telle quelle l aurait enferme dehors de son propre serveur.

Un bannissement se defait, mais seulement si on peut encore entrer. S enfermer
dehors est la seule faute qu on ne peut pas reparer soi-meme.

CE QUE FAIT CE GARDE : il refuse tout geste qui bannit, tant que l adresse de
Patrick n a pas ete relevee. Pour la relever :

    python3 ~/outils/quelle-est-mon-adresse.py

Cet outil ecrit un temoin qui vaut quinze minutes. Ensuite, le bannissement
passe.
"""
import json, os, pathlib, re, sys, time

REFUS = 2
TEMOIN = pathlib.Path.home()/".claude"/"portes"/".ip-patrick-verifiee"
FRAICHEUR = 15 * 60

# Les gestes qui enferment quelqu un dehors.
BANNIT = re.compile(
    r"\bipset\s+add\b"
    r"|fail2ban-client\s+set\s+\S+\s+banip"
    r"|\bufw\s+(deny|reject|insert)\s+from\b"
    r"|iptables\s+.*-j\s+(DROP|REJECT)")


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = str((d.get("tool_input") or {}).get("command") or "")
    if not cmd or not BANNIT.search(cmd):
        return 0

    try:
        if TEMOIN.exists() and (time.time() - TEMOIN.stat().st_mtime) < FRAICHEUR:
            return 0
    except Exception:
        pass

    print("GARDE DU BANNISSEMENT — REFUS.\n", file=sys.stderr)
    print("Tu vas bannir une adresse, et tu n'as pas verifie celle de "
          "Patrick :\n", file=sys.stderr)
    print("  " + cmd.strip()[:110], file=sys.stderr)
    print("\nLe 17/09/2026, son adresse maison apparaissait dans les traces de "
          "plusieurs robots — c'etaient mes propres essais, partis de chez lui. "
          "Bannir la liste telle quelle l'aurait enferme dehors.", file=sys.stderr)
    print("\nUn bannissement se defait, mais seulement si on peut encore "
          "entrer. S'enfermer dehors ne se repare pas tout seul.",
          file=sys.stderr)
    print("\nReleve d'abord son adresse :", file=sys.stderr)
    print("  python3 ~/outils/quelle-est-mon-adresse.py", file=sys.stderr)
    print("\nEnsuite le bannissement passe, pendant quinze minutes.",
          file=sys.stderr)
    return REFUS


if __name__ == "__main__":
    sys.exit(main())
