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


# ── LE CALCUL ────────────────────────────────────────────────────────────────
# Ne le 16/09/2026. A la question « combien font 17 fois 23 ? », Arthur
# sortait un circuit sur les rappels. Pourquoi : « combien » et « font » sont
# des mots qu'il ignore, il ne lui restait que « fois » — et « fois » se
# trouve dans un circuit. Il repondait donc a cote, avec aplomb.
#
# La reparation : un calculateur qui reconnait un calcul AVANT toute regle.
# Il ne fait JAMAIS tourner le texte de la question comme du programme
# (« eval »), parce que ce serait ouvrir la porte a n'importe quoi. Il lit les
# nombres et le signe lui-meme, et refuse tout ce qu'il ne reconnait pas.

# Les expressions de DEUX mots se lisent en premier : « divise par » doit
# compter pour UN seul signe. Sinon « 144 divise par 12 » trouvait deux signes
# (« divise » et « par ») et Arthur se taisait au lieu de repondre 12.
_EXPRESSIONS = [
    (["divise par", "divises par", "divisee par"], "/"),
    (["multiplie par", "multiplies par", "multipliee par"], "*"),
]

# « par » tout seul ne veut rien dire : il accompagne « divise » ou
# « multiplie », jamais l'un des deux a lui seul. Il est donc retire d'ici.
_SIGNES = [
    (["plus", "+", "ajoute", "additionne"],          "+"),
    (["moins", "-", "soustrais", "enleve"],          "-"),
    (["fois", "x", "*", "multiplie", "multiplies"],  "*"),
    (["divise", "divises", "/", "sur"],              "/"),
]


def _lire_un_calcul(question):
    """Rend (nombre, signe, nombre) si la question EST un calcul, sinon None.

    On veut exactement deux nombres et un seul signe. Tout le reste est
    refuse : mieux vaut ne pas repondre que repondre a cote.
    """
    # On enleve la ponctuation, MAIS on garde le point et la virgule quand ils
    # sont entre deux chiffres : sinon « 2,5 » devenait « 2 5 », soit deux
    # nombres au lieu d'un, et Arthur refusait de calculer.
    q = " " + str(question).lower() + " "
    q = re.sub(r"[?!;:]", " ", q)
    q = re.sub(r"(?<!\d)[.,]|[.,](?!\d)", " ", q)

    nombres = re.findall(r"-?\d+(?:[.,]\d+)?", q)
    if len(nombres) != 2:
        return None

    # D'abord les expressions de deux mots ; on les efface ensuite pour ne pas
    # les recompter mot par mot.
    trouves = []
    for mots, signe in _EXPRESSIONS:
        for mot in mots:
            if re.search(r"(?<![a-z])" + re.escape(mot) + r"(?![a-z])", q):
                trouves.append(signe)
                q = re.sub(r"(?<![a-z])" + re.escape(mot) + r"(?![a-z])", " ", q)
                break

    if not trouves:
        for mots, signe in _SIGNES:
            for mot in mots:
                motif = (r"(?<![a-z0-9])" + re.escape(mot) + r"(?![a-z0-9])")
                if re.search(motif, q):
                    trouves.append(signe)
                    break
    if len(trouves) != 1:
        return None

    try:
        a = float(nombres[0].replace(",", "."))
        b = float(nombres[1].replace(",", "."))
    except ValueError:
        return None
    return a, trouves[0], b


def _joli(nombre):
    """4.0 s'ecrit « 4 », et 4.5 s'ecrit « 4.5 »."""
    if abs(nombre - round(nombre)) < 1e-9:
        return str(int(round(nombre)))
    return ("%.6f" % nombre).rstrip("0").rstrip(".")


def outil_calcul(question):
    lu = _lire_un_calcul(question)
    if lu is None:
        return None
    a, signe, b = lu
    if signe == "/" and b == 0:
        return "On ne peut pas diviser par zero. Il n'y a pas de resultat."
    resultat = {"+": a + b, "-": a - b, "*": a * b, "/": (a / b if b else None)}[signe]
    mot = {"+": "plus", "-": "moins", "*": "fois", "/": "divise par"}[signe]
    return "%s %s %s = %s" % (_joli(a), mot, _joli(b), _joli(resultat))


# On branche le calcul EN PREMIER : avant toutes les regles, avant les
# circuits. Un calcul n'est jamais une question sur la tour.
_chercher_un_outil_sans_calcul = chercher_un_outil


def chercher_un_outil(question_normalisee):
    """Rend la fonction de l outil qui correspond, ou None.

    Le calcul passe avant tout le reste : sinon un simple « fois » suffisait
    a declencher un circuit de la tour.
    """
    if _lire_un_calcul(question_normalisee) is not None:
        return lambda: outil_calcul(question_normalisee)
    return _chercher_un_outil_sans_calcul(question_normalisee)


# ── LES YEUX SUR LA TOUR (16/09/2026) ────────────────────────────────────────
# Demande de Patrick : « il pourra repondre a "qui est en ligne ?", "le serveur
# va bien ?" en lisant les vraies donnees ». Les deux outils vivent dans
# haichi_outils_tour.py parce qu'ils parlent a une autre machine : si cette
# machine ne repond pas, Arthur doit continuer a marcher sans eux.
try:
    import haichi_outils_tour as _tour
