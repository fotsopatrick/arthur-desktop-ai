#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CE QUE DIT CHAQUE OUTIL — haichi_outils, source par source.

Ce qu'on prouve, SANS reseau, SANS ssh et SANS relancer quoi que ce soit
(les lecteurs internes sont remplaces, les portes sont de faux serveurs sur
127.0.0.1, HOME est un dossier jetable) :
  - quand la source repond, l'outil dit ce qu'elle dit ;
  - quand elle se tait, l'outil le DIT au lieu d'inventer ;
  - quand elle repond de travers, l'outil ne plante pas pour autant ;
  - redemarrer le cockpit passe par le service, jamais par un retour en arriere.
"""
import datetime
import json
import os
import runpy
import socket
import subprocess
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import haichi_outils as ho  # noqa: E402


def _faux_lire(table):
    """Un _lire qui rend le texte prevu pour chaque adresse, ou leve l'erreur prevue."""
    vus = []

    def lire(url, patience=6):
        vus.append((url, patience))
        r = table[url] if url in table else OSError("Connection refused")
        if isinstance(r, Exception):
            raise r
        return r if isinstance(r, str) else json.dumps(r)
    lire.vus = vus
    return lire


# ── les petits lecteurs ─────────────────────────────────────────────────────
class _Page(BaseHTTPRequestHandler):
    def do_GET(self):
        corps = "<h2>Bonjour</h2>".encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *a):
        pass


@pytest.fixture
def serveur():
    s = HTTPServer(("127.0.0.1", 0), _Page)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield s.server_address[1]
    s.shutdown()
    s.server_close()


def test_lire_et_port_ouvert(serveur):
    """_lire rend le texte d'une vraie page ; _port_ouvert voit qui repond."""
    assert ho._lire("http://127.0.0.1:%d/" % serveur, 2) == "<h2>Bonjour</h2>"
    assert ho._port_ouvert(serveur) is True
    libre = socket.socket()
    libre.bind(("127.0.0.1", 0))
    port = libre.getsockname()[1]
    libre.close()
    assert ho._port_ouvert(port) is False


# ── l'heure ─────────────────────────────────────────────────────────────────
def test_heure_dit_le_jour_en_francais(monkeypatch):
    """Le 30/09/2026 a 08:05 est un mercredi, en toutes lettres."""
    class Fixe(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 30, 8, 5)
    monkeypatch.setattr(ho.datetime, "datetime", Fixe)
    assert ho.outil_heure() == ("🕐 Il est 08:05 — nous sommes mercredi 30 septembre "
                                "2026. (heure de cette machine)")


# ── les modules du cockpit ──────────────────────────────────────────────────
def _config(tmp_path, monkeypatch, pages, ouverts):
    chemin = tmp_path / "config.json"
    chemin.write_text(json.dumps({"pages": pages}) if pages is not None else "{pas du json",
                      encoding="utf-8")
    monkeypatch.setattr(ho, "_LIEUX_DE_LA_CONFIGURATION",
                        [str(tmp_path / "absent.json"), str(chemin)])
    monkeypatch.setattr(ho, "_port_ouvert", lambda p: str(p) in ouverts)
    return chemin


def test_configuration_premier_lieu_qui_existe(tmp_path, monkeypatch):
    """On regarde les lieux dans l'ordre ; aucun n'existe → None."""
    monkeypatch.setattr(ho, "_LIEUX_DE_LA_CONFIGURATION", [str(tmp_path / "x.json")])
    assert ho._ou_est_la_configuration() is None
    assert ho._modules() == ([], [])
    assert ho.outil_modules() == "Je n arrive pas a lire la liste des modules du cockpit."


def test_modules_allumes_et_eteints(tmp_path, monkeypatch):
    """Chaque page a un port : ouvert → allume, ferme → eteint ; sans port → ignoree."""
    _config(tmp_path, monkeypatch, [
        {"nom": "Veille", "url": "http://127.0.0.1:8011/"},
        {"nom": "Reseau", "url": "http://127.0.0.1:8020/"},
        {"nom": "Sans port", "url": "https://exemple/"},
        {"url": "http://x:9000"},
    ], {"8011"})
    assert ho._modules() == ([("Veille", "8011")], [("Reseau", "8020"), ("?", "9000")])
    txt = ho.outil_modules()
    assert "3 modules : 1 allumes et 2 eteints" in txt
    assert "• Reseau (port 8020)" in txt and "• ? (port 9000)" in txt


