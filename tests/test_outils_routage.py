#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QUEL OUTIL POUR QUELLE QUESTION — haichi_outils.chercher_un_outil et le calcul.

Ce qu'on prouve, SANS reseau et SANS appeler un seul outil pour de vrai :
  - chaque question typique reveille le BON outil ;
  - les questions voisines (« la veillee », « qui tournent », « qui est la
    presidente ») ne reveillent RIEN, ou pas le mauvais ;
  - le calcul passe avant tout, ne lit que deux nombres et un signe, et
    refuse ce qui n'est pas un calcul ;
  - un outil qui veut la question la recoit, les autres non ;
  - les greffons ne passent qu'apres, et leur panne est dite en clair.
"""
import os
import sys
import types

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import haichi_outils as ho  # noqa: E402


@pytest.fixture(autouse=True)
def sans_greffon(monkeypatch):
    """Par defaut, aucun greffon ne repond : le routage ne depend que d'Arthur."""
    faux = types.ModuleType("haichi_greffons")
    faux.essayer = lambda q: None
    monkeypatch.setitem(sys.modules, "haichi_greffons", faux)
    return faux


def _nom(question):
    """Le nom de l'outil choisi, en le trouvant dans OUTILS (sans l'appeler)."""
    return ho._chercher_un_outil_sans_calcul(question)


# ── le bon outil pour la bonne question ─────────────────────────────────────
@pytest.mark.parametrize("question, outil", [
    ("quelle heure est il", "outil_heure"),
    ("on est quel jour", "outil_heure"),
    ("date du jour", "outil_heure"),
    ("combien de modules sont allumes", "outil_modules"),
    ("etat du cockpit", "outil_modules"),
    ("tu as lu la veille ia", "outil_veille"),
    ("montre moi la veille", "outil_veille"),
    ("etat du reseau", "outil_reseau"),
    ("combien de connexions", "outil_reseau"),
    ("qui es tu", "outil_moi"),
    ("combien de sujets tu connais", "outil_moi"),
    ("eveil systeme", "outil_eveil_systeme"),
    ("git status", "outil_eveil_systeme"),
    ("etat de la machine", "outil_eveil_systeme"),
    ("lance les tests", "outil_analyse_banc"),
    ("le banc est vert", "outil_analyse_banc"),
    ("refactor ce dossier", "outil_refactor"),
    ("gouvernance des agents", "outil_cockpit_gouvernance"),
    ("parle moi du system c", "outil_cockpit_gouvernance"),
    ("qui est en ligne", "outil_qui_est_en_ligne"),
    ("qui est la", "outil_qui_est_en_ligne"),
    ("qui tourne en ce moment", "outil_qui_est_en_ligne"),
    ("le serveur va bien", "outil_serveur_va_bien"),
    ("quel est l etat du serveur", "outil_serveur_va_bien"),
    ("est ce que tout va bien", "outil_serveur_va_bien"),
    ("qui est dans la salle", "outil_agents_salle"),
    ("qui parle le plus", "outil_agents_salle"),
    ("que font les agents", "outil_que_font_les_agents"),
    ("quels agents sont muets", "outil_que_font_les_agents"),
    ("qui a un moteur allume", "outil_agents_moteur_allume"),
    ("qui est musele", "outil_agents_moteur_allume"),
    ("rollback cockpit", "outil_expliquer_rollback"),
    ("redemarre le cockpit", "outil_redemarrer_cockpit"),
    ("le cockpit est casse", "outil_redemarrer_cockpit"),
    ("je veux une application de recettes", "outil_deposer_pour_les_agents"),
    ("transmets aux agents", "outil_deposer_pour_les_agents"),
    ("qui est victor", "outil_ce_qua_fait_un_agent"),
    ("les exploits de clark", "outil_ce_qua_fait_un_agent"),
])
def test_chaque_question_reveille_son_outil(question, outil):
    """Une question typique trouve l'outil ecrit pour elle, et pas un voisin."""
    f = _nom(question)
    assert f is not None and f.__name__ == outil


