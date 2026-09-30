#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA BOITE AUX REPONSES — Patrick repond DANS la page, il ne revient pas taper.

POURQUOI ELLE EXISTE (17/09/2026). Ses mots : « corrige le garde fou qui
affiche tes questions dans une page web pour qu'il me donne la possibilite de
mettre mon choix directement dans la page et de valider », puis « avec
possibilite de commenter ».

Avant, la page AFFICHAIT mes questions. C'est tout. Patrick lisait, puis
revenait dans le terminal pour taper « 2 ». Deux endroits pour une seule
reponse : c'est ainsi qu'on perd une reponse, et qu'on repose la question.

CE QU'ELLE FAIT. Un tout petit serveur qui ecoute sur le port 8851 de cette
machine, et rien d'autre (127.0.0.1 = cette machine seule, personne du dehors
ne peut l'atteindre). Il sert la page des demandes, et il RECOIT la reponse :
la lettre choisie, et le commentaire ecrit a la main. Il la range aussitot
dans le carnet des reponses, celui qui m'empeche de reposer deux fois la
meme question.

L'INTERRUPTEUR. Si le fichier .page-des-demandes-eteinte existe, la page ne
s'ouvre plus toute seule. Patrick l'allume et l'eteint depuis son cockpit.
Demande du meme jour : « possibilite de desactiver la page web dans le
cockpit local ».

USAGE :  python3 boite-aux-reponses.py            # elle se met a ecouter
         python3 boite-aux-reponses.py --arreter  # elle se tait
