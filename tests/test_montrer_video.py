#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MES VIDEOS — outils/montrer-la-video.py.

Ce qu'on prouve, sans ffmpeg, sans navigateur, sans le vrai HOME (faux
ffprobe / ffmpeg qui repondent sur commande, dossiers dans tmp_path) :
  - la duree vient de ffprobe, 0 quand il se tait ou manque ;
  - la vignette est fabriquee une fois, puis reprise tant que la video n'a
    pas change ;
  - un dossier = une liste ; les dossiers caches et les non-videos sont ignores ;
  - la page porte le lecteur, les listes, la video mise en avant, echappees ;
  - main pose la marque « vue », ouvre (ou pas) la page, dit VIDEOS MONTREES.
"""
import importlib.util
import json
import os
import sys
import types

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHIER = os.path.join(REPO, "outils", "montrer-la-video.py")


class _FauxSubprocess:
    """ffprobe rend self.duree ; ffmpeg ecrit l'image demandee ; Popen note."""
    DEVNULL = -3

    def __init__(self):
        self.duree = "125.7\n"
        self.ffmpeg_marche = True
        self.appels = []
        self.lances = []
        self.panne_popen = None

    def run(self, cmd, **kw):
        self.appels.append(cmd)
        if cmd[0] == "ffprobe":
            if self.duree is None:
                raise FileNotFoundError("ffprobe")
            return types.SimpleNamespace(stdout=self.duree, returncode=0)
        if cmd[0] == "ffmpeg" and self.ffmpeg_marche:
            with open(cmd[-1], "wb") as f:
                f.write(b"jpeg")
        return types.SimpleNamespace(stdout="", returncode=0)

    def Popen(self, cmd, **kw):
        if self.panne_popen and cmd[0] == "xdg-open":
            raise self.panne_popen
        self.lances.append(cmd)


@pytest.fixture
def mv(tmp_path, monkeypatch):
    """Le module charge avec un HOME jetable ; DOSSIER, VIGNETTES, PAGE, MARQUE dans tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    spec = importlib.util.spec_from_file_location("montrer_la_video", FICHIER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    dossier = tmp_path / "livrables" / "videos"
    dossier.mkdir(parents=True)
    monkeypatch.setattr(mod, "MAISON", str(tmp_path))
    monkeypatch.setattr(mod, "DOSSIER", str(dossier))
    monkeypatch.setattr(mod, "VIGNETTES", str(dossier / ".vignettes"))
    monkeypatch.setattr(mod, "PAGE", str(tmp_path / "livrables" / "mes-videos.html"))
    monkeypatch.setattr(mod, "MARQUE", str(tmp_path / "portes" / ".videos-montrees"))
    faux = _FauxSubprocess()
    monkeypatch.setattr(mod, "subprocess", faux)
    mod._faux = faux
    return mod


def _video(mod, relatif, taille=10, quand=None):
    chemin = os.path.join(mod.DOSSIER, relatif)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "wb") as f:
        f.write(b"v" * taille)
    if quand is not None:
        os.utime(chemin, (quand, quand))
    return chemin


# ---------------------------------------------------------------- petits outils

def test_joli_et_mmss(mv):
    """Un nom de fichier devient un titre ; les secondes deviennent m:ss."""
    assert mv.joli("ma-belle_video.mp4") == "ma belle video"
    assert mv.joli("clip.webm") == "clip"
    assert mv.mmss(0) == "0:00"
    assert mv.mmss(125) == "2:05"
    assert mv.mmss(3600) == "60:00"


def test_duree(mv):
    """ffprobe dit 125.7 -> 125 ; vide -> 0 ; absent ou illisible -> 0."""
    assert mv.duree("x.mp4") == 125
    assert mv._faux.appels[0][0] == "ffprobe" and mv._faux.appels[0][-1] == "x.mp4"
    mv._faux.duree = ""
    assert mv.duree("x.mp4") == 0
    mv._faux.duree = "N/A"
    assert mv.duree("x.mp4") == 0
    mv._faux.duree = None
    assert mv.duree("x.mp4") == 0


def test_vignette_fabriquee_puis_reprise(mv):
    """Premiere fois : ffmpeg au cinquieme de la duree. Ensuite : reprise telle quelle."""
    chemin = _video(mv, "a.mp4", quand=1_000_000)
    assert mv.vignette(chemin, "a") == "a.jpg"
    ffmpeg = [c for c in mv._faux.appels if c[0] == "ffmpeg"]
    assert len(ffmpeg) == 1
    assert ffmpeg[0][ffmpeg[0].index("-ss") + 1] == "25"       # 125 // 5
    assert os.path.exists(os.path.join(mv.VIGNETTES, "a.jpg"))
    mv._faux.appels.clear()
    assert mv.vignette(chemin, "a") == "a.jpg"
    assert mv._faux.appels == []


def test_vignette_refaite_si_video_plus_recente(mv):
    """La video a change apres la vignette : on refait l'image."""
    chemin = _video(mv, "a.mp4", quand=1_000_000)
    mv.vignette(chemin, "a")
    os.utime(chemin, (2_000_000_000, 2_000_000_000))
    mv._faux.appels.clear()
    mv.vignette(chemin, "a")
    assert any(c[0] == "ffmpeg" for c in mv._faux.appels)