@pytest.mark.parametrize("question", [
    "l heure de la tour",                        # pas une expression entiere
    "la veillee de noel",                        # « la veille » dans un autre mot
    "qui tournent les pages",                    # « qui tourne » + lettres
    "qui est la presidente de la france",        # « qui est la$ » exige la fin
    "tout va bien chez toi",                     # « tout va bien$ » exige la fin
    "raconte moi une histoire",
    "",
])
def test_les_questions_voisines_ne_reveillent_rien(question):
    """Un mot isole ou un morceau de mot ne suffit pas a reveiller un outil."""
    assert _nom(question) is None
    assert ho.chercher_un_outil(question) is None


def test_question_vide_ou_absente():
    """None ou des blancs : aucun outil, aucune panne."""
    assert ho.chercher_un_outil(None) is None
    assert ho.chercher_un_outil("   ") is None


def test_expression_presente_mots_entiers_et_fin():
    """« $ » veut dire : l'expression FINIT la question (blancs permis)."""
    assert ho._expression_presente("qui est la$", "bon qui est la  ")
    assert not ho._expression_presente("qui est la$", "qui est la bas")
    assert ho._expression_presente("git status", "fais un git status stp")
    assert not ho._expression_presente("git status", "git statuses")


@pytest.mark.xfail(strict=True, reason="bug: 'les agents actifs' (outil_agents_moteur_allume) "
                   "est masque par 'agents actifs' d'outil_agents_salle, range avant")
def test_les_agents_actifs_va_au_moteur():
    """L'expression « les agents actifs » est declaree pour l'outil moteur."""
    assert _nom("les agents actifs").__name__ == "outil_agents_moteur_allume"


@pytest.mark.xfail(strict=True, reason="bug: 'combien d agents sans cervelle' "
                   "(outil_que_font_les_agents) est masque par 'combien d agents' d'outil_agents_salle")
def test_combien_sans_cervelle_va_aux_familles():
    """L'expression « combien d agents sans cervelle » est declaree pour les familles."""
    assert _nom("combien d agents sans cervelle").__name__ == "outil_que_font_les_agents"


# ── le calcul passe avant tout ──────────────────────────────────────────────
@pytest.mark.parametrize("question, attendu", [
    ("combien font 17 fois 23 ?", "17 fois 23 = 391"),
    ("12 plus 30", "12 plus 30 = 42"),
    ("10 moins 4", "10 moins 4 = 6"),
    ("5 - 2", "5 moins 2 = 3"),
    ("5 moins -3", "5 moins -3 = 8"),
    ("-5 plus 3", "-5 plus 3 = -2"),
    ("144 divise par 12", "144 divise par 12 = 12"),
    ("144 divisé par 12", "144 divise par 12 = 12"),
    ("7 multiplié par 6", "7 fois 6 = 42"),
    ("multiplie 12 par 12", "12 fois 12 = 144"),
    ("3 sur 4", "3 divise par 4 = 0.75"),
    ("2,5 plus 1", "2.5 plus 1 = 3.5"),
    ("1.5 x 2", "1.5 fois 2 = 3"),
    ("10 / 3", "10 divise par 3 = 3.333333"),
    ("6 * 7", "6 fois 7 = 42"),
])
def test_le_calcul_repond_juste(question, attendu):
    """Deux nombres, un signe entre eux : un resultat exact, joliment ecrit."""
    assert ho.outil_calcul(question) == attendu
    f = ho.chercher_un_outil(question)
    assert f() == attendu


def test_diviser_par_zero_est_dit():
    """Diviser par zero ne plante pas : Arthur dit qu'il n'y a pas de resultat."""
    assert "pas diviser par zero" in ho.outil_calcul("8 divise par 0")
    assert "pas diviser par zero" in ho.chercher_un_outil("8 / 0")()


@pytest.mark.parametrize("question", [
    "le plus grand de 3 et 7",       # « de ... et » n'est pas un signe
    "3 tours sur 2 sites",           # du texte autour du signe
    "12 par 12",                     # « par » seul ne dit rien
    "combien font 3",                # un seul nombre
    "1 plus 2 plus 3",               # trois nombres
    "10-3",                          # rien entre les deux nombres
    "3 fois 4 moins",                # deux signes
    "quelle heure est il",
])
def test_ce_qui_n_est_pas_un_calcul_est_refuse(question):
    """Mieux vaut ne pas calculer que calculer a cote."""
    assert ho._lire_un_calcul(question) is None
    assert ho.outil_calcul(question) is None


