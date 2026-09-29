#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fabrique l'image de Gamma, l'OURS bleu nuit, sans aucune bibliothèque.

POURQUOI ÉCRIT COMME ÇA. Comme Arthur (sphère bleu ciel) et Braignak (sphère
de bronze), Gamma est DESSINÉ par le code, point par point, parce que la
bibliothèque de dessin habituelle (cairo) n'existe pas sur cette machine.

SON LOOK, ET POURQUOI. Patrick a choisi « Bleu nuit » dans la page de choix
(gamma-ours). Gamma est un OURS bleu nuit : une sphère bleue avec deux
oreilles rondes, deux yeux, un museau clair et un nez. Le halo cyan autour est
un clin d'œil à Arthur ; la couleur bleu nuit le rend distinct des deux autres
tout en restant dans l'esprit de la maison.
"""
import math
import os
import struct
import zlib

TAILLE = 180          # image carrée de 180 points de côté, comme Arthur et Braignak


def melanger(fond, dessus, force):
    """Pose une couleur par-dessus une autre, avec une force de 0 à 1."""
    force = min(1.0, max(0.0, force))
    return tuple(int(f + (d - f) * force) for f, d in zip(fond, dessus))


def fabriquer(chemin):
    c = TAILLE / 2
    rayon = TAILLE * 0.30          # le corps (la sphère)
    halo = TAILLE * 0.47           # la lueur autour

    lignes = []
    for y in range(TAILLE):
        ligne = bytearray([0])     # chaque ligne commence par un 0 (sans filtre)
        for x in range(TAILLE):
            dx, dy = x - c, y - c
            d = math.hypot(dx, dy)
            r = v = b = 0
            a = 0

            # ── la lueur cyan autour (clin d'œil à Arthur) ──
            if d <= halo:
                force = max(0.0, 1 - (d / halo)) ** 2
                r, v, b = 63, 208, 224
                a = int(140 * force)

            # ── les deux oreilles rondes en haut ──
            for ox in (-rayon * 0.38, rayon * 0.38):
                ex = (dx - ox) / (rayon * 0.30)     # largeur de l'oreille
                ey = (dy + rayon * 0.78) / (rayon * 0.24)
                de = math.hypot(ex, ey)
                if de <= 1.0 and dy < -rayon * 0.2:
                    bord = min(1.0, (1.0 - de) * 3)
                    ore = melanger((31, 98, 138), (63, 138, 192), 0.5)
                    r, v, b = melanger((r, v, b), ore, 0.92 * bord)
                    a = max(a, int(255 * bord))
                # intérieur d'oreille plus clair
                di = math.hypot((dx - ox) / (rayon * 0.15),
                                (dy + rayon * 0.80) / (rayon * 0.13))
                if di <= 1.0 and dy < -rayon * 0.2:
                    bord = min(1.0, (1.0 - di) * 3)
                    r, v, b = melanger((r, v, b), (95, 160, 200), 0.8 * bord)
                    a = max(a, int(255 * bord))

            # ── le corps : une sphère bleu nuit ──
            if d <= rayon:
                lx = (dx + rayon * 0.35) / rayon
                ly = (dy + rayon * 0.40) / rayon
                t = min(1.0, max(0.0, math.hypot(lx, ly)))
                haut = (96, 190, 235)       # reflet bleu clair en haut à gauche
                milieu = (28, 90, 138)      # le bleu nuit
                bas = (8, 32, 56)           # l'ombre, en bas à droite
                if t < 0.55:
                    couleur = melanger(haut, milieu, t / 0.55)
                else:
                    couleur = melanger(milieu, bas, (t - 0.55) / 0.45)
                bord = min(1.0, (rayon - d) / 2.0)     # bord doux
                r, v, b = couleur
                a = int(255 * bord) if bord < 1 else 255

            # ── les deux yeux ronds, blancs avec pupille bleu foncé ──
            for ox in (-rayon * 0.26, rayon * 0.26):
                ex = (dx - ox) / (rayon * 0.12)
                ey = (dy + rayon * 0.05) / (rayon * 0.16)
                de = math.hypot(ex, ey)
                if de <= 1.0 and d <= rayon:
                    bord = min(1.0, (1.0 - de) * 6)
                    r, v, b = melanger((r, v, b), (236, 248, 255), bord)
                    a = max(a, int(255 * bord))
                # pupille bleu nuit au centre de l'œil
                dp = math.hypot((dx - ox) / (rayon * 0.055),
                                (dy + rayon * 0.06) / (rayon * 0.065))
                if dp <= 1.0 and d <= rayon:
                    bord = min(1.0, (1.0 - dp) * 4)
                    r, v, b = melanger((r, v, b), (10, 36, 64), bord)
                    a = max(a, int(255 * bord))
                # éclat blanc en haut à gauche de l'œil
                dg = math.hypot((dx - ox + rayon * 0.05) / (rayon * 0.030),
                                (dy + rayon * 0.02) / (rayon * 0.030))
                if dg <= 1.0 and d <= rayon:
                    bord = min(1.0, (1.0 - dg) * 3)
                    r, v, b = melanger((r, v, b), (255, 255, 255), 0.9 * bord)
                    a = max(a, int(255 * bord))

            # ── le museau clair et le nez bleu foncé, en bas ──
            # museau : ovale clair
            if d <= rayon:
                mx = dx / (rayon * 0.32)
                my = (dy - rayon * 0.46) / (rayon * 0.20)
                dm = math.hypot(mx, my)
                if dm <= 1.0:
                    bord = min(1.0, (1.0 - dm) * 4)
                    r, v, b = melanger((r, v, b), (207, 232, 248), 0.7 * bord)
                    a = max(a, int(255 * bord))
            # nez
            nez = math.hypot(dx / (rayon * 0.10),
                             (dy - rayon * 0.47) / (rayon * 0.07))
            if nez <= 1.0 and d <= rayon:
                bord = min(1.0, (1.0 - nez) * 4)
                r, v, b = melanger((r, v, b), (10, 36, 64), bord)
                a = max(a, int(255 * bord))
            # bouche : petit trait courbe sous le nez
            if d <= rayon:
                bx = dx / (rayon * 0.16)
                by = (dy - rayon * 0.52) / (rayon * 0.025)
                courbe = abs(bx * bx - 0.25)
                if abs(by - courbe) < 0.6 and abs(bx) < 0.5:
                    r, v, b = melanger((r, v, b), (20, 50, 80), 0.7)
                    a = max(a, 255)

            # le reflet du haut de la sphère : ça la rend ronde
            dr = math.hypot((dx + rayon * 0.34) / (rayon * 0.30),
                            (dy + rayon * 0.52) / (rayon * 0.17))
            if dr <= 1.0 and d <= rayon:
                bord = max(0.0, 1.0 - dr) ** 1.6
                r, v, b = melanger((r, v, b), (150, 220, 250), 0.5 * bord)

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

    dossier = os.path.dirname(os.path.abspath(chemin))
    if dossier and not os.path.isdir(dossier):
        os.makedirs(dossier, exist_ok=True)
    with open(chemin, "wb") as f:
        f.write(png)
    return chemin


if __name__ == "__main__":
    import sys
    ou = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "gamma.png")
    fabriquer(ou)
    print("dessine : %s (%d octets)" % (ou, os.path.getsize(ou)))