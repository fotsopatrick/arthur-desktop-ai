#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE COMPAGNON HAICHI (30/09/2026) — haichi_avatar.py.

Ce qu'on prouve, SANS ecran, SANS GTK et SANS vrai cockpit (un faux « gi »
en memoire, un faux cockpit sur 127.0.0.1, un HOME de bac a sable) :
  - une reponse creuse (« inconnu », vide, « erreur ») n'est pas une reponse ;
  - Arthur monte les etages dans l'ordre : ses outils, le grand modele,
    le cerveau en memoire, et sinon il AVOUE sans inventer ;
  - il dit toujours ce qu'il a fait et combien de temps ca a pris ;
  - le jeton du cockpit part avec chaque POST ;
  - la case de saisie ne perd jamais la phrase de Patrick ;
  - la bulle echappe le texte et rend les liens cliquables ;
  - la voix, la bouche, le rond rabattu et le bouton fermer font ce qu'ils
    disent ;
  - le visage anime, le carnet de parole et la boite aux lettres se
    branchent quand leurs fichiers existent, et se taisent sinon.
"""
import importlib.util
import json
import os
import runpy
import socket
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHEMIN = os.path.join(REPO, "haichi_avatar.py")
if REPO not in sys.path:
    sys.path.insert(0, REPO)


# ---------------------------------------------------------------------------
# Le faux GTK : des widgets qui acceptent tout et se souviennent de tout.
# ---------------------------------------------------------------------------
class _Widget:
    """Un widget qui accepte n'importe quel appel public (MagicMock par nom),
    mais PAS les noms prives : hasattr(self, "_visages") doit rester faux."""

    def __init__(self, *a, **k):
        pass

    def __getattr__(self, nom):
        if nom.startswith("_"):
            raise AttributeError(nom)
        m = mock.MagicMock(name=nom)
        object.__setattr__(self, nom, m)
        return m


class _Tampon:
    def __init__(self):
        self.texte = ""

    def set_text(self, t):
        self.texte = t

    def get_start_iter(self):
        return 0

    def get_end_iter(self):
        return len(self.texte)

    def get_text(self, debut, fin, cache):
        return self.texte[debut:fin]


class _VueTexte(_Widget):
    def __init__(self, *a, **k):
        self._tampon = _Tampon()

    def get_buffer(self):
        return self._tampon


class _Saisie(_Widget):
    def __init__(self, *a, **k):
        self._texte = ""
        self.historique = []

    def get_text(self):
        return self._texte

    def set_text(self, t):
        self._texte = t
        self.historique.append(t)


class _Espace(types.ModuleType):
    """Gtk / Gdk / GLib : tout nom inconnu devient une fabrique de mocks
    NEUFS a chaque appel (deux Gtk.Label() ne sont pas le meme objet)."""

    def __getattr__(self, nom):
        if nom.startswith("__"):
            raise AttributeError(nom)
        m = mock.MagicMock(name=nom, side_effect=lambda *a, **k: mock.MagicMock())
        setattr(self, nom, m)
        return m


def _faux_gi():
    gi = types.ModuleType("gi")
    gi.require_version = mock.MagicMock()
    depot = types.ModuleType("gi.repository")
    Gtk, Gdk, GLib = _Espace("Gtk"), _Espace("Gdk"), _Espace("GLib")
    Gtk.Window = type("Window", (_Widget,), {})
    Gtk.ScrolledWindow = type("ScrolledWindow", (_Widget,), {})
    Gtk.TextView = _VueTexte
    Gtk.Entry = _Saisie
    Gtk.main_quit = mock.MagicMock()
    Gtk.main = mock.MagicMock()
    Gdk.KEY_Return, Gdk.KEY_KP_Enter = 65293, 65421
    Gdk.ModifierType = types.SimpleNamespace(SHIFT_MASK=1)
    Gdk.CURRENT_TIME = 0
    GLib.minuteries = []
    GLib.au_repos = []

    def timeout_add(ms, fn, *a):
        GLib.minuteries.append((ms, fn))
        return len(GLib.minuteries)

    def idle_add(fn, *a):
        GLib.au_repos.append((fn, a))
        fn(*a)                    # on joue tout de suite : la bulle est visible
        return 1

    GLib.timeout_add, GLib.idle_add = timeout_add, idle_add
    depot.Gtk, depot.Gdk, depot.GLib = Gtk, Gdk, GLib
    gi.repository = depot
    return gi, depot


class _FilSync:
    """Un fil qui s'execute tout de suite, dans le test (deterministe)."""
    lances = []

    def __init__(self, target=None, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        _FilSync.lances.append((self.target, self.args))
        self.target(*self.args)


class _FilNote(_FilSync):
    """Un fil qu'on note sans le jouer."""

    def start(self):
        _FilSync.lances.append((self.target, self.args))


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Faux gi installe (et retire apres), HOME de bac a sable, jeton connu."""
    gi, depot = _faux_gi()
    monkeypatch.setitem(sys.modules, "gi", gi)
    monkeypatch.setitem(sys.modules, "gi.repository", depot)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("COCKPIT_TOKEN", "jeton-de-test")
    monkeypatch.setattr(sys, "path", list(sys.path))
    _FilSync.lances = []
    return types.SimpleNamespace(Gtk=depot.Gtk, Gdk=depot.Gdk, GLib=depot.GLib,
                                 home=tmp_path)


@pytest.fixture
def mod(env, monkeypatch):
    spec = importlib.util.spec_from_file_location("haichi_avatar_sous_test", CHEMIN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.setattr(m, "threading", types.SimpleNamespace(Thread=_FilSync))
    return m


@pytest.fixture
def h(mod):
    return mod.Haichi()


def _texte_bulle(h):
    return h.etiquette_texte.set_markup.call_args[0][0]


def _pensee_bulle(h):
    return h.etiquette_pensee.set_text.call_args[0][0]


# ---------------------------------------------------------------------------
# Un faux cockpit, sur 127.0.0.1 port libre.
# ---------------------------------------------------------------------------
class _Cockpit(BaseHTTPRequestHandler):
    routes = {}
    recus = []

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        brut = self.rfile.read(n)
        _Cockpit.recus.append((self.path, self.headers.get("X-Cockpit-Token"), brut))
        code, corps = _Cockpit.routes.get(self.path, (404, {"erreur": "route"}))
        donnees = corps if isinstance(corps, bytes) else json.dumps(corps).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(donnees)))
        self.end_headers()
        self.wfile.write(donnees)

    def log_message(self, *a):
        pass


@pytest.fixture
def cockpit(mod, monkeypatch):
    _Cockpit.routes, _Cockpit.recus = {}, []
    s = HTTPServer(("127.0.0.1", 0), _Cockpit)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    monkeypatch.setattr(mod, "COCKPIT", "http://127.0.0.1:%d" % s.server_address[1])
    yield _Cockpit
    s.shutdown()
    s.server_close()


@pytest.fixture
def cerveau(monkeypatch):
    """Un faux nano_moteur_ultra en memoire : on choisit ce qu'il rend."""
    faux = types.ModuleType("nano_moteur_ultra")
    faux.questions = []
    faux.rendre = {"erreur": "rien"}

    def nano_moteur_ultra(q):
        faux.questions.append(q)
        if isinstance(faux.rendre, Exception):
            raise faux.rendre
        return faux.rendre

    faux.nano_moteur_ultra = nano_moteur_ultra
    monkeypatch.setitem(sys.modules, "nano_moteur_ultra", faux)
    return faux


def _port_ferme():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ---------------------------------------------------------------------------
# Ce qui est une vraie reponse, et ce qui ne l'est pas
# ---------------------------------------------------------------------------
def test_vraie_reponse_accepte_les_trois_cles(h):
    """answer, reponse et raw_output sont lus, dans cet ordre, et nettoyes."""
    assert h._est_une_vraie_reponse({"answer": "  Oulan-Bator \n"}) == "Oulan-Bator"
    assert h._est_une_vraie_reponse({"reponse": "Yaounde"}) == "Yaounde"
    assert h._est_une_vraie_reponse({"raw_output": "brut"}) == "brut"
    assert h._est_une_vraie_reponse({"answer": "A", "reponse": "B"}) == "A"


@pytest.mark.parametrize("d", [
    None, [], "texte", 42,
    {"erreur": "inconnu", "answer": "Paris"},
    {}, {"answer": ""}, {"answer": "   "},
    {"answer": "(rien)"}, {"answer": "Inconnu."}, {"answer": "Je ne sais pas !"},
    {"reponse": "erreur"},
])
def test_vraie_reponse_refuse_le_creux(h, d):
    """Pas un dict, une fiche « erreur », un vide ou une formule creuse : None."""
    assert h._est_une_vraie_reponse(d) is None


def test_vraie_reponse_ne_confond_pas_une_phrase_qui_contient_erreur(h):
    """« Il y a une erreur dans ton code » est une vraie reponse."""
    assert h._est_une_vraie_reponse({"answer": "Il y a une erreur."}) == "Il y a une erreur."


@pytest.mark.xfail(strict=True, reason="bug: haichi_avatar.py:653 — un champ answer non "
                   "texte (nombre) fait planter .strip() ; le fil de _demander meurt, Arthur se tait")
def test_vraie_reponse_nombre(h):
    """Un cockpit qui rend {"answer": 42} : la reponse est « 42 », pas un plantage."""
    assert h._est_une_vraie_reponse({"answer": 42}) == "42"


# ---------------------------------------------------------------------------
# Ce qu'il raconte de son travail
# ---------------------------------------------------------------------------
def test_raconter_comment_avec_et_sans_pensee(h):
    """Chaque etage, son temps, son resultat, et le total ; la pensee devant."""
    etages = [("mes outils", 12, "rien"), ("le grand modele", 1500, "trouve")]
    ligne = "mes outils 12 ms rien -> le grand modele 1500 ms trouve  (en tout 1512 ms)"
    assert h._raconter_comment(etages, "") == ligne
    assert h._raconter_comment(etages, "wikipedia") == "wikipedia | " + ligne
    assert h._raconter_comment([], "") == "  (en tout 0 ms)"


# ---------------------------------------------------------------------------
# Les etages de _demander
# ---------------------------------------------------------------------------
def test_etage1_mes_outils_repond(h, cockpit, cerveau):
    """Le serveur d'action repond : bulle remplie, grand modele JAMAIS appele,
    le jeton du cockpit part avec la question."""
    cockpit.routes["/api/arthur-action"] = (200, {"answer": "Oulan-Bator", "thought": "capitales"})
    h._demander("capitale de la Mongolie ?")
    assert _texte_bulle(h) == "Oulan-Bator"
    pensee = _pensee_bulle(h)
    assert pensee.startswith("capitales | mes outils ") and "ms trouve" in pensee
    chemins = [c[0] for c in cockpit.recus]
    assert chemins == ["/api/arthur-action"]
    _, jeton, brut = cockpit.recus[0]
    assert jeton == "jeton-de-test"
    assert json.loads(brut) == {"prompt": "capitale de la Mongolie ?", "action": "parler"}
    assert cerveau.questions == []


def test_etage1_pensee_par_defaut(h, cockpit):
    """Sans thought ni source, la pensee dit « mes outils »."""
    cockpit.routes["/api/arthur-action"] = (200, {"reponse": "Oui."})
    h._demander("ca marche ?")
    assert _pensee_bulle(h).startswith("mes outils | mes outils ")


def test_etage2_grand_modele_apres_un_inconnu_poli(h, cockpit, cerveau):
    """Un « inconnu » poli en 200 n'arrete pas la route : il previent qu'il
    cherche, puis le grand modele repond."""
    cockpit.routes["/api/arthur-action"] = (200, {"erreur": "inconnu"})
    cockpit.routes["/api/nano-search"] = (200, {"answer": "Victor Hugo", "source": "nemotron"})
    h._demander("qui a ecrit les Miserables")
    textes = [c[0][0] for c in h.etiquette_texte.set_markup.call_args_list]
    assert "Je cherche, un instant — je te reponds." in textes
    assert textes[-1] == "Victor Hugo"
    pensee = _pensee_bulle(h)
    assert pensee.startswith("nemotron | mes outils ")
    assert "ms rien -> le grand modele " in pensee and pensee.count("trouve") == 1
    assert [c[0] for c in cockpit.recus] == ["/api/arthur-action", "/api/nano-search"]
    assert json.loads(cockpit.recus[1][2]) == {"prompt": "qui a ecrit les Miserables"}
    assert cockpit.recus[1][1] == "jeton-de-test"
    assert cerveau.questions == []


def test_etage2bis_cerveau_en_memoire(h, cockpit, cerveau):
    """Le cockpit tombe (500) : on demande au cerveau local, sans HTTP."""
    cockpit.routes["/api/arthur-action"] = (500, {"erreur": "panne"})
    cockpit.routes["/api/nano-search"] = (500, {"erreur": "panne"})
    cerveau.rendre = {"reponse": "42", "thought": "calcul local"}
    h._demander("six fois sept")
    assert cerveau.questions == ["six fois sept"]
    assert _texte_bulle(h) == "42"
    pensee = _pensee_bulle(h)
    assert pensee.startswith("calcul local | ")
    assert "le cerveau, en memoire" in pensee and pensee.endswith("ms)")
    assert REPO in sys.path          # le repli sait ou trouver le moteur


def test_etage3_aveu_sans_invention(h, cockpit, cerveau):
    """Rien nulle part : Arthur dit qu'il ne sait pas, avec la raison, et la
    dit a voix haute si la voix est allumee."""
    cockpit.routes["/api/arthur-action"] = (200, {"answer": "je ne sais pas"})
    cockpit.routes["/api/nano-search"] = (200, {"erreur": "quota epuise"})
    cerveau.rendre = RuntimeError("moteur casse")
    h.voix_allumee = True
    h._demander("question impossible")
    assert _texte_bulle(h) == "Je ne sais pas, et je ne vais pas inventer. quota epuise"
    pensee = _pensee_bulle(h)
    assert pensee.startswith("mes outils ")
    assert "le cerveau, en memoire" in pensee and pensee.count("rien") == 3
    voix = [c for c in cockpit.recus if c[0] == "/api/voix"]
    assert len(voix) == 1
    assert json.loads(voix[0][2]) == {
        "texte": "Je ne sais pas, et je ne vais pas inventer. quota epuise", "jouer": True}


def test_etage3_raison_par_defaut(h, cockpit, cerveau):
    """Le grand modele repond vide sans erreur : la raison generique est dite."""
    cockpit.routes["/api/arthur-action"] = (200, {"answer": ""})
    cockpit.routes["/api/nano-search"] = (200, {"answer": "(rien)"})
    h._demander("x")
    assert _texte_bulle(h).endswith("les deux etages n ont rien trouve")


def test_cockpit_absent_tout_part_en_repli(h, mod, cerveau, monkeypatch):
    """Port ferme : aucune exception ne remonte, le cerveau local repond."""
    monkeypatch.setattr(mod, "COCKPIT", "http://127.0.0.1:%d" % _port_ferme())
    cerveau.rendre = {"answer": "je suis la"}
    h._demander("tu es la ?")
    assert _texte_bulle(h) == "je suis la"
    assert "mes outils" in _pensee_bulle(h)


def test_reponse_json_illisible_est_une_panne(h, cockpit, cerveau):
    """Un corps qui n'est pas du JSON est traite comme une erreur, pas un plantage."""
    cockpit.routes["/api/arthur-action"] = (200, b"<html>pas du json</html>")
    cockpit.routes["/api/nano-search"] = (200, b"")
    h._demander("q")
    assert _texte_bulle(h).startswith("Je ne sais pas, et je ne vais pas inventer. ")


@pytest.mark.xfail(strict=True, reason="bug: haichi_avatar.py:735 — si /api/nano-search rend "
                   "du JSON non objet (null, liste) et que le cerveau local echoue, d.get() "
                   "leve AttributeError : Arthur reste fige sur « Je cherche »")
def test_nano_search_rend_null(h, cockpit, cerveau):
    """nano-search rend « null » : Arthur doit quand meme avouer, pas se figer."""
    cockpit.routes["/api/arthur-action"] = (200, {"erreur": "inconnu"})
    cockpit.routes["/api/nano-search"] = (200, b"null")
    h._demander("q")
    assert _texte_bulle(h).startswith("Je ne sais pas")


def test_cerveau_local_indisponible(mod, cerveau):
    """Le moteur qui plante donne une fiche « erreur », jamais une exception."""
    cerveau.rendre = ValueError("x")
    assert mod._reponse_du_cerveau_local("q") == {"erreur": "ni cockpit ni cerveau local disponibles"}
    cerveau.rendre = {"answer": "ok"}
    assert mod._reponse_du_cerveau_local("q") == {"answer": "ok"}


# ---------------------------------------------------------------------------
# La voix
# ---------------------------------------------------------------------------
def test_voix_basculer_allume_puis_eteint(h, cockpit):
    """Allumer : bouton 🔊, classe active, « Ma voix est allumée. » ;
    eteindre : bouton 🔇, et le cockpit recoit voix-stop."""
    h._basculer_voix(None)
    assert h.voix_allumee is True
    h.bouton_voix.set_label.assert_called_with("🔊")
    h.bouton_voix.get_style_context.return_value.add_class.assert_any_call("active")
    assert json.loads(cockpit.recus[-1][2]) == {"texte": "Ma voix est allumée.", "jouer": True}
    h._basculer_voix(None)
    assert h.voix_allumee is False
    h.bouton_voix.set_label.assert_called_with("🔇")
    h.bouton_voix.get_style_context.return_value.remove_class.assert_called_with("active")
    assert cockpit.recus[-1][0] == "/api/voix-stop" and cockpit.recus[-1][2] == b"{}"
    assert cockpit.recus[-1][1] == "jeton-de-test"


def test_voix_stop_cockpit_absent_ne_plante_pas(h, mod, monkeypatch):
    """Eteindre la voix sans cockpit : silence, pas d'exception."""
    monkeypatch.setattr(mod, "COCKPIT", "http://127.0.0.1:%d" % _port_ferme())
    h.voix_allumee = True
    h._basculer_voix(None)
    assert h.voix_allumee is False
    h._dire_a_voix_haute("rien ne part")     # avale l'erreur aussi


def test_voix_eteinte_ne_parle_pas(h):
    """Voix eteinte : aucun fil de parole n'est lance."""
    h._peut_etre_a_voix_haute("bonjour")
    assert _FilSync.lances == []


def test_voix_texte_tronque_a_1200(h, cockpit):
    """Un tres long texte est coupe a 1200 signes avant de partir."""
    h._dire_a_voix_haute("a" * 5000)
    assert len(json.loads(cockpit.recus[-1][2])["texte"]) == 1200


# ---------------------------------------------------------------------------
# La bulle
# ---------------------------------------------------------------------------
def test_accueil_a_la_naissance(h, mod):
    """A la naissance, la bulle dit bonjour, sans pensee."""
    assert _texte_bulle(h) == mod.ACCUEIL
    h.etiquette_pensee.set_visible.assert_called_with(False)
    h.etiquette_pensee.hide.assert_called()


def test_bulle_echappe_et_rend_les_liens(h):
    """Le texte est echappe pour Pango et les liens deviennent cliquables."""
    h.montrer_bulle("Voir <b>ici</b> : https://exemple.org/a?b=1&c=2 et file:///tmp/x", "p" * 300)
    m = _texte_bulle(h)
    assert "&lt;b&gt;ici&lt;/b&gt;" in m
    assert '<a href="https://exemple.org/a?b=1&amp;c=2"><span foreground="#2563eb" ' \
           'underline="single">https://exemple.org/a?b=1&amp;c=2</span></a>' in m
    assert '<a href="file:///tmp/x">' in m
    h.etiquette_texte.set_use_markup.assert_called_with(True)
    assert _pensee_bulle(h) == "p" * 160
    h.etiquette_pensee.set_visible.assert_called_with(True)
    h.rouleau.get_vadjustment.return_value.set_value.assert_called_with(0)


def test_bulle_markup_refuse_repli_texte_brut(h):
    """Si Pango refuse le balisage, le texte brut s'affiche quand meme."""
    h.etiquette_texte.set_markup.side_effect = RuntimeError("markup")
    h.rouleau.get_vadjustment.side_effect = RuntimeError("pas d'ascenseur")
    h.montrer_bulle("a < b", "")
    h.etiquette_texte.set_text.assert_called_with("a < b")


# ---------------------------------------------------------------------------
# La saisie et le clavier
# ---------------------------------------------------------------------------
def test_envoyer_case_vide_reprend_le_clavier(h, mod, monkeypatch):
    """Case vide (ou blanche) : rien ne part, le clavier est repris."""
    monkeypatch.setattr(mod, "threading", types.SimpleNamespace(Thread=_FilNote))
    h.saisie.set_text("   ")
    h.present.reset_mock()
    h.envoyer()
    assert _FilSync.lances == []
    h.present.assert_called_once()


def test_envoyer_part_puis_vide_la_case(h, mod, env, monkeypatch):
    """La phrase est mise de cote, la bulle dit qu'il reflechit, le fil part
    avec la question, et SEULEMENT ensuite la case est videe."""
    monkeypatch.setattr(mod, "threading", types.SimpleNamespace(Thread=_FilNote))
    h.saisie.set_text("  qui est Victor  ")
    h.envoyer()
    assert h._dernier_texte == "qui est Victor"
    assert _texte_bulle(h) == "Haichi réfléchit…"
    assert _FilSync.lances == [(h._demander, ("qui est Victor",))]
    assert h.saisie.historique[-2:] == ["", ""]      # tout de suite, puis au repos
    assert h.saisie.get_text() == ""


def test_envoyer_echec_du_fil_rend_la_phrase(h, mod, monkeypatch):
    """Le fil ne part pas : la phrase est rendue, l'erreur est dite."""
    class _FilCasse(_FilSync):
        def start(self):
            raise RuntimeError("plus de fils")

    monkeypatch.setattr(mod, "threading", types.SimpleNamespace(Thread=_FilCasse))
    h.saisie.set_text("ma longue spec")
    h.envoyer()
    assert h.saisie.get_text() == "ma longue spec"
    assert _texte_bulle(h) == "Je n ai pas pu partir chercher : plus de fils"


def test_touche_saisie(h, env, monkeypatch):
    """Entree envoie ; Maj+Entree laisse passer ; une lettre ne fait rien."""
    envois = []
    monkeypatch.setattr(h, "envoyer", lambda: envois.append(1))
    ev = types.SimpleNamespace
    assert h._touche_saisie(None, ev(keyval=env.Gdk.KEY_Return, state=0)) is True
    assert h._touche_saisie(None, ev(keyval=env.Gdk.KEY_KP_Enter, state=0)) is True
    assert h._touche_saisie(None, ev(keyval=env.Gdk.KEY_Return, state=1)) is False
    assert h._touche_saisie(None, ev(keyval=ord("a"), state=0)) is False
    assert envois == [1, 1]


def test_reprendre_le_clavier(h, env):
    """Presente la fenetre, reclame le focus, et rend False (signal non bloque)."""
    fen = h.get_window.return_value
    assert h.reprendre_le_clavier() is False
    fen.focus.assert_called_with(env.Gdk.CURRENT_TIME)
    h.get_window.return_value = None
    h.present.side_effect = None
    assert h.reprendre_le_clavier() is False


def test_reprendre_le_clavier_avale_les_erreurs(h):
    """Une fenetre pas encore dessinee ne fait pas planter la reprise."""
    h.present.side_effect = RuntimeError("pas encore")
    h.saisie.grab_focus = mock.MagicMock(side_effect=RuntimeError("non"))
    assert h.reprendre_le_clavier() is False


def test_signaux_branches(h):
    """Les signaux de la fenetre et de la case sont bien branches :
    clic gauche = on l'attrape, clic droit = rien ; destroy quitte."""
    signaux = {}
    for c in h.connect.call_args_list:
        signaux.setdefault(c[0][0], []).append(c[0][1])
    assert set(signaux) >= {"destroy", "button-press-event", "map-event"}
    for fn in signaux["button-press-event"] + signaux["map-event"]:
        fn(h, types.SimpleNamespace(button=1, x_root=10.7, y_root=20.2, time=99))
    h.begin_move_drag.assert_called_with(1, 10, 20, 99)
    h.begin_move_drag.reset_mock()
    for fn in signaux["button-press-event"]:
        assert fn(h, types.SimpleNamespace(button=3, x_root=0, y_root=0, time=0)) is False
    h.begin_move_drag.assert_not_called()
    # la case : activate envoie, un clic reprend le clavier
    envois = []
    h.envoyer = lambda: envois.append(1)
    for c in h.saisie.connect.call_args_list:
        c[0][1]()
    assert envois == [1]


def test_boutons_branches(h, mod, monkeypatch):
    """Le bouton rabattre bascule, le bouton fermer eteint l'agent."""
    monkeypatch.setattr(mod, "open", lambda *a, **k: (_ for _ in ()).throw(OSError()),
                        raising=False)
    rappel = h.bouton_rabattre.connect.call_args[0][1]
    rappel(None)
    assert h.rabattu is True
    assert h.bouton_fermer.connect.call_args[0][1] == h._eteindre_agent


def test_image_qui_refuse_les_clics(mod, env):
    """Si l'image refuse les evenements, la fenetre reste attrapable."""
    image = mock.MagicMock()
    image.add_events.side_effect = TypeError("pas d'evenements")
    env.Gtk.Image = mock.MagicMock()
    env.Gtk.Image.new_from_file.return_value = image
    h = mod.Haichi()
    assert h.dessin is image
    image.connect.assert_not_called()
    assert any(c[0][0] == "button-press-event" for c in h.connect.call_args_list)


def test_completion_des_commandes(h):
    """La case propose les commandes « / », triees, comme Braignak."""
    compl = h.saisie.set_completion.call_args[0][0]
    compl.set_inline_completion.assert_called_with(True)
    compl.set_popup_completion.assert_called_with(False)


def test_zone_texte_multiligne(mod):
    """La case multi-lignes rend ce qu'on y met, None devient vide."""
    z = mod.ZoneTexte()
    z.set_text("ligne 1\nligne 2")
    assert z.get_text() == "ligne 1\nligne 2"
    z.set_text(None)
    assert z.get_text() == ""
    z.vue.grab_focus = mock.MagicMock()
    z.grab_focus()
    z.grab_focus_without_selecting()
    assert z.vue.grab_focus.call_count == 2


# ---------------------------------------------------------------------------
# Rabattre en rond, fermer
# ---------------------------------------------------------------------------
def test_rabattre_puis_rouvrir(h, mod, tmp_path, monkeypatch):
    """Rabattu : bulle et barre cachees, 28x28, marges a 0, bouton △ ;
    rouvert : tout revient a 300x380 et ▽. Chaque bascule est notee."""
    journal = tmp_path / "rabattu.log"
    monkeypatch.setattr(mod, "open", lambda chemin, mode="r": open(journal, mode),
                        raising=False)
    h._basculer_rabattu()
    assert h.rabattu is True
    h.rouleau.hide.assert_called_once()
    h._barre.hide.assert_called_once()
    h.resize.assert_called_with(28, 28)
    h.dessin.set_size_request.assert_called_with(24, 24)
    h._colonne.set_margin_bottom.assert_called_with(0)
    h.bouton_rabattre.set_label.assert_called_with("△")
    h._basculer_rabattu()
    assert h.rabattu is False
    h.resize.assert_called_with(mod.LARGEUR, mod.HAUTEUR)
    h._colonne.set_margin_start.assert_called_with(10)
    h.dessin.get_style_context.return_value.remove_class.assert_called_with("dessin-rond")
    h.bouton_rabattre.set_label.assert_called_with("▽")
    assert journal.read_text() == ("arthur toggle -> rabattu=True\n"
                                   "arthur toggle -> rabattu=False\n")


def test_rabattre_erreur_avalee(h, mod, monkeypatch):
    """Si GTK refuse, rien ne plante et l'etat ne change pas."""
    monkeypatch.setattr(mod, "open", lambda *a, **k: (_ for _ in ()).throw(OSError()),
                        raising=False)
    h.rouleau.hide.side_effect = RuntimeError("gtk")
    h._basculer_rabattu()
    assert h.rabattu is False


def test_eteindre_agent(h, mod, env, monkeypatch):
    """Fermer arrete le service systemd ET quitte la boucle, meme si systemctl manque."""
    popen = mock.MagicMock()
    monkeypatch.setattr(mod, "subprocess", types.SimpleNamespace(Popen=popen))
    h._eteindre_agent()
    popen.assert_called_once_with(["systemctl", "--user", "stop", "arthur-flottant.service"])
    assert env.Gtk.main_quit.call_count == 1
    popen.side_effect = FileNotFoundError("systemctl")
    h._eteindre_agent(None)
    assert env.Gtk.main_quit.call_count == 2


# ---------------------------------------------------------------------------
# Le visage anime, le carnet, la boite aux lettres (fichiers dans ~/outils)
# ---------------------------------------------------------------------------
VISAGES = '''
ORIGINE = {"arthur": "/origine/arthur.png"}
FAITES = []
def fabriquer_les_images(qui): FAITES.append(qui)
def image_du_moment(t, etat, graine): return etat + str(graine)
def chemin_image(qui, nom): return "/img/%s-%s.png" % (qui, nom)
def respiration(t): return 2
'''

CARNET = '''
NOTES = []
def noter(agent, sens, texte, detail):
    if texte == "boum":
        raise RuntimeError("carnet plein")
    NOTES.append((agent, sens, texte, detail))
'''

BOITE = '''
LOTS = [["vieux message"], ["quelle heure est-il", "et demain ?"]]
def ramasser(qui):
    return LOTS.pop(0) if LOTS else []
'''


def _outils(env, **fichiers):
    d = env.home / "outils"
    d.mkdir(exist_ok=True)
    for nom, contenu in fichiers.items():
        (d / nom).write_text(contenu)


def test_sans_outils_photo_fixe(h, env):
    """Sans ~/outils : pas d'animation, pas de minuterie, pas de carnet."""
    assert not hasattr(h, "_visages")
    assert env.GLib.minuteries == []
    assert h._carnet is None
    assert h._battement() is False
    h.parler_pendant("rien")            # sans visage : ne fait rien
    assert not hasattr(h, "_parle_jusqua")


def test_visage_anime(mod, env, monkeypatch):
    """Avec le fichier des visages : une minuterie de 50 ms, l'image changee
    SEULEMENT quand elle change, la respiration, la bouche qui parle."""
    _outils(env, **{"visages-animes.py": VISAGES})
    h = mod.Haichi()
    assert h._visages.FAITES == ["arthur"] and h._graine == 1
    ms, fn = env.GLib.minuteries[0]
    assert ms == 50 and fn == h._battement
    assert h._parle_jusqua > 0           # l'accueil fait deja parler la bouche
    h._parle_jusqua = 0.0                # on le laisse se taire
    assert h._battement() is True
    h.dessin.set_from_file.assert_called_once_with("/img/arthur-repos1.png")
    h.dessin.set_size_request.assert_called_with(150, 168)
    h.dessin.set_size_request.reset_mock()
    assert h._battement() is True
    h.dessin.set_from_file.assert_called_once()          # pas rechargee
    h.dessin.set_size_request.assert_not_called()        # pas redemandee
    h.parler_pendant("x" * 28)
    assert h._battement() is True
    h.dessin.set_from_file.assert_called_with("/img/arthur-parle1.png")
    # rabattu : on ne regonfle pas le dessin
    h.rabattu, h._haut_pose = True, None
    h._battement()
    h.dessin.set_size_request.assert_not_called()


def test_parler_pendant_bornes(mod, env, monkeypatch):
    """La bouche bouge au moins 1 s, au plus 20 s, 14 lettres par seconde."""
    _outils(env, **{"visages-animes.py": VISAGES})
    h = mod.Haichi()
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1000.0)
    h.parler_pendant("")
    assert h._parle_jusqua == 1001.0
    h.parler_pendant("a" * 28)
    assert h._parle_jusqua == 1002.0
    h.parler_pendant("a" * 10000)
    assert h._parle_jusqua == 1020.0
    h.parler_pendant(None)
    assert h._parle_jusqua == 1001.0