def test_vignette_courte_et_ffmpeg_en_panne(mv):
    """Video tres courte : -ss 1 au minimum. ffmpeg n'ecrit rien : nom vide."""
    mv._faux.duree = "3"
    mv._faux.ffmpeg_marche = False
    chemin = _video(mv, "b.mp4")
    assert mv.vignette(chemin, "b") == ""
    ffmpeg = [c for c in mv._faux.appels if c[0] == "ffmpeg"][0]
    assert ffmpeg[ffmpeg.index("-ss") + 1] == "1"


# ---------------------------------------------------------------- ramasser

def test_ramasser_par_dossier(mv):
    """Racine = « Les videos finies » ; un sous-dossier = une liste ;
    dossiers caches et autres fichiers ignores ; .webm et .MP4 pris."""
    _video(mv, "finale.mp4", taille=2 * 1048576 + 5)
    _video(mv, "Voyage/jour-1.MP4")
    _video(mv, "Voyage/jour_2.webm")
    _video(mv, "notes.txt")
    _video(mv, ".cache/cachee.mp4")
    listes = mv.ramasser()
    assert set(listes) == {"Les videos finies", "Voyage"}
    finale = listes["Les videos finies"][0]
    assert finale["titre"] == "finale" and finale["chemin"] == "finale.mp4"
    assert finale["cle"] == "finale" and finale["duree"] == 125
    assert finale["poids"] == 2 * 1048576 + 5
    assert finale["vignette"] == "finale.jpg"
    assert len(finale["quand"]) == 10
    v = listes["Voyage"]
    assert [x["chemin"] for x in v] == ["Voyage/jour-1.MP4", "Voyage/jour_2.webm"]
    assert v[0]["cle"] == "Voyage__jour-1"


def test_ramasser_dossier_vide_ou_absent(mv, tmp_path, monkeypatch):
    """Aucune video : aucune liste."""
    assert mv.ramasser() == {}
    monkeypatch.setattr(mv, "DOSSIER", str(tmp_path / "nulle-part"))
    assert mv.ramasser() == {}


# ---------------------------------------------------------------- ecrire

def _v(chemin, quand="01/09/2026", duree=65, poids=3 * 1048576, titre=None):
    return {"titre": titre or mv_joli(chemin), "chemin": chemin, "cle": chemin,
            "duree": duree, "poids": poids, "quand": quand,
            "vignette": os.path.basename(chemin) + ".jpg"}


def mv_joli(chemin):
    return os.path.basename(chemin).rsplit(".", 1)[0]


