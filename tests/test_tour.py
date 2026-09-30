#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LES YEUX SUR LA TOUR — haichi_outils_tour.py.

Ce qu'on prouve, SANS ssh et SANS internet (subprocess.run est remplace par
une fausse tour, les facades du site sont de faux serveurs sur 127.0.0.1) :
  - chaque chiffre rendu vient de la mesure, et une mesure ratee est DITE ;
  - la porte fermee (clef absente) est expliquee en francais ;
  - la charge se juge sur le quart d'heure, pas sur la pointe d'une minute ;
  - le videur debout sans cellule ne compte pas comme un videur ;
  - une facade retiree expres n'est pas une panne ;
  - on ne refait pas la mesure deux fois dans la minute.
"""
import json
import os
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import haichi_outils_tour as tour  # noqa: E402


@pytest.fixture(autouse=True)
def memoire_vide(monkeypatch):
    """Chaque test part d'une memoire vide, et sans facade reelle sur internet."""
    monkeypatch.setattr(tour, "_memoire", {})
    monkeypatch.setattr(tour, "_FACADES", [])
    monkeypatch.setattr(tour, "_MAISON", [])


class _Fini:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def _fausse_tour(monkeypatch, reponse):
    """Remplace ssh : `reponse` est un _Fini, une exception, ou une fonction(commande)."""
    appels = []

    def run(cmd, **kw):
        appels.append((cmd, kw))
        r = reponse(cmd[-1]) if callable(reponse) else reponse
        if isinstance(r, BaseException):
            raise r
        return r
    monkeypatch.setattr(tour.subprocess, "run", run)
    return appels


# ── parler a la tour ────────────────────────────────────────────────────────
def test_demander_rend_le_texte_et_passe_par_le_gardien(monkeypatch):
    """Ca marche : (texte, None), par ssh en mode sans question, via le gardien de clefs."""
    appels = _fausse_tour(monkeypatch, _Fini("bonjour\n"))
    assert tour._demander_a_la_tour("echo bonjour", patience=3) == ("bonjour\n", None)
    cmd, kw = appels[0]
    assert cmd[0] == "ssh" and "BatchMode=yes" in cmd and cmd[-1] == "echo bonjour"
    assert kw["timeout"] == 3
    assert kw["env"]["SSH_AUTH_SOCK"].endswith("/.ssh/agent.sock")


def test_demander_tour_muette(monkeypatch):
    """La tour ne repond pas a temps : on dit combien de secondes on a attendu."""
    _fausse_tour(monkeypatch, subprocess.TimeoutExpired("ssh", 5))
    assert tour._demander_a_la_tour("x", patience=5) == (
        None, "La tour n'a pas repondu en 5 secondes.")


def test_demander_ssh_introuvable(monkeypatch):
    """ssh ne se lance pas : on dit pourquoi."""
    _fausse_tour(monkeypatch, FileNotFoundError("ssh absent"))
    texte, souci = tour._demander_a_la_tour("x")
    assert texte is None and souci == "Je n'ai pas pu lancer la connexion : ssh absent"


@pytest.mark.parametrize("stderr, attendu", [
    ("Warning: x\nmoi@tour: Permission denied (publickey).\n",
     "la porte de la tour est fermee. Il faut lancer ~/connexion-tour.sh une fois, "
     "et taper la phrase secrete."),
    ("", "raison inconnue"),
    ("ligne 1\nssh: connect to host tour port 22: No route to host\n",
     "ssh: connect to host tour port 22: No route to host"),
    ("E" * 300, "E" * 150),
])
def test_demander_echec(monkeypatch, stderr, attendu):
    """Code non nul : la derniere ligne d'erreur, traduite si c'est la clef, coupee a 150."""
    _fausse_tour(monkeypatch, _Fini("", stderr, 255))
    assert tour._demander_a_la_tour("x") == (None, attendu)


# ── le cache ────────────────────────────────────────────────────────────────
def test_en_memoire_une_minute(monkeypatch):
    """Dans la minute, on rend la reponse gardee ; apres, on la refait."""
    horloge = [1000.0]
    monkeypatch.setattr(tour.time, "time", lambda: horloge[0])
    fabriques = []

    def fabriquer():
        fabriques.append(1)
        return len(fabriques)
    assert tour._en_memoire("k", fabriquer) == 1
    horloge[0] += 59
    assert tour._en_memoire("k", fabriquer) == 1
    horloge[0] += 2
    assert tour._en_memoire("k", fabriquer) == 2
    assert tour._en_memoire("autre", fabriquer) == 3


# ── les machines de la maison ───────────────────────────────────────────────
def test_machines_sans_reglages(tmp_path, monkeypatch):
    """Sans reglages-maison.json : seulement le cockpit de cette machine."""
    monkeypatch.setattr(tour, "__file__", str(tmp_path / "haichi_outils_tour.py"))
    assert tour._machines_de_la_maison() == [("cette machine", "127.0.0.1", 8790, "le cockpit")]