def test_bouche_eteinte_puis_rallumee(mod, env):
    """Bouche eteinte : 🤐, image d'origine, le battement ne touche plus a rien ;
    rallumee : 👄 et classe active."""
    _outils(env, **{"visages-animes.py": VISAGES})
    h = mod.Haichi()
    h._basculer_bouche()
    assert h._bouche_allumee is False
    h.bouton_bouche.set_label.assert_called_with("\U0001F910")
    h.dessin.set_from_file.assert_called_with("/origine/arthur.png")
    h.dessin.set_size_request.assert_called_with(150, 166)
    assert h._image_posee is None
    h.dessin.set_from_file.reset_mock()
    assert h._battement() is True
    h.dessin.set_from_file.assert_not_called()
    h._basculer_bouche()
    assert h._bouche_allumee is True
    h.bouton_bouche.set_label.assert_called_with("\U0001F444")
    h.bouton_bouche.get_style_context.return_value.add_class.assert_called_with("active")


def test_bouche_eteinte_sans_visages(h):
    """Sans visage anime, eteindre la bouche ne plante pas."""
    h._basculer_bouche()
    assert h._bouche_allumee is False
    h.bouton_bouche.get_style_context.return_value.remove_class.assert_called_with("active")


def test_carnet_de_parole(mod, env, cockpit):
    """Le carnet note ce qui est recu et ce qui est rendu ; s'il plante,
    l'agent parle quand meme."""
    _outils(env, **{"paroles-des-agents.py": CARNET})
    h = mod.Haichi()
    assert h._carnet.NOTES[0] == ("arthur", "rendu", mod.ACCUEIL, "")
    cockpit.routes["/api/arthur-action"] = (200, {"answer": "oui"})
    h._demander("tu notes ?")
    assert ("arthur", "recu", "tu notes ?", "") in h._carnet.NOTES
    assert h._carnet.NOTES[-1][:3] == ("arthur", "rendu", "oui")
    h.montrer_bulle("boum")                       # le carnet leve : avale
    assert _texte_bulle(h) == "boum"


