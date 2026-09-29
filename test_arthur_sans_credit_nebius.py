# -*- coding: utf-8 -*-
"""ARTHUR MARCHE SANS CREDIT NEBIUS (27/09/2026).

Patrick : « credit nebius fini, il doit toujours marcher — teste qu'il marche bien sans credit ».
Vrai chemin : le cockpit (8790) -> le moteur d'Arthur. Contrat :
  1. des questions de culture generale recoivent la BONNE reponse ;
  2. si Nemotron n'a pas repondu, Arthur le DIT dans sa raison et passe a Qwen (Alice) ;
     si les credits reviennent, la source « nemotron » est acceptee aussi ;
  3. un outil de la maison (la veille) ne depend jamais de Nebius ;
  4. chaque reponse arrive en moins de 15 secondes.
"""
import json, re, sys, time, urllib.request
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import jeton_cockpit

rouges = 0
def dire(ok, quoi):
    global rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    rouges += 0 if ok else 1

def demander(q):
    t = time.time()
    req = urllib.request.Request("http://127.0.0.1:8790/api/nano-search", data=json.dumps({"prompt": q}).encode(),
                                 headers=jeton_cockpit.entetes())
    r = json.load(urllib.request.urlopen(req, timeout=60))
    raw = r.get("raw_output", "") or ""
    th = re.search(r"<think>(.*?)</think>", raw, re.S)
    an = re.search(r"<answer>(.*?)</answer>", raw, re.S)
    return (an.group(1) if an else str(r.get("answer", ""))), (th.group(1) if th else ""), r.get("source"), time.time() - t

for q, attendu in [("quelle est la capitale du Cameroun ?", "yaound"),
                   ("combien de pattes a une araignée ?", "8"),
                   ("qui a écrit Les Misérables ?", "hugo")]:
    rep, raison, source, duree = demander(q)
    dire(attendu in rep.lower(), f"« {q} » -> « {rep[:60]} »")
    dire(source == "nemotron" or (source == "alice" and "crédit" in raison.lower()),
         f"   source {source} ; la raison dit ce qui s'est passe avec Nebius : {('crédit' in raison.lower())}")
    dire(duree < 15, f"   repondu en {duree:.1f} s")
rep, raison, source, duree = demander("à quoi Nvidia est exposé ?")
dire(source == "outil" and "Goulet" in rep, "la veille (outil de la maison) repond sans Nebius")
print(f"\nBILAN ARTHUR SANS CREDIT NEBIUS : {10 - rouges} verts, {rouges} rouges")
sys.exit(1 if rouges else 0)