@pytest.mark.parametrize("contenu, attendu", [
    ({"machines": [["pc", "10.0.0.2", 22, "ssh"]]}, [("pc", "10.0.0.2", 22, "ssh")]),
    ({"machines": []}, None),
    ({"autre": 1}, None),
    ("{casse", None),
])
def test_machines_lues_dans_les_reglages(tmp_path, monkeypatch, contenu, attendu):
    """Les machines viennent des reglages ; vide, absent ou illisible → la valeur par defaut."""
    monkeypatch.setattr(tour, "__file__", str(tmp_path / "haichi_outils_tour.py"))
    (tmp_path / "reglages-maison.json").write_text(
        contenu if isinstance(contenu, str) else json.dumps(contenu), encoding="utf-8")
    defaut = [("cette machine", "127.0.0.1", 8790, "le cockpit")]
    assert tour._machines_de_la_maison() == (attendu or defaut)


@pytest.mark.xfail(strict=True, reason="bug: haichi_outils_tour.py:92 un reglages-maison.json "
                   "qui est une liste leve AttributeError (non attrapee) a l'import du module")
@pytest.mark.parametrize("contenu", [["pas", "un objet"], 7])
def test_machines_reglages_pas_un_objet(tmp_path, monkeypatch, contenu):
    """Un reglages-maison.json qui n'est pas un objet : la valeur par defaut, sans planter."""
    monkeypatch.setattr(tour, "__file__", str(tmp_path / "haichi_outils_tour.py"))
    (tmp_path / "reglages-maison.json").write_text(json.dumps(contenu), encoding="utf-8")
    assert tour._machines_de_la_maison() == [("cette machine", "127.0.0.1", 8790, "le cockpit")]


def test_frapper_ouvert_et_ferme():
    """Frapper a une porte ouverte : vrai ; a une porte fermee : faux."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    port = s.getsockname()[1]
    try:
        assert tour._frapper("127.0.0.1", port, 1) is True
    finally:
        s.close()
    assert tour._frapper("127.0.0.1", port, 1) is False


# ── qui est en ligne ────────────────────────────────────────────────────────
def test_qui_est_en_ligne_complet(monkeypatch):
    """Les conteneurs de la tour et les machines de la maison, eteintes nommees."""
    _fausse_tour(monkeypatch, _Fini("site|Up 3 days\nbruit sans barre\n|Up\nodoo | Up 1 hour \n"))
    monkeypatch.setattr(tour, "_MAISON", [("pc", "h1", 1, "cockpit"), ("nas", "h2", 2, "disque"),
                                          ("nas", "h3", 3, "copie")])
    monkeypatch.setattr(tour, "_frapper", lambda hote, port: hote == "h1")
    txt = tour.outil_qui_est_en_ligne()
    assert txt.startswith("👥 QUI EST EN LIGNE")
    assert "   · site                   Up 3 days" in txt
    assert "   · odoo                   Up 1 hour" in txt
    assert "   → 2 en marche." in txt
    assert "   · pc porte 1 — cockpit" in txt and "   ✗ nas porte 2 — disque" in txt
    assert txt.endswith("   → nas ne repond pas.")


def test_qui_est_en_ligne_rien_ne_tourne(monkeypatch):
    """La tour repond mais rien ne tourne : c'est dit anormal ; maison toute allumee."""
    _fausse_tour(monkeypatch, _Fini(""))
    monkeypatch.setattr(tour, "_MAISON", [("pc", "h", 1, "r")])
    monkeypatch.setattr(tour, "_frapper", lambda h, p: True)
    txt = tour.outil_qui_est_en_ligne()
    assert "   Rien ne tourne. C'est anormal." in txt
    assert "ne repond pas" not in txt


def test_qui_est_en_ligne_tour_fermee(monkeypatch):
    """ssh refuse : on dit qu'on n'a pas pu regarder, et pourquoi."""
    _fausse_tour(monkeypatch, _Fini("", "Permission denied (publickey)", 255))
    txt = tour.outil_qui_est_en_ligne()
    assert "   Je n'ai pas pu regarder : la porte de la tour est fermee." in txt


def test_qui_est_en_ligne_garde_une_minute(monkeypatch):
    """Deux questions de suite : une seule connexion a la tour."""
    appels = _fausse_tour(monkeypatch, _Fini("a|Up"))
    tour.outil_qui_est_en_ligne()
    tour.outil_qui_est_en_ligne()
    assert len(appels) == 1


