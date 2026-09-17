#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MES VIDEOS — une page a la YouTube, avec toutes les videos deja fabriquees.

POURQUOI (17/09/2026). Ses mots : « fait un garde fou qui t oblige a me
montrer la video dans une page web », « dans cette page toutes les videos
deja generees par video narre », « fait nous un truc a la youtube », « fais
des playlists par groupe ».

Ne d une faute reelle du meme jour : j ai fabrique une video de 158 secondes
et je lui ai donne son NOM. Il ne l a jamais vue. Un nom de fichier ne se
regarde pas.

CE QUE FAIT CE FICHIER
  1. il cherche TOUTES les videos de ~/livrables/videos ;
  2. il les range en listes — un dossier = une liste ;
  3. il fabrique une vignette pour chacune, prise dans la video elle-meme ;
  4. il ecrit une page avec un grand lecteur en haut et les listes a cote ;
  5. il pose la marque qui dit au garde : « celle-la, Patrick l a vue ».

USAGE :  montrer-la-video.py [la video a mettre en avant] [--sans-ouvrir]
Reussi quand la derniere ligne dit : VIDEOS MONTREES
"""
import html
import json
import os
import subprocess
import sys
import time

MAISON = os.path.expanduser("~")
DOSSIER = os.path.join(MAISON, "livrables", "videos")
VIGNETTES = os.path.join(DOSSIER, ".vignettes")
PAGE = os.path.join(MAISON, "livrables", "mes-videos.html")
MARQUE = os.path.join(MAISON, ".claude", "portes", ".videos-montrees")
ADRESSE = "http://127.0.0.1:8851/video"


def duree(chemin):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0", chemin],
                           capture_output=True, text=True, timeout=20)
        return int(float(r.stdout.strip() or 0))
    except Exception:
        return 0


def vignette(chemin, cle):
    """Une image prise DANS la video, au cinquieme de sa duree. Gardee une
    fois pour toutes : la refaire a chaque ouverture serait refaire le meme
    voyage pour la meme image."""
    os.makedirs(VIGNETTES, exist_ok=True)
    sortie = os.path.join(VIGNETTES, cle + ".jpg")
    if os.path.exists(sortie) and os.path.getmtime(sortie) >= os.path.getmtime(chemin):
        return os.path.basename(sortie)
    d = duree(chemin)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(max(1, d // 5)),
                    "-i", chemin, "-frames:v", "1", "-vf", "scale=480:-2", sortie],
                   capture_output=True, timeout=90)
    return os.path.basename(sortie) if os.path.exists(sortie) else ""


def joli(nom):
    return nom.replace("-", " ").replace("_", " ").replace(".mp4", "").replace(".webm", "")


def mmss(s):
    return "%d:%02d" % (s // 60, s % 60)


def ramasser():
    """Toutes les videos, rangees par dossier. Le dossier est la liste."""
    listes = {}
    for racine, dirs, fichiers in os.walk(DOSSIER):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in sorted(fichiers):
            if not f.lower().endswith((".mp4", ".webm")):
                continue
            chemin = os.path.join(racine, f)
            relatif = os.path.relpath(chemin, DOSSIER)
            groupe = os.path.dirname(relatif) or "Les videos finies"
            cle = relatif.replace("/", "__").rsplit(".", 1)[0]
            listes.setdefault(groupe, []).append({
                "titre": joli(f), "chemin": relatif, "cle": cle,
                "duree": duree(chemin), "poids": os.path.getsize(chemin),
                "quand": time.strftime("%d/%m/%Y", time.localtime(os.path.getmtime(chemin))),
                "vignette": vignette(chemin, cle)})
    return listes


GABARIT = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mes videos</title>
<style>
 :root{color-scheme:dark}
 *{box-sizing:border-box}
 body{margin:0;background:#0b1120;color:#e2e8f0;
      font-family:Roboto,system-ui,sans-serif}
 header{padding:18px 26px;border-bottom:1px solid #1e293b;
        display:flex;align-items:baseline;gap:14px}
 header h1{font-size:19px;margin:0;font-weight:600;letter-spacing:.01em}
 header span{color:#64748b;font-size:13.5px}
 .page{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:26px;
       padding:24px 26px 70px;max-width:1700px}
 @media(max-width:1000px){.page{grid-template-columns:1fr}}
 video{width:100%;background:#000;border-radius:12px;display:block}
 .titrejoue{font-size:23px;font-weight:600;margin:16px 0 4px;color:#f8fafc}
 .sousjoue{color:#94a3b8;font-size:14.5px;margin:0 0 18px}
 .groupe{margin-bottom:26px}
 .nomgroupe{font-size:12.5px;text-transform:uppercase;letter-spacing:.07em;
            color:#64748b;margin:0 0 10px;display:flex;justify-content:space-between}
 .item{display:flex;gap:12px;padding:8px;border-radius:10px;cursor:pointer;
       border:1px solid transparent;transition:background .12s,border-color .12s}
 .item:hover{background:#111c33;border-color:#1e293b}
 .item.joue{background:#10233f;border-color:#38bdf8}
 .vig{position:relative;flex:0 0 auto;width:146px;height:82px;border-radius:8px;
      background:#0d1729 center/cover no-repeat;overflow:hidden}
 .vig b{position:absolute;right:5px;bottom:5px;background:#000c;color:#fff;
        font-size:11.5px;font-weight:600;padding:1px 5px;border-radius:4px}
 .meta{min-width:0;flex:1}
 .meta p{margin:0}
 .t{font-size:14.5px;font-weight:600;color:#e2e8f0;line-height:1.3}
 .s{font-size:12.5px;color:#64748b;margin-top:4px}
 footer{padding:0 26px 40px;color:#475569;font-size:12.5px}
</style></head><body>
<header><h1>Mes videos</h1><span>__COMBIEN__ videos, __LISTES__ listes &middot; mise a jour du __QUAND__</span></header>
<div class="page">
  <div>
    <video id="lecteur" controls poster="__POSTER__" src="__SRC__"></video>
    <p class="titrejoue" id="titre">__TITRE__</p>
    <p class="sousjoue" id="sous">__SOUS__</p>
  </div>
  <div id="listes">__LISTES_HTML__</div>
</div>
<footer>Une liste = un dossier. Clique une vignette : elle se joue en haut.
Les voix sont fabriquees avec Google Cloud Text-to-Speech.</footer>
<script>
// Cliquer une vignette joue la video en haut. Pas de page qui se recharge.
document.addEventListener("click", function (e) {
  var it = e.target.closest(".item"); if (!it) return;
  document.querySelectorAll(".item").forEach(function (x) { x.classList.remove("joue"); });
  it.classList.add("joue");
  var l = document.getElementById("lecteur");
  l.src = it.dataset.src; l.poster = it.dataset.poster; l.play();
  document.getElementById("titre").textContent = it.dataset.titre;
  document.getElementById("sous").textContent = it.dataset.sous;
  window.scrollTo({top: 0, behavior: "smooth"});
});
</script>
</body></html>"""


