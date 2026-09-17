#!/bin/bash
# Toutes les epreuves d'Arthur, d'un seul coup.
#
# Ne le 16/09/2026. Il y avait dix-sept series d'epreuves dans ce dossier et
# AUCUNE facon de les lancer ensemble. On corrigeait un coin, on cassait
# l'autre, et personne ne le voyait : huit epreuves etaient rouges depuis
# des jours sans que ca se sache.
#
# Une epreuve qu'on ne lance pas ne garde rien. Celui-ci se lance en entier,
# compte, et sort en ERREUR des qu'une seule est rouge.
#
#   bash ~/haichi/tous-les-tests.sh
#
cd "$(dirname "$0")" || exit 1

verts=0 rouges=0 sautes=0
liste_rouges=""

for f in test_*.py; do
    sortie=$(timeout 200 python3 "$f" 2>&1 | grep -v "dbind-WARNING\|qt.qpa")

    # Certaines epreuves ont besoin d'une chose exterieure (un navigateur
    # ouvert, une machine allumee). On le DIT, on ne fait pas semblant.
    if echo "$sortie" | grep -qi "9222/json/version\|navigateur.*pas ouvert"; then
        printf "  ~ %-44s a besoin d'un navigateur ouvert\n" "$f"
        sautes=$((sautes + 1)); continue
    fi

    # Trois facons d'ecrire un bilan existent dans ce dossier. Le 16/09/2026,
    # ce lanceur ne connaissait que deux, et il a annonce ROUGE pour deux
    # series qui disaient « 2 vert, 0 rouge ». Un detecteur qui ne connait
    # pas toutes les formes crie au feu : c'est la meme faute qu'on vient de
    # reparer ailleurs. On les reconnait donc toutes les trois.
    bilan=$(echo "$sortie" | grep -oE "[0-9]+ rouge\(s\)|[0-9]+ ratees|[0-9]+ rouge\b" | tail -1)
    nombre=$(echo "$bilan" | grep -oE "^[0-9]+")

    if [ -z "$nombre" ]; then
        printf "  ? %-44s pas de bilan lisible\n" "$f"
        rouges=$((rouges + 1)); liste_rouges="$liste_rouges $f"
    elif [ "$nombre" -eq 0 ]; then
        combien=$(echo "$sortie" | grep -oE "[0-9]+ epreuves passees|rouge\(s\) sur [0-9]+|[0-9]+ vert\b" | tail -1 | grep -oE "[0-9]+")
        printf "  · %-44s %s epreuves au vert\n" "$f" "${combien:-?}"
        verts=$((verts + 1))
    else
        printf "  ✗ %-44s %s\n" "$f" "$bilan"
        rouges=$((rouges + 1)); liste_rouges="$liste_rouges $f"
    fi
done

echo
echo "════════════════════════════════════════════════════════════════════"
if [ "$rouges" -eq 0 ]; then
    echo "  $verts series au vert, $sautes sautee(s) faute d'outil exterieur."
    exit 0
fi
echo "  $verts au vert, $rouges ROUGE(S) :$liste_rouges"
echo "════════════════════════════════════════════════════════════════════"
exit 1
