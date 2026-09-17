#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MES DEMANDES — les afficher à l'écran, dans une jolie page.

POURQUOI CE FICHIER EXISTE (10/09/2026). Patrick l'a dit : « quand t'as des
demandes, affiche-moi ça à l'écran, crée un garde-fou qui affiche tes demandes
à l'écran dans une jolie page web ». Jusque-là, mes demandes se perdaient au
milieu d'un long message : il fallait relire pour les retrouver.

CE QUE FAIT CE FICHIER. Il reçoit une liste de demandes, écrit une page web
lisible d'un coup d'œil, et l'ouvre SUR SON ÉCRAN — une seule fois par liste,
pour ne pas faire clignoter son navigateur.

    echo '[{"quoi": "...", "pourquoi": "...", "qui": "..."}]' | mes-demandes.py
    mes-demandes.py --fichier liste.json

Réussi quand la page s'ouvre et que la dernière ligne dit : PAGE MONTREE
"""
import hashlib
import html
import json
import os
import subprocess
import sys
import time

PAGE = os.path.expanduser("~/livrables/mes-demandes.html")
MARQUE = os.path.expanduser("~/.claude/portes/.demandes-vues")
# L INTERRUPTEUR (17/09/2026). Si ce fichier existe, la page ne s ouvre plus
# toute seule. Patrick l allume et l eteint depuis son cockpit local.
ETEINTE = os.path.expanduser("~/.claude/portes/.page-des-demandes-eteinte")
BOITE = "http://127.0.0.1:8851/"

GABARIT = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ce que j'attends de toi</title>
<style>
 :root{color-scheme:dark}
 body{margin:0;background:#0b1120;color:#e2e8f0;
      font-family:Roboto,system-ui,sans-serif;padding:28px 20px 60px}
 h1{font-size:22px;font-weight:500;margin:0 0 4px;letter-spacing:.01em}
 .quand{color:#64748b;font-size:13px;margin:0 0 26px}
 .liste{display:grid;gap:14px;max-width:820px}
 .carte{background:#111c33;border:1px solid #1e293b;border-left:5px solid #f59e0b;
        border-radius:10px;padding:16px 18px}
 .carte.fait{border-left-color:#22c55e;opacity:.55}
 .quoi{font-size:20px;font-weight:600;margin:0 0 6px;color:#f8fafc}
 .sujet{font-size:15px;margin:0 0 12px;color:#94a3b8;line-height:1.5}
 .ligne{font-size:15px;margin:7px 0;color:#cbd5e1;line-height:1.45}
 .titrechoix{margin:18px 0 10px;font-size:12.5px;letter-spacing:.06em;
             text-transform:uppercase;color:#64748b}
 .choix{display:grid;gap:10px}
 .ch{display:flex;gap:14px;align-items:flex-start;background:#0d1729;
     border:1px solid #1e293b;border-radius:10px;padding:14px 16px;
     cursor:pointer;transition:border-color .12s,background .12s}
 .ch:hover{border-color:#38bdf8;background:#101d36}
 .ch.pris{border-color:#22c55e;background:#0e2318}
 .lettre{flex:0 0 auto;width:38px;height:38px;border-radius:50%;
         display:grid;place-items:center;font-size:18px;font-weight:700;
         background:#1e3a5f;color:#93c5fd}
 .ch.rouge .lettre{background:#4c1d24;color:#fca5a5}
 .ch.pris .lettre{background:#14532d;color:#86efac}
 .txtchoix{flex:1}
 .quoichoix{font-size:16.5px;font-weight:600;color:#f1f5f9;margin:0 0 3px}
 .suitechoix{font-size:14.5px;color:#94a3b8;line-height:1.45;margin:0}
 .definitif{display:inline-block;margin-left:8px;font-size:11.5px;
            background:#4c1d24;color:#fca5a5;border-radius:4px;
            padding:2px 7px;letter-spacing:.04em;vertical-align:middle}
 .reponse{margin-top:14px;font-size:15.5px;color:#22c55e;min-height:22px}
 .mot{width:100%;box-sizing:border-box;margin-top:12px;background:#0d1729;
      border:1px solid #1e293b;border-radius:9px;color:#e2e8f0;padding:11px 13px;
      font-family:inherit;font-size:15px;min-height:62px;resize:vertical}
 .mot:focus{outline:none;border-color:#38bdf8}
 .valider{margin-top:11px;background:#1d4ed8;color:#fff;border:0;
          border-radius:9px;padding:12px 22px;font-size:16px;font-weight:600;
          font-family:inherit;cursor:pointer}
 .valider:hover{background:#2563eb}
 .valider:disabled{background:#14532d;cursor:default}
 .etiq{display:inline-block;min-width:112px;color:#64748b;font-size:12.5px;
       text-transform:uppercase;letter-spacing:.04em}
 .rien{color:#22c55e;font-size:16px}
 footer{margin-top:30px;color:#475569;font-size:12.5px;max-width:820px}
</style></head><body>
<h1>Ce que j'attends de toi</h1>
<p class="quand">Les choses que je ne peux pas décider à ta place.
Mise à jour du __QUAND__.</p>
<div class="liste">__CARTES__</div>
<footer>Une carte = une chose qui a besoin de toi. Quand la carte disparaît, c'est réglé.</footer>
<script>
// DEUX GESTES. On choisit une lettre, on peut ecrire un mot, puis on valide.
// « Valider » envoie la reponse a la boite qui ecoute sur cette machine
// (port 8851). C'est elle qui la range dans mon carnet : Patrick n'a plus
// a revenir la retaper dans le terminal.
document.addEventListener("click", function (e) {
  var c = e.target.closest(".ch");
  if (c) {
    var boite = c.closest(".choix");
    boite.querySelectorAll(".ch").forEach(function (x) { x.classList.remove("pris"); });
    c.classList.add("pris");
    return;
  }
  var b = e.target.closest(".valider");
  if (!b) return;
  var carte = b.closest(".carte");
  var pris = carte.querySelector(".ch.pris");
  var dit = carte.querySelector(".reponse");
  if (!pris) { dit.style.color = "#fbbf24";
               dit.textContent = "Choisis d'abord une lettre."; return; }
  var envoi = {
    question: carte.querySelector(".quoi").textContent,
    choix: pris.dataset.lettre + " — " + pris.querySelector(".quoichoix").textContent,
    commentaire: (carte.querySelector(".mot") || {}).value || ""
  };
  b.disabled = true; b.textContent = "j'envoie...";
  fetch("/repondre", {method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(envoi)})
    .then(function (r) { return r.json(); })
    .then(function (r) {
      dit.style.color = "#22c55e";
      dit.textContent = r.dit + "  Tu peux fermer la page.";
      b.textContent = "reponse envoyee";
    })
    .catch(function () {
      dit.style.color = "#fbbf24";
      dit.textContent = "La boite aux reponses ne repond pas. Dis-le moi dans le chat.";
      b.disabled = false; b.textContent = "Valider ma reponse";
    });
});
</script>
</body></html>"""