def ecrire(listes, en_avant=None):
    e = html.escape
    toutes = [v for g in listes.values() for v in g]
    if not toutes:
        return None
    choisie = None
    if en_avant:
        for v in toutes:
            if os.path.basename(v["chemin"]) == os.path.basename(en_avant):
                choisie = v
    choisie = choisie or max(toutes, key=lambda v: v["quand"])

    blocs = []
    for groupe in sorted(listes, key=lambda g: (g != "Les videos finies", g)):
        vs = listes[groupe]
        total = sum(v["duree"] for v in vs)
        blocs.append('<div class="groupe"><p class="nomgroupe"><span>%s</span>'
                     '<span>%d videos &middot; %s</span></p>'
                     % (e(joli(groupe)), len(vs), mmss(total)))
        for v in vs:
            sous = "%s &middot; %s &middot; %d Mo" % (mmss(v["duree"]), v["quand"],
                                                     v["poids"] // 1048576)
            blocs.append(
                '<div class="item%s" data-src="/videos/%s" data-poster="/vignettes/%s"'
                ' data-titre="%s" data-sous="%s">'
                '<div class="vig" style="background-image:url(/vignettes/%s)">'
                '<b>%s</b></div><div class="meta"><p class="t">%s</p>'
                '<p class="s">%s</p></div></div>'
                % (" joue" if v is choisie else "", e(v["chemin"]), e(v["vignette"]),
                   e(v["titre"]), sous.replace("&middot;", "-"), e(v["vignette"]),
                   mmss(v["duree"]), e(v["titre"]), sous))
        blocs.append("</div>")

    sous = "%s &middot; %s &middot; %d Mo" % (mmss(choisie["duree"]), choisie["quand"],
                                              choisie["poids"] // 1048576)
    page = (GABARIT.replace("__COMBIEN__", str(len(toutes)))
                   .replace("__LISTES__", str(len(listes)))
                   .replace("__QUAND__", time.strftime("%d/%m/%Y a %H h %M"))
                   .replace("__SRC__", "/videos/" + choisie["chemin"])
                   .replace("__POSTER__", "/vignettes/" + choisie["vignette"])
                   .replace("__TITRE__", e(choisie["titre"]))
                   .replace("__SOUS__", sous)
                   .replace("__LISTES_HTML__", "".join(blocs)))
    os.makedirs(os.path.dirname(PAGE), exist_ok=True)
    open(PAGE, "w", encoding="utf-8").write(page)
    return choisie


def reveiller_la_boite():
    import socket
    s = socket.socket(); s.settimeout(0.4)
    try:
        s.connect(("127.0.0.1", 8851)); return
    except OSError:
        pass
    finally:
        s.close()
    subprocess.Popen(["python3", os.path.join(MAISON, "outils", "boite-aux-reponses.py")],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    time.sleep(0.8)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    listes = ramasser()
    choisie = ecrire(listes, args[0] if args else None)
    if not choisie:
        print("aucune video a montrer")
        return 1
    # LA MARQUE. C est elle que le garde regarde : sans elle, il refuse.
    vues = {}
    try:
        vues = json.load(open(MARQUE, encoding="utf-8"))
    except Exception:
        pass
    for g in listes.values():
        for v in g:
            vues[v["chemin"]] = time.time()
    os.makedirs(os.path.dirname(MARQUE), exist_ok=True)
    open(MARQUE, "w", encoding="utf-8").write(json.dumps(vues, ensure_ascii=False))

    reveiller_la_boite()
    if "--sans-ouvrir" not in sys.argv:
        try:
            subprocess.Popen(["xdg-open", ADRESSE],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as ex:
            print("page ecrite, mais pas ouverte : %s" % ex)
    n = sum(len(g) for g in listes.values())
    print("VIDEOS MONTREES (%d videos, %d listes) — %s" % (n, len(listes), ADRESSE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
