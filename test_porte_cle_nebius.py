#!/usr/bin/env python3
"""LA CLÉ DE NEBIUS — une porte avec un verrou, pas une serrure a fenetre.

Releve le 21/09/2026 : la route /effacer effacait la clef Nebius sur
n importe quel POST — sans verifier d ou venait la requete. Une page
enfer au fond d un onglet pouvait donc effacer la clef d un POST forge.
Une porte qui laisse passer l inconnu ne garde rien : on exige une
origine legitime (meme hote), et 403 dans le cas contraire.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

vert = rouge = 0


def juge(t, ok, d=""):
    global vert, rouge
    print("  %-5s %-54s %s" % ("VERT" if ok else "ROUGE", t, d))
    if ok:
        vert += 1
    else:
        rouge += 1


import page_cle_nebius as page

bac = tempfile.mkdtemp(prefix="cle-nebius-test-")
serv = None

try:
    # Le test travaille dans son bac a sable : jamais sur la vraie clef.
    page.COFFRE = os.path.join(bac, "cle-nebius.txt")
    with open(page.COFFRE, "w", encoding="utf-8") as f:
        f.write("x" * 40 + "\n")

    serv = ThreadingHTTPServer(("127.0.0.1", 0), page.Poste)
    port = serv.server_address[1]
    th = threading.Thread(target=serv.serve_forever, daemon=True)
    th.start()
    BASE = "http://127.0.0.1:%d" % port

    def post(chemin, origin=None, referer=None):
        req = urllib.request.Request(
            BASE + chemin, data=b"{}",
            headers={"Content-Type": "application/json"})
        if origin:
            req.add_header("Origin", origin)
        if referer:
            req.add_header("Referer", referer)
        b = urllib.request.urlopen(req, timeout=5)
        return b.status, json.loads(b.read().decode("utf-8"))

    print("\n1) LA PORTE EXISTE, DANS SON BAC")
    r = urllib.request.urlopen(BASE + "/etat", timeout=5)
    juge("la page repond (etat)", r.status == 200)
    juge("une clef est en place dans le bac (pour l effacer vraiment)",
         os.path.exists(page.COFFRE) and len(open(page.COFFRE).read()) >= 20)

    print("\n2) LE MAUVAIS : aucun en-tete d origine")
    try:
        post("/effacer")
        juge("SANS origine -> rejete 403", False, "accepte : porte ouverte")
    except urllib.error.HTTPError as e:
        juge("SANS origine -> rejete 403", e.code == 403, "code %d" % e.code)
    juge("la clef est toujours la (rien n a ete efface)",
         os.path.exists(page.COFFRE))

    print("\n3) LE MAUVAIS : origine etrangere")
    try:
        post("/effacer", origin="http://evil.example")
        juge("origine etrangere -> rejete 403", False, "accepte : porte ouverte")
    except urllib.error.HTTPError as e:
        juge("origine etrangere -> rejete 403", e.code == 403, "code %d" % e.code)
    juge("la clef est toujours la", os.path.exists(page.COFFRE))

    print("\n4) LE MAUVAIS : referer etranger, sans origin")
    try:
        post("/effacer", referer="http://evil.example/p")
        juge("referer etranger -> rejete 403", False)
    except urllib.error.HTTPError as e:
        juge("referer etranger -> rejete 403", e.code == 403, "code %d" % e.code)
    juge("la clef est toujours la", os.path.exists(page.COFFRE))

    print("\n5) LE BON : origine legitime (la page elle-meme)")
    code, d = post("/effacer", origin=BASE)
    juge("meme origine -> accepte", code == 200 and d.get("ok"))
    juge("la clef a vraiment ete effacee (resultat voulu)",
         not os.path.exists(page.COFFRE))

finally:
    if serv is not None:
        serv.shutdown()
    try:
        shutil.rmtree(bac)
    except OSError:
        pass

print("\nBILAN PORTE-NEBIUS : %d verts, %d rouges" % (vert, rouge))
sys.exit(0 if rouge == 0 else 1)