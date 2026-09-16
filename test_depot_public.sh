#!/usr/bin/env bash
# CE QUE LE JURY DU CONCOURS VA REGARDER.
#
# Leur reglement exige : un depot public, un schema de l'architecture, un mode
# d'emploi, et des instructions pour le lancer. Ce banc verifie que tout y est
# AVANT de publier — pas apres.
set -u
ROUGES=0
dire(){ if [ "$1" = ok ]; then echo "  VERT   $2"; else echo "  ROUGE  $2"; ROUGES=$((ROUGES+1)); fi; }
D="$(cd "$(dirname "$0")" && pwd)"

echo "  --- les papiers exiges ---"
[ -f "$D/README.md" ]    && dire ok "le mode d'emploi"      || dire non "README.md manque"
[ -f "$D/LICENSE" ]      && dire ok "la licence"            || dire non "LICENSE manque"
[ -f "$D/SECURITE.md" ]  && dire ok "les regles de securite"|| dire non "SECURITE.md manque"
[ -f "$D/ARCHITECTURE.md" ] && dire ok "le schema de l'architecture" || dire non "ARCHITECTURE.md manque — le jury le demande"

echo "  --- le mode d'emploi dit-il ce qu'ils cherchent ? ---"
if [ -f "$D/README.md" ]; then
  R="$D/README.md"
  grep -qi "nemotron"  "$R" && dire ok "il nomme le modele NVIDIA"        || dire non "il ne nomme pas Nemotron — c'est EXIGE"
  grep -qi "nebius"    "$R" && dire ok "il nomme Nebius"                  || dire non "il ne nomme pas Nebius — c'est EXIGE"
  grep -qi "install"   "$R" && dire ok "il dit comment l'installer"       || dire non "il ne dit pas comment l'installer"
  grep -qiE "offline|no network" "$R" && dire ok "il dit qu'il marche sans reseau" || dire non "il ne dit pas qu'il marche sans reseau"
fi

echo "  --- le schema montre-t-il les quatre etages ? ---"
if [ -f "$D/ARCHITECTURE.md" ]; then
  A="$D/ARCHITECTURE.md"
  n=0
  for m in tool rule document nemotron; do grep -qi "$m" "$A" && n=$((n+1)); done
  dire $([ "$n" -ge 4 ] && echo ok || echo non) "les quatre etages sont decrits ($n sur 4)"
  grep -qiE "admit|i don't know|dont know" "$A" && dire ok "l'aveu est explique" || dire non "l'aveu n'est pas explique"
fi

echo "  --- aucun secret ne part dans le depot public ---"
if git -C "$D" ls-files >/dev/null 2>&1; then
  SALES=$(git -C "$D" ls-files | while read -r f; do
    grep -lE "sk-[A-Za-z0-9]{20}|ghp_[A-Za-z0-9]{20}|eyJ[A-Za-z0-9_-]{30}" "$D/$f" 2>/dev/null
  done | grep -vE "/(test|.*[_-]test)[^/]*$" | head -3)
  [ -z "$SALES" ] && dire ok "aucun secret dans les fichiers suivis" || dire non "SECRET TROUVE : $(echo "$SALES" | head -1)"
  grep -qE "cle-nebius|NEBIUS_API_KEY" "$D/.gitignore" 2>/dev/null && dire ok "la cle Nebius est explicitement exclue" || dire non "la cle Nebius n'est pas exclue du depot"
fi

echo
echo "BILAN DEPOT PUBLIC : $ROUGES rouge(s) sur 12"
[ "$ROUGES" -eq 0 ] || exit 1
