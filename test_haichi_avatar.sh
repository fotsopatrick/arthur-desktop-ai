#!/bin/bash
# Verifie le vrai compagnon de bureau : fond transparent, Haichi net.
export DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000
rouges=0
dire(){ if [ "$1" = ok ]; then echo "  VERT   $2"; else echo "  ROUGE  $2"; rouges=$((rouges+1)); fi; }

ligne=$(wmctrl -l -G -x 2>/dev/null | grep -i "haichi.avatar" | head -1)
if [ -z "$ligne" ]; then
  dire non "le compagnon Haichi n est pas lance"
  echo; echo "BILAN AVATAR : 1 rouge — il n existe pas encore"; exit 1
fi
dire ok "le compagnon Haichi est lance"
id=$(echo "$ligne" | awk '{print $1}'); x=$(echo "$ligne" | awk '{print $3}')

xprop -id "$id" _NET_FRAME_EXTENTS 2>/dev/null | grep -q "0, 0, 0, 0" \
  && dire ok "il n a aucune bordure" || dire non "il a encore une bordure"

xprop -id "$id" _NET_WM_STATE 2>/dev/null | grep -q "_NET_WM_STATE_ABOVE" \
  && dire ok "il reste au-dessus des autres fenetres" || dire non "il passe derriere"

[ "$x" -ge 1900 ] 2>/dev/null \
  && dire ok "il est sur l ecran de droite (x=$x)" || dire non "mauvais ecran (x=$x)"

# la fenetre doit avoir 32 bits de couleur : c est la preuve de la transparence
prof=$(xwininfo -id "$id" 2>/dev/null | grep -i "Depth" | awk '{print $2}')
[ "$prof" = "32" ] \
  && dire ok "son fond est vraiment transparent (32 bits de couleur)" \
  || dire non "son fond n est pas transparent (profondeur $prof, il faut 32)"

code=$(curl -s -o /dev/null -m 6 -w "%{http_code}" http://127.0.0.1:8790/api/nano-search -X POST -H 'Content-Type: application/json' -d '{"prompt":"test"}')
[ "$code" = "200" ] && dire ok "il peut parler au cockpit (code $code)" || dire non "le cockpit ne repond pas ($code)"

echo; echo "BILAN AVATAR : $rouges rouge(s) sur 6"
[ "$rouges" -eq 0 ] || exit 1