def test_modules_tous_allumes_pas_de_liste(tmp_path, monkeypatch):
    """Rien d'eteint : pas de section « Les eteints »."""
    _config(tmp_path, monkeypatch, [{"nom": "A", "url": ":1"}], {"1"})
    assert ho.outil_modules() == "🎛️ Le cockpit a 1 modules : 1 allumes et 0 eteints."


def test_modules_plus_de_douze_eteints(tmp_path, monkeypatch):
    """Au-dela de douze eteints, on en montre douze et on compte le reste."""
    _config(tmp_path, monkeypatch,
            [{"nom": "m%d" % i, "url": ":%d" % (9000 + i)} for i in range(15)], set())
    txt = ho.outil_modules()
    assert "15 modules : 0 allumes et 15 eteints" in txt
    assert "m11 (port 9011)" in txt and "m12" not in txt
    assert "... et 3 autres." in txt


def test_modules_configuration_illisible(tmp_path, monkeypatch):
    """Un config.json casse : on dit qu'on n'arrive pas a lire, sans planter."""
    _config(tmp_path, monkeypatch, None, set())
    assert ho._modules() == ([], [])
    assert "Je n arrive pas a lire" in ho.outil_modules()


# ── la veille IA ────────────────────────────────────────────────────────────
def test_veille_eteinte(monkeypatch):
    """Port 8011 ferme : la veille est dite ETEINTE, rien n'est lu."""
    monkeypatch.setattr(ho, "_port_ouvert", lambda p: False)
    monkeypatch.setattr(ho, "_lire", lambda *a: pytest.fail("ne doit pas lire"))
    assert "ETEINTE" in ho.outil_veille()


def test_veille_donne_ses_titres(monkeypatch):
    """Les titres h2/h3 sont rendus sans balises, six au plus, coupes a 110."""
    monkeypatch.setattr(ho, "_port_ouvert", lambda p: True)
    long = "L" * 200
    page = ("<h1>ignore</h1><h2 class='a'>Un <b>modele</b> sort</h2>"
            "<h3>Deux</h3><h2> </h2><h2>%s</h2>" % long
            + "".join("<h3>t%d</h3>" % i for i in range(10)))
    monkeypatch.setattr(ho, "_lire", _faux_lire({"http://127.0.0.1:8011/": page}))
    txt = ho.outil_veille()
    assert txt.startswith("📰 La veille IA du matin dit :")
    assert "  • Un modele sort" in txt and "  • Deux" in txt
    assert "  • " + "L" * 110 + "\n" in txt and "L" * 111 not in txt
    assert "ignore" not in txt and "t1" in txt and "t2" not in txt


def test_veille_sans_titre(monkeypatch):
    """Elle repond, mais sans titre : on le dit."""
    monkeypatch.setattr(ho, "_port_ouvert", lambda p: True)
    monkeypatch.setattr(ho, "_lire", _faux_lire({"http://127.0.0.1:8011/": "<p>rien</p>"}))
    assert "aucun titre" in ho.outil_veille()


def test_veille_repond_mal(monkeypatch):
    """Elle ouvre la porte mais la lecture casse : « repond mal »."""
    monkeypatch.setattr(ho, "_port_ouvert", lambda p: True)
    monkeypatch.setattr(ho, "_lire", _faux_lire({}))
    assert ho.outil_veille() == "📰 La veille IA du matin repond mal : Connection refused"


# ── le reseau ───────────────────────────────────────────────────────────────
def test_reseau_repond(monkeypatch):
    """Le cockpit donne le resume : on le repete, chiffres compris."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({ho.COCKPIT + "/api/reseau/statut": {
        "resume": {"connexions": 42, "process": 7},
        "capture": {"machine": "pc", "maintenant": "08:00"}}}))
    assert ho.outil_reseau() == ("🌐 Reseau de la machine pc, releve a 08:00 : 42 connexions "
                                 "ouvertes, 7 programmes qui parlent au reseau.")


def test_reseau_vide_dit_point_d_interrogation(monkeypatch):
    """Un JSON vide : des « ? », pas des chiffres inventes."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({ho.COCKPIT + "/api/reseau/statut": {}}))
    assert "machine ?, releve a ? : ? connexions" in ho.outil_reseau()


