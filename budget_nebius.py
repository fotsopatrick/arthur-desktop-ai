# -*- coding: utf-8 -*-
"""LE PLAFOND NEBIUS — aucun appel au-dela d'un nombre de jetons par jour.

Ne le 27/09/2026. Patrick decouvre une dette de 205 $ chez Nebius : « ils ne
permettent meme pas de limiter les jetons ». En septembre, des agents de code
avaient appele le plus gros Nemotron sans compter. Choix de Patrick : un
plafond dans NOTRE code, qui refuse l'appel AVANT qu'il parte.

Un « jeton » : un morceau de mot. Nebius compte les jetons envoyes et recus,
et facture au jeton. Ici on compte les jetons que Nebius dit avoir consommes
(champ « usage » de sa reponse).

Le carnet des depenses : un fichier par jour, dans ~/.local/state/budget-nebius/
(ou BUDGET_NEBIUS_DOSSIER). Le reglage : ~/.config/budget-nebius.json
    {"jetons_par_jour": 100000, "jetons_max_par_appel": 2000}
Carnet abime ou illisible -> on REFUSE (on ne depense pas a l'aveugle).
Le meme carnet sert a Arthur et a Uatu : un seul plafond pour toute la maison.

Epreuve : test_budget_nebius.py
"""
import datetime
import fcntl
import json
import os

DEFAUT = {"jetons_par_jour": 100000, "jetons_max_par_appel": 2000}
REGLAGE = os.path.expanduser("~/.config/budget-nebius.json")


def _dossier():
    d = os.environ.get("BUDGET_NEBIUS_DOSSIER") or os.path.expanduser("~/.local/state/budget-nebius")
    os.makedirs(d, exist_ok=True)
    return d


def reglages():
    r = dict(DEFAUT)
    try:
        with open(REGLAGE, encoding="utf-8") as f:
            r.update({k: int(v) for k, v in json.load(f).items() if k in DEFAUT})
    except (OSError, ValueError):
        pass
    return r


def _fichier(jour):
    return os.path.join(_dossier(), f"{jour}.json")


def _lire(jour):
    """(jetons deja depenses, erreur) ; erreur = texte si le carnet est abime."""
    try:
        with open(_fichier(jour), encoding="utf-8") as f:
            d = json.load(f)
        return int(d.get("jetons", 0)), None
    except FileNotFoundError:
        return 0, None
    except (OSError, ValueError, TypeError) as e:
        return 0, f"le carnet des depenses Nebius est abime ({type(e).__name__})"


def autoriser(estimation, reglages=None, jour=None):
    """(permis, raison, reste). Refuse si le plafond du jour serait depasse."""
    r = reglages or globals()["reglages"]()
    jour = jour or datetime.date.today().isoformat()
    deja, erreur = _lire(jour)
    if erreur:
        return False, f"Je n'appelle pas Nebius : {erreur}. Je prefere ne rien depenser a l'aveugle.", 0
    reste = r["jetons_par_jour"] - deja
    if deja + max(0, int(estimation)) > r["jetons_par_jour"]:
        return (False,
                f"Plafond Nebius du jour atteint ({deja} jetons sur {r['jetons_par_jour']}). "
                f"Je n'envoie rien avant demain ; je reponds avec le cerveau de la maison.", max(0, reste))
    return True, "", reste


def max_par_appel(demande, reglages=None):
    r = reglages or globals()["reglages"]()
    return min(int(demande), r["jetons_max_par_appel"])


def noter(usage, modele, qui, jour=None, estimation=0):
    """Ajoute au carnet ce que l'appel a coute (usage rendu par Nebius, sinon l'estimation)."""
    jour = jour or datetime.date.today().isoformat()
    jetons = int((usage or {}).get("total_tokens") or 0) or int(estimation)
    chemin = _fichier(jour)
    with open(chemin, "a+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        brut = f.read()
        try:
            d = json.loads(brut) if brut.strip() else {}
        except ValueError:
            d = {"jetons": 10 ** 9, "abime_avant": brut[:80]}   # abime : on bloque la journee
        d["jetons"] = int(d.get("jetons", 0)) + jetons
        d["appels"] = int(d.get("appels", 0)) + 1
        d.setdefault("par_qui", {})
        d["par_qui"][qui] = d["par_qui"].get(qui, 0) + jetons
        d["dernier"] = {"modele": modele, "jetons": jetons, "estime": not (usage or {}).get("total_tokens"),
                        "quand": datetime.datetime.now().isoformat(timespec="seconds")}
        f.seek(0)
        f.truncate()
        f.write(json.dumps(d, ensure_ascii=False))
    return jetons


def etat(jour=None):
    jour = jour or datetime.date.today().isoformat()
    deja, erreur = _lire(jour)
    r = reglages()
    return {"jour": jour, "jetons": deja, "plafond": r["jetons_par_jour"], "erreur": erreur}
