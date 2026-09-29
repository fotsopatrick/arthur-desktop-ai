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

CHOIX_DE_BASE = {
    "qwen":   "Qwen, sur Alice — gratuit, à la maison",
    "nebius": "NVIDIA Nemotron, chez Nebius Token Factory — payant (celui du concours)",
    "local":  "Nemotron local, sur ce PC (ollama) — gratuit, plus lent",
}


def choix_possibles():
    """(29/09) Les trois de base, plus chaque cerveau declare dans
    reglages-maison.json -> "cerveaux" (deepseek, claude... : fournisseurs.py)."""
    choix = dict(CHOIX_DE_BASE)
    try:
        sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
        import fournisseurs
        for nom, f in fournisseurs.cerveaux().items():
            if nom not in choix:
                choix[nom] = "%s (%s) — %s" % (f.get("modele") or "?", f.get("type"),
                                               "payant" if fournisseurs.est_payant(f) else "gratuit")
    except Exception:
        pass
    return choix


CHOIX = CHOIX_DE_BASE   # (compatibilite) — la liste vivante : choix_possibles()
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
    tous = choix_possibles()
    if nom not in tous:
        return False, "Cerveau inconnu : « %s ». Choix possibles : %s." % (nom, ", ".join(tous))
    # (29/09) Un reglage illisible n'est pas un reglage vide : avant, lire()
    # rendait {} et on reecrivait un fichier ne contenant QUE cerveau_gros —
    # les adresses des machines etaient effacees. On refuse, et on le dit.
    from ecriture_sure import lire_json, ecrire_json, FichierAbime
    try:
        d = lire_json(fichier(), {})
    except FichierAbime as e:
        return False, "Je ne change rien : %s. Répare-le d'abord." % e
    if not isinstance(d, dict):
        return False, "Je ne change rien : %s n'est pas un objet JSON." % fichier()
    avant = d.get("cerveau_gros") or DEFAUT
    d["cerveau_gros"] = nom
    ecrire_json(fichier(), d, indent=2)   # atomique
    return True, "Gros cerveau d'Arthur : %s → %s (%s). Actif dès la prochaine question." % (avant, nom, tous[nom])


def etat():
    a = actuel()
    tous = choix_possibles()
    lignes = ["Gros cerveau d'Arthur (couche 3) : %s — %s" % (a, tous.get(a, "?")), "Choix possibles :"]
    lignes += ["  %s %-9s %s" % ("→" if k == a else " ", k, v) for k, v in tous.items()]
    lignes.append("Changer : arthur-cerveau <%s>" % "|".join(tous))
    lignes.append("Ajouter un cerveau (DeepSeek, Claude, Mistral...) : voir cerveaux.exemple.json")
    return "\n".join(lignes)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(etat())
        sys.exit(0)
    ok, msg = choisir(sys.argv[1])
    print(msg)
    sys.exit(0 if ok else 2)
