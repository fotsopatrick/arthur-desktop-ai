#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GARDE DU SAVOIR — le mur qui decide seul si une fiche entre dans le savoir.

APP RENTISSAGE BOTTOM-UP, 3e temps (21/09/2026).

Le veilleur prepare des fiches ; le GARDE, executable retournant un code,
refuse ou valide. Il n'est pas un prompt : il est branche dans la boucle, et
les epreuves l'appellent comme un programme.

TROIS PORTES, dans l'ordre :

  PORTE 1 — SOURCE DATEE  : une fiche sans source datee est MOU. Sans elle,
        aucune preuve. Refus -> quarantaine (exit 1).
  PORTE 2 — CONTRADICTION : si les mots de la fiche recoupent les mots d'un
        savoir existant ET que la reponse diffe sur le fond, on ne joue pas
        les histoires : on n'ecrase pas le connu sur un coup (exit 1).
  PORTE 3 — ECRITURE      : fiche saine -> ecrite dans le registre actif,
        sortie de l'attente (exit 0).

Le registre ecrit est celui du dossier de travail (HAICHI_SAVOIR_DIR) s'il
est fourni, jamais le vrai savoir de Patrick lors des epreuves.

Usages :
  garde-savoir.py --sans-source                -> refuse (fiche sans source)
  garde-savoir.py --question Q --reponse R
                  --source S --date AAAA-MM-JJ -> juge une fiche construite
  garde-savoir.py                              -> juge la premiere fiche de
                                                   fiches-attente.json
"""
import json
import os
import re
import sys
import time

try:
    from savoir_commun import mots_depuis, confiance_sur
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from savoir_commun import mots_depuis, confiance_sur


def _chemin(nom):
    # (29/09) Par defaut, le dossier du DEPOT — celui que lit le moteur —
    # et non le dossier courant : lance d'ailleurs (client MCP), le garde
    # ecrivait un registre qu'Arthur ne voyait jamais.
    dossier = os.environ.get("HAICHI_SAVOIR_DIR") or \
        os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dossier, nom)


def _ecrire_json(chemin, donnees):
    """Ecriture atomique (voir ecriture_sure.py)."""
    from ecriture_sure import ecrire_json
    ecrire_json(chemin, donnees)


def _charger_registre():
    for nom in ("registre_connaissances.json", "registre_exemple.json"):
        chemin = _chemin(nom)
        if os.path.exists(chemin):
            # (29/09) Un registre de travail illisible ne doit PAS ceder la
            # place a l'exemple : _valide reecrirait ensuite l'exemple par-
            # dessus le savoir de travail, qui serait perdu. On s'arrete.
            return json.load(open(chemin, encoding="utf-8")), chemin
    return {}, _chemin("registre_connaissances.json")


def _date_valide(date):
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date or "")))


def _mots_des_mots(liste):
    """Aplatit une liste de mots (certains contenant des espaces) en mots un."""
    out = set()
    for mot in liste or []:
        for m in re.split(r"[^A-Za-zÀ-ÿ0-9]+", str(mot).lower()):
            if m:
                out.add(m)
    return out


def _refuse(registre_attente, fiche, raison, chemin_attente):
    """Ecrit la fiche en QUARANTAINE, la retire de l'attente, et crie."""
    quin = _chemin("quarantaine.json")
    quar = []
    if os.path.exists(quin):
        try:
            quar = json.load(open(quin, encoding="utf-8"))
        except Exception:
            quar = []
    quar.append({**fiche, "motif_refus": raison, "date_refus": time.strftime("%Y-%m-%d")})
    _ecrire_json(quin, quar)

    if registre_attente:
        attente, _ = registre_attente
        attente = [f for f in attente if f.get("_lacune") != fiche.get("_lacune")]
        _ecrire_json(chemin_attente, attente)

    print("REFUS : %s" % raison)
    return 1


def _valide(registre, chemin_registre, fiche, registre_attente, chemin_attente):
    cle = None
    for k, v in registre.items():
        if v.get("answer") == fiche.get("answer") and _mots_des_mots(v.get("mots")) == \
                _mots_des_mots(fiche.get("mots")):
            cle = k
            break
    if cle is None:
        # time_ns : deux fiches validees dans la meme seconde ne s'ecrasent plus
        cle = "apprentissage_%s" % time.time_ns()
        while cle in registre:
            cle += "_"
    registre[cle] = {
        "mots": fiche["mots"],
        "think": fiche["think"],
        "answer": fiche["answer"],
        "source": fiche.get("source", ""),
        "date_capture": fiche.get("date_capture", ""),
        "confiance": _confiance(fiche),
    }
    _ecrire_json(chemin_registre, registre)

    if registre_attente:
        attente, _ = registre_attente
        attente = [f for f in attente if f.get("_lacune") != fiche.get("_lacune")]
        _ecrire_json(chemin_attente, attente)
    print("VALIDE : fiche ecrite dans le registre (%s)" % cle)
    return 0


def _mots_recoupent(a, b):
    """Forte ressemblance ? >= 60% des mots de la plus petite liste dans l'autre."""
    seta, setb = _mots_des_mots(a), _mots_des_mots(b)
    if not seta or not setb:
        return False
    communs = seta & setb
    petit = min(len(seta), len(setb))
    return len(communs) / petit >= 0.6