def test_ecrire_rien_a_montrer(mv):
    """Pas de video : pas de page, None."""
    assert mv.ecrire({}) is None
    assert mv.ecrire({"vide": []}) is None
    assert not os.path.exists(mv.PAGE)


def test_ecrire_page_complete(mv):
    """La page : compte, listes (« videos finies » en tete), lecteur, titres echappes."""
    listes = {
        "Zeta": [_v("Zeta/z.mp4", titre="<b>z</b>")],
        "Les videos finies": [_v("a.mp4", quand="02/09/2026"), _v("b.mp4", duree=10)],
    }
    choisie = mv.ecrire(listes)
    page = open(mv.PAGE, encoding="utf-8").read()
    assert choisie["chemin"] == "a.mp4"
    assert "3 videos, 2 listes" in page
    assert 'src="/videos/a.mp4"' in page and 'poster="/vignettes/a.mp4.jpg"' in page
    assert page.index("Les videos finies") < page.index("Zeta")
    assert "2 videos &middot; 1:15" in page          # 65 + 10 secondes
    assert "&lt;b&gt;z&lt;/b&gt;" in page and "<b>z</b>" not in page
    assert page.count('class="item joue"') == 1
    assert "1:05 &middot; 02/09/2026 &middot; 3 Mo" in page
    assert 'data-sous="1:05 - 02/09/2026 - 3 Mo"' in page
    for gabarit in ("__COMBIEN__", "__SRC__", "__LISTES_HTML__", "__TITRE__"):
        assert gabarit not in page


def test_ecrire_video_mise_en_avant(mv):
    """La video demandee (par son nom, chemin complet ou non) passe en tete."""
    listes = {"G": [_v("G/un.mp4", quand="09/09/2026"), _v("G/deux.mp4")]}
    assert mv.ecrire(listes, "/ailleurs/deux.mp4")["chemin"] == "G/deux.mp4"
    assert 'src="/videos/G/deux.mp4"' in open(mv.PAGE, encoding="utf-8").read()
    # nom inconnu : on retombe sur la plus recente
    assert mv.ecrire(listes, "inconnue.mp4")["chemin"] == "G/un.mp4"


@pytest.mark.xfail(strict=True, reason="bug: montrer-la-video.py:164 max() compare "
                   "'quand' au format jj/mm/aaaa comme du texte : le 30/01 passe "
                   "devant le 01/09 (et une annee plus ancienne peut gagner)")
def test_ecrire_la_plus_recente_par_defaut(mv):
    """Sans video demandee, la plus RECENTE est jouee."""
    listes = {"G": [_v("G/janvier.mp4", quand="30/01/2026"),
                    _v("G/septembre.mp4", quand="01/09/2026")]}
    assert mv.ecrire(listes)["chemin"] == "G/septembre.mp4"


@pytest.mark.xfail(strict=True, reason="bug: montrer-la-video.py:192-193 __SRC__ et "
                   "__POSTER__ sont inseres sans html.escape : un guillemet dans un nom "
                   "de fichier casse l'attribut (injection d'attribut)")
def test_ecrire_lecteur_echappe(mv):
    """Un nom de fichier avec guillemet ne doit pas sortir de l'attribut src."""
    listes = {"G": [_v('G/a" onerror="alert(1).mp4')]}
    mv.ecrire(listes)
    assert 'onerror="alert(1)' not in open(mv.PAGE, encoding="utf-8").read()


# ---------------------------------------------------------------- reveil

