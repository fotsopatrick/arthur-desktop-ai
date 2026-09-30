#!/bin/bash
# Toutes les epreuves d'Arthur, d'un seul coup.
#
# Ne le 16/09/2026. Depuis le 30/09/2026, ce fichier passe la main au lanceur
# unique (qualite/lancer.py) : il lance AUSSI les series de tests/ (pytest),
# mesure la couverture, isole chaque serie dans un HOME jetable (plus aucun
# test ne touche au vrai ~/), et ecrit le tableau de bord
# qualite/rapport/index.html. Il sort en ERREUR des qu'une serie est rouge.
#
#   bash tous-les-tests.sh        (ou ./tester, qui ouvre aussi le tableau)
#
cd "$(dirname "$0")" || exit 1
exec python3 qualite/lancer.py "$@"
