#!/bin/bash
# UNE VIDEO SE MONTRE, ELLE NE SE NOMME PAS.
#
# Demande du 17/09/2026 : « fait un garde fou qui t'oblige a me montrer la
# video dans une page web ».
#
# Ne d'une faute reelle du meme jour : j'ai fabrique une video de 158
# secondes, et je lui ai donne son NOM. Il ne l'a jamais vue. Un nom de
# fichier ne se regarde pas.
P=8851
reussi=0; rate=0
juge() { if [ "$1" = "1" ]; then echo "  OK    $2"; reussi=$((reussi+1));
         else echo "  RATE  $2"; rate=$((rate+1)); fi; }

echo "1) L OUTIL QUI MONTRE UNE VIDEO EXISTE-T-IL ?"
[ -x ~/outils/montrer-la-video.py ] && juge 1 "l outil est la" \
                                    || juge 0 "aucun outil pour montrer une video"

echo "2) FABRIQUE-T-IL UNE PAGE QUI JOUE VRAIMENT LA VIDEO ?"
v=$(ls -t ~/livrables/videos/*.mp4 2>/dev/null | head -1)
if [ -z "$v" ]; then juge 0 "aucune video a montrer"; else
  python3 ~/outils/montrer-la-video.py "$v" --sans-ouvrir >/dev/null 2>&1
  page=$(curl -s -m 5 "http://127.0.0.1:$P/video")
  echo "$page" | grep -q "<video" && juge 1 "la page contient un lecteur video" \
                                  || juge 0 "la page ne joue rien"
fi

echo "3) LA VIDEO ELLE-MEME EST-ELLE SERVIE ?"
n=$(basename "$v")
c=$(curl -s -o /dev/null -w "%{http_code}" -m 15 "http://127.0.0.1:$P/videos/$n")
echo "      elle repond : ${c:-rien}"
[ "$c" = "200" ] && juge 1 "la video se telecharge" || juge 0 "la video ne se sert pas"

echo "4) LE GARDE REFUSE-T-IL UNE VIDEO NON MONTREE ?"
rm -f ~/.claude/portes/.videos-montrees
s=$(echo '{}' | python3 ~/.claude/portes/garde-video-montree.py 2>&1; echo "code=$?")
echo "      il dit : $(echo "$s" | tail -2 | head -1 | cut -c1-70)"
echo "$s" | grep -q "code=2" && juge 1 "il refuse quand la video n a pas ete montree" \
                            || juge 0 "il ne refuse pas"

echo "5) LAISSE-T-IL PASSER UNE FOIS MONTREE ?"
python3 ~/outils/montrer-la-video.py "$v" --sans-ouvrir >/dev/null 2>&1
s=$(echo '{}' | python3 ~/.claude/portes/garde-video-montree.py 2>&1; echo "code=$?")
echo "$s" | grep -q "code=0" && juge 1 "il laisse passer une fois montree" \
                            || juge 0 "il refuse meme apres avoir montre"

echo
echo "  $reussi passees, $rate ratees"
[ "$rate" -eq 0 ]
