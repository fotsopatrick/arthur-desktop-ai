#!/usr/bin/env python3
"""Les yeux d'Arthur sur la tour : qui est en ligne, et si le serveur va bien.

NE LE 16/09/2026, D'UNE DEMANDE DE PATRICK
------------------------------------------
Ses mots : « donner a Haichi les outils du cockpit… il pourra repondre a
"qui est en ligne ?", "le serveur va bien ?" en lisant les vraies donnees ».

DEUX REGLES QUI NE BOUGENT PAS
1. On MESURE, on ne devine pas. Chaque chiffre rendu vient d'une commande
   qui vient de tourner. Si la mesure rate, Arthur le DIT — il n'invente
   jamais un serveur en bonne sante.
2. On ne fait jamais attendre Patrick deux fois pour la meme chose. Joindre
   la tour prend une a deux secondes ; on garde donc la reponse une minute.

POURQUOI ON NE LIT PAS LA BASE DE DONNEES
Le 16/09/2026, la mesure a montre qu'il n'y a PLUS de conteneur de base ni
d'Odoo allumes sur la tour (leurs donnees sont sauvees dans les volumes
tour_db-data et tour_odoo-data, mais rien ne tourne). Un outil qui
interrogerait la base repondrait donc toujours « rien ». On regarde ce qui
tourne vraiment, ce qui est la seule verite utile.
"""
import json
import os
import re
import socket
import subprocess
import time
import urllib.request

# ── LE CACHE ────────────────────────────────────────────────────────────────
_GARDE_SECONDES = 60
_memoire = {}


def _en_memoire(cle, fabriquer):
    """Rend la reponse gardee si elle a moins d'une minute, sinon la refait."""
    maintenant = time.time()
    vieux = _memoire.get(cle)
    if vieux and (maintenant - vieux[0]) < _GARDE_SECONDES:
        return vieux[1]
    frais = fabriquer()
    _memoire[cle] = (maintenant, frais)
    return frais


# ── PARLER A LA TOUR ────────────────────────────────────────────────────────
_SSH = [
    "ssh", "-o", "BatchMode=yes",
    "-o", "IdentityAgent=" + os.path.expanduser("~/.ssh/agent.sock"),
    "-o", "IdentitiesOnly=yes",
    "-o", "ConnectTimeout=6",
    "tour-vps",
]


def _demander_a_la_tour(commande, patience=20):
    """Rend (texte, None) si ca marche, (None, ce qui a manque) sinon."""
    milieu = dict(os.environ)
    milieu["SSH_AUTH_SOCK"] = os.path.expanduser("~/.ssh/agent.sock")
    try:
        fini = subprocess.run(_SSH + [commande], capture_output=True,
                              text=True, timeout=patience, env=milieu)
    except subprocess.TimeoutExpired:
        return None, ("La tour n'a pas repondu en %d secondes." % patience)
    except OSError as e:
        return None, ("Je n'ai pas pu lancer la connexion : %s" % e)
    if fini.returncode != 0:
        souci = (fini.stderr or "").strip().splitlines()
        souci = souci[-1] if souci else "raison inconnue"
        if "Permission denied" in souci or "publickey" in souci:
            souci = ("la porte de la tour est fermee. Il faut lancer "
                     "~/connexion-tour.sh une fois, et taper la phrase secrete.")
        return None, souci[:150]
    return fini.stdout, None


# ── LES MACHINES DE LA MAISON ───────────────────────────────────────────────
def _machines_de_la_maison():
    """Ou sont les machines. Elles ne sont PAS ecrites ici.

    Ne le 16/09/2026 : leurs adresses etaient en dur dans ce fichier, et le
    depot allait devenir public. Elles vivent maintenant dans
    reglages-maison.json, qui reste a la maison. Sans ce fichier, Arthur ne
    regarde que la machine sur laquelle il tourne — et il marche quand meme.
    """
    defaut = [("cette machine", "127.0.0.1", 8790, "le cockpit")]
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "reglages-maison.json")
    try:
        with open(chemin, encoding="utf-8") as f:
            lues = json.load(f).get("machines")
        return [tuple(m) for m in lues] if lues else defaut
    except (OSError, ValueError, TypeError):
        return defaut


_MAISON = _machines_de_la_maison()


def _frapper(hote, port, patience=1.5):
    """Frappe a la porte d'une machine. Rend vrai si quelqu'un ouvre."""
    try:
        with socket.create_connection((hote, port), timeout=patience):
            return True
    except OSError:
        return False


# ── OUTIL 1 : QUI EST EN LIGNE ? ────────────────────────────────────────────
def _releve_qui_est_en_ligne():
    lignes = []

    texte, souci = _demander_a_la_tour(
        "docker ps --format '{{.Names}}|{{.Status}}'")
    if souci:
        lignes.append(("tour", None, souci))
    else:
        debout = []
        for ligne in (texte or "").strip().splitlines():
            if "|" not in ligne:
                continue
            nom, etat = ligne.split("|", 1)
            if nom.strip():
                debout.append((nom.strip(), etat.strip()))
        lignes.append(("tour", debout, None))

    maison = []
    for nom, hote, port, role in _MAISON:
        maison.append((nom, port, role, _frapper(hote, port)))
    lignes.append(("maison", maison, None))
    return lignes


