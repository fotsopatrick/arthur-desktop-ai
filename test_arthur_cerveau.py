#!/usr/bin/env python3
"""CHANGER LE GROS CERVEAU D'ARTHUR EN UNE COMMANDE (24/09/2026).

Patrick : « pouvoir changer la couche où se trouve Qwen facilement, par
Claude, Antigravity, opencode ». Les trois savent lancer une commande ; ceux
qui parlent MCP ont aussi l'outil arthur_cerveau. On vérifie :
  1. « arthur_cerveau.py » seul dit le cerveau actuel et les choix possibles ;
  2. « arthur_cerveau.py qwen » change le réglage, sans toucher aux autres clés ;
  3. un nom inconnu est REFUSÉ (code 2) et le fichier ne bouge pas ;
  4. le serveur MCP d'Arthur expose arthur_cerveau, et il change bien le réglage.
Tout se passe sur une COPIE du réglage (ARTHUR_REGLAGES), jamais sur le vrai.
"""
import json, os, shutil, subprocess, sys, tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
rouges = 0; n = 0
def verdict(ok, texte):
    global rouges, n
    n += 1
    print(("  VERT  " if ok else "  ROUGE ") + texte)
    if not ok:
        rouges += 1

bac = tempfile.mkdtemp()
copie = os.path.join(bac, "reglages-maison.json")
json.dump({"alice_cerveau": "http://exemple:8081", "cerveau_gros": "nebius"}, open(copie, "w"))
env = dict(os.environ, ARTHUR_REGLAGES=copie)
outil = os.path.join(ICI, "arthur_cerveau.py")
lancer = lambda *a: subprocess.run([sys.executable, outil, *a], env=env, capture_output=True, text=True)

if not os.path.exists(outil):
    verdict(False, "arthur_cerveau.py existe")
else:
    r = lancer()
    verdict(r.returncode == 0 and "nebius" in r.stdout and "qwen" in r.stdout and "local" in r.stdout,
            "1. sans argument : le cerveau actuel et les choix possibles")
    r = lancer("qwen")
    d = json.load(open(copie))
    verdict(r.returncode == 0 and d.get("cerveau_gros") == "qwen", "2a. « qwen » : le réglage change")
    verdict(d.get("alice_cerveau") == "http://exemple:8081", "2b. les autres clés sont intactes")
    avant = open(copie).read()
    # par un lien (comme ~/bin/arthur-cerveau), SANS ARTHUR_REGLAGES : il doit lire le vrai
    # réglage à côté du vrai fichier, pas à côté du lien
    lien = os.path.join(bac, "arthur-cerveau"); os.symlink(outil, lien)
    env_sans = {k: v for k, v in os.environ.items() if k != "ARTHUR_REGLAGES"}
    vrai = json.load(open(os.path.join(ICI, "reglages-maison.json"))).get("cerveau_gros") if os.path.exists(os.path.join(ICI, "reglages-maison.json")) else "qwen"
    r = subprocess.run([sys.executable, lien], env=env_sans, capture_output=True, text=True)
    verdict(("couche 3) : %s " % vrai) in r.stdout, "2c. lancé par un lien, il lit le vrai réglage (%s)" % vrai)
    r = lancer("gpt5")
    verdict(r.returncode == 2 and open(copie).read() == avant, "3. un cerveau inconnu est refusé, le fichier ne bouge pas")

# 4. le serveur MCP
serveur = os.path.join(ICI, "mcp_arthur_server.py")
msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "arthur_cerveau", "arguments": {"cerveau": "local"}}}]
p = subprocess.run([sys.executable, serveur], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                   env=env, capture_output=True, text=True, timeout=30)
reponses = {}
for ligne in p.stdout.splitlines():
    try:
        d = json.loads(ligne); reponses[d.get("id")] = d
    except ValueError:
        pass
noms = [t.get("name") for t in ((reponses.get(2) or {}).get("result") or {}).get("tools", [])]
verdict("arthur_cerveau" in noms, "4a. le serveur MCP expose arthur_cerveau")
verdict(json.load(open(copie)).get("cerveau_gros") == "local", "4b. l'appel MCP change bien le réglage")

shutil.rmtree(bac)
print("BILAN CERVEAU : %d rouge(s) sur %d" % (rouges, n))
sys.exit(1 if rouges else 0)
