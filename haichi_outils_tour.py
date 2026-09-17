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
# Chaque facade porte QUATRE choses : son nom, son adresse, les codes qui
# veulent dire « elle va bien », et — si on ne l'attend plus — POURQUOI.
#
# Cette quatrieme case est nee d'une faute reelle (16/09/2026). Arthur
# annoncait « Ca ne va PAS : l'accueil de la tour INTROUVABLE ». Il a parle
# au serveur : sur les huit programmes qui tournent, aucun n'est l'accueil.
# La page n'etait pas tombee, elle avait ete ENLEVEE — volontairement.
#
# Un detecteur qui ne connait que « la » et « pas la » crie au feu devant une
# piece qu'on a demolie expres. Et une alerte qui se declenche toujours pour
# rien finit par ne plus etre lue : c'est comme ca qu'on rate la vraie panne.
# On garde donc la ligne — on ne cache rien — mais on dit calmement qu'elle
# est partie, et on ne compte plus ca comme un ennui.
RETIREE_ODOO = ("retiree expres : Odoo a ete supprime. La fonctionnalite se "
                "retrouve dans la sauvegarde, sans le rallumer.")

_FACADES = [
    ("le site public",      "https://matourdecontrole.fr/",                    {200}, None),
    ("la vente d'agents",   "https://offreagent.matourdecontrole.fr/",         {200}, None),
    ("l'accueil de la tour", "https://tour.matourdecontrole.fr/tour/dashboard", {200, 303}, RETIREE_ODOO),
]