def test_boite_aux_lettres(mod, env, monkeypatch):
    """Le vieux courrier est jete a l'ouverture ; ensuite chaque phrase
    deposee est ecrite dans la case et envoyee."""
    _outils(env, **{"boite-aux-lettres.py": BOITE})
    h = mod.Haichi()
    assert (1000, h._relever_la_boite) in env.GLib.minuteries
    envoyes = []
    monkeypatch.setattr(h, "envoyer", lambda: envoyes.append(h.saisie.get_text()))
    assert h._relever_la_boite() is True
    assert envoyes == ["quelle heure est-il", "et demain ?"]
    assert h._relever_la_boite() is True and len(envoyes) == 2


def test_boite_aux_lettres_cassee(mod, env):
    """Une boite qui plante a l'ouverture ne fait pas tomber la fenetre ;
    relever sans boite rend True sans rien faire."""
    _outils(env, **{"boite-aux-lettres.py": "raise RuntimeError('casse')\n"})
    h = mod.Haichi()
    assert env.GLib.minuteries == []
    assert h._relever_la_boite() is True


# ---------------------------------------------------------------------------
# L'image manquante, le lancement en programme principal
# ---------------------------------------------------------------------------
def test_image_absente_est_fabriquee(mod, monkeypatch):
    """haichi.png absent : on le fabrique avant de l'afficher."""
    cible = os.path.join(REPO, "haichi.png")
    vrai = os.path.exists
    monkeypatch.setattr(os.path, "exists", lambda p: False if p == cible else vrai(p))
    fabrique = types.ModuleType("fabriquer_haichi_png")
    fabrique.fabriquer = mock.MagicMock()
    monkeypatch.setitem(sys.modules, "fabriquer_haichi_png", fabrique)
    mod.Haichi()
    fabrique.fabriquer.assert_called_once_with(cible)


