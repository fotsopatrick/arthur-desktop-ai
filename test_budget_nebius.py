# -*- coding: utf-8 -*-
"""LE PLAFOND NEBIUS (27/09/2026) — aucun appel au-dela d'un nombre de jetons par jour.

Patrick : « j'ai une dette de 205 ?? ils ne permettent meme pas de limiter les jetons » -> choix A :
notre propre plafond, dans le code. Un « jeton » = un morceau de mot que Nebius compte et facture.
Ce que ce banc exige (dans un bac a sable : un carnet de depenses jetable) :
  1. sous le plafond, l'appel est permis, et ce qu'il a coute est note ;
  2. au plafond, l'appel est REFUSE avant de partir, avec une phrase claire ;
  3. un nouveau jour repart a zero ;
  4. un carnet abime -> on refuse (on ne depense pas a l'aveugle) et on le dit ;
  5. un appel ne peut pas demander plus que le maximum par appel ;
  6. le vrai chemin : nemotron_nebius.demander ET chat refusent sans rien envoyer quand le plafond est atteint.
"""
import json, os, sys, tempfile
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
bac = tempfile.mkdtemp(prefix="budget-nebius-")
os.environ["BUDGET_NEBIUS_DOSSIER"] = bac
rouges = 0
def dire(ok, quoi):
    global rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    rouges += 0 if ok else 1

try:
    import budget_nebius as B
except Exception as e:
    print("  ROUGE  le module budget_nebius n'existe pas encore : " + str(e)[:60])
    print("\nBILAN PLAFOND NEBIUS : 1 rouge"); sys.exit(1)

reglages = {"jetons_par_jour": 1000, "jetons_max_par_appel": 300}
ok, raison, reste = B.autoriser(200, reglages=reglages, jour="2026-09-27")
dire(ok and reste == 1000, f"sous le plafond : permis (reste {reste})")
B.noter({"total_tokens": 700}, "nvidia/x", "essai", jour="2026-09-27")
ok, raison, reste = B.autoriser(200, reglages=reglages, jour="2026-09-27")
dire(ok and reste == 300, f"apres 700 jetons : reste {reste}")
B.noter({"total_tokens": 300}, "nvidia/x", "essai", jour="2026-09-27")
ok, raison, reste = B.autoriser(50, reglages=reglages, jour="2026-09-27")
dire(not ok and "plafond" in raison.lower(), f"au plafond : refuse (« {raison[:70]} »)")
ok, _, reste = B.autoriser(50, reglages=reglages, jour="2026-09-28")
dire(ok and reste == 1000, "un nouveau jour repart a zero")
dire(B.max_par_appel(5000, reglages) == 300, "un appel ne demande jamais plus que le maximum par appel")
open(os.path.join(bac, "2026-09-29.json"), "w").write("{abime")
ok, raison, _ = B.autoriser(10, reglages=reglages, jour="2026-09-29")
dire(not ok and "abim" in raison.lower(), "carnet abime -> refus dit en clair")

# le vrai chemin, sans reseau : le plafond du jour est deja atteint
import datetime, nemotron_nebius as N
aujourd = datetime.date.today().isoformat()
json.dump({"jetons": 10**9, "appels": 1}, open(os.path.join(bac, aujourd + ".json"), "w"))
parti = []
import urllib.request as U
vrai = U.urlopen
U.urlopen = lambda *a, **k: parti.append(1) or (_ for _ in ()).throw(RuntimeError("ne devait pas partir"))
d = N.demander("pourquoi le ciel est bleu ?", cle="cle-de-test")
c = N.chat([{"role": "user", "content": "bonjour"}])
U.urlopen = vrai
dire(not parti and d.get("reponse") is None and "plafond" in (d.get("panne") or "").lower(),
     "demander : refuse AVANT d'envoyer, et le dit")
dire(not parti and c.get("reponse") is None and "plafond" in (c.get("panne") or "").lower(),
     "chat (les agents du jeu) : refuse AVANT d'envoyer")
# un faux Nebius d'epreuve (adresse locale) ne doit rien ecrire dans le carnet
import subprocess
avant = sorted(os.listdir(bac))
json.dump({"jetons": 0}, open(os.path.join(bac, aujourd + ".json"), "w"))
for t in ("test_nemotron_retour.py", "test_etage_nemotron.py"):
    subprocess.run([sys.executable, os.path.join(ICI, t)], capture_output=True, env={**os.environ, "BUDGET_NEBIUS_DOSSIER": bac})
dire(json.load(open(os.path.join(bac, aujourd + ".json"))).get("jetons") == 0,
     "les bancs a faux Nebius n'ecrivent aucune fausse depense")

print(f"\nBILAN PLAFOND NEBIUS : {9 - rouges} verts, {rouges} rouges")
sys.exit(1 if rouges else 0)