def outil_qui_est_en_ligne():
    releve = _en_memoire("qui_en_ligne", _releve_qui_est_en_ligne)
    morceaux = ["👥 QUI EST EN LIGNE — mesure a l'instant, pas une supposition.", ""]

    for quoi, contenu, souci in releve:
        if quoi == "tour":
            morceaux.append("Sur la tour (le serveur qui porte le site) :")
            if souci:
                morceaux.append("   Je n'ai pas pu regarder : " + souci)
            elif not contenu:
                morceaux.append("   Rien ne tourne. C'est anormal.")
            else:
                for nom, etat in contenu:
                    morceaux.append("   · %-22s %s" % (nom, etat))
                morceaux.append("   → %d en marche." % len(contenu))
            morceaux.append("")
        else:
            morceaux.append("A la maison :")
            for nom, port, role, ouvert in contenu:
                morceaux.append("   %s %s porte %d — %s"
                                % ("·" if ouvert else "✗", nom, port, role))
            eteints = [n for n, _, _, o in contenu if not o]
            if eteints:
                morceaux.append("   → %s ne repond pas." % ", ".join(sorted(set(eteints))))
    return "\n".join(morceaux)


# ── OUTIL 2 : LE SERVEUR VA-T-IL BIEN ? ─────────────────────────────────────
_FACADES = [
    ("le site public",      "https://matourdecontrole.fr/",                    {200}),
    ("la vente d'agents",   "https://offreagent.matourdecontrole.fr/",         {200}),
    ("l'accueil de la tour", "https://tour.matourdecontrole.fr/tour/dashboard", {200, 303}),
]


def _releve_sante():
    texte, souci = _demander_a_la_tour(
        "uptime; echo ---; df -h / | tail -1; echo ---; "
        "free -m | sed -n 2p; echo ---; "
        "docker ps -a --format '{{.Names}}|{{.Status}}'")
    mesures = {"souci": souci}
    if not souci:
        bouts = (texte or "").split("---")
        mesures["uptime"] = bouts[0].strip() if len(bouts) > 0 else ""
        mesures["disque"] = bouts[1].strip() if len(bouts) > 1 else ""
        mesures["memoire"] = bouts[2].strip() if len(bouts) > 2 else ""
        mesures["conteneurs"] = bouts[3].strip() if len(bouts) > 3 else ""

    portes = []
    for nom, adresse, bons in _FACADES:
        try:
            d = urllib.request.Request(adresse, method="GET")
            with urllib.request.urlopen(d, timeout=12) as r:
                code = r.getcode()
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception:
            code = 0
        portes.append((nom, adresse, code, code in bons))
    mesures["portes"] = portes
    return mesures


def outil_serveur_va_bien():
    m = _en_memoire("sante", _releve_sante)
    lignes = ["🏥 LE SERVEUR VA-T-IL BIEN ? — mesure a l'instant.", ""]
    ennuis = []

    if m.get("souci"):
        lignes.append("Je n'ai pas pu regarder la machine : " + m["souci"])
        ennuis.append("je ne vois pas la machine")
    else:
        # « load average: 2.58, 1.94, 1.52 » — on veut SEULEMENT le premier
        # nombre. Ecrire [\d.,]+ attrapait « 2.58, » avec sa virgule, et le
        # programme s'arretait en erreur.
        charge = re.search(r"load average:\s*(\d+(?:[.,]\d+)?)", m.get("uptime", ""))
        depuis = re.search(r"up\s+(.+?),\s+\d+\s+user", m.get("uptime", ""))
        if depuis:
            lignes.append("Allume depuis %s." % depuis.group(1))
        if charge:
            valeur = float(charge.group(1).replace(",", "."))
            lignes.append("Travail en cours : %.2f  (au-dessus de 4, il peine)"
                          % valeur)
            if valeur > 4:
                ennuis.append("il peine, il a trop de travail")

        d = m.get("disque", "").split()
        if len(d) >= 5:
            plein = int(d[4].rstrip("%"))
            lignes.append("Disque : %s occupes sur %s, il reste %s (%d%% plein)."
                          % (d[2], d[1], d[3], plein))
            if plein >= 90:
                ennuis.append("le disque est presque plein")

        mem = m.get("memoire", "").split()
        if len(mem) >= 7:
            lignes.append("Memoire : %s Mo utilises sur %s Mo." % (mem[2], mem[1]))

        tombes = []
        for ligne in m.get("conteneurs", "").splitlines():
            if "|" in ligne:
                nom, etat = ligne.split("|", 1)
                if nom.strip() and not etat.strip().startswith("Up"):
                    tombes.append((nom.strip(), etat.strip()))
        if tombes:
            lignes.append("")
            lignes.append("Ce qui est tombe :")
            for nom, etat in tombes:
                lignes.append("   ✗ %-22s %s" % (nom or "(sans nom)", etat))
            ennuis.append("%d chose(s) tombee(s)" % len(tombes))

    lignes.append("")
    lignes.append("Les portes du site :")
    for nom, adresse, code, bon in m.get("portes", []):
        mot = {0: "injoignable", 200: "ouverte", 303: "demande de se connecter",
               404: "INTROUVABLE", 502: "en panne"}.get(code, "code %d" % code)
        lignes.append("   %s %-22s %s" % ("·" if bon else "✗", nom, mot))
        if not bon:
            ennuis.append("%s : %s" % (nom, mot))

    lignes.append("")
    if ennuis:
        lignes.append("⚠️ Ca ne va PAS tout a fait : " + " ; ".join(ennuis) + ".")
    else:
        lignes.append("✅ Tout va bien.")
    return "\n".join(lignes)