def _lancer(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["haichi_avatar.py"] + list(args))
    return runpy.run_path(CHEMIN, run_name="__main__")


def test_principal_ecran_le_plus_a_droite(env, monkeypatch):
    """En programme : en bas a droite de l'ecran le plus a droite, une
    question de depart programmee a 900 ms, et la boucle GTK lancee."""
    zones = [types.SimpleNamespace(x=0, y=0, width=1920, height=1080),
             types.SimpleNamespace(x=1920, y=0, width=2560, height=1440)]
    affichage = mock.MagicMock()
    affichage.get_n_monitors.return_value = 2
    affichage.get_monitor.side_effect = lambda i: mock.MagicMock(
        get_workarea=mock.MagicMock(return_value=zones[i]))
    env.Gdk.Display = mock.MagicMock()
    env.Gdk.Display.get_default.return_value = affichage
    g = _lancer(monkeypatch, "qui", "est", "Victor")
    h = g["h"]
    h.move.assert_called_once_with(1920 + 2560 - 300 - 40, 1440 - 380 - 90)
    assert h.saisie.get_text() == "qui est Victor"
    assert [ms for ms, _ in env.GLib.minuteries] == [900]
    env.Gtk.main.assert_called_once()


def test_principal_sans_affichage(env, monkeypatch):
    """Sans affichage lisible : position de secours, et pas de question."""
    env.Gdk.Display = mock.MagicMock()
    env.Gdk.Display.get_default.side_effect = RuntimeError("pas d'ecran")
    g = _lancer(monkeypatch)
    g["h"].move.assert_called_once_with(1920 - 300 - 40, 1080 - 380 - 90)
    assert env.GLib.minuteries == []
    assert g["h"].saisie.get_text() == ""