def _releve_sante():
    texte, souci = _demander_a_la_tour(
        "uptime; echo ---; df -h / | tail -1; echo ---; "
        "free -m | sed -n 2p; echo ---; "
        "docker ps -a --format '{{.Names}}|{{.Status}}'; echo ---; nproc; "
        "echo ---; systemctl is-active fail2ban; "
        "sudo -n fail2ban-client status 2>/dev/null "
        "| grep 'Number of jail' | grep -oE '[0-9]+$' ; "
        "sudo -n fail2ban-client status sshd 2>/dev/null "
        "| grep 'Currently banned' | grep -oE '[0-9]+$'")
    mesures = {"souci": souci}
    if not souci:
        bouts = (texte or "").split("---")
        mesures["uptime"] = bouts[0].strip() if len(bouts) > 0 else ""
        mesures["disque"] = bouts[1].strip() if len(bouts) > 1 else ""
        mesures["memoire"] = bouts[2].strip() if len(bouts) > 2 else ""
        mesures["conteneurs"] = bouts[3].strip() if len(bouts) > 3 else ""
        # Le seuil de « il peine » n'est pas un chiffre qu'on choisit : c'est
        # le nombre de coeurs. On le demande, on ne le devine pas.
        try:
            mesures["coeurs"] = int(bouts[4].strip()) if len(bouts) > 4 else 0
        except ValueError:
            mesures["coeurs"] = 0

        # Le videur : le programme qui bloque ceux qui frappent trop souvent
        # a la porte. Patrick, le 16/09/2026 : « comment le banisseur est mort
        # et ca passe inapercu 2 jours ? » — parce que personne ne le
        # regardait. Il est reste mort du 14/09 13h47 au 16/09 18h12.
        #
        # On regarde DEUX choses, pas une : est-il debout, et garde-t-il
        # vraiment ? Un videur debout avec zero cellule ne garde rien.
        mesures["videur"] = None
        if len(bouts) > 5:
            lignes_videur = bouts[5].strip().splitlines()
            if lignes_videur:
                def _nombre(rang):
                    try:
                        return int(lignes_videur[rang].strip())
                    except (IndexError, ValueError):
                        return 0
                mesures["videur"] = {
                    "debout": lignes_videur[0].strip() == "active",
                    "cellules": _nombre(1),
                    "bannis": _nombre(2),
                }

    portes = []
    for nom, adresse, bons, retiree in _FACADES:
        try:
            d = urllib.request.Request(adresse, method="GET")
            with urllib.request.urlopen(d, timeout=12) as r:
                code = r.getcode()
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception:
            code = 0
        portes.append((nom, adresse, code, code in bons, retiree))
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
        # « load average: 5.71, 2.07, 1.56 » — trois chiffres, pas un.
        # La derniere minute, les cinq dernieres, le dernier quart d'heure.
        #
        # On jugeait sur le PREMIER. C'etait faux (16/09/2026) : une tache
        # planifiee qui demarre le fait sauter pendant trente secondes, et
        # Arthur criait a la panne. L'etat de fond, c'est le TROISIEME.
        # Le premier ne sert qu'a dire « en ce moment, ca pousse ».
        apres = re.search(r"load average:(.*)", m.get("uptime", ""))
        trois = re.findall(r"\d+(?:[.,]\d+)?", apres.group(1)) if apres else []
        depuis = re.search(r"up\s+(.+?),\s+\d+\s+user", m.get("uptime", ""))
        if depuis:
            lignes.append("Allume depuis %s." % depuis.group(1))

        coeurs = int(m.get("coeurs") or 0)
        if len(trois) >= 3:
            minute = float(trois[0].replace(",", "."))
            quart = float(trois[2].replace(",", "."))
            if coeurs:
                lignes.append("Travail : %.2f en ce moment, %.2f sur le dernier "
                              "quart d'heure, pour %d coeurs."
                              % (minute, quart, coeurs))
                if quart > coeurs:
                    lignes.append("   → le quart d'heure depasse les coeurs : "
                                  "c'est de fond.")
                    ennuis.append("il peine, il a trop de travail depuis un "
                                  "quart d'heure")
                elif minute > coeurs:
                    lignes.append("   → une pointe passagere, deja retombee : "
                                  "rien a reparer.")
            else:
                # Sans le nombre de coeurs, on ne sait pas juger. On le DIT.
                lignes.append("Travail : %.2f en ce moment, %.2f sur le quart "
                              "d'heure. Je n'ai pas pu compter les coeurs, "
                              "donc je ne dis pas si c'est trop." % (minute, quart))

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

    videur = m.get("videur")
    if videur is None:
        lignes.append("")
        lignes.append("Le videur : je n'ai pas pu regarder.")
    else:
        lignes.append("")
        if not videur.get("debout"):
            lignes.append("Le videur : ✗ A TERRE. Plus personne ne bloque ceux "
                          "qui frappent trop souvent a la porte.")
            ennuis.append("le videur est a terre")
        elif not videur.get("cellules"):
            # Debout ne veut pas dire qu'il garde. Meme lecon qu'un port qui
            # repond sans que la page marche.
            lignes.append("Le videur : ✗ debout, mais ZERO cellule — il ne "
                          "garde rien du tout.")
            ennuis.append("le videur ne garde rien")
        else:
            lignes.append("Le videur : · debout, %d cellule(s), %d adresse(s) "
                          "bloquee(s) a la porte."
                          % (videur["cellules"], videur.get("bannis", 0)))

    lignes.append("")
    lignes.append("Les portes du site :")
    for porte in m.get("portes", []):
        nom, adresse, code, bon = porte[0], porte[1], porte[2], porte[3]
        retiree = porte[4] if len(porte) >= 5 else None
        mot = {0: "injoignable", 200: "ouverte", 303: "demande de se connecter",
               404: "INTROUVABLE", 502: "en panne"}.get(code, "code %d" % code)
        if retiree:
            # On le DIT — mais ce n'est pas un ennui : c'est voulu.
            lignes.append("   — %-22s %s" % (nom, retiree))
        else:
            lignes.append("   %s %-22s %s" % ("·" if bon else "✗", nom, mot))
            if not bon:
                ennuis.append("%s : %s" % (nom, mot))

    lignes.append("")
    if ennuis:
        lignes.append("⚠️ Ca ne va PAS tout a fait : " + " ; ".join(ennuis) + ".")
    else:
        lignes.append("✅ Tout va bien.")
    return "\n".join(lignes)