def test_reveil_boite(mv, monkeypatch):
    """Port 8851 muet : on lance la boite ; port qui repond : rien."""
    etat = {"ecoute": False}

    class S:
        def __init__(self, *a):
            pass

        def settimeout(self, t):
            pass

        def connect(self, a):
            assert a == ("127.0.0.1", 8851)
            if not etat["ecoute"]:
                raise ConnectionRefusedError

        def close(self):
            pass
    monkeypatch.setattr("socket.socket", S)
    monkeypatch.setattr(mv.time, "sleep", lambda s: None)
    mv.reveiller_la_boite()
    assert mv._faux.lances[0][0] == "python3"
    assert mv._faux.lances[0][1].endswith("boite-aux-reponses.py")
    etat["ecoute"] = True
    mv.reveiller_la_boite()
    assert len(mv._faux.lances) == 1


@pytest.mark.xfail(strict=True, reason="bug: montrer-la-video.py:211 lance "
                   "~/outils/boite-aux-reponses.py (absent d'un clone neuf) au lieu "
                   "de la boite livree a cote ; mes-demandes.py a deja ete corrige (29/09)")
def test_reveil_boite_livree_a_cote(mv, monkeypatch):
    """La boite lancee est celle du depot, a cote de ce fichier."""
    class S:
        def __init__(self, *a):
            pass

        def settimeout(self, t):
            pass

        def connect(self, a):
            raise ConnectionRefusedError

        def close(self):
            pass
    monkeypatch.setattr("socket.socket", S)
    monkeypatch.setattr(mv.time, "sleep", lambda s: None)
    mv.reveiller_la_boite()
    assert mv._faux.lances[0][1] == os.path.join(REPO, "outils", "boite-aux-reponses.py")


# ---------------------------------------------------------------- main

@pytest.fixture
def principal(mv, monkeypatch):
    """main avec un reveil note, sans socket."""
    mv._reveils = []
    monkeypatch.setattr(mv, "reveiller_la_boite", lambda: mv._reveils.append(1))
    return mv


def _main(mv, monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "argv", ["montrer-la-video.py", *args])
    code = mv.main()
    return code, capsys.readouterr().out


def test_main_aucune_video(principal, monkeypatch, capsys):
    """Dossier vide : 1, et on le dit ; pas de marque."""
    code, out = _main(principal, monkeypatch, capsys)
    assert code == 1 and "aucune video a montrer" in out
    assert not os.path.exists(principal.MARQUE)


def test_main_montre_et_marque(principal, monkeypatch, capsys):
    """Videos presentes : page ecrite, marque posee, navigateur ouvert."""
    _video(principal, "a.mp4")
    _video(principal, "G/b.mp4")
    code, out = _main(principal, monkeypatch, capsys, "b.mp4")
    assert code == 0
    assert "VIDEOS MONTREES (2 videos, 2 listes)" in out
    assert set(json.load(open(principal.MARQUE))) == {"a.mp4", "G/b.mp4"}
    assert principal._reveils == [1]
    assert principal._faux.lances == [["xdg-open", principal.ADRESSE]]
    assert 'src="/videos/G/b.mp4"' in open(principal.PAGE, encoding="utf-8").read()


def test_main_garde_les_anciennes_marques(principal, monkeypatch, capsys):
    """Une marque existante est completee, pas ecrasee ; --sans-ouvrir n'ouvre pas."""
    os.makedirs(os.path.dirname(principal.MARQUE))
    with open(principal.MARQUE, "w") as f:
        json.dump({"ancienne.mp4": 1.0}, f)
    _video(principal, "a.mp4")
    code, _ = _main(principal, monkeypatch, capsys, "--sans-ouvrir")
    assert code == 0
    vues = json.load(open(principal.MARQUE))
    assert vues["ancienne.mp4"] == 1.0 and "a.mp4" in vues
    assert principal._faux.lances == []


def test_main_navigateur_absent(principal, monkeypatch, capsys):
    """xdg-open manque : on le dit, et on dit quand meme VIDEOS MONTREES."""
    principal._faux.panne_popen = FileNotFoundError("xdg-open")
    _video(principal, "a.mp4")
    code, out = _main(principal, monkeypatch, capsys)
    assert code == 0
    assert "page ecrite, mais pas ouverte" in out and "VIDEOS MONTREES" in out