def carte(d):
    e = html.escape
    l = ['<div class="carte">', '<p class="quoi">%s</p>' % e(d.get("quoi", "?"))]
    if d.get("sujet"):
        l.append('<p class="sujet">%s</p>' % e(d["sujet"]))
    if d.get("pourquoi"):
        l.append('<p class="ligne"><span class="etiq">Pourquoi toi</span>%s</p>'
                 % e(d["pourquoi"]))
    if d.get("qui"):
        l.append('<p class="ligne"><span class="etiq">Ce que tu fais</span>%s</p>'
                 % e(d["qui"]))
    if d.get("apres"):
        l.append('<p class="ligne"><span class="etiq">Et ensuite</span>%s</p>'
                 % e(d["apres"]))

    # LES CHOIX (17/09/2026). Patrick : « affiche-moi ce genre de question
    # toujours dans une page web avec visuel et choix ». Une question sans
    # ses choix oblige a relire le message pour savoir quoi repondre.
    # Chaque choix s ecrit :  le choix — ce qui se passe si tu le prends
    # Ajouter « (definitif) » a la fin rend la carte ROUGE : on ne peut pas
    # revenir en arriere. C est le seul cas ou la couleur change.
    choix = d.get("choix") or []
    if choix:
        l.append('<p class="titrechoix">Choisis</p><div class="choix">')
        for i, c in enumerate(choix):
            lettre = chr(ord("A") + i)
            texte = c.strip()
            rouge = ""
            marque = ""
            for mot in ("(definitif)", "(définitif)"):
                if texte.lower().endswith(mot):
                    texte = texte[: -len(mot)].strip()
                    rouge, marque = " rouge", '<span class="definitif">DEFINITIF</span>'
            tete, _, suite = texte.partition("—")
            if not suite:
                tete, _, suite = texte.partition(" - ")
            l.append(
                '<div class="ch%s" data-lettre="%s"><div class="lettre">%s</div>'
                '<div class="txtchoix"><p class="quoichoix">%s%s</p>'
                '<p class="suitechoix">%s</p></div></div>'
                % (rouge, lettre, lettre, e(tete.strip()), marque,
                   e(suite.strip() or "(pas d explication)")))
        l.append('</div>'
                 '<textarea class="mot" placeholder="Tu peux ajouter un mot '
                 "— ce n'est pas obligatoire\"></textarea>"
                 '<div><button class="valider">Valider ma reponse</button></div>'
                 '<p class="reponse"></p>')

    l.append("</div>")
    return "".join(l)


