#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fabrique l image de Haichi, sans aucune bibliotheque a installer.

La bibliotheque de dessin habituelle (cairo) n est pas sur cette machine :
le programme plantait en silence et Haichi n apparaissait pas (15/09/2026).
Ici on ecrit le fichier image nous-memes, point par point, avec ce que Python
a deja dans le ventre.
"""
import zlib, struct, math, os

TAILLE = 180          # image carree de 180 points de cote


def melanger(fond, dessus, force):
    """Pose une couleur par-dessus une autre, avec une force de 0 a 1."""
    return tuple(int(f + (d - f) * force) for f, d in zip(fond, dessus))


def fabriquer(chemin):
    c = TAILLE / 2
    rayon = TAILLE * 0.30          # le corps
    halo = TAILLE * 0.47           # la lueur autour

    lignes = []
    for y in range(TAILLE):
        ligne = bytearray([0])     # chaque ligne commence par un 0 (sans filtre)
        for x in range(TAILLE):
            dx, dy = x - c, y - c
            d = math.hypot(dx, dy)
            r = v = b = 0
            a = 0

            if d <= halo:          # la lueur bleue autour
                force = max(0.0, 1 - (d / halo)) ** 2
                r, v, b = 56, 189, 248
                a = int(120 * force)

            if d <= rayon:         # le corps
                # plus clair en haut a gauche, plus sombre en bas a droite
                lx, ly = (dx + rayon * 0.35) / rayon, (dy + rayon * 0.4) / rayon
                t = min(1.0, max(0.0, math.hypot(lx, ly)))
                haut = (166, 235, 255)
                milieu = (41, 158, 237)
                bas = (10, 71, 140)
                if t < 0.55:
                    couleur = melanger(haut, milieu, t / 0.55)
                else:
                    couleur = melanger(milieu, bas, (t - 0.55) / 0.45)
                bord = min(1.0, (rayon - d) / 2.0)     # bord doux
                r, v, b = couleur
                a = int(255 * bord) if bord < 1 else 255

            # les deux yeux, blancs, en forme d ovale
            for ox in (-rayon * 0.30, rayon * 0.30):
                ex = (dx - ox) / (rayon * 0.125)
                ey = (dy + rayon * 0.05) / (rayon * 0.215)
                de = math.hypot(ex, ey)
                if de <= 1.0:
                    bord = min(1.0, (1.0 - de) * 6)
                    r, v, b = melanger((r, v, b), (255, 255, 255), bord)
                    a = max(a, int(250 * bord))

            ligne += bytes((r, v, b, a))
        lignes.append(bytes(ligne))

    donnees = zlib.compress(b"".join(lignes), 9)

    def bloc(nom, contenu):
        x = nom + contenu
        return struct.pack(">I", len(contenu)) + x + struct.pack(">I", zlib.crc32(x))

    png = (b"\x89PNG\r\n\x1a\n"
           + bloc(b"IHDR", struct.pack(">IIBBBBB", TAILLE, TAILLE, 8, 6, 0, 0, 0))
           + bloc(b"IDAT", donnees)
           + bloc(b"IEND", b""))
    open(chemin, "wb").write(png)
    return chemin


if __name__ == "__main__":
    ici = os.path.dirname(os.path.abspath(__file__))
    p = fabriquer(os.path.join(ici, "haichi.png"))
    print("image fabriquee :", p, os.path.getsize(p), "octets")