@pytest.mark.parametrize("reponse", [OSError("refuse"), "pas du json", "[1, 2]"])
def test_reseau_en_panne(monkeypatch, reponse):
    """Cockpit muet, texte illisible ou liste au lieu d'objet : on le dit."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({ho.COCKPIT + "/api/reseau/statut": reponse}))
    assert ho.outil_reseau().startswith("🌐 Je n arrive pas a lire l etat du reseau")


# ── la gouvernance ──────────────────────────────────────────────────────────
URL_GOUV = ho.COCKPIT + "/api/gouvernance/etat"


def test_gouvernance_complete(monkeypatch):
    """Agents allumes / museles, decisions et garde-fous sont comptes."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({URL_GOUV: {
        "ok": True, "horodatage": "08:00",
        "agents": [{"nom": "Victor", "etat": "allume"}, {"nom": "Clark", "etat": "musele"},
                   {"nom": "Lois", "etat": "allume"}],
        "decisions": [1, 2], "garde_fous": ["a"]}}))
    txt = ho.outil_cockpit_gouvernance()
    assert "Agents actifs (2/3) : Victor, Lois" in txt
    assert "Agents muselés/surveillés : Clark" in txt
    assert "arbitrage : 2" in txt and "actifs : 1 (murs" in txt
    assert txt.endswith("Relevé à : 08:00")


def test_gouvernance_tous_allumes_sans_horodatage(monkeypatch):
    """Personne de musele : pas de ligne « muselés » ; sans heure → « maintenant »."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({URL_GOUV: {
        "ok": True, "agents": [{"nom": "A", "etat": "allume"}]}}))
    txt = ho.outil_cockpit_gouvernance()
    assert "muselés" not in txt and "(1/1) : A" in txt
    assert txt.endswith("maintenant")


def test_gouvernance_pas_ok(monkeypatch):
    """Le cockpit repond « ok: false » : etat indisponible, dit comme tel."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({URL_GOUV: {"ok": False}}))
    assert "indisponible" in ho.outil_cockpit_gouvernance()


def test_gouvernance_injoignable(monkeypatch):
    """Le cockpit ne repond pas : on nomme l'adresse et l'erreur."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({}))
    assert ho.outil_cockpit_gouvernance() == (
        "🏛️ Le Cockpit d'Agents est injoignable sur %s : Connection refused." % ho.COCKPIT)


# ── moi ─────────────────────────────────────────────────────────────────────
def test_moi_se_compte(monkeypatch):
    """Arthur compte ses sujets et ses circuits dans sa propre base."""
    faux = types.ModuleType("nano_moteur_ultra")
    faux.ENGINE = types.SimpleNamespace(base={"circuit_a": 1, "circuit_b": 2, "meteo": 3})
    monkeypatch.setitem(sys.modules, "nano_moteur_ultra", faux)
    assert ho.outil_moi().startswith("🧠 Je connais 3 sujets par coeur, dont 2 circuits")


def test_moi_ne_se_trouve_pas(monkeypatch):
    """Sans moteur, il dit qu'il n'arrive pas a se compter."""
    monkeypatch.setitem(sys.modules, "nano_moteur_ultra", None)
    assert ho.outil_moi().startswith("🧠 Je n arrive pas a me compter moi-meme")


# ── l'eveil et le banc (outils MCP locaux) ──────────────────────────────────
def _faux_skill(monkeypatch, nom, **fonctions):
    import skills
    m = types.ModuleType("skills." + nom)
    for k, v in fonctions.items():
        setattr(m, k, v)
    monkeypatch.setitem(sys.modules, "skills." + nom, m)
    monkeypatch.setattr(skills, nom, m, raising=False)


def test_eveil_complet(monkeypatch):
    """Git, systeme, agents : tout est traduit en lignes lisibles, sur le depot."""
    recu = []
    _faux_skill(monkeypatch, "mcp_eveil", eveil=lambda chemin: recu.append(chemin) or {
        "git": {"branch": "main", "clean": True,
                "last_commits": [{"message": "M" * 80}]},
        "system": {"hostname": "tour", "load_1m": 0.5, "mem_used_pct": 40,
                   "disk_used_pct": 70},
        "agents": {"a": {"status": "up"}, "b": {"status": "down"}, "c": {}}})
    txt = ho.outil_eveil_systeme()
    assert recu == [ho.ICI]
    assert txt.startswith("🔍 EVEIL SYNTHETIQUE (tour)")
    assert "branche main, arbre propre. Dernier commit : " + "M" * 60 + "\n" in txt
    assert "charge 0.5, RAM 40%, disque 70%" in txt
    assert "Agents UP : a\n" in txt and "Agents DOWN : b\n" in txt


def test_eveil_vide(monkeypatch):
    """Un eveil vide : des « ? », arbre « modifie », aucune ligne d'agents."""
    _faux_skill(monkeypatch, "mcp_eveil", eveil=lambda chemin: {})
    txt = ho.outil_eveil_systeme()
    assert "(?)" in txt and "branche ?, arbre modifie. Dernier commit : ?" in txt
    assert "Agents" not in txt


