#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'IMAGE DE HAICHI (30/09/2026) — fabriquer_haichi_png.py.

Ce qu'on prouve, sans aucune bibliotheque d'image (on relit le PNG a la
main, comme il a ete ecrit) :
  - le fichier est un vrai PNG : signature, blocs, sommes de controle ;
  - 180 x 180 points, RGBA 8 bits, chaque ligne sans filtre ;
  - le fond est vide (transparent), la lueur est bleue et douce, le corps
    est opaque, les deux yeux sont blancs et symetriques ;
  - le lancement en programme ecrit haichi.png A COTE du fichier (ici dans
    un dossier de bac a sable, jamais dans le depot).
"""
import os
import runpy
import struct
import sys
import zlib

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHEMIN = os.path.join(REPO, "fabriquer_haichi_png.py")
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import fabriquer_haichi_png as fab  # noqa: E402


def _blocs(octets):
    assert octets[:8] == b"\x89PNG\r\n\x1a\n"
    i, blocs = 8, []
    while i < len(octets):
        (n,) = struct.unpack(">I", octets[i:i + 4])
        nom, contenu = octets[i + 4:i + 8], octets[i + 8:i + 8 + n]
        (crc,) = struct.unpack(">I", octets[i + 8 + n:i + 12 + n])
        assert crc == zlib.crc32(nom + contenu), nom
        blocs.append((nom, contenu))
        i += 12 + n
    return blocs


@pytest.fixture(scope="module")
def image(tmp_path_factory):
    chemin = str(tmp_path_factory.mktemp("png") / "haichi.png")
    rendu = fab.fabriquer(chemin)
    octets = open(chemin, "rb").read()
    blocs = _blocs(octets)
    brut = zlib.decompress(b"".join(c for n, c in blocs if n == b"IDAT"))
    t = fab.TAILLE
    lignes = [brut[y * (1 + 4 * t):(y + 1) * (1 + 4 * t)] for y in range(t)]

    def point(x, y):
        return tuple(lignes[y][1 + 4 * x:1 + 4 * x + 4])

    return {"chemin": chemin, "rendu": rendu, "blocs": blocs, "brut": brut,
            "lignes": lignes, "point": point}


def test_melanger():
    """Force 0 : le fond ; force 1 : le dessus ; entre les deux, au prorata."""
    assert fab.melanger((0, 0, 0), (200, 100, 50), 0) == (0, 0, 0)
    assert fab.melanger((0, 0, 0), (200, 100, 50), 1) == (200, 100, 50)
    assert fab.melanger((10, 20, 30), (110, 120, 130), 0.5) == (60, 70, 80)


def test_png_valide(image):
    """Signature, IHDR 180x180 RGBA 8 bits, un IDAT, un IEND vide, CRC justes."""
    assert image["rendu"] == image["chemin"]
    noms = [n for n, _ in image["blocs"]]
    assert noms == [b"IHDR", b"IDAT", b"IEND"]
    ihdr = image["blocs"][0][1]
    assert struct.unpack(">IIBBBBB", ihdr) == (180, 180, 8, 6, 0, 0, 0)
    assert image["blocs"][2][1] == b""


def test_lignes_sans_filtre(image):
    """Chaque ligne : un octet de filtre a 0 puis 180 points de 4 octets."""
    assert len(image["brut"]) == 180 * (1 + 180 * 4)
    assert all(l[0] == 0 for l in image["lignes"])


def test_fond_transparent(image):
    """Les coins sont hors de la lueur : entierement vides."""
    p = image["point"]
    for x, y in [(0, 0), (179, 0), (0, 179), (179, 179)]:
        assert p(x, y) == (0, 0, 0, 0)


def test_lueur_bleue_douce(image):
    """Entre le corps et le bord : bleu ciel, a moitie transparent, qui
    s'eteint en s'eloignant."""
    p = image["point"]
    pres, loin = p(90 + 60, 90), p(90 + 70, 90)
    assert pres[:3] == (56, 189, 248) and loin[:3] == (56, 189, 248)
    assert 0 < loin[3] < pres[3] < 120


def test_corps_opaque_eclaire_en_haut_a_gauche(image):
    """Le corps est opaque ; le haut gauche est plus clair que le bas droit."""
    p = image["point"]
    assert p(90, 110)[3] == 255
    clair, sombre = p(75, 72), p(125, 125)
    assert clair[3] == 255 and sombre[3] == 255
    assert sum(clair[:3]) > sum(sombre[:3])


def test_bord_du_corps_doux(image):
    """Au bord exact du corps, l'alpha n'est ni vide ni plein."""
    p = image["point"]
    # rayon = 54 : le point (90, 90+53) est a 53 du centre, dans le bord doux
    a = p(90, 143)[3]
    assert 0 < a < 255


def test_deux_yeux_blancs_symetriques(image):
    """Les yeux, a +-16 points du centre, un peu au-dessus : blancs et opaques,
    et l'image est symetrique gauche-droite a leur hauteur."""
    p = image["point"]
    rayon = fab.TAILLE * 0.30
    y = int(round(90 - rayon * 0.05))
    gauche, droite = p(int(90 - rayon * 0.30), y), p(int(round(90 + rayon * 0.30)), y)
    assert gauche == (255, 255, 255, 255)
    assert droite == (255, 255, 255, 255)
    assert p(90, y) != (255, 255, 255, 255)     # entre les yeux : le corps


def test_programme_principal_ecrit_a_cote(tmp_path, monkeypatch, capsys):
    """Lance en programme, il ecrit haichi.png dans SON dossier et le dit.
    (On lui fait croire que son dossier est un bac a sable.)"""
    vrai = os.path.abspath
    faux = str(tmp_path / "fabriquer_haichi_png.py")
    def abspath(p):
        # seul le code du module est trompe ; runpy, lui, lit le vrai fichier
        if p == CHEMIN and sys._getframe(1).f_code.co_filename == CHEMIN:
            return faux
        return vrai(p)

    monkeypatch.setattr(os.path, "abspath", abspath)
    runpy.run_path(CHEMIN, run_name="__main__")
    cible = tmp_path / "haichi.png"
    assert cible.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    sortie = capsys.readouterr().out
    assert sortie.strip() == "image fabriquee : %s %d octets" % (cible, cible.stat().st_size)