def reveiller_la_boite():
    """Met la boite aux reponses debout si elle dort. Deux fois de suite ne
    lance pas deux boites : la deuxieme voit le port pris et se tait."""
    import socket
    s = socket.socket()
    s.settimeout(0.4)
    try:
        s.connect(("127.0.0.1", 8851))
        return                      # elle ecoute deja
    except OSError:
        pass
    finally:
        s.close()
    subprocess.Popen(["python3", os.path.expanduser("~/outils/boite-aux-reponses.py")],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    time.sleep(0.8)


def montrer(demandes, ouvrir=True):
    os.makedirs(os.path.dirname(PAGE), exist_ok=True)
    if demandes:
        cartes = "".join(carte(d) for d in demandes)
    else:
        cartes = '<p class="rien">Rien ne t\'attend. Tout est de mon côté.</p>'
    page = (GABARIT.replace("__QUAND__", time.strftime("%d/%m/%Y à %H h %M"))
                   .replace("__CARTES__", cartes))
    open(PAGE, "w", encoding="utf-8").write(page)

    empreinte = hashlib.sha256(
        json.dumps(demandes, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    ancienne = ""
    try:
        ancienne = open(MARQUE, encoding="utf-8").read().strip()
    except Exception:
        pass
    if empreinte == ancienne:
        print("PAGE INCHANGEE (%d demande(s)) — on ne rouvre pas" % len(demandes))
        return
    open(MARQUE, "w", encoding="utf-8").write(empreinte)
    if os.path.exists(ETEINTE):
        print("PAGE ETEINTE par l interrupteur du cockpit "
              "(%d demande(s) ecrites quand meme)" % len(demandes))
        return
    if ouvrir and demandes:
        try:
            reveiller_la_boite()
            subprocess.Popen(["xdg-open", BOITE],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print("la page est écrite, mais je n'ai pas pu l'ouvrir : %s" % e)
    print("PAGE MONTREE (%d demande(s))" % len(demandes))


def main():
    if "--fichier" in sys.argv:
        chemin = sys.argv[sys.argv.index("--fichier") + 1]
        demandes = json.load(open(chemin, encoding="utf-8"))
    else:
        brut = sys.stdin.read().strip()
        demandes = json.loads(brut) if brut else []
    montrer(demandes, ouvrir="--sans-ouvrir" not in sys.argv)


if __name__ == "__main__":
    main()
