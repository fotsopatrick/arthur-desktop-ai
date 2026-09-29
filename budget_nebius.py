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

LE PLAFOND TOTAL (29/09/2026). Nebius ne permet toujours pas de limiter la
depense, et Patrick a 200 EUR de credits pour TROIS projets. Un plafond par
jour ne suffit pas : 30 jours x 100 000 jetons, c'est beaucoup. Il y a donc
aussi un plafond CUMULE, tous jours confondus, dans le meme carnet partage :
    "jetons_total_max": 3000000       (defaut)
et, si l'on renseigne le prix lu sur la page des tarifs de Nebius :
    "euros_par_million": 1.2, "euros_max": 40
Arthur refuse alors tout appel qui ferait passer la depense estimee au-dela
de euros_max. Le compteur total vit dans total.json, a cote des jours.
Le meme carnet sert a Arthur et a Uatu : un seul plafond pour toute la maison.

Epreuve : test_budget_nebius.py
"""
import datetime
import fcntl
import json
import os

DEFAUT = {"jetons_par_jour": 100000, "jetons_max_par_appel": 2000,
          "jetons_total_max": 3000000, "euros_par_million": 0, "euros_max": 0,
          "paiement_autorise": 0}
REGLAGE = os.path.expanduser("~/.config/budget-nebius.json")


def _dossier():
    d = os.environ.get("BUDGET_NEBIUS_DOSSIER") or os.path.expanduser("~/.local/state/budget-nebius")
    os.makedirs(d, exist_ok=True)
    return d


def reglages():
    r = dict(DEFAUT)
    try:
        with open(REGLAGE, encoding="utf-8") as f:
            r.update({k: float(v) if k.startswith("euros") else int(v)
                      for k, v in json.load(f).items() if k in DEFAUT})
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


def _lire_total():
    """(jetons depenses depuis toujours, erreur)."""
    try:
        with open(os.path.join(_dossier(), "total.json"), encoding="utf-8") as f:
            return int(json.load(f).get("jetons", 0)), None
    except FileNotFoundError:
        return 0, None
    except (OSError, ValueError, TypeError, AttributeError) as e:
        return 0, f"le compteur total Nebius est abime ({type(e).__name__})"


def paiement_autorise(reglages=None):
    """(permis, raison). L'INTERRUPTEUR (29/09/2026).

    Patrick : « la facture a depasse les credits offerts, 0 euro pour ce
    projet ». Par defaut, AUCUN appel payant ne part. Pour rouvrir, il faut
    ecrire les TROIS choses dans ~/.config/budget-nebius.json :
        {"paiement_autorise": 1, "euros_par_million": <prix lu chez Nebius>,
         "euros_max": <ce qu'on accepte de depenser, en euros>}
    Un oubli, un zero, un fichier absent : c'est non."""
    r = dict(DEFAUT)
    r.update(reglages or globals()["reglages"]())
    if not r.get("paiement_autorise"):
        return False, ("Nebius est coupe : aucun plafond en euros n'est autorise "
                       "(0 EUR prevu pour ce projet). Je n'envoie rien.")
    if not (float(r.get("euros_par_million") or 0) > 0 and float(r.get("euros_max") or 0) > 0):
        return False, ("Nebius est coupe : il faut un prix (euros_par_million) ET un "
                       "plafond (euros_max) pour autoriser une depense. Je n'envoie rien.")
    return True, ""


def euros(jetons, reglages=None):
    """Depense estimee en euros, ou None si le prix n'est pas renseigne."""
    r = reglages or globals()["reglages"]()
    prix = float(r.get("euros_par_million") or 0)
    return round(jetons / 1e6 * prix, 2) if prix > 0 else None


def autoriser(estimation, reglages=None, jour=None):
    """(permis, raison, reste). Refuse si le plafond du jour, le plafond total
    en jetons, ou le plafond en euros serait depasse."""
    r = dict(DEFAUT)
    r.update(reglages or globals()["reglages"]())
    jour = jour or datetime.date.today().isoformat()
    deja, erreur = _lire(jour)
    total, erreur_total = _lire_total()
    erreur = erreur or erreur_total
    if erreur:
        return False, f"Je n'appelle pas Nebius : {erreur}. Je prefere ne rien depenser a l'aveugle.", 0
    est = max(0, int(estimation))
    if total + est > r["jetons_total_max"]:
        return (False,
                f"Plafond TOTAL Nebius atteint ({total} jetons sur {r['jetons_total_max']}). "
                f"Je n'envoie plus rien ; je reponds avec le cerveau de la maison.", 0)
    cout = euros(total + est, r)
    if cout is not None and r.get("euros_max") and cout > float(r["euros_max"]):
        return (False,
                f"Plafond en euros atteint (environ {euros(total, r)} EUR sur {r['euros_max']}). "
                f"Je n'envoie plus rien.", 0)
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
    # le compteur TOTAL, sous le meme verrou de principe
    with open(os.path.join(_dossier(), "total.json"), "a+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        brut = f.read()
        try:
            t = json.loads(brut) if brut.strip() else {}
        except ValueError:
            t = {"jetons": 10 ** 12, "abime_avant": brut[:80]}   # abime : on bloque tout
        t["jetons"] = int(t.get("jetons", 0)) + jetons
        t["appels"] = int(t.get("appels", 0)) + 1
        t.setdefault("par_qui", {})
        t["par_qui"][qui] = t["par_qui"].get(qui, 0) + jetons
        f.seek(0)
        f.truncate()
        f.write(json.dumps(t, ensure_ascii=False))
    return jetons


def etat(jour=None):
    jour = jour or datetime.date.today().isoformat()
    deja, erreur = _lire(jour)
    total, erreur_total = _lire_total()
    r = reglages()
    return {"jour": jour, "jetons": deja, "plafond": r["jetons_par_jour"],
            "total": total, "plafond_total": r["jetons_total_max"],
            "euros": euros(total, r), "euros_max": r["euros_max"] or None,
            "erreur": erreur or erreur_total}


if __name__ == "__main__":
    print(json.dumps(etat(), ensure_ascii=False, indent=2))