except Exception:          # la tour est injoignable, ou le fichier manque
    _tour = None


def outil_qui_est_en_ligne():
    if _tour is None:
        return ("Je ne peux pas regarder qui est en ligne : l'outil qui parle "
                "a la tour n'a pas pu demarrer. Je prefere te le dire.")
    return _tour.outil_qui_est_en_ligne()


def outil_serveur_va_bien():
    if _tour is None:
        return ("Je ne peux pas regarder la sante du serveur : l'outil qui "
                "parle a la tour n'a pas pu demarrer. Je prefere te le dire.")
    return _tour.outil_serveur_va_bien()


OUTILS.extend([
    (["qui est en ligne", "qui est la", "qui tourne", "quels agents sont la",
      "qui travaille", "qui est allume", "qui est connecte",
      "les agents en ligne", "qui est present"], outil_qui_est_en_ligne),
    (["le serveur va bien", "la tour va bien", "sante du serveur",
      "etat du serveur", "etat de la tour", "le serveur est il en panne",
      "le site marche", "le site est en panne", "tout va bien",
      "y a t il une panne"], outil_serveur_va_bien),
])


# ── AJOUT DU 16/09/2026 (session orel-39, coordonnee avec orel-40) ──────
# Un outil de plus : les agents de la SALLE (dive/salle/releve.json).
# Source DIFFERENTE de celle d'Arthur (lui = conteneurs docker + ports) :
# ici, les 414 agents qui se parlent dans la salle, par famille, et qui
# parle le plus. Ajoute en mode additif : il rejoint /api/outils tout seul.
# Il ne ment pas : si le releve ne repond pas, il le dit.
def outil_agents_salle():
    try:
        d = json.loads(_lire("https://dive.matourdecontrole.fr/salle/releve.json",
                             patience=8))
    except Exception:
        return "Je n arrive pas a lire le releve des agents de la salle."
    gens = d.get("correspondants") or []
    if not gens:
        return "Le releve des agents de la salle est vide."
    fam = {}
    for a in gens:
        f = a.get("famille", "autre")
        fam[f] = fam.get(f, 0) + 1
    top = sorted(gens, key=lambda x: -(x.get("total", 0)))[:3]
    txt = (u"\U0001F465 " + str(len(gens)) + " agents dans la salle. Par famille : "
           + ", ".join("%s %d" % (k, v)
                       for k, v in sorted(fam.items(), key=lambda x: -x[1])))
    txt += ". Les plus actifs : " + ", ".join(
        "%s (%d messages)" % (a.get("nom", "?"), a.get("total", 0)) for a in top) + "."
    return txt


OUTILS.extend([
    (["qui est dans la salle", "les agents de la salle", "qui parle le plus",
      "combien d agents", "agents actifs", "qui est la maintenant"],
     outil_agents_salle),
])


# ── 2e OUTIL DU 16/09/2026 (session orel-65) ───────────────────────────
# « Que font les agents ? » — le meme releve, mais range par FAMILLE :
# combien d agents dans chaque famille, et combien de messages cette
# famille a echanges en tout. Le cockpit appelle les outils SANS mot
# (cockpit.py:1409 fait fonction()), donc cet outil ne demande aucun nom :
# il donne la vue d ensemble, pas un agent precis.
# Il precise aussi combien d agents n ont PAS de cervelle (moteur eteint),
# car c est ce qui dit lesquels sont muets. Il ne ment pas : si le releve
# ne repond pas, il le dit.
def outil_que_font_les_agents():
    try:
        d = json.loads(_lire("https://dive.matourdecontrole.fr/salle/releve.json",
                             patience=8))
    except Exception:
        return "Je n arrive pas a lire le releve des agents de la salle."
    gens = d.get("correspondants") or []
    if not gens:
        return "Le releve des agents de la salle est vide."
    # Par famille : combien d agents, et combien de messages en tout.
    combien = {}
    messages = {}
    sans_cervelle = 0
    for a in gens:
        f = a.get("famille", "autre")
        combien[f] = combien.get(f, 0) + 1
        messages[f] = messages.get(f, 0) + a.get("total", 0)
        if not a.get("cervelle"):
            sans_cervelle += 1
    familles = sorted(combien.keys(), key=lambda k: -messages[k])
    bouts = ["%s : %d agents, %d messages echanges"
             % (f, combien[f], messages[f]) for f in familles]
    txt = (u"\U0001F4CB Ce que font les agents, par famille. "
           + " ; ".join(bouts) + ".")
    txt += (" Au total %d agents ont le moteur eteint (aucune cervelle)."
            % sans_cervelle)
    return txt


OUTILS.extend([
    (["que font les agents", "les agents par famille", "que fait chaque famille",
      "a quoi servent les agents", "les familles d agents",
      "combien d agents sans cervelle", "quels agents sont muets"],
     outil_que_font_les_agents),
])
