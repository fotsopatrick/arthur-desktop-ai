#!/usr/bin/env python3
"""Épreuve du jeton du cockpit (24/09/2026).

Le 23/09, le cockpit s'est mis à exiger X-Cockpit-Token sur ses POST ; Arthur
ne l'envoyait pas et répondait 401 à tout. On vérifie :
  1. le jeton se lit depuis l'environnement, puis depuis un fichier .env ;
  2. sans jeton nulle part, aucun en-tête vide n'est envoyé ;
  3. le cockpit en marche ACCEPTE la question d'Arthur (pas de 401) ;
  4. aucune requête d'Arthur vers le cockpit n'est écrite sans le jeton.
"""
import glob, json, os, re, sys, tempfile, urllib.error, urllib.request

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

sauve = {k: os.environ.pop(k, None) for k in ("COCKPIT_TOKEN", "COCKPIT_ENV")}
try:
    os.environ["COCKPIT_TOKEN"] = "jeton-de-l-environnement"
    verdict(jeton_cockpit.jeton() == "jeton-de-l-environnement", "1a. le jeton vient de l'environnement")
    del os.environ["COCKPIT_TOKEN"]
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
        f.write('AUTRE=1\nCOCKPIT_TOKEN="jeton-du-fichier"\n')
    os.environ["COCKPIT_ENV"] = f.name
    verdict(jeton_cockpit.jeton() == "jeton-du-fichier", "1b. à défaut, il vient du fichier .env")
    os.environ["COCKPIT_ENV"] = f.name + ".absent"
    verdict("X-Cockpit-Token" not in jeton_cockpit.entetes(), "2. sans jeton nulle part, aucun en-tête vide")
    os.unlink(f.name)
finally:
    for k, v in sauve.items():
        os.environ.pop(k, None)
        if v is not None:
            os.environ[k] = v

# 3. le vrai cockpit, s'il tourne
try:
    r = urllib.request.Request("http://127.0.0.1:8790/api/nano-search",
                               data=json.dumps({"prompt": "Combien de sujets connais-tu ?"}).encode(),
                               headers=jeton_cockpit.entetes())
    code = urllib.request.urlopen(r, timeout=120).status
except urllib.error.HTTPError as e:
    code = e.code
except Exception:
    code = None
if code is None:
    print("  ~     3. cockpit éteint : épreuve en ligne sautée")
else:
    verdict(code == 200, "3. le cockpit accepte la question d'Arthur (code %s)" % code)

# 4. plus aucune requête POST vers le cockpit sans le jeton
fautifs = []
for chemin in glob.glob(os.path.join(ICI, "*.py")):
    # nemotron_nebius.py appelle Nebius (son ADRESSE est Token Factory), pas le cockpit
    if ".avant" in chemin or os.path.basename(chemin) in ("jeton_cockpit.py", "test_jeton_cockpit.py", "nemotron_nebius.py"):
        continue
    t = open(chemin, encoding="utf-8").read()
    for m in re.finditer(r"urllib\.request\.Request\((?:[^()]|\([^()]*\))*\)", t):
        bloc = m.group(0)
        if ("8790" in bloc or "ADRESSE" in bloc or "COCKPIT" in bloc) and "data=" in bloc and "jeton_cockpit" not in bloc:
            fautifs.append(os.path.basename(chemin))
verdict(not fautifs, "4. toute requête POST vers le cockpit porte le jeton" + (" — manquant : " + ", ".join(sorted(set(fautifs))) if fautifs else ""))

print("BILAN JETON : %d rouge(s) sur %d" % (rouges, n))
sys.exit(1 if rouges else 0)
