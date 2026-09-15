#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LES OUTILS DE HAICHI — pour aller VOIR au lieu de reciter.

Une regle ecrite ne change jamais : « la tour est une plateforme de pilotage ».
Un OUTIL, lui, va regarder maintenant : quelle heure il est, quels modules sont
allumes, si la veille du matin tourne. C est ce qui manquait a Haichi.

Ne le 15/09/2026, d une demande de Patrick : « il n a pas acces a l outil
veille IA ». La reponse honnete etait : la veille IA ne tourne meme pas.
Un outil doit pouvoir dire ca, au lieu d inventer.

Chaque outil a : des mots qui le reveillent, et une fonction qui va voir.
"""
import json, socket, re, os, datetime, urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
COCKPIT = "http://127.0.0.1:8790"


def _lire(url, patience=6):
    with urllib.request.urlopen(url, timeout=patience) as r:
        return r.read().decode("utf-8", "replace")


def _port_ouvert(port, patience=0.4):
    s = socket.socket(); s.settimeout(patience)
    try:
        s.connect(("127.0.0.1", int(port))); return True
    except Exception:
        return False
    finally:
        s.close()


def _modules():
    """Rend (allumes, eteints) : deux listes de (nom, port)."""
    try:
        d = json.load(open(os.path.join(ICI, "config.json"), encoding="utf-8"))
    except Exception:
        return [], []
    allumes, eteints = [], []
    for p in d.get("pages", []):
        m = re.search(r":(\d+)", p.get("url", ""))
        if not m:
            continue
        nom, port = p.get("nom", "?"), m.group(1)
        (allumes if _port_ouvert(port) else eteints).append((nom, port))
    return allumes, eteints


# ── les outils, un par un ──────────────────────────────────────────────────

def outil_heure():
    m = datetime.datetime.now()
    jours = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
    mois = ["janvier","fevrier","mars","avril","mai","juin","juillet","aout",
            "septembre","octobre","novembre","decembre"]
    return (f"🕐 Il est {m.strftime('%H:%M')} — nous sommes {jours[m.weekday()]} "
            f"{m.day} {mois[m.month-1]} {m.year}. (heure de cette machine)")


def outil_modules():
    allumes, eteints = _modules()
    if not allumes and not eteints:
        return "Je n arrive pas a lire la liste des modules du cockpit."
    txt = (f"🎛️ Le cockpit a {len(allumes) + len(eteints)} modules : "
           f"{len(allumes)} allumes et {len(eteints)} eteints.")
    if eteints:
        txt += "\n\nLes eteints :\n" + "\n".join(
            f"  • {n} (port {p})" for n, p in eteints[:12])
        if len(eteints) > 12:
            txt += f"\n  • ... et {len(eteints)-12} autres."
    return txt


def outil_veille():
    allume = _port_ouvert(8011)
    if not allume:
        return ("📰 La veille IA du matin est ETEINTE. Son module vit sur le "
                "port 8011 de cette machine, et personne n y repond. "
                "Je ne peux donc rien en lire — je ne vais pas inventer.")
    try:
        page = _lire("http://127.0.0.1:8011/", 8)
        titres = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", page, re.S)[:6]
        titres = [re.sub(r"<[^>]+>", "", t).strip() for t in titres]
        if titres:
            return "📰 La veille IA du matin dit :\n\n" + "\n".join(
                f"  • {t[:110]}" for t in titres if t)
        return "📰 La veille IA du matin repond, mais je n y trouve aucun titre."
    except Exception as e:
        return f"📰 La veille IA du matin repond mal : {str(e)[:70]}"


def outil_reseau():
    try:
        d = json.loads(_lire(COCKPIT + "/api/reseau/statut", 8))
        r = d.get("resume", {})
        c = d.get("capture", {})
        return (f"🌐 Reseau de la machine {c.get('machine','?')}, releve a "
                f"{c.get('maintenant','?')} : {r.get('connexions','?')} connexions "
                f"ouvertes, {r.get('process','?')} programmes qui parlent au reseau.")
    except Exception as e:
        return f"🌐 Je n arrive pas a lire l etat du reseau : {str(e)[:70]}"


def outil_moi():
    try:
        import nano_moteur_ultra as m
        n = len(m.ENGINE.base)
        circuits = len([k for k in m.ENGINE.base if k.startswith("circuit")])
        return (f"🧠 Je connais {n} sujets par coeur, dont {circuits} circuits de la tour. "
                f"Je reponds en moins d un millieme de seconde quand la reponse est "
                f"dans mes regles. Sinon je vais voir ailleurs, et si personne ne "
                f"sait, je le dis.")
    except Exception as e:
        return f"🧠 Je n arrive pas a me compter moi-meme : {str(e)[:70]}"


# ── quel outil pour quelle question ───────────────────────────────────────
# Chaque outil est reveille par des expressions. On exige une expression
# ENTIERE, pas un mot isole : sinon "l heure de la tour" reveillerait l horloge.
OUTILS = [
    (["quelle heure", "il est quelle heure", "heure est il", "quel jour",
      "quelle date", "on est quel jour", "date du jour"], outil_heure),
    (["modules eteints", "modules allumes", "modules du cockpit",
      "combien de modules", "quels modules", "etat du cockpit"], outil_modules),
    (["veille ia", "veille du matin", "la veille"], outil_veille),
    (["etat du reseau", "combien de connexions", "le reseau de la machine"], outil_reseau),
    (["combien de sujets", "que sais tu faire", "qui es tu", "tes regles",
      "combien tu connais"], outil_moi),
]


def chercher_un_outil(question_normalisee):
    """Rend la fonction de l outil qui correspond, ou None."""
    for expressions, fonction in OUTILS:
        for e in expressions:
            if e in question_normalisee:
                return fonction
    return None


if __name__ == "__main__":
    for nom, f in [("heure", outil_heure), ("modules", outil_modules),
                   ("veille", outil_veille), ("reseau", outil_reseau),
                   ("moi", outil_moi)]:
        print("=" * 60); print(nom.upper()); print(f())
