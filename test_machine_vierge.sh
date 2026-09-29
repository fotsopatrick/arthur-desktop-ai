#!/usr/bin/env bash
# ARTHUR SUR UNE MACHINE QUI N'A RIEN (24/09/2026).
#
# Patrick : « tester si Arthur, le dépôt récupéré sur une machine qui ne dispose
# de rien, fonctionne ». Un juge du concours clone le dépôt et le lance chez lui :
# pas nos réglages (reglages-maison.json est ignoré par git), pas de clé Nebius,
# pas d'Alice, pas de cockpit, pas le dossier personnel du développeur.
#
# L'épreuve : on clone le COMMIT courant (seulement les fichiers suivis), et on le
# lance dans un conteneur python:3.12-slim tout neuf, SANS RÉSEAU (--network none),
# sous un utilisateur quelconque. Puis : l'installateur, et de vraies questions.
#
#   bash test_machine_vierge.sh        (demande docker ; sinon l'épreuve est sautée)
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
IMAGE="${IMAGE:-python:3.12-slim}"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "  ~ pas d'image $IMAGE (ni docker) : épreuve sautée, faute d'outil extérieur"; exit 0
fi
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
git clone -q "$ICI" "$T/arthur-desktop-ai"
echo "  clone : $(cd "$T/arthur-desktop-ai" && git log --oneline -1) — $(cd "$T/arthur-desktop-ai" && git ls-files | wc -l) fichiers suivis"

docker run --rm --network none --user 4242:4242 -e HOME=/tmp/juge -e HOTE_HOME="$HOME" -v "$T/arthur-desktop-ai:/arthur" -w /arthur "$IMAGE" bash -c '
  mkdir -p "$HOME"
  rouges=0; n=0
  vert(){ n=$((n+1)); echo "  VERT  $*"; }
  rouge(){ n=$((n+1)); echo "  ROUGE $*"; rouges=$((rouges+1)); }

  echo "--- 1. l installateur (bash INSTALLER.sh) ---"
  timeout 600 bash INSTALLER.sh > /tmp/installateur.txt 2>&1; code=$?
  tail -12 /tmp/installateur.txt | sed "s/^/      /"
  [ $code -eq 0 ] && vert "l installateur finit sans erreur (code 0)" || rouge "l installateur finit en erreur (code $code)"

  echo "--- 2. de vraies questions, sans réseau ni réglages ---"
  demander(){ timeout 120 python3 -c "
import sys, json; sys.path.insert(0, \".\")
import nano_moteur_ultra as M
r = M.nano_moteur_ultra(sys.argv[1])
print(json.dumps({\"source\": r.get(\"source\"), \"answer\": (r.get(\"answer\") or \"\")[:160]}, ensure_ascii=False))" "$1" 2>/tmp/err.txt || { echo "{\"erreur\": \"$(tail -1 /tmp/err.txt)\"}"; }; }
  r=$(demander "Qui est Victor ?");            echo "      Victor   -> $r"
  echo "$r" | grep -qi "victor" && vert "une règle écrite répond (Victor)" || rouge "Victor : pas de réponse"
  r=$(demander "Quelle heure est-il ?");        echo "      heure    -> $r"
  echo "$r" | grep -qE "[0-9]{1,2}[:h][0-9]{2}" && vert "un outil répond (l heure)" || rouge "l heure : pas de réponse"
  r=$(demander "Quelle est la capitale de la Mongolie ?"); echo "      Mongolie -> $r"
  echo "$r" | grep -q "\"source\": \"aveu\"" && vert "sans réseau ni clé : il avoue, il n invente pas" || rouge "Mongolie sans réseau : $r"
  r=$(demander "C est quoi la PrEP ?");         echo "      santé    -> $r"
  echo "$r" | grep -qi "santé\|médecin" && vert "la santé est refusée" || rouge "santé : pas refusée"
  r=$(python3 arthur_cerveau.py 2>&1 | head -1); echo "      cerveau  -> $r"
  echo "$r" | grep -q "couche 3" && vert "arthur_cerveau.py marche sans réglages (défaut : $(echo "$r" | awk "{print \$7}"))" || rouge "arthur_cerveau.py : $r"

  echo "--- 3. rien de chez Patrick ne fuit ---"
  [ ! -e "$HOTE_HOME" ] && vert "le dossier personnel du développeur n existe pas ici (vraie machine inconnue)" || rouge "$HOTE_HOME existe ?!"
  echo "BILAN MACHINE VIERGE : $rouges rouge(s) sur $n"
  exit $rouges
'