"""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAISON = os.path.expanduser("~")
PORT = 8851
PAGE = os.path.join(MAISON, "livrables", "mes-demandes.html")
CARNET_OUTIL = os.path.join(MAISON, "outils", "carnet-des-reponses.py")
ARRIVEES = os.path.join(MAISON, ".claude", "portes", "reponses-arrivees.json")
PAGE_VIDEOS = os.path.join(MAISON, "livrables", "mes-videos.html")
DOSSIER_VIDEOS = os.path.join(MAISON, "livrables", "videos")
VIGNETTES = os.path.join(DOSSIER_VIDEOS, ".vignettes")
verrou = threading.Lock()


def ranger_la_reponse(question, choix, commentaire):
    """Range la reponse a DEUX endroits, pour deux usages differents.

    1. Le carnet des reponses : pour que je ne repose jamais la question.
    2. La boite d'arrivee : pour que la session en cours la voie tout de
       suite, sans relire tout le carnet."""
    reponse = choix or ""
    if commentaire:
        reponse = (reponse + " — " + commentaire).strip(" —")

    # 1. le carnet
    try:
        subprocess.run(["python3", CARNET_OUTIL, "--noter", question, reponse],
                       capture_output=True, text=True, timeout=10)
    except Exception:
        pass

    # 2. la boite d'arrivee
    with verrou:
        liste = []
        try:
            liste = json.load(open(ARRIVEES, encoding="utf-8"))
        except Exception:
            pass
        import time
        liste.append({"question": question, "choix": choix,
                      "commentaire": commentaire,
                      "quand": time.strftime("%Y-%m-%dT%H:%M")})
        os.makedirs(os.path.dirname(ARRIVEES), exist_ok=True)
        open(ARRIVEES, "w", encoding="utf-8").write(
            json.dumps(liste[-200:], ensure_ascii=False, indent=2))
    return reponse


class Guichet(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass          # on ne salit pas le terminal de Patrick

    def _envoyer(self, code, corps, type_="application/json; charset=utf-8"):
        octets = corps.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(octets)))
        self.end_headers()
        self.wfile.write(octets)

    def _fichier(self, chemin, type_):
        """Sert un fichier. Une video se lit PAR MORCEAUX : le navigateur
        demande « donne-moi d ici a la » quand on deplace le curseur. Sans
        cela, on ne peut pas avancer dans la video."""
        import urllib.parse
        chemin = os.path.realpath(chemin)
        base = os.path.realpath(DOSSIER_VIDEOS)
        if chemin != base and not chemin.startswith(base + os.sep):
            self._envoyer(403, '{"dit":"hors du dossier des videos"}'); return
        if not os.path.isfile(chemin):
            self._envoyer(404, '{"dit":"pas de fichier la"}'); return
        taille = os.path.getsize(chemin)
        plage = self.headers.get("Range")
        debut, fin = 0, taille - 1
        if plage and plage.startswith("bytes="):
            a, _, b = plage[6:].partition("-")
            try:
                if a == "" and b != "":
                    # suffixe RFC 7233 : « bytes=-N » veut les N DERNIERS octets.
                    debut = max(0, taille - int(b))
                    fin = taille - 1
                else:
                    debut = int(a) if a else 0
                    fin = int(b) if b else taille - 1
            except ValueError:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % taille)
                self.end_headers()
                return
            fin = min(fin, taille - 1)
            if debut > fin or debut < 0:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % taille)
                self.end_headers()
                return
        n = fin - debut + 1
        self.send_response(206 if plage else 200)
        self.send_header("Content-Type", type_)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(n))
        if plage:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (debut, fin, taille))
        self.end_headers()
        with open(chemin, "rb") as f:
            f.seek(debut)
            reste = n
            while reste > 0:
                bout = f.read(min(65536, reste))
                if not bout:
                    break
                try:
                    self.wfile.write(bout)
                except (BrokenPipeError, ConnectionResetError):
                    return
                reste -= len(bout)

    def _serrure(self, ecrire):
        """(29/09) Seule CETTE machine, par CETTE page, a le droit d'entrer.

        Ecouter sur 127.0.0.1 ne suffit pas : n'importe quel site ouvert dans
        le navigateur peut envoyer un POST ici (sans meme lire la reponse),
        et un domaine « rebinde » vers 127.0.0.1 passe pour local.
          - Host doit etre 127.0.0.1:PORT ou localhost:PORT (anti-rebinding) ;
          - pour ecrire, Origin (ou Referer) doit etre cette meme page."""
        port = self.server.server_address[1]   # le port vraiment ecoute
        hotes = {"127.0.0.1:%d" % port, "localhost:%d" % port}
        hote = (self.headers.get("Host") or "").lower()
        if hote not in hotes:
            return False
        if not ecrire:
            return True
        origine = self.headers.get("Origin") or self.headers.get("Referer") or ""
        if "://" not in origine:
            return False
        schema, reste = origine.split("://", 1)
        return schema == "http" and reste.split("/", 1)[0].lower() == hote

    def do_GET(self):
        if not self._serrure(False):
            self.send_error(403, "Hote inconnu : requete rejetee.")
            return
        import urllib.parse
        route = urllib.parse.unquote(self.path.split("?")[0])
        if route.startswith("/videos/"):
            n = route[len("/videos/"):]
            t = "video/webm" if n.lower().endswith(".webm") else "video/mp4"
            self._fichier(os.path.join(DOSSIER_VIDEOS, n), t); return
        if route.startswith("/vignettes/"):
            self._fichier(os.path.join(VIGNETTES, route[len("/vignettes/"):]),
                          "image/jpeg"); return
        if route.startswith("/video"):
            try:
                self._envoyer(200, open(PAGE_VIDEOS, encoding="utf-8").read(),
                              "text/html; charset=utf-8")
            except Exception:
                self._envoyer(200, "<p>Aucune video montree pour l instant.</p>",
                              "text/html; charset=utf-8")
            return
        if self.path.startswith("/arrivees"):
            try:
                self._envoyer(200, open(ARRIVEES, encoding="utf-8").read())
            except Exception:
                self._envoyer(200, "[]")
            return
        try:
            self._envoyer(200, open(PAGE, encoding="utf-8").read(),
                          "text/html; charset=utf-8")
        except Exception:
            self._envoyer(200, "<p>Aucune demande pour l instant.</p>",
                          "text/html; charset=utf-8")

    def do_POST(self):
        if not self._serrure(True):
            self.send_error(403, "Origine inconnue : requete rejetee.")
            return
        if not self.path.startswith("/repondre"):
            self._envoyer(404, '{"dit":"je ne connais pas cette porte"}')
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            self._envoyer(400, '{"dit":"je n ai pas compris"}')
            return
        question = (d.get("question") or "").strip()
        if not question:
            self._envoyer(400, '{"dit":"il manque la question"}')
            return
        r = ranger_la_reponse(question, (d.get("choix") or "").strip(),
                              (d.get("commentaire") or "").strip())
        self._envoyer(200, json.dumps(
            {"dit": "C est note : " + r}, ensure_ascii=False))


def main():
    if "--arreter" in sys.argv:
        subprocess.run(["pkill", "-f", "^python3 .*boite-aux-reponses.py$"])
        print("la boite s est tue")
        return 0
    try:
        serveur = ThreadingHTTPServer(("127.0.0.1", PORT), Guichet)
    except OSError as e:
        print("la boite ne peut pas ecouter sur %d : %s" % (PORT, e))
        return 1
    print("la boite aux reponses ecoute sur http://127.0.0.1:%d/" % PORT)
    serveur.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