def test_eveil_en_panne(monkeypatch):
    """L'eveil leve une erreur : on le dit, sans trace Python."""
    def boum(chemin):
        raise RuntimeError("git absent")
    _faux_skill(monkeypatch, "mcp_eveil", eveil=boum)
    assert ho.outil_eveil_systeme() == "🔍 Je n'arrive pas a faire l'eveil : git absent"


def test_banc_tout_vert(monkeypatch):
    """Aucun rouge : une seule ligne, avec le compte et la duree."""
    _faux_skill(monkeypatch, "mcp_analyse_banc", run_pytest=lambda chemin: {
        "total": 10, "passed": 10, "failed": 0, "errors": 0, "duration_s": 1.5})
    assert ho.outil_analyse_banc() == "🧪 BANC DE TESTS : 10/10 verts en 1.5s. Aucun rouge."


def test_banc_avec_rouges(monkeypatch):
    """Des rouges : on les nomme, cinq au plus, message coupe a 100."""
    echecs = [{"test": "t%d" % i, "file": "f.py", "message": "x" * 150} for i in range(7)]
    echecs.append({})
    _faux_skill(monkeypatch, "mcp_analyse_banc", run_pytest=lambda chemin: {
        "total": 9, "passed": 1, "failed": 7, "errors": 1, "duration_s": 2,
        "failures": echecs})
    txt = ho.outil_analyse_banc()
    assert txt.startswith("🧪 BANC DE TESTS : 1/9 verts, 7 rouge(s), 1 erreur(s) en 2s.")
    assert "❌ t4 dans f.py : " + "x" * 100 + "\n" in txt
    assert "t5" not in txt


def test_banc_vide_et_erreurs_seules(monkeypatch):
    """Zero rouge mais une erreur : ce n'est pas vert."""
    _faux_skill(monkeypatch, "mcp_analyse_banc", run_pytest=lambda chemin: {"errors": 1})
    assert "0/0 verts, 0 rouge(s), 1 erreur(s)" in ho.outil_analyse_banc()


@pytest.mark.xfail(strict=True, reason="bug: haichi_outils.outil_analyse_banc ignore "
                   "error_message ; un pytest en timeout (0 test) est annonce « Aucun rouge »")
def test_banc_qui_n_a_pas_tourne_n_est_pas_vert(monkeypatch):
    """Un pytest coupe au bout de 120 s n'a rien verifie : ce n'est pas « aucun rouge »."""
    _faux_skill(monkeypatch, "mcp_analyse_banc", run_pytest=lambda chemin: {
        "total": 0, "passed": 0, "failed": 0, "errors": 0, "duration_s": 120.0,
        "failures": [], "error_message": "pytest timeout (120s)"})
    txt = ho.outil_analyse_banc()
    assert "Aucun rouge" not in txt and "timeout" in txt


def test_banc_en_panne(monkeypatch):
    """Le banc ne se lance pas : on le dit."""
    monkeypatch.setitem(sys.modules, "skills.mcp_analyse_banc", None)
    assert ho.outil_analyse_banc().startswith("🧪 Je n'arrive pas a lancer les tests")


def test_refactor_explique_seulement():
    """Le refactor ne fait rien tout seul : il explique comment s'en servir."""
    assert "dry-run" in ho.outil_refactor()


# ── la tour (enveloppes) ────────────────────────────────────────────────────
def test_tour_absente_on_le_dit(monkeypatch):
    """Sans le module de la tour, les deux outils disent qu'ils ne peuvent pas regarder."""
    monkeypatch.setattr(ho, "_tour", None)
    assert ho.outil_qui_est_en_ligne().startswith("Je ne peux pas regarder qui est en ligne")
    assert ho.outil_serveur_va_bien().startswith("Je ne peux pas regarder la sante")


def test_tour_presente_on_lui_passe_la_main(monkeypatch):
    """Avec le module de la tour, on rend exactement ce qu'il dit."""
    monkeypatch.setattr(ho, "_tour", types.SimpleNamespace(
        outil_qui_est_en_ligne=lambda: "EN LIGNE", outil_serveur_va_bien=lambda: "SANTE"))
    assert ho.outil_qui_est_en_ligne() == "EN LIGNE"
    assert ho.outil_serveur_va_bien() == "SANTE"


