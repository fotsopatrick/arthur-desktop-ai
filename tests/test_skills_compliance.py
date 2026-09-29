#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ANALYSE STATIQUE DE CONFORMITÉ DES SKILL.md — interdit les anti-patterns.

jimmy : écrit AVANT la mise à jour des trois modes d'emploi, vu au ROUGE,
puis les SKILL.md ont été corrigés jusqu'au VERT.

Vérifie, sur beelzebuth / jimmy / fixe-de-bug :
  1. LISTE NOIRE — aucune suggestion d'utiliser grep/sed/awk/cat/tail/ls, ni
     l'ordre de lire une sortie console pour analyser un résultat.
  2. LISTE BLANCHE — l'usage des 3 outils MCP (mcp_eveil, mcp_analyse_banc,
     mcp_refactor) est bien exigé.
  3. GESTION JSON — la vérification explicite de "error" / "success": false
     dans le retour MCP est bien enseignée à l'agent.
"""
import os
import re

import pytest

MAISON = os.path.expanduser("~")
SKILLS = os.path.join(MAISON, ".claude", "skills")

# (29/09) Ces SKILL.md vivent dans ~/.claude/skills, hors du depot : sur une
# autre machine, la serie est sautee (et le dit) au lieu d'echouer.
if not all(os.path.isfile(os.path.join(SKILLS, n, "SKILL.md"))
           for n in ("beelzebuth", "jimmy", "fixe-de-bug")):
    pytest.skip("SKILL.md de beelzebuth/jimmy/fixe-de-bug absents (~/.claude/skills, hors du depot)",
                allow_module_level=True)

CIBLES = {
    "beelzebuth": os.path.join(SKILLS, "beelzebuth", "SKILL.md"),
    "jimmy": os.path.join(SKILLS, "jimmy", "SKILL.md"),
    "fixe-de-bug": os.path.join(SKILLS, "fixe-de-bug", "SKILL.md"),
}

# LISTE NOIRE. On cherche l'ORDRE de s'en servir pour lire/analyser une
# sortie (un exemple de commande, ou "lance grep", "avec sed", etc.) — pas
# le simple mot au milieu d'une phrase de contexte. On accepte le mot dans
# une phrase qui dit explicitement de NE PAS l'utiliser.
INTERDITS = ["grep", "sed", "awk", "cat", "tail", "ls"]
ORDRE_INTERDIT = re.compile(
    r"(```[^`]*\b(grep|sed|awk|cat|tail|ls)\b[^`]*```"       # dans un bloc de code
    r"|\b(lance|lancer|utilise|utiliser|avec|via|passe par)\s+`?(grep|sed|awk|cat|tail|ls)\b"
    r"|\bscroll(?:er|e)?\s+(?:le|un|dans le)?\s*terminal\b"
    r"|\blire\s+la\s+sortie\s+(?:du\s+)?terminal\b)",
    re.I | re.S)
NEGATION = re.compile(
    r"(interdit|jamais|ne\s+plus|fini|remplace|remplacé|à la place de|"
    r"au lieu de|plus\s+de\s+scroll)", re.I)

# Les SKILL.md citent l'outil par son nom d'APPEL MCP (celui que le serveur
# stdio expose dans tools/list : eveil_systeme, analyse_banc, refactor),
# pas par le nom du fichier .py qui l'implémente derrière — c'est la bonne
# convention, déjà en place avant ce contrôle. On accepte les deux formes.
OUTILS_MCP = {
    "mcp_eveil": re.compile(r"mcp_eveil|eveil_systeme", re.I),
    "mcp_analyse_banc": re.compile(r"mcp_analyse_banc|analyse_banc", re.I),
    "mcp_refactor": re.compile(r"mcp_refactor|\brefactor\b", re.I),
}
GESTION_JSON = re.compile(
    r"(\"error\"|'error'|\berror\b.{0,20}\bJSON\b|"
    r"\"success\"\s*:\s*false|'success'\s*:\s*false|success.{0,10}false)",
    re.I)


def lire(cle):
    chemin = CIBLES[cle]
    assert os.path.isfile(chemin), "SKILL.md introuvable : %s" % chemin
    return open(chemin, encoding="utf-8").read()


@pytest.mark.parametrize("cle", list(CIBLES))
def test_le_fichier_existe(cle):
    assert os.path.isfile(CIBLES[cle]), "manquant : %s" % CIBLES[cle]


@pytest.mark.parametrize("cle", list(CIBLES))
def test_liste_noire_pas_de_bash_brut_suggere(cle):
    """Aucun ordre d'utiliser grep/sed/awk/cat/tail/ls pour lire un résultat,
    sauf s'il est cité pour dire explicitement de ne plus s'en servir."""
    texte = lire(cle)
    for m in ORDRE_INTERDIT.finditer(texte):
        fenetre = texte[max(0, m.start() - 80):m.end() + 80]
        assert NEGATION.search(fenetre), (
            "%s suggère encore un vieux réflexe bash sans dire qu'il est "
            "remplacé : %r" % (cle, m.group(0)[:60]))


@pytest.mark.parametrize("cle", list(CIBLES))
def test_liste_blanche_outils_mcp_exiges(cle):
    """Chaque SKILL.md exige explicitement les outils MCP qui le concernent."""
    texte = lire(cle)
    if cle == "beelzebuth":
        attendu = "mcp_eveil"
    elif cle in ("jimmy",):
        attendu = "mcp_analyse_banc"
    else:  # fixe-de-bug
        attendu = "mcp_refactor"
    assert OUTILS_MCP[attendu].search(texte), (
        "%s ne mentionne pas %s (ni son nom d'appel MCP) — l'outil n'est "
        "pas exigé" % (cle, attendu))


@pytest.mark.parametrize("cle", list(CIBLES))
def test_gestion_json_enseignee(cle):
    """Le SKILL.md apprend à vérifier "error" ou "success": false dans le
    retour d'un outil MCP, pas juste à l'appeler en aveugle."""
    texte = lire(cle)
    assert GESTION_JSON.search(texte), (
        "%s n'enseigne pas de vérifier error/success:false dans le retour "
        "JSON" % cle)


@pytest.mark.parametrize("cle", list(CIBLES))
def test_regle_de_repli_target_not_found_pour_fixe_de_bug(cle):
    """fixe-de-bug seul : la règle de repli sur target_not_found."""
    if cle != "fixe-de-bug":
        pytest.skip("règle propre à fixe-de-bug")
    texte = lire(cle).lower()
    assert "target_not_found" in texte, (
        "fixe-de-bug ne dit pas quoi faire quand mcp_refactor répond "
        "target_not_found")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", __file__]))
