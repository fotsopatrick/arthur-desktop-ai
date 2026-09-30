#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LA BOITE AUX REPONSES — outils/boite-aux-reponses.py.

Ce qu'on prouve, SANS le vrai port 8851 et SANS le vrai HOME (un Guichet
ecoute sur un port libre de 127.0.0.1, les chemins pointent dans tmp_path) :
  - la serrure : Host inconnu -> 403 ; POST d'une autre origine -> 403 ;
    POST de la meme page (Origin ou Referer) -> accepte ;
  - POST /repondre range la reponse (carnet + boite d'arrivee) ;
    JSON abime -> 400, question absente -> 400, autre porte -> 404 ;
  - GET sert la page des demandes, la page des videos, les arrivees,
    avec un texte de secours quand le fichier manque ;
  - une video se lit par morceaux (Range -> 206) ;
  - on ne sort pas du dossier des videos ;
  - main : --arreter, port pris, ecoute.
"""
import http.client
import importlib.util
import json
import os
import sys
import threading
import types
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHIER = os.path.join(REPO, "outils", "boite-aux-reponses.py")


class _FauxSubprocess:
    """Remplace subprocess dans le module : on note, on ne lance rien."""

    def __init__(self):
        self.appels = []

    def run(self, cmd, **kw):
        self.appels.append(cmd)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")


@pytest.fixture
def boite(tmp_path, monkeypatch):
    """Le module charge avec un HOME jetable ; tous ses chemins dans tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    spec = importlib.util.spec_from_file_location("boite_aux_reponses", FICHIER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    videos = tmp_path / "livrables" / "videos"
    monkeypatch.setattr(mod, "PAGE", str(tmp_path / "livrables" / "mes-demandes.html"))
    monkeypatch.setattr(mod, "PAGE_VIDEOS", str(tmp_path / "livrables" / "mes-videos.html"))
    monkeypatch.setattr(mod, "ARRIVEES", str(tmp_path / "portes" / "arrivees.json"))
    monkeypatch.setattr(mod, "DOSSIER_VIDEOS", str(videos))
    monkeypatch.setattr(mod, "VIGNETTES", str(videos / ".vignettes"))
    monkeypatch.setattr(mod, "CARNET_OUTIL", str(tmp_path / "carnet.py"))
    faux = _FauxSubprocess()
    monkeypatch.setattr(mod, "subprocess", faux)
    mod._faux = faux
    return mod


@pytest.fixture
def guichet(boite):
    """Un vrai serveur Guichet sur un port libre ; rend (module, port)."""
    s = ThreadingHTTPServer(("127.0.0.1", 0), boite.Guichet)
    t = threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    t.start()
    yield boite, s.server_address[1]
    s.shutdown()
    s.server_close()


def _req(port, chemin, methode="GET", corps=None, entetes=None):
    """Une requete urllib ; rend (code, entetes, octets) meme en erreur HTTP."""
    url = "http://127.0.0.1:%d%s" % (port, chemin)
    r = urllib.request.Request(url, data=corps, method=methode, headers=entetes or {})
    try:
        with urllib.request.urlopen(r, timeout=5) as rep:
            return rep.status, rep.headers, rep.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def _poster(port, donnees, origine="meme", entetes=None):
    h = {"Content-Type": "application/json"}
    if origine == "meme":
        h["Origin"] = "http://127.0.0.1:%d" % port
    elif origine:
        h["Origin"] = origine
    h.update(entetes or {})
    corps = donnees if isinstance(donnees, bytes) else json.dumps(donnees).encode()
    return _req(port, "/repondre", "POST", corps, h)


# ---------------------------------------------------------------- ranger

def test_ranger_la_reponse_carnet_et_arrivees(boite):
    """Choix + commentaire : une reponse jointe, le carnet appele, l'arrivee notee."""
    r = boite.ranger_la_reponse("On pose ?", "A — oui", "vite")
    assert r == "A — oui — vite"
    assert boite._faux.appels == [["python3", boite.CARNET_OUTIL, "--noter", "On pose ?", r]]
    lu = json.load(open(boite.ARRIVEES, encoding="utf-8"))
    assert lu[0]["question"] == "On pose ?"
    assert lu[0]["choix"] == "A — oui" and lu[0]["commentaire"] == "vite"
    assert "T" in lu[0]["quand"]


def test_ranger_commentaire_seul_et_choix_seul(boite):
    """Sans choix, le commentaire seul, sans tiret pendant ; sans commentaire, le choix seul."""
    assert boite.ranger_la_reponse("q", "", "juste un mot") == "juste un mot"
    assert boite.ranger_la_reponse("q", None, "") == ""
    assert boite.ranger_la_reponse("q", "B", "") == "B"
    assert len(json.load(open(boite.ARRIVEES, encoding="utf-8"))) == 3


def test_ranger_garde_les_200_dernieres_et_survit_aux_pannes(boite, monkeypatch):
    """La boite d'arrivee ne garde que 200 reponses ; un carnet en panne n'arrete rien ;
    une boite d'arrivee abimee repart de zero."""
    os.makedirs(os.path.dirname(boite.ARRIVEES))
    with open(boite.ARRIVEES, "w", encoding="utf-8") as f:
        json.dump([{"question": str(i)} for i in range(200)], f)

    def panne(*a, **k):
        raise OSError("python3 introuvable")
    monkeypatch.setattr(boite._faux, "run", panne)
    boite.ranger_la_reponse("la 201e", "A", "")
    lu = json.load(open(boite.ARRIVEES, encoding="utf-8"))
    assert len(lu) == 200
    assert lu[0]["question"] == "1" and lu[-1]["question"] == "la 201e"

    with open(boite.ARRIVEES, "w", encoding="utf-8") as f:
        f.write("pas du json")
    boite.ranger_la_reponse("apres", "A", "")
    assert [x["question"] for x in json.load(open(boite.ARRIVEES, encoding="utf-8"))] == ["apres"]


# ---------------------------------------------------------------- serrure + POST

def test_post_meme_origine_accepte(guichet):
    """La page elle-meme poste : 200, « C est note », reponse rangee."""
    boite, port = guichet
    code, h, corps = _poster(port, {"question": " On pose la porte ? ",
                                    "choix": "A — oui", "commentaire": " vite "})
    assert code == 200
    assert json.loads(corps)["dit"] == "C est note : A — oui — vite"
    assert h["Content-Type"].startswith("application/json")
    lu = json.load(open(boite.ARRIVEES, encoding="utf-8"))
    assert lu[-1]["question"] == "On pose la porte ?"
    assert lu[-1]["commentaire"] == "vite"


def test_post_localhost_et_referer(guichet):
    """Host localhost + Origin localhost, ou Referer de la page : accepte."""
    boite, port = guichet
    code, _, _ = _poster(port, {"question": "q1", "choix": "A"}, origine="http://localhost:%d" % port,
                         entetes={"Host": "localhost:%d" % port})
    assert code == 200
    code, _, _ = _poster(port, {"question": "q2", "choix": "A"}, origine=None,
                         entetes={"Referer": "http://127.0.0.1:%d/page?x=1" % port})
    assert code == 200


@pytest.mark.parametrize("origine", [
    "http://evil.example",
    "https://127.0.0.1:{port}",          # mauvais schema
    "http://127.0.0.1:1",               # mauvais port
    "null",                             # pas de ://
    None,                               # pas d'Origin du tout
])
def test_post_origine_etrangere_refusee(guichet, origine):
    """Toute autre origine : 403, et rien n'est range."""
    boite, port = guichet
    if origine:
        origine = origine.format(port=port)
    code, _, _ = _poster(port, {"question": "q", "choix": "A"}, origine=origine)
    assert code == 403
    assert not os.path.exists(boite.ARRIVEES)
    assert boite._faux.appels == []


def test_post_host_etranger_refuse(guichet):
    """Un domaine rebinde vers 127.0.0.1 (Host inconnu) : 403, meme avec Origin assorti."""
    boite, port = guichet
    code, _, _ = _poster(port, {"question": "q"}, origine="http://evil.example:%d" % port,
                         entetes={"Host": "evil.example:%d" % port})
    assert code == 403
    assert not os.path.exists(boite.ARRIVEES)


def test_get_host_etranger_refuse(guichet):
    """GET avec un Host etranger ou mauvais port : 403."""
    boite, port = guichet
    assert _req(port, "/", entetes={"Host": "evil.example"})[0] == 403
    assert _req(port, "/", entetes={"Host": "127.0.0.1:%d" % (port + 1)})[0] == 403


def test_post_json_abime(guichet):
    """Un corps qui n'est pas du JSON : 400 « je n ai pas compris »."""
    _, port = guichet
    code, _, corps = _poster(port, b"{pas du json")
    assert code == 400
    assert json.loads(corps)["dit"] == "je n ai pas compris"


def test_post_question_absente_ou_vide(guichet):
    """Sans question (ou blanche, ou corps vide) : 400 « il manque la question »."""
    boite, port = guichet
    for d in ({"choix": "A"}, {"question": "   "}, b""):
        code, _, corps = _poster(port, d)
        assert code == 400
        assert json.loads(corps)["dit"] == "il manque la question"
    assert not os.path.exists(boite.ARRIVEES)


def test_post_autre_porte(guichet):
    """Un POST ailleurs que /repondre : 404."""
    _, port = guichet
    code, _, corps = _req(port, "/ailleurs", "POST", b"{}",
                          {"Origin": "http://127.0.0.1:%d" % port})
    assert code == 404
    assert "porte" in json.loads(corps)["dit"]


# ---------------------------------------------------------------- GET pages

def test_get_pages_de_secours(guichet):
    """Fichiers absents : textes de secours, et [] pour les arrivees."""
    _, port = guichet
    code, h, corps = _req(port, "/")
    assert code == 200 and b"Aucune demande" in corps
    assert h["Content-Type"].startswith("text/html")
    assert b"Aucune video" in _req(port, "/video")[2]
    assert _req(port, "/arrivees")[2] == b"[]"


def test_get_pages_existantes(guichet):
    """Fichiers presents : servis tels quels."""
    boite, port = guichet
    os.makedirs(os.path.dirname(boite.PAGE), exist_ok=True)
    open(boite.PAGE, "w", encoding="utf-8").write("<h1>Demandes é</h1>")
    open(boite.PAGE_VIDEOS, "w", encoding="utf-8").write("<h1>Videos</h1>")
    boite.ranger_la_reponse("q", "A", "")
    assert _req(port, "/?x=1")[2].decode("utf-8") == "<h1>Demandes é</h1>"
    assert _req(port, "/video")[2] == b"<h1>Videos</h1>"
    assert json.loads(_req(port, "/arrivees")[2])[0]["question"] == "q"


# ---------------------------------------------------------------- videos

@pytest.fixture
def video(guichet):
    """Une fausse video de 100 000 octets (plus qu'un morceau de 64 Kio)."""
    boite, port = guichet
    os.makedirs(os.path.join(boite.DOSSIER_VIDEOS, ".vignettes"))
    contenu = bytes(i % 251 for i in range(100000))
    with open(os.path.join(boite.DOSSIER_VIDEOS, "film ete.mp4"), "wb") as f:
        f.write(contenu)
    with open(os.path.join(boite.DOSSIER_VIDEOS, "clip.WEBM"), "wb") as f:
        f.write(b"webm")
    with open(os.path.join(boite.VIGNETTES, "film.jpg"), "wb") as f:
        f.write(b"jpeg")
    return boite, port, contenu


def test_video_entiere(video):
    """Sans Range : 200, tout le fichier, Accept-Ranges annonce."""
    _, port, contenu = video
    code, h, corps = _req(port, "/videos/film%20ete.mp4")
    assert code == 200 and corps == contenu
    assert h["Content-Type"] == "video/mp4"
    assert h["Accept-Ranges"] == "bytes"
    assert "Content-Range" not in h


def test_video_webm_et_vignette(video):
    """Le type suit l'extension ; les vignettes sont des jpeg."""
    _, port, _ = video
    code, h, corps = _req(port, "/videos/clip.WEBM")
    assert (code, h["Content-Type"], corps) == (200, "video/webm", b"webm")
    code, h, corps = _req(port, "/vignettes/film.jpg")
    assert (code, h["Content-Type"], corps) == (200, "image/jpeg", b"jpeg")


@pytest.mark.parametrize("plage,debut,fin", [
    ("bytes=10-19", 10, 19),
    ("bytes=99990-", 99990, 99999),
    ("bytes=99990-500000", 99990, 99999),   # fin rabotee a la taille
    ("bytes=0-", 0, 99999),
])
def test_video_par_morceaux(video, plage, debut, fin):
    """Avec Range : 206, le bon morceau, Content-Range juste."""
    _, port, contenu = video
    code, h, corps = _req(port, "/videos/film%20ete.mp4", entetes={"Range": plage})
    assert code == 206
    assert corps == contenu[debut:fin + 1]
    assert h["Content-Range"] == "bytes %d-%d/100000" % (debut, fin)
    assert int(h["Content-Length"]) == fin - debut + 1


def test_video_absente(video):
    """Un fichier qui n'existe pas (ou un dossier) : 404."""
    _, port, _ = video
    assert _req(port, "/videos/rien.mp4")[0] == 404
    assert _req(port, "/videos/.vignettes")[0] == 404


@pytest.mark.parametrize("chemin", [
    "/videos/../../../etc/passwd",
    "/videos/..%2f..%2f..%2fetc%2fpasswd",
    "/videos/%2e%2e/mes-demandes.html",
    "/videos//etc/passwd",               # chemin absolu apres /videos/
    "/vignettes/../../mes-demandes.html",
])
def test_video_hors_du_dossier_refusee(video, chemin):
    """Remonter hors du dossier des videos : 403."""
    boite, port, _ = video
    os.makedirs(os.path.dirname(boite.PAGE), exist_ok=True)
    open(boite.PAGE, "w").write("secret")
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request("GET", chemin)
    r = c.getresponse()
    corps = r.read()
    c.close()
    assert r.status == 403
    assert b"secret" not in corps and b"root:" not in corps


def test_video_lien_symbolique_vers_dehors_refuse(video, tmp_path):
    """Un lien symbolique dans le dossier qui pointe dehors : 403 (realpath)."""
    boite, port, _ = video
    dehors = tmp_path / "dehors.mp4"
    dehors.write_bytes(b"secret")
    os.symlink(dehors, os.path.join(boite.DOSSIER_VIDEOS, "lien.mp4"))
    assert _req(port, "/videos/lien.mp4")[0] == 403


@pytest.mark.xfail(strict=True, reason="bug: boite-aux-reponses.py:99 compare par "
                   "startswith sans separateur ; un dossier voisin 'videos-xxx' passe")
def test_video_dossier_voisin_refuse(video, tmp_path):
    """Un dossier voisin qui commence par le meme nom (videos-prive) doit rester ferme."""
    boite, port, _ = video
    voisin = tmp_path / "livrables" / "videos-prive"
    voisin.mkdir()
    (voisin / "x.mp4").write_bytes(b"prive")
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request("GET", "/videos/..%2fvideos-prive/x.mp4")
    r = c.getresponse()
    r.read()
    c.close()
    assert r.status == 403


def _brut(port, plage):
    """Une requete Range, lue a la main (la reponse peut etre malformee)."""
    import socket
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    s.sendall(("GET /videos/film%%20ete.mp4 HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n"
               "Range: %s\r\nConnection: close\r\n\r\n" % (port, plage)).encode())
    recu = b""
    try:
        while True:
            b = s.recv(65536)
            if not b:
                break
            recu += b
    except OSError:
        pass
    s.close()
    return recu


@pytest.mark.xfail(strict=True, reason="bug: boite-aux-reponses.py:108 int() d'une plage "
                   "illisible leve ValueError : connexion coupee sans reponse (attendu 416)")
def test_video_plage_illisible(video):
    """Range: bytes=abc- ne doit pas faire tomber la requete sans reponse."""
    _, port, _ = video
    assert _brut(port, "bytes=abc-").startswith(b"HTTP/1.0 416")


@pytest.mark.xfail(strict=True, reason="bug: boite-aux-reponses.py:111 debut > fin donne "
                   "Content-Length negatif (attendu 416)")
def test_video_plage_inversee(video):
    """Range: bytes=50-10 (ou au-dela de la fin) : 416, pas un Content-Length negatif."""
    _, port, _ = video
    assert _brut(port, "bytes=50-10").startswith(b"HTTP/1.0 416")


@pytest.mark.xfail(strict=True, reason="bug: boite-aux-reponses.py:108 la plage suffixe "
                   "'bytes=-N' (N derniers octets, RFC 7233) est lue comme 0..N")
def test_video_plage_suffixe(video):
    """Range: bytes=-10 veut les 10 DERNIERS octets."""
    _, port, contenu = video
    code, h, corps = _req(port, "/videos/film%20ete.mp4", entetes={"Range": "bytes=-10"})
    assert corps == contenu[-10:]


def test_video_client_qui_raccroche(video, boite):
    """Le navigateur qui coupe en plein envoi (BrokenPipe) : le serveur se tait
    proprement, et continue de servir."""
    _, port, contenu = video

    class Tuyau:
        def write(self, b):
            raise BrokenPipeError

    g = boite.Guichet.__new__(boite.Guichet)
    g.headers = {}
    g.wfile = Tuyau()
    g.request_version = "HTTP/1.1"
    envoyes = []
    g.send_response = lambda code: envoyes.append(code)
    g.send_header = lambda *a: None
    g.end_headers = lambda: None
    g._fichier(os.path.join(boite.DOSSIER_VIDEOS, "film ete.mp4"), "video/mp4")
    assert envoyes == [200]
    assert _req(port, "/videos/clip.WEBM")[2] == b"webm"


def test_video_fichier_qui_raccourcit(video, boite, monkeypatch):
    """Un fichier qui raccourcit pendant l'envoi : on s'arrete, sans boucler."""
    ecrit = []
    g = boite.Guichet.__new__(boite.Guichet)
    g.headers = {}
    g.wfile = types.SimpleNamespace(write=ecrit.append)
    g.send_response = g.send_header = lambda *a: None
    g.end_headers = lambda: None
    chemin = os.path.join(boite.DOSSIER_VIDEOS, "film ete.mp4")
    vraie = os.path.getsize
    monkeypatch.setattr(boite.os.path, "getsize",
                        lambda p: vraie(p) + 5000 if p == os.path.realpath(chemin) else vraie(p))
    g._fichier(chemin, "video/mp4")
    assert sum(len(b) for b in ecrit) == 100000


# ---------------------------------------------------------------- main

def test_main_arreter(boite, monkeypatch, capsys):
    """--arreter : pkill sur la boite, et un mot."""
    monkeypatch.setattr(sys, "argv", ["boite-aux-reponses.py", "--arreter"])
    assert boite.main() == 0
    assert boite._faux.appels[0][0] == "pkill"
    assert "tue" in capsys.readouterr().out


def test_main_port_pris(boite, monkeypatch, capsys):
    """Port deja pris : 1 et un message, pas de trace."""
    monkeypatch.setattr(sys, "argv", ["boite-aux-reponses.py"])

    def pris(*a, **k):
        raise OSError("Address already in use")
    monkeypatch.setattr(boite, "ThreadingHTTPServer", pris)
    assert boite.main() == 1
    assert "ne peut pas ecouter sur 8851" in capsys.readouterr().out


def test_main_ecoute(boite, monkeypatch, capsys):
    """Sans option : un serveur Guichet sur 127.0.0.1:PORT qui ecoute."""
    monkeypatch.setattr(sys, "argv", ["boite-aux-reponses.py"])
    vus = []

    class FauxServeur:
        def __init__(self, adresse, classe):
            vus.append((adresse, classe))

        def serve_forever(self):
            vus.append("ecoute")
    monkeypatch.setattr(boite, "ThreadingHTTPServer", FauxServeur)
    assert boite.main() is None
    assert vus == [(("127.0.0.1", 8851), boite.Guichet), "ecoute"]
    assert "http://127.0.0.1:8851/" in capsys.readouterr().out
