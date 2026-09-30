#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MES DEMANDES — outils/mes-demandes.py.

Ce qu'on prouve, sans navigateur, sans le vrai port 8851, sans le vrai HOME :
  - une carte montre la demande, echappee (pas d'HTML injecte) ;
  - les choix portent une lettre, « — » ou « - » separe le choix de sa suite,
    « (definitif) » rend la carte rouge ;
  - la page est ecrite, et ouverte UNE fois par liste (la marque) ;
  - l'interrupteur eteint l'ouverture, pas l'ecriture ;
  - la boite est reveillee seulement si elle dort ;
  - main lit l'entree standard ou --fichier, et respecte --sans-ouvrir.
"""
import importlib.util
import io
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHIER = os.path.join(REPO, "outils", "mes-demandes.py")


class _FauxSubprocess:
    DEVNULL = -3

    def __init__(self):
        self.lances = []
        self.panne = None

    def Popen(self, cmd, **kw):
        if self.panne:
            raise self.panne
        self.lances.append((cmd, kw))


@pytest.fixture
def demandes(tmp_path, monkeypatch):
    """Le module charge avec un HOME jetable ; PAGE, MARQUE, ETEINTE dans tmp_path ;
    Popen et sleep remplaces, le reveil de la boite note sans rien lancer."""
    monkeypatch.setenv("HOME", str(tmp_path))
    spec = importlib.util.spec_from_file_location("mes_demandes", FICHIER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "PAGE", str(tmp_path / "livrables" / "mes-demandes.html"))
    monkeypatch.setattr(mod, "MARQUE", str(tmp_path / "portes" / ".demandes-vues"))
    monkeypatch.setattr(mod, "ETEINTE", str(tmp_path / "portes" / ".eteinte"))
    faux = _FauxSubprocess()
    monkeypatch.setattr(mod, "subprocess", faux)
    mod._faux = faux
    mod._reveils = []
    monkeypatch.setattr(mod, "reveiller_la_boite", lambda: mod._reveils.append(1))
    return mod


def _page(mod):
    return open(mod.PAGE, encoding="utf-8").read()


# ---------------------------------------------------------------- carte

def test_carte_minimale_et_echappee(demandes):
    """Une demande sans rien d'autre : sa question, echappee ; pas de choix."""
    c = demandes.carte({"quoi": "<script>x</script> & co"})
    assert c.startswith('<div class="carte">') and c.endswith("</div>")
    assert "&lt;script&gt;x&lt;/script&gt; &amp; co" in c
    assert "<script>" not in c
    assert "choix" not in c and "valider" not in c
    assert '<p class="quoi">?</p>' in demandes.carte({})


def test_carte_toutes_les_lignes(demandes):
    """sujet, pourquoi, qui, apres : chacun sa ligne, avec son etiquette."""
    c = demandes.carte({"quoi": "Q", "sujet": "S", "pourquoi": "P", "qui": "W", "apres": "A"})
    assert '<p class="sujet">S</p>' in c
    assert "Pourquoi toi</span>P" in c
    assert "Ce que tu fais</span>W" in c
    assert "Et ensuite</span>A" in c


def test_carte_choix_lettres_et_separateurs(demandes):
    """A, B, C... ; « — » puis « - » separent ; sans suite, « pas d explication »."""
    c = demandes.carte({"quoi": "Q", "choix": [
        "Oui — on y va", "Non - on attend", "Peut-etre"]})
    assert c.count('class="ch"') == 3
    assert 'data-lettre="A"' in c and 'data-lettre="C"' in c
    assert '<p class="quoichoix">Oui</p><p class="suitechoix">on y va</p>' in c
    assert '<p class="quoichoix">Non</p><p class="suitechoix">on attend</p>' in c
    assert '<p class="quoichoix">Peut-etre</p><p class="suitechoix">(pas d explication)</p>' in c
    assert 'class="mot"' in c and "Valider ma reponse" in c


@pytest.mark.parametrize("fin", ["(definitif)", "(définitif)", "(DEFINITIF)"])
def test_carte_choix_definitif_rouge(demandes, fin):
    """« (definitif) » en fin de choix : carte rouge et etiquette DEFINITIF, mot retire."""
    c = demandes.carte({"quoi": "Q", "choix": ["Effacer — plus de retour " + fin, "Garder"]})
    assert 'class="ch rouge" data-lettre="A"' in c
    assert '<span class="definitif">DEFINITIF</span>' in c
    assert "plus de retour</p>" in c
    assert 'class="ch" data-lettre="B"' in c


# ---------------------------------------------------------------- montrer

def test_montrer_ecrit_et_ouvre_une_fois(demandes, capsys):
    """Premiere fois : page ecrite, boite reveillee, navigateur ouvert.
    Meme liste ensuite : on ne rouvre pas."""
    liste = [{"quoi": "Poser la porte ?", "choix": ["Oui", "Non"]}]
    demandes.montrer(liste)
    page = _page(demandes)
    assert "Poser la porte ?" in page
    assert "__CARTES__" not in page and "__QUAND__" not in page
    assert demandes._reveils == [1]
    assert demandes._faux.lances[0][0] == ["xdg-open", "http://127.0.0.1:8851/"]
    assert "PAGE MONTREE (1 demande(s))" in capsys.readouterr().out
    assert len(open(demandes.MARQUE).read().strip()) == 64

    demandes.montrer(liste)
    assert "PAGE INCHANGEE (1 demande(s))" in capsys.readouterr().out
    assert len(demandes._faux.lances) == 1

    demandes.montrer(liste + [{"quoi": "Autre"}])
    assert len(demandes._faux.lances) == 2


def test_montrer_liste_vide(demandes, capsys):
    """Rien a demander : la page le dit, et on n'ouvre rien."""
    demandes.montrer([])
    assert "Rien ne t'attend" in _page(demandes)
    assert demandes._faux.lances == [] and demandes._reveils == []
    assert "PAGE MONTREE (0 demande(s))" in capsys.readouterr().out


def test_montrer_sans_ouvrir(demandes, capsys):
    """ouvrir=False : ecrite, marquee, rien d'ouvert."""
    demandes.montrer([{"quoi": "Q"}], ouvrir=False)
    assert demandes._faux.lances == []
    assert os.path.exists(demandes.MARQUE)
    assert "PAGE MONTREE" in capsys.readouterr().out


def test_montrer_interrupteur_eteint(demandes, capsys):
    """Le fichier ETEINTE existe : la page est ecrite quand meme, pas ouverte."""
    os.makedirs(os.path.dirname(demandes.ETEINTE))
    open(demandes.ETEINTE, "w").close()
    demandes.montrer([{"quoi": "Q"}])
    assert "Q" in _page(demandes)
    assert demandes._faux.lances == [] and demandes._reveils == []
    assert "PAGE ETEINTE" in capsys.readouterr().out


def test_montrer_ouverture_en_panne(demandes, capsys):
    """xdg-open absent : on le dit, et la page reste ecrite."""
    demandes._faux.panne = FileNotFoundError("xdg-open")
    demandes.montrer([{"quoi": "Q"}])
    out = capsys.readouterr().out
    assert "je n'ai pas pu l'ouvrir" in out and "xdg-open" in out
    assert "PAGE MONTREE" in out


# ---------------------------------------------------------------- reveil

class _FauxSocket:
    ecoute = False
    connexions = []

    def __init__(self, *a):
        self.ferme = False

    def settimeout(self, t):
        pass

    def connect(self, adresse):
        _FauxSocket.connexions.append(adresse)
        if not _FauxSocket.ecoute:
            raise ConnectionRefusedError

    def close(self):
        self.ferme = True


@pytest.fixture
def reveil(tmp_path, monkeypatch):
    """Le vrai reveiller_la_boite, avec un faux socket et un faux Popen."""
    monkeypatch.setenv("HOME", str(tmp_path))
    spec = importlib.util.spec_from_file_location("mes_demandes_r", FICHIER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    faux = _FauxSubprocess()
    monkeypatch.setattr(mod, "subprocess", faux)
    monkeypatch.setattr("socket.socket", _FauxSocket)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    _FauxSocket.connexions = []
    return mod, faux


def test_reveil_boite_deja_debout(reveil):
    """Le port 8851 repond : on ne lance rien."""
    mod, faux = reveil
    _FauxSocket.ecoute = True
    mod.reveiller_la_boite()
    assert _FauxSocket.connexions == [("127.0.0.1", 8851)]
    assert faux.lances == []


def test_reveil_boite_endormie(reveil):
    """Le port se tait : on lance la boite livree A COTE de ce fichier."""
    mod, faux = reveil
    _FauxSocket.ecoute = False
    mod.reveiller_la_boite()
    cmd, kw = faux.lances[0]
    assert cmd == ["python3", os.path.join(REPO, "outils", "boite-aux-reponses.py")]
    assert kw["start_new_session"] is True


# ---------------------------------------------------------------- main

def test_main_entree_standard(demandes, monkeypatch, capsys):
    """Liste JSON sur l'entree standard, --sans-ouvrir respecte."""
    monkeypatch.setattr(sys, "argv", ["mes-demandes.py", "--sans-ouvrir"])
    monkeypatch.setattr(sys, "stdin", io.StringIO('[{"quoi": "Depuis stdin"}]'))
    demandes.main()
    assert "Depuis stdin" in _page(demandes)
    assert demandes._faux.lances == []
    assert "PAGE MONTREE (1 demande(s))" in capsys.readouterr().out


def test_main_entree_vide(demandes, monkeypatch, capsys):
    """Entree standard vide : liste vide."""
    monkeypatch.setattr(sys, "argv", ["mes-demandes.py"])
    monkeypatch.setattr(sys, "stdin", io.StringIO("  \n"))
    demandes.main()
    assert "Rien ne t'attend" in _page(demandes)


def test_main_fichier(demandes, monkeypatch, capsys, tmp_path):
    """--fichier liste.json : lue, montree et ouverte."""
    f = tmp_path / "liste.json"
    f.write_text(json.dumps([{"quoi": "Depuis fichier"}]), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["mes-demandes.py", "--fichier", str(f)])
    demandes.main()
    assert "Depuis fichier" in _page(demandes)
    assert len(demandes._faux.lances) == 1
