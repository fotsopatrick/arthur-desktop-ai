#!/bin/bash
# LA BOITE AUX REPONSES — Patrick doit pouvoir repondre DANS la page.
#
# Demande du 17/09/2026, mot pour mot : « corrige le garde fou qui affiche tes
# questions dans une page web pour qu'il me donne la possibilite de mettre mon
# choix directement dans la page et de valider » + « avec possibilite de
# commenter ».
#
# Une page qui ne fait qu'AFFICHER oblige a revenir taper la reponse ici.
# Une boite aux reponses la recoit et la range dans le carnet.
P=8851
reussi=0; rate=0
juge() { if [ "$1" = "1" ]; then echo "  OK    $2"; reussi=$((reussi+1));
         else echo "  RATE  $2"; rate=$((rate+1)); fi; }

echo "1) LA BOITE EST-ELLE DEBOUT ?"
c=$(curl -s -o /dev/null -w "%{http_code}" -m 5 http://127.0.0.1:$P/)
echo "      elle repond : ${c:-rien}"
[ "$c" = "200" ] && juge 1 "la boite repond" || juge 0 "la boite ne repond pas"

echo "2) LA PAGE MONTRE-T-ELLE UN BOUTON POUR VALIDER ?"
page=$(curl -s -m 5 http://127.0.0.1:$P/)
echo "$page" | grep -q "valider" && juge 1 "le bouton valider est la" \
                                 || juge 0 "aucun bouton valider"

echo "3) Y A-T-IL UNE CASE POUR COMMENTER ?"
echo "$page" | grep -q "textarea" && juge 1 "la case a commentaire est la" \
                                 || juge 0 "aucune case a commentaire"

echo "4) UNE REPONSE ENVOYEE ARRIVE-T-ELLE DANS LE CARNET ?"
q="epreuve du $(date +%s)"
r=$(curl -s -m 8 -X POST http://127.0.0.1:$P/repondre \
     -H "Content-Type: application/json" \
     -d "{\"question\":\"$q\",\"choix\":\"C\",\"commentaire\":\"range-le ailleurs\"}")
echo "      la boite dit : ${r:-rien}"
if python3 ~/outils/carnet-des-reponses.py --lire 2>/dev/null | grep -q "$q"; then
  juge 1 "la reponse est bien rangee dans le carnet"
else
  juge 0 "la reponse n est PAS arrivee dans le carnet"
fi

echo "5) L INTERRUPTEUR DU COCKPIT ETEINT-IL LA PAGE ?"
touch ~/.claude/portes/.page-des-demandes-eteinte
sortie=$(echo '[{"quoi":"essai","choix":["A oui — on essaie"]}]' \
         | python3 ~/outils/mes-demandes.py 2>&1)
rm -f ~/.claude/portes/.page-des-demandes-eteinte
echo "      il dit : $sortie"
echo "$sortie" | grep -qi "eteinte\|éteinte" \
  && juge 1 "eteinte, la page ne s ouvre pas" \
  || juge 0 "l interrupteur ne fait rien"

echo
echo "  $reussi passees, $rate ratees"
[ "$rate" -eq 0 ]
