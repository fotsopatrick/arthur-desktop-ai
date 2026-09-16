#!/usr/bin/env bash
# INSTALLER ARTHUR — une seule commande, et il vous dit ce qui marche.
#
# Il ne telecharge RIEN et ne contacte AUCUN serveur. Il verifie ce qui est
# deja la, lance les controles, et vous dit exactement ou vous en etes.
#
# Ne le 16/09/2026 : en comparant notre depot avec celui d'un projet du meme
# concours, il manquait ce fichier. Leur projet s'installait en une commande,
# le notre demandait de deviner. Ce fichier comble cet ecart.
set -u
VERT="\033[32m"; ROUGE="\033[31m"; GRIS="\033[90m"; GRAS="\033[1m"; FIN="\033[0m"
ICI="$(cd "$(dirname "$0")" && pwd)"
SOUCIS=0

titre() { printf "\n${GRAS}%s${FIN}\n" "$1"; }
ok()    { printf "  ${VERT}OK${FIN}     %s\n" "$1"; }
souci() { printf "  ${ROUGE}SOUCI${FIN}  %s\n" "$1"; SOUCIS=$((SOUCIS+1)); }
info()  { printf "  ${GRIS}%s${FIN}\n" "$1"; }

printf "${GRAS}\n  Arthur — installation\n${FIN}"
info "rien ne sera telecharge, aucun serveur ne sera contacte"

# ---------------------------------------------------------------- Python
titre "1. Python"
if command -v python3 >/dev/null 2>&1; then
  V=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null)
  MAJ=${V%%.*}; MIN=${V##*.}
  if [ "$MAJ" -ge 3 ] && [ "$MIN" -ge 8 ]; then
    ok "Python $V"
  else
    souci "Python $V est trop ancien — il en faut au moins 3.8"
  fi
else
  souci "Python n'est pas installe. Sur Debian ou Ubuntu : apt install python3"
fi

# ------------------------------------------------------------ les fichiers
titre "2. Les fichiers d'Arthur"
MANQUE=0
for f in nano_moteur_ultra.py haichi_outils.py haichi_greffons.py \
         registre_connaissances.json haichi_avatar.py haichi.png; do
  if [ -f "$ICI/$f" ]; then ok "$f"; else souci "$f manque"; MANQUE=1; fi
done

# --------------------------------------------------------------- sa memoire
titre "3. Sa memoire"
if [ -f "$ICI/registre_connaissances.json" ]; then
  N=$(python3 -c "
import json,sys
try:
    d=json.load(open('$ICI/registre_connaissances.json',encoding='utf-8'))
    print(len(d))
except Exception:
    print(0)
" 2>/dev/null)
  if [ "${N:-0}" -gt 100 ]; then ok "$N sujets appris"; else souci "sa memoire est vide ou illisible"; fi
fi

# --------------------------------------------------------- son interface
titre "4. Sa fenetre sur le bureau"
if python3 -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk" 2>/dev/null; then
  ok "la boite a fenetres est la — le compagnon pourra s'afficher"
else
  info "la boite a fenetres (GTK) manque : Arthur repondra quand meme, mais"
  info "sans son avatar sur le bureau. Sur Debian ou Ubuntu :"
  info "  apt install python3-gi gir1.2-gtk-3.0"
fi

# ----------------------------------------------------------- les controles
titre "5. Les controles"
if [ "$MANQUE" -eq 0 ]; then
  for t in test_haichi_repond_juste.py test_haichi_outils.py test_haichi_greffons.py; do
    if [ -f "$ICI/$t" ]; then
      if ( cd "$ICI" && timeout 300 python3 "$t" >/dev/null 2>&1 ); then
        ok "$t"
      else
        souci "$t ne passe pas au vert"
      fi
    fi
  done
else
  souci "des fichiers manquent : je ne lance pas les controles"
fi

# ------------------------------------------------------------ l'essai vrai
titre "6. L'essai : Arthur repond-il ?"
if [ "$MANQUE" -eq 0 ]; then
  R=$( cd "$ICI" && timeout 60 python3 -c "
import sys; sys.path.insert(0,'.')
import nano_moteur_ultra as m
print(m.nano_moteur_ultra('Qui est Victor ?')['answer'][:200])
" 2>&1 )
  if echo "$R" | grep -qi "victor"; then
    ok "il repond : $(echo "$R" | cut -c1-70)…"
  else
    souci "il ne repond pas comme prevu"
  fi
fi

# ------------------------------------------------------------------ bilan
printf "\n${GRAS}"
if [ "$SOUCIS" -eq 0 ]; then
  printf "  Tout est en place.${FIN}\n\n"
  printf "  Pour le lancer :\n"
  printf "    python3 haichi_avatar.py\n"
  printf "    python3 haichi_avatar.py \"qui est Victor\"\n\n"
  exit 0
else
  printf "  %d souci(s) — voir les lignes rouges ci-dessus.${FIN}\n\n" "$SOUCIS"
  exit 1
fi