# ── la sante du serveur ─────────────────────────────────────────────────────
def _sortie(uptime=" 08:00:00 up 3 days,  4:05,  2 users,  load average: 0.52, 0.58, 0.59",
            df="/dev/sda1  50G  20G  30G  40% /",
            free="Mem:  7900  3100  1200  100  3600  4500",
            conteneurs="site|Up 3 days\nodoo|Exited (0) 2 days ago",
            coeurs="4", videur="active\n3\n12"):
    return "\n---\n".join([uptime, df, free, conteneurs, coeurs, videur]) + "\n"


class _Facade(BaseHTTPRequestHandler):
    def do_GET(self):
        code = int(self.path.strip("/") or 200)
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *a):
        pass


@pytest.fixture
def facades():
    s = HTTPServer(("127.0.0.1", 0), _Facade)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d/" % s.server_address[1]
    s.shutdown()
    s.server_close()


def test_releve_sante_mesure_tout(monkeypatch, facades):
    """Le releve decoupe la reponse et frappe a chaque facade (vrais codes HTTP)."""
    appels = _fausse_tour(monkeypatch, _Fini(_sortie()))
    libre = socket.socket()
    libre.bind(("127.0.0.1", 0))
    ferme = "http://127.0.0.1:%d/" % libre.getsockname()[1]
    libre.close()
    monkeypatch.setattr(tour, "_FACADES", [
        ("ok", facades + "200", {200}, None),
        ("connexion", facades + "303", {200, 303}, None),
        ("perdue", facades + "404", {200}, None),
        ("morte", ferme, {200}, None),
        ("partie", facades + "404", {200}, "retiree"),
    ])
    m = tour._releve_sante()
    assert "fail2ban" in appels[0][0][-1] and "nproc" in appels[0][0][-1]
    assert m["souci"] is None and m["coeurs"] == 4
    assert m["disque"].startswith("/dev/sda1") and m["memoire"].startswith("Mem:")
    assert m["videur"] == {"debout": True, "cellules": 3, "bannis": 12}
    assert [(p[0], p[2], p[3], p[4]) for p in m["portes"]] == [
        ("ok", 200, True, None), ("connexion", 303, True, None),
        ("perdue", 404, False, None), ("morte", 0, False, None),
        ("partie", 404, False, "retiree")]


def test_releve_sante_bizarre(monkeypatch):
    """Reponse tronquee, coeurs illisibles, videur muet : pas d'exception, des manques."""
    _fausse_tour(monkeypatch, _Fini("seulement l'uptime"))
    m = tour._releve_sante()
    assert m["uptime"] == "seulement l'uptime" and m["disque"] == ""
    assert m["coeurs"] == 0 and m["videur"] is None
    _fausse_tour(monkeypatch, _Fini(_sortie(coeurs="beaucoup", videur="")))
    m = tour._releve_sante()
    assert m["coeurs"] == 0 and m["videur"] is None
    _fausse_tour(monkeypatch, _Fini(_sortie(videur="inactive\nquoi")))
    assert tour._releve_sante()["videur"] == {"debout": False, "cellules": 0, "bannis": 0}


def test_releve_sante_tour_fermee(monkeypatch):
    """ssh rate : seul le souci est note, les portes sont quand meme regardees."""
    _fausse_tour(monkeypatch, subprocess.TimeoutExpired("ssh", 20))
    m = tour._releve_sante()
    assert m == {"souci": "La tour n'a pas repondu en 20 secondes.", "portes": []}


def _sante(monkeypatch, **mesures):
    m = {"souci": None, "uptime": "", "disque": "", "memoire": "", "conteneurs": "",
         "coeurs": 4, "videur": {"debout": True, "cellules": 2, "bannis": 5}, "portes": []}
    m.update(mesures)
    monkeypatch.setattr(tour, "_releve_sante", lambda: m)
    monkeypatch.setattr(tour, "_memoire", {})
    return tour.outil_serveur_va_bien()


def test_sante_tout_va_bien(monkeypatch):
    """Charge faible, disque a 40 %, rien de tombe, videur qui garde : « Tout va bien »."""
    txt = _sante(monkeypatch,
                 uptime=" 08:00 up 3 days,  4:05,  2 users,  load average: 0.52, 0.58, 0.59",
                 disque="/dev/sda1 50G 20G 30G 40% /",
                 memoire="Mem: 7900 3100 1200 100 3600 4500",
                 conteneurs="site|Up 3 days\n|Exited\nsans barre",
                 portes=[("le site", "u", 200, True, None), ("vieux", "u", 404, False)])
    assert "Allume depuis 3 days,  4:05." in txt
    assert "Travail : 0.52 en ce moment, 0.59 sur le dernier quart d'heure, pour 4 coeurs." in txt
    assert "Disque : 20G occupes sur 50G, il reste 30G (40% plein)." in txt
    assert "Memoire : 3100 Mo utilises sur 7900 Mo." in txt
    assert "Le videur : · debout, 2 cellule(s), 5 adresse(s) bloquee(s)" in txt
    assert "   · le site                ouverte" in txt
    assert "   ✗ vieux                  INTROUVABLE" in txt
    assert "Ce qui est tombe" not in txt
    assert txt.endswith("⚠️ Ca ne va PAS tout a fait : vieux : INTROUVABLE.")