# ── la salle des agents ─────────────────────────────────────────────────────
SALLE = "https://dive.matourdecontrole.fr/salle/releve.json"
GENS = [
    {"nom": "Victor", "famille": "dev", "total": 50, "cervelle": {"moteur": "qwen"}},
    {"nom": "Clark", "famille": "dev", "total": 5, "cervelle": {"moteur": "lecture-seule"}},
    {"nom": "Lois", "famille": "presse", "total": 30, "cervelle": "claude"},
    {"nom": "Pete", "total": 1},
    {"famille": "presse"},
]


def test_salle_par_famille_et_plus_actifs(monkeypatch):
    """Compte par famille (la plus nombreuse d'abord) et les trois plus bavards."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({SALLE: {"correspondants": GENS}}))
    assert ho.outil_agents_salle() == (
        "👥 5 agents dans la salle. Par famille : dev 2, presse 2, autre 1. "
        "Les plus actifs : Victor (50 messages), Lois (30 messages), Clark (5 messages).")


def test_que_font_les_agents(monkeypatch):
    """Par famille : agents et messages, familles triees par messages ; muets comptes."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({SALLE: {"correspondants": GENS}}))
    assert ho.outil_que_font_les_agents() == (
        "📋 Ce que font les agents, par famille. dev : 2 agents, 55 messages echanges ; "
        "presse : 2 agents, 30 messages echanges ; autre : 1 agents, 1 messages echanges. "
        "Au total 2 agents ont le moteur eteint (aucune cervelle).")


def test_moteurs_allumes_vifs_et_museles(monkeypatch):
    """Un moteur « lecture-seule » est dit MUSELE, pas actif."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({SALLE: {"correspondants": GENS}}))
    assert ho.outil_agents_moteur_allume() == (
        "🔋 3 agents sur 5 ont un moteur allume. Vraiment actifs : Victor (qwen), "
        "Lois (claude). Museles (moteur lecture-seule : ils lisent mais n agissent pas) : Clark.")


def test_moteurs_seulement_museles_ou_inconnus(monkeypatch):
    """Que des museles : pas de ligne « vraiment actifs » ; moteur vide → « ? »."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({SALLE: {"correspondants": [
        {"nom": "C", "cervelle": {"moteur": "lecture-seule v2"}}]}}))
    txt = ho.outil_agents_moteur_allume()
    assert "Vraiment actifs" not in txt and txt.endswith("pas) : C.")
    monkeypatch.setattr(ho, "_lire", _faux_lire({SALLE: {"correspondants": [
        {"nom": "D", "cervelle": {"autre": 1}}]}}))
    assert ho.outil_agents_moteur_allume() == ("🔋 1 agents sur 1 ont un moteur allume. "
                                               "Vraiment actifs : D (?).")


def test_aucun_moteur(monkeypatch):
    """Personne n'a de cervelle : on le dit."""
    monkeypatch.setattr(ho, "_lire", _faux_lire({SALLE: {"correspondants": [{"nom": "x"}]}}))
    assert ho.outil_agents_moteur_allume() == "Aucun agent n a de moteur allume en ce moment."


@pytest.mark.parametrize("outil", ["outil_agents_salle", "outil_que_font_les_agents",
                                   "outil_agents_moteur_allume"])
def test_salle_muette_ou_vide(monkeypatch, outil):
    """Releve injoignable, illisible ou vide : dit en clair, sans rien inventer."""
    f = getattr(ho, outil)
    monkeypatch.setattr(ho, "_lire", _faux_lire({}))
    assert f() == "Je n arrive pas a lire le releve des agents de la salle."
    monkeypatch.setattr(ho, "_lire", _faux_lire({SALLE: "<html>"}))
    assert f() == "Je n arrive pas a lire le releve des agents de la salle."
    for vide in ({}, {"correspondants": None}, {"correspondants": []}):
        monkeypatch.setattr(ho, "_lire", _faux_lire({SALLE: vide}))
        assert f() == "Le releve des agents de la salle est vide."


# ── redemarrer / rollback ───────────────────────────────────────────────────
def test_redemarrer_passe_par_le_service(monkeypatch):
    """Le redemarrage est demande au service systemd, en differe, detache."""
    lances = []

    class FauxPopen:
        def __init__(self, cmd, **kw):
            lances.append((cmd, kw))
    monkeypatch.setattr(subprocess, "Popen", FauxPopen)
    txt = ho.outil_redemarrer_cockpit()
    assert lances[0][0] == ["sh", "-c", "sleep 2; systemctl --user restart cockpit"]
    assert lances[0][1]["start_new_session"] is True
    assert "rollback" not in lances[0][0][2]
    assert "Le code n'est pas touche" in txt


