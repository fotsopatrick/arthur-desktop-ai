#!/usr/bin/env bash
# LE DEPOT EST-IL VRAIMENT INSTALLABLE PAR UN INCONNU ?
#
# Ne le 16/09/2026. J'avais repare la calculatrice d'Arthur, et je l'avais
# annonce. Puis j'ai clone le depot dans un dossier vide, comme un juge de
# hackathon le ferait — et « 17 fois 23 » redonnait un circuit sur les
# rappels. Mes reparations n'etaient pas ENREGISTREES.
#
# Ce controle ne regarde donc pas mon dossier de travail. Il clone, et il
# fait parler le programme cloné. C'est la seule facon de savoir ce qu'un
# inconnu recevra vraiment.
set -u
DEPOT="${1:-$HOME/haichi}"
BAC=$(mktemp -d)
trap 'rm -rf "$BAC"' EXIT
VERTS=0; ROUGES=0

dire() { printf "  %-5s %-42s %s\n" "$1" "$2" "$3"; }
juge() { if [ "$1" = "oui" ]; then VERTS=$((VERTS+1)); dire "OK" "$2" "$3";
         else ROUGES=$((ROUGES+1)); dire "RATE" "$2" "$3"; fi }

echo
echo "1) UN INCONNU CLONE LE DEPOT"
git clone --quiet "$DEPOT" "$BAC/arthur" 2>/dev/null
[ -d "$BAC/arthur" ] && juge oui "le clone reussit" "$(ls -1 "$BAC/arthur" | wc -l) fichiers" \
                     || juge non "le clone reussit" "echec"
cd "$BAC/arthur" 2>/dev/null || exit 1

echo
echo "2) CE QUE LE HACKATHON EXIGE"
[ -f LICENSE ] && juge oui "une licence est presente" "$(head -1 LICENSE)" \
               || juge non "une licence est presente" "ABSENTE"
grep -qi "MIT\|Apache\|BSD\|GPL" LICENSE 2>/dev/null \
  && juge oui "elle est reconnue par l'OSI" "$(head -1 LICENSE)" \
  || juge non "elle est reconnue par l'OSI" "inconnue"
[ -f README.md ] && juge oui "un mode d'emploi est present" "$(wc -l < README.md) lignes" \
                 || juge non "un mode d'emploi est present" "ABSENT"
grep -qi "nemotron" README.md 2>/dev/null \
  && juge oui "le mode d'emploi nomme Nemotron" "oui" \
  || juge non "le mode d'emploi nomme Nemotron" "non"
grep -qi "nebius" README.md 2>/dev/null \
  && juge oui "le mode d'emploi nomme Nebius" "oui" \
  || juge non "le mode d'emploi nomme Nebius" "non"

echo
echo "3) AUCUN SECRET N'EST PARTI AVEC"
n=$(ls -d .secrets cle-nebius.txt .env 2>/dev/null | wc -l)
[ "$n" = "0" ] && juge oui "le coffre a clefs est reste a la maison" "0 fichier" \
               || juge non "le coffre a clefs est reste a la maison" "$n fichier(s)"
f=$(grep -rlE "eyJ[A-Za-z0-9_-]{30,}|ghp_[A-Za-z0-9]{30,}|BEGIN (RSA |OPENSSH )?PRIVATE KEY" \
     --include="*.py" --include="*.js" --include="*.json" --include="*.md" . 2>/dev/null \
     | grep -v "^./test" | head -1)
[ -z "$f" ] && juge oui "aucun vrai secret dans les fichiers" "rien trouve" \
            || juge non "aucun vrai secret dans les fichiers" "$f"

echo
echo "4) IL DEMARRE ET IL REPOND JUSTE"
python3 - <<'PY'
import os, sys, time
sys.path.insert(0, os.getcwd())
try:
    import nano_moteur_ultra as NM
    m = NM.NanoMoteurUltraEngine()
except Exception as e:
    print("  RATE  il demarre                                  %s" % str(e)[:40]); sys.exit(9)

EPREUVES = [
 ("qui est Victor ?",        lambda r: "Victor" in str(r.get("answer","")),  "il connait l'equipe"),
 ("combien font 17 fois 23 ?", lambda r: "391" in str(r.get("answer","")),    "il CALCULE (391)"),
 ("explique en une phrase ce qu'est un transistor",
                             lambda r: "CIRCUIT" not in str(r.get("answer","")).upper(),
                                                                             "aucun circuit hors sujet"),
 ("c'est quoi la PrEP ?",    lambda r: r.get("source") == "aveu",            "il REFUSE la sante"),
 ("qui est en ligne ?",      lambda r: r.get("source") == "outil",           "il regarde la machine"),
]
rouges = 0
for q, verif, quoi in EPREUVES:
    t0 = time.perf_counter(); r = m.repondre(q); ms = (time.perf_counter()-t0)*1000
    ok = verif(r); rouges += (not ok)
    print("  %-5s %-42s %s, %.0f ms" % ("OK" if ok else "RATE", quoi, r.get("source"), ms))
sys.exit(rouges)
PY
r=$?
if [ "$r" -eq 0 ]; then VERTS=$((VERTS+5)); else ROUGES=$((ROUGES+r)); VERTS=$((VERTS+5-r)); fi

echo
echo "======================================================================"
echo "  $VERTS epreuves passees, $ROUGES ratees"
echo "======================================================================"
[ "$ROUGES" -eq 0 ] || exit 1