def test_calcul_avant_les_regles():
    """« 3 fois 4 » contient « fois » : c'est le calcul qui repond, pas un outil."""
    assert ho.chercher_un_outil("quelle heure 3 fois 4")() == "3 fois 4 = 12"


def test_lire_un_calcul_nombre_illisible(monkeypatch):
    """Un nombre que float ne sait pas lire est refuse, sans exception."""
    vrai_float = float

    def float_capricieux(x):
        raise ValueError("illisible")
    monkeypatch.setattr("builtins.float", float_capricieux)
    try:
        assert ho._lire_un_calcul("3 plus 4") is None
    finally:
        monkeypatch.setattr("builtins.float", vrai_float)


def test_joli():
    """4.0 s'ecrit « 4 », 4.5 « 4.5 », et un tiers n'a pas de queue de zeros."""
    assert ho._joli(4.0) == "4"
    assert ho._joli(-2.0) == "-2"
    assert ho._joli(4.5) == "4.5"
    assert ho._joli(1 / 3) == "0.333333"


# ── l'outil qui veut la question la recoit ──────────────────────────────────
def test_emballer_donne_la_question_a_qui_la_demande():
    """Un outil a un parametre recoit la question ; un outil sans parametre non."""
    recu = []

    def avec(q):
        recu.append(q)
        return "vu " + q

    def sans():
        return "seul"
    assert ho._emballer(None, "x") is None
    assert ho._emballer(sans, "x") is sans
    assert ho._emballer(avec, "qui est victor")() == "vu qui est victor"
    assert recu == ["qui est victor"]


def test_emballer_signature_illisible():
    """Un objet dont on ne lit pas la signature est rendu tel quel."""
    class Bizarre:
        __signature__ = "pas une signature"

        def __call__(self):
            return "ok"
    b = Bizarre()
    assert ho._emballer(b, "q") is b


def test_ce_qua_fait_recoit_la_question(monkeypatch):
    """« qui est victor » : l'outil des agents recoit bien la question entiere."""
    vu = []
    monkeypatch.setattr(ho, "outil_ce_qua_fait_un_agent",
                        lambda question: vu.append(question) or "Victor code.")
    # la liste OUTILS garde l'ancienne fonction : on la remplace aussi la-bas
    neuve = [(expr, ho.outil_ce_qua_fait_un_agent
              if getattr(f, "__name__", "") == "outil_ce_qua_fait_un_agent" else f)
             for expr, f in ho.OUTILS]
    monkeypatch.setattr(ho, "OUTILS", neuve)
    assert ho.chercher_un_outil("qui est victor")() == "Victor code."
    assert vu == ["qui est victor"]


# ── les greffons passent APRES ──────────────────────────────────────────────
def test_greffon_repond_quand_personne_d_autre(sans_greffon):
    """Aucun outil d'Arthur ne repond : le greffon a la main."""
    sans_greffon.essayer = lambda q: {"titre": "Meteo", "reponse": "Il pleut."}
    assert ho.chercher_un_outil("fera t il beau demain")() == "Il pleut."


def test_greffon_ne_passe_pas_devant_arthur(sans_greffon):
    """Un greffon qui voudrait repondre a « quelle heure » n'est meme pas consulte."""
    appels = []
    sans_greffon.essayer = lambda q: appels.append(q) or {"titre": "T", "reponse": "non"}
    f = ho.chercher_un_outil("quelle heure est il")
    assert f.__name__ == "outil_heure"
    assert appels == []


def test_greffon_en_panne_le_dit(sans_greffon):
    """Un greffon tombe : son titre et sa panne sont dits, rien n'est invente."""
    sans_greffon.essayer = lambda q: {"titre": "Meteo", "reponse": None,
                                      "panne": "pas de fonction"}
    assert ho.chercher_un_outil("meteo")() == "Le greffon « Meteo » est tombé : pas de fonction"


def test_greffon_qui_plante_est_ignore(sans_greffon):
    """Un module de greffons qui leve une exception ne fait pas tomber Arthur."""
    def boum(q):
        raise RuntimeError("boum")
    sans_greffon.essayer = boum
    assert ho.chercher_un_outil("meteo") is None


def test_greffons_introuvables(monkeypatch):
    """Sans module de greffons du tout, on rend simplement None."""
    monkeypatch.setitem(sys.modules, "haichi_greffons", None)
    assert ho._greffon("meteo") is None