def _reponses_se_contredisent(existante, nouvelle):
    """Deux reponses sur le meme sujet se contredisent si chacune porte un mot
    SIGNIFICATIF (>= 4 lettres, hors mots vides) absent de l'autre. Pas de
    reponse exacte -> pas de desaccord : la nouvelle repete la meme chose."""
    ea = _mots_des_mots(existante.get("answer", "").split())
    na = _mots_des_mots(nouvelle.get("answer", "").split())
    if not ea or not na:
        return False
    differants = (ea - na) | (na - ea)
    if not differants:
        return False
    mots_differents = [w for w in differants if len(w) >= 4]
    return bool(mots_differents)


def _confiance(fiche):
    """Fiabilite d'une fiche. Une fiche SANS source est legacy (main humaine) :
    on lui rend la fiabilite du connu. Une fiche avec source est jugee par
    confiance_sur (grade de la source + fraicheur de la date)."""
    source = (fiche.get("source") or "").strip()
    if not source:
        return 0.9
    try:
        return confiance_sur(source, fiche.get("date_capture", ""))
    except Exception:
        return 0.5


def juger(fiche, registre, registre_attente, chemin_attente):
    # PORTE 0 (29/09) : une fiche sans reponse ou sans mots n'est pas un savoir.
    # Une reponse vide ne « contredisait » rien et passait toutes les portes.
    if not str(fiche.get("answer") or "").strip() or not fiche.get("mots"):
        return _refuse(registre_attente, fiche, "fiche sans reponse ou sans mots",
                       chemin_attente)

    # PORTE 1 : source datée obligatoire.
    source = (fiche.get("source") or "").strip()
    if not source or source.lower() in ("sans source", "none", "inconnu"):
        return _refuse(registre_attente, fiche, "fiche sans source",
                       chemin_attente)
    if not _date_valide(fiche.get("date_capture")):
        return _refuse(registre_attente, fiche,
                       "fiche sans date de capture valide (%r)" % fiche.get("date_capture"),
                       chemin_attente)

    # PORTE 2 : contradiction avec le savoir existant, departagee par la
    # confiance. La fiche la plus fiable gagne ; la nouvelle ne joue pas les
    # histoires si elle est moins fiable (ou egale) au connu.
    nouvelle_conf = _confiance(fiche)
    a_surclasser = []
    for k, v in registre.items():
        if not isinstance(v, dict) or "mots" not in v:
            continue
        if _mots_recoupent(fiche.get("mots", []), v.get("mots", [])) and \
                _reponses_se_contredisent(v, fiche):
            conf_existante = _confiance(v)
            if conf_existante > nouvelle_conf:
                return _refuse(registre_attente, fiche,
                               "contredit une fiche plus fiable « %s » (confiance %s)" % (k, conf_existante),
                               chemin_attente)
            if conf_existante == nouvelle_conf:
                return _refuse(registre_attente, fiche,
                               "contredit « %s » a confiance egale (%s) : on ne remplace pas le connu" % (k, conf_existante),
                               chemin_attente)
            a_surclasser.append(k)

    if a_surclasser:
        # (29/09) Le connu surclasse n'est plus detruit sans trace : il part
        # dans la quarantaine, d'ou un humain peut le rendre au registre.
        quin = _chemin("quarantaine.json")
        try:
            quar = json.load(open(quin, encoding="utf-8")) if os.path.exists(quin) else []
            if not isinstance(quar, list):
                quar = []
        except Exception:
            quar = []
        for k in a_surclasser:
            quar.append({**registre[k], "_cle": k,
                         "motif_refus": "surclasse par une fiche plus fiable",
                         "date_refus": time.strftime("%Y-%m-%d")})
        _ecrire_json(quin, quar)
        for k in a_surclasser:
            del registre[k]

    # PORTE 3 : écriture.
    chemin_registre = _chemin("registre_connaissances.json")
    return _valide(registre, chemin_registre, fiche,
                   registre_attente, chemin_attente)


def main(argv):
    def arg(nom):
        for i, a in enumerate(argv):
            if a == nom and i + 1 < len(argv):
                return argv[i + 1]
        return None

    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0

    registre, chemin_registre = _charger_registre()

    attente = []
    chemin_attente = _chemin("fiches-attente.json")
    if os.path.exists(chemin_attente):
        try:
            attente = json.load(open(chemin_attente, encoding="utf-8"))
        except Exception:
            attente = []
    registre_attente = (attente, chemin_attente) if attente else None

    # Mode sans-source : forcer une fiche sans source, elle doit etre refusee.
    if "--sans-source" in argv:
        fiche = {"mots": ["test"], "think": "", "answer": "test",
                 "source": "sans source", "date_capture": "2026-09-21",
                 "_lacune": "test-sans-source"}
        return _refuse(registre_attente, fiche, "fiche sans source",
                       chemin_attente)

    if arg("--question") is not None:
        # Fiche construite depuis les arguments de la ligne de commande.
        fiche = {
            "mots": mots_depuis(arg("--question")),
            "think": "Question : %s" % arg("--question"),
            "answer": arg("--reponse") or "",
            "source": arg("--source") or "",
            "date_capture": arg("--date") or "",
            "_lacune": arg("--question"),
        }
        return juger(fiche, registre, registre_attente, chemin_attente)

    # Mode attente : la premiere fiche preparee par le veilleur.
    if not attente:
        print("VAUTANT : rien a juger (aucune fiche en attente).")
        return 0
    fiche = attente[0]
    return juger(fiche, registre, registre_attente, chemin_attente)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))