def test_redemarrer_qui_rate_le_dit(monkeypatch):
    """Le lancement echoue : on le dit, on ne pretend pas avoir redemarre."""
    def rate(*a, **k):
        raise OSError("pas de sh")
    monkeypatch.setattr(subprocess, "Popen", rate)
    assert ho.outil_redemarrer_cockpit() == ("Je n'ai pas pu demander le redemarrage du "
                                             "cockpit : pas de sh")


def test_rollback_ne_fait_qu_expliquer():
    """Le rollback n'est jamais fait sur une phrase : on explique la commande."""
    txt = ho.outil_expliquer_rollback()
    assert "Je ne remonte pas le code" in txt and "rollback-cockpit.sh" in txt


# ── deposer pour les agents / ce qu'a fait un agent (~/outils) ───────────────
@pytest.fixture
def maison(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "outils").mkdir()
    return tmp_path / "outils"


def test_deposer_pour_de_vrai(maison):
    """La salle des agents recoit la question et rend son numero."""
    (maison / "salle-des-agents.py").write_text(
        "def phrase_pour_arthur(q):\n    return 'Depose n°7 : ' + q\n", encoding="utf-8")
    assert ho.outil_deposer_pour_les_agents("code moi un jeu") == "Depose n°7 : code moi un jeu"


def test_deposer_salle_absente(maison):
    """Sans la salle, Arthur NE dit PAS que c'est transmis."""
    txt = ho.outil_deposer_pour_les_agents("code moi un jeu")
    assert txt.startswith("Je n'ai pas pu ouvrir la salle des agents")
    assert "Je ne te dis donc PAS que c'est transmis." in txt


def test_ce_qua_fait_absent_laisse_la_main(maison):
    """Sans l'outil sur cette machine : chaine vide, les regles ecrites repondent."""
    assert ho.outil_ce_qua_fait_un_agent("qui est victor") == ""


def test_ce_qua_fait_repond(maison):
    """L'outil present rend le souvenir ; un souvenir vide devient chaine vide."""
    (maison / "ce-qua-fait-un-agent.py").write_text(
        "def ce_qua_fait(q):\n    return 'Victor a code' if 'victor' in q else None\n",
        encoding="utf-8")
    assert ho.outil_ce_qua_fait_un_agent("qui est victor") == "Victor a code"
    assert ho.outil_ce_qua_fait_un_agent("qui est clark") == ""


def test_ce_qua_fait_casse(maison):
    """Un outil casse : on dit qu'on n'a pas pu ouvrir, on n'invente rien."""
    (maison / "ce-qua-fait-un-agent.py").write_text("def (:\n", encoding="utf-8")
    txt = ho.outil_ce_qua_fait_un_agent("qui est victor")
    assert txt.startswith("Je n'ai pas pu ouvrir le souvenir des agents")
    assert txt.endswith("Je ne t'invente donc rien.")


# ── le fichier lance tout seul, sans la tour ────────────────────────────────
def test_lance_tout_seul_sans_la_tour(monkeypatch, capsys, tmp_path):
    """Lance comme programme, sans module de la tour et sans reseau : il affiche
    ses cinq outils et chacun dit honnetement ce qu'il ne voit pas."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setitem(sys.modules, "haichi_outils_tour", None)
    monkeypatch.setitem(sys.modules, "nano_moteur_ultra", None)

    class SocketFerme(socket.socket):
        def connect(self, adresse):
            raise ConnectionRefusedError("ferme")
    monkeypatch.setattr(socket, "socket", SocketFerme)

    def urlopen_refuse(*a, **k):
        raise OSError("pas de reseau")
    monkeypatch.setattr("urllib.request.urlopen", urlopen_refuse)
    g = runpy.run_path(os.path.join(REPO, "haichi_outils.py"), run_name="__main__")
    sortie = capsys.readouterr().out
    assert g["_tour"] is None
    for titre in ("HEURE", "MODULES", "VEILLE", "RESEAU", "MOI"):
        assert "\n" + titre + "\n" in sortie
    assert "ETEINTE" in sortie and "pas de reseau" in sortie
    assert g["outil_qui_est_en_ligne"]().startswith("Je ne peux pas regarder")