def test_sante_sans_ennui(monkeypatch):
    """Aucun ennui du tout : la derniere ligne est « Tout va bien »."""
    assert _sante(monkeypatch).endswith("✅ Tout va bien.")


def test_sante_charge_de_fond_et_pointe(monkeypatch):
    """Le quart d'heure au-dessus des coeurs : ennui. La minute seule : une pointe."""
    txt = _sante(monkeypatch, uptime="load average: 9.00, 5.00, 6,50")
    assert "c'est de fond" in txt and "il peine" in txt
    txt = _sante(monkeypatch, uptime="load average: 9.00, 2.00, 1.00")
    assert "une pointe passagere" in txt and txt.endswith("Tout va bien.")


def test_sante_sans_coeurs(monkeypatch):
    """Sans le nombre de coeurs, on ne juge pas : on le dit."""
    txt = _sante(monkeypatch, coeurs=0, uptime="load average: 99, 99, 99")
    assert "Je n'ai pas pu compter les coeurs" in txt and txt.endswith("Tout va bien.")


def test_sante_disque_plein_et_tombes(monkeypatch):
    """Disque a 95 % et deux conteneurs tombes : les deux ennuis sont listes."""
    txt = _sante(monkeypatch, disque="/dev/sda1 50G 48G 2G 95% /",
                 conteneurs="site|Up 1 day\nodoo|Exited (1) 2 days ago\ndb|Restarting")
    assert "Ce qui est tombe :" in txt
    assert "   ✗ odoo                   Exited (1) 2 days ago" in txt
    assert "le disque est presque plein ; 2 chose(s) tombee(s)." in txt


@pytest.mark.parametrize("videur, attendu, ennui", [
    (None, "Le videur : je n'ai pas pu regarder.", None),
    ({"debout": False}, "Le videur : ✗ A TERRE.", "le videur est a terre"),
    ({"debout": True, "cellules": 0}, "debout, mais ZERO cellule", "le videur ne garde rien"),
])
def test_sante_videur(monkeypatch, videur, attendu, ennui):
    """Videur absent, a terre, ou debout sans cellule : chacun dit en clair."""
    txt = _sante(monkeypatch, videur=videur)
    assert attendu in txt
    if ennui:
        assert ennui in txt.splitlines()[-1]


def test_sante_machine_invisible(monkeypatch):
    """ssh rate : on le dit, et ca compte comme un ennui."""
    txt = _sante(monkeypatch, souci="la porte est fermee", videur=None)
    assert "Je n'ai pas pu regarder la machine : la porte est fermee" in txt
    assert "je ne vois pas la machine" in txt.splitlines()[-1]


def test_sante_facade_retiree_expres(monkeypatch):
    """Une facade enlevee volontairement est dite, mais n'est pas une panne."""
    txt = _sante(monkeypatch, portes=[
        ("l'accueil", "u", 404, False, tour.RETIREE_ODOO),
        ("injoignable", "u", 0, False, None),
        ("panne", "u", 502, False, None),
        ("bizarre", "u", 418, False, None),
        ("connexion", "u", 303, True, None)])
    assert "   — l'accueil              retiree expres" in txt
    assert "   · connexion              demande de se connecter" in txt
    dernier = txt.splitlines()[-1]
    assert "injoignable : injoignable ; panne : en panne ; bizarre : code 418." in dernier
    assert "accueil" not in dernier


def test_sante_de_bout_en_bout(monkeypatch):
    """Avec la fausse tour : ce qui est tombe (odoo) est la seule chose qui ne va pas."""
    _fausse_tour(monkeypatch, _Fini(_sortie()))
    txt = tour.outil_serveur_va_bien()
    assert "✗ odoo" in txt
    assert txt.splitlines()[-1] == "⚠️ Ca ne va PAS tout a fait : 1 chose(s) tombee(s)."


@pytest.mark.xfail(strict=True, reason="bug: haichi_outils_tour.py:283 int(d[4].rstrip('%')) "
                   "leve ValueError si la 5e colonne de df n'est pas un pourcentage")
def test_sante_ligne_de_disque_decalee(monkeypatch):
    """df coupe sa ligne (nom de disque trop long) : on ne doit pas planter."""
    txt = _sante(monkeypatch, disque="50G 20G 30G 40% /")
    assert txt.endswith("Tout va bien.")
