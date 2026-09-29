#!/usr/bin/env python3
"""CHOISIR LE GROS CERVEAU D'ARTHUR (la couche 3), EN UNE COMMANDE.

    arthur_cerveau.py              → le cerveau actuel, et les choix possibles
    arthur_cerveau.py qwen         → Qwen, sur Alice (gratuit, à la maison)
    arthur_cerveau.py nebius       → NVIDIA Nemotron, chez Nebius Token Factory (payant)
    arthur_cerveau.py local        → Nemotron local, sur ce PC (ollama, gratuit)

Le changement vaut tout de suite : le moteur relit le réglage à chaque question.
Utilisable par Claude Code, Antigravity, opencode (une commande shell), et par
MCP (outil arthur_cerveau du serveur mcp_arthur_server.py).
Le réglage vit dans reglages-maison.json (ARTHUR_REGLAGES pour un autre fichier).
"""
import json, os, sys, tempfile

CHOIX = {
    "qwen":   "Qwen, sur Alice — gratuit, à la maison",
    "nebius": "NVIDIA Nemotron, chez Nebius Token Factory — payant (celui du concours)",
    "local":  "Nemotron local, sur ce PC (ollama) — gratuit, plus lent",
}
DEFAUT = "qwen"


def fichier():
    # realpath : lancé par le lien ~/bin/arthur-cerveau, le réglage est à côté du VRAI fichier
    return os.environ.get("ARTHUR_REGLAGES") or os.path.join(os.path.dirname(os.path.realpath(__file__)), "reglages-maison.json")


def lire():
    try:
        with open(fichier(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def actuel():
    return lire().get("cerveau_gros") or DEFAUT


def choisir(nom):
    """Change le cerveau. Rend (ok, message). N'écrit rien si le nom est inconnu."""
    nom = (nom or "").strip().lower()
    if nom not in CHOIX:
        return False, "Cerveau inconnu : « %s ». Choix possibles : %s." % (nom, ", ".join(CHOIX))
    d = lire()
    avant = d.get("cerveau_gros") or DEFAUT
    d["cerveau_gros"] = nom
    # écriture atomique : un fichier à moitié écrit casserait tous les réglages d'Arthur
    dossier = os.path.dirname(os.path.abspath(fichier()))
    fd, tmp = tempfile.mkstemp(dir=dossier, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, fichier())
    return True, "Gros cerveau d'Arthur : %s → %s (%s). Actif dès la prochaine question." % (avant, nom, CHOIX[nom])


def etat():
    a = actuel()
    lignes = ["Gros cerveau d'Arthur (couche 3) : %s — %s" % (a, CHOIX.get(a, "?")), "Choix possibles :"]
    lignes += ["  %s %-7s %s" % ("→" if k == a else " ", k, v) for k, v in CHOIX.items()]
    lignes.append("Changer : arthur-cerveau <%s>" % "|".join(CHOIX))
    return "\n".join(lignes)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(etat())
        sys.exit(0)
    ok, msg = choisir(sys.argv[1])
    print(msg)
    sys.exit(0 if ok else 2)
