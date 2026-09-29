#!/usr/bin/env python3
"""LA PAGE D'ARTHUR RÉPOND-ELLE VRAIMENT ? (24/09/2026)

Mesuré le 24/09 : la bulle de la page envoyait chaque question à
/api/arthur-action. Cette route ne répond à rien : elle écrit un livrable
vide (« Livrable généré par Arthur… ») et rend {ok, message}. La page
affichait alors « Action exécutée par Arthur ! » — à TOUTES les questions.
567 fichiers arthur_resultat_*.txt vides s'étaient accumulés dans ~/livrables.

On vérifie :
  1. envoyer() interroge le moteur à étages (/api/nano-search), pas l'action ;
  2. la page montre l'étage qui a répondu et le temps mis (source, latence) ;
  3. elle n'a plus de réponse de remplissage (« Action exécutée par Arthur ! ») ;
  4. en vrai, le cockpit rend une vraie réponse à « Qui est Victor ? ».
"""
import json, os, re, sys, urllib.error, urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import jeton_cockpit

rouges = 0; n = 0
def verdict(ok, texte):
    global rouges, n
    n += 1
    print(("  VERT  " if ok else "  ROUGE ") + texte)
    if not ok:
        rouges += 1

page = open(os.path.join(ICI, "haichi_flottant.html"), encoding="utf-8").read()
corps = re.search(r"async function envoyer\(\)\s*\{(.*?)\n  \}\n", page, re.S)
envoyer = corps.group(1) if corps else ""
verdict(bool(envoyer), "la fonction envoyer() est trouvée")
verdict("/api/nano-search" in envoyer and "/api/arthur-action" not in envoyer,
        "1. envoyer() interroge le moteur à étages (/api/nano-search), pas /api/arthur-action")
verdict("source" in envoyer and "latency_ms" in envoyer, "2. la bulle montre l'étage qui a répondu et le temps mis")
verdict("Action exécutée par Arthur" not in page, "3. plus de réponse de remplissage")

try:
    r = urllib.request.Request("http://127.0.0.1:8790/api/nano-search",
                               data=json.dumps({"prompt": "Qui est Victor ?"}).encode(), headers=jeton_cockpit.entetes())
    d = json.loads(urllib.request.urlopen(r, timeout=120).read().decode())
    verdict("victor" in (d.get("answer") or "").lower(), "4. le cockpit répond vraiment (%s, %s ms)" % (d.get("source"), d.get("latency_ms")))
except (urllib.error.URLError, OSError):
    print("  ~     4. cockpit éteint : épreuve en ligne sautée")

print("BILAN PAGE : %d rouge(s) sur %d" % (rouges, n))
sys.exit(1 if rouges else 0)
