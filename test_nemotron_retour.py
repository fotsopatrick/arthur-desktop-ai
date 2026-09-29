#!/usr/bin/env python3
"""LE RETOUR DE NEMOTRON, SANS MENTIR SUR LE CRÉDIT (24/09/2026).

Le 21/09, la branche Nebius a été coupée : le crédit était à zéro. Mais le
concours Nebius × NVIDIA exige Nemotron sur Nebius Token Factory. Le contrat
devient donc :

  1. réglage « nebius » + clé + crédit : Arthur demande à Nemotron, et le dit ;
  2. Nebius répond 402 (budget épuisé) : Arthur le DIT en clair (« plus de
     crédit »), et redescend à la maison — il n'invente rien ;
  3. réponse vide (le modèle a tout dépensé en réflexion) : même honnêteté ;
  4. aucun dossier nommé « ~ » n'est créé (bug : os.makedirs("~/livrables")).

Tout se passe contre un FAUX Nebius local : aucun appel réel, aucun crédit dépensé.
"""
import http.server, json, os, sys, tempfile, threading

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import nemotron_nebius as N
import nano_moteur_ultra as M

MODE = {"v": "ok"}
class FauxNebius(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if MODE["v"] == "402":
            corps, code = {"detail": "Payment Required: You have exhausted your budget."}, 402
        elif MODE["v"] == "vide":
            corps, code = {"choices": [{"message": {"content": None, "reasoning_content": "brouillon"}, "finish_reason": "length"}]}, 200
        else:
            corps, code = {"choices": [{"message": {"content": "Oulan-Bator."}, "finish_reason": "stop"}]}, 200
        b = json.dumps(corps).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

serveur = http.server.HTTPServer(("127.0.0.1", 0), FauxNebius)
threading.Thread(target=serveur.serve_forever, daemon=True).start()
N.ADRESSE = "http://127.0.0.1:%d/v1/chat/completions" % serveur.server_address[1]
os.environ["NEBIUS_API_KEY"] = "cle-de-test"

rouges = 0; n = 0
def verdict(ok, texte):
    global rouges, n
    n += 1
    print(("  VERT  " if ok else "  ROUGE ") + texte)
    if not ok:
        rouges += 1

bac = tempfile.mkdtemp(); avant = os.getcwd(); os.chdir(bac)
try:
    MODE["v"] = "ok"
    d = N.demander("Quelle est la capitale de la Mongolie ?")
    verdict(d.get("reponse") == "Oulan-Bator.", "1. Nemotron répond (faux Nebius) : %r" % d.get("reponse"))
    verdict(not os.path.exists(os.path.join(bac, "~")), "4. aucun dossier « ~ » créé par le journal des dialogues")

    MODE["v"] = "402"
    d = N.demander("Quelle est la capitale de la Mongolie ?")
    verdict(d.get("reponse") is None and d.get("credit_epuise") is True,
            "2a. 402 : pas de réponse, et « crédit épuisé » est signalé")
    verdict("crédit" in (d.get("panne") or "").lower(), "2b. il le dit en clair : %r" % (d.get("panne") or "")[:70])

    MODE["v"] = "vide"
    d = N.demander("Quelle est la capitale de la Mongolie ?")
    verdict(d.get("reponse") is None and "place de repondre" in (d.get("panne") or ""),
            "3. réponse vide : il ne rend pas les brouillons")
finally:
    os.chdir(avant)

# Le moteur : réglage « nebius », question hors règles
moteur = M.NanoMoteurUltraEngine()
Q = "Quelle est la capitale de la Mongolie ?"
MODE["v"] = "ok"
r = moteur.repondre(Q, choisir="nebius")
verdict(r.get("source") == "nemotron", "5. moteur, crédit présent : la réponse vient de Nemotron (source=%s)" % r.get("source"))
verdict("nebius" in (r.get("reasoning") or r.get("raison") or json.dumps(r, ensure_ascii=False)).lower(),
        "6. il dit qu'il est passé par Nebius")

MODE["v"] = "402"
moteur.demander_a_alice = lambda *a, **k: (None, "Alice coupée pour l'épreuve")   # la maison ne répond pas non plus
r = moteur.repondre(Q, choisir="nebius")
tout = json.dumps(r, ensure_ascii=False).lower()
verdict(r.get("source") != "nemotron", "7. moteur, 402 : la source n'est pas Nemotron (source=%s)" % r.get("source"))
verdict("crédit" in tout, "8. le moteur dit que Nebius n'a plus de crédit")
verdict("oulan" not in tout, "9. et il n'invente pas la réponse")

serveur.shutdown()
print("BILAN NEMOTRON : %d rouge(s) sur %d" % (rouges, n))
sys.exit(1 if rouges else 0)
