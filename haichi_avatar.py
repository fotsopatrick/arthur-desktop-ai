#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HAICHI — le compagnon pose sur le bureau.

Pourquoi ce programme existe, et pas une page web dans Chrome :
Chrome ne sait pas rendre son fond transparent sur cette machine — il le peint
en BLANC (essai du 15/09/2026). Et rendre toute la fenetre translucide par le
bureau rendait AUSSI Haichi et sa barre pales, ce que Patrick a refuse.
Ici, le fond est vraiment vide : on voit le bureau derriere. Haichi, sa bulle
et sa barre restent nets, parce qu ils ont leur propre fond.

Il parle au cockpit local (port 8790), le meme cerveau que la page web.
"""
import json, math, threading, urllib.request, subprocess, os, sys
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

COCKPIT = "http://127.0.0.1:8790"
LARGEUR, HAUTEUR = 430, 560
ACCUEIL = "Salut Patrick ! Je suis Arthur. Pose-moi une question."

FEUILLE_DE_STYLE = b"""
window { background-color: transparent; }

/* la bulle : son propre fond, bien net */
.bulle {
  background-color: rgba(10, 16, 28, 0.94);
  border: 1.5px solid rgba(56, 189, 248, 0.75);
  border-radius: 18px;
  padding: 14px 16px;
}
.bulle > * { background-color: transparent; }
.bulle scrollbar { background: transparent; }
.pensee { color: #f59e0b; font-size: 10.5px; font-family: monospace; }
.texte  { color: #e6f1fb; font-size: 13.5px; }

/* la barre du bas : son propre fond aussi */
.barre {
  background-color: rgba(10, 16, 28, 0.94);
  border: 1.5px solid rgba(56, 189, 248, 0.45);
  border-radius: 24px;
  padding: 5px 6px;
}
entry {
  background: transparent; border: none; box-shadow: none;
  color: #e6f1fb; font-size: 13px; caret-color: #38bdf8;
}
entry selection { background-color: rgba(56,189,248,.45); }
.envoyer {
  background-image: none;
  background-color: #0ea5e9;
  color: #ffffff; font-weight: bold; font-size: 12px;
  border-radius: 20px; border: none; padding: 6px 14px;
}
.envoyer:hover { background-color: #38bdf8; }
.voix {
  background-image: none; background-color: rgba(30,41,59,.9);
  color: #94a3b8; border-radius: 50%; border: 1px solid rgba(148,163,184,.45);
  padding: 4px 8px; font-size: 13px;
}
.voix.active { color: #38bdf8; border-color: #38bdf8;
               background-color: rgba(56,189,248,.18); }
"""


class Haichi(Gtk.Window):
    def __init__(self):
        super().__init__(title="Arthur-Avatar")
        self.set_default_size(LARGEUR, HAUTEUR)
        self.set_decorated(False)          # aucune barre de titre
        self.set_keep_above(True)          # toujours devant
        self.set_skip_taskbar_hint(True)   # pas dans la barre des taches
        self.stick()                       # sur tous les bureaux
        self.set_app_paintable(True)

        # le fond vraiment vide : on voit le bureau derriere
        ecran = self.get_screen()
        visuel = ecran.get_rgba_visual()
        if visuel:
            self.set_visual(visuel)
        # Pas besoin de peindre le fond nous-memes : le visuel transparent
        # ci-dessus suffit, et la bibliotheque de dessin n est pas installee.
        self.connect("destroy", Gtk.main_quit)

        style = Gtk.CssProvider(); style.load_from_data(FEUILLE_DE_STYLE)
        Gtk.StyleContext.add_provider_for_screen(
            ecran, style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.voix_allumee = False
        self._monter_le_corps()
        self._deplacable()
        self.montrer_bulle(ACCUEIL, "")

    # ---- le corps ----------------------------------------------------------
    def _monter_le_corps(self):
        colonne = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        colonne.set_margin_start(10); colonne.set_margin_end(10)
        colonne.set_margin_top(10);   colonne.set_margin_bottom(10)
        self.add(colonne)

        # la bulle, en haut
        self.boite_bulle = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.etiquette_pensee = Gtk.Label(xalign=0); self.etiquette_pensee.set_line_wrap(True)
        self.etiquette_pensee.get_style_context().add_class("pensee")
        self.etiquette_texte = Gtk.Label(xalign=0); self.etiquette_texte.set_line_wrap(True)
        self.etiquette_texte.set_selectable(True)      # pour pouvoir copier
        self.etiquette_texte.get_style_context().add_class("texte")
        self.boite_bulle.pack_start(self.etiquette_pensee, False, False, 0)
        self.boite_bulle.pack_start(self.etiquette_texte, False, False, 0)

        # Le cadre qui defile porte le fond de la bulle. Ne le 15/09/2026 :
        # une reponse longue debordait et se faisait couper par le bas.
        rouleau = Gtk.ScrolledWindow()
        rouleau.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        # Hauteur FIXE de la bulle. Deux essais rates le 15/09/2026 : en
        # laissant la bulle prendre sa taille naturelle, le texte long etait
        # coupe par le bas. Ici elle garde toujours la meme place, et le texte
        # qui depasse defile a l interieur.
        rouleau.set_min_content_height(185)
        rouleau.set_max_content_height(185)
        rouleau.set_propagate_natural_height(False)
        rouleau.get_style_context().add_class("bulle")
        rouleau.add(self.boite_bulle)
        self.rouleau = rouleau
        colonne.pack_start(rouleau, False, False, 0)

        # Haichi lui-meme, au milieu.
        # On affiche une IMAGE, pas un dessin en direct : la bibliotheque de
        # dessin (cairo) n est pas installee sur cette machine, et le dessin
        # echouait en silence — Haichi n apparaissait pas (15/09/2026).
        chemin_image = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "haichi.png")
        # L image vient du VRAI Hachi de la vitrine : le shiba roux avec son
        # casque bleu, assis sur son ballon de football americain. Elle a ete
        # tiree du dessin de la vitrine (hachi-teleport.js), pas redessinee.
        if not os.path.exists(chemin_image):
            import fabriquer_haichi_png
            fabriquer_haichi_png.fabriquer(chemin_image)
        self.dessin = Gtk.Image.new_from_file(chemin_image)
        self.dessin.set_size_request(230, 255)
        colonne.pack_start(self.dessin, False, False, 0)

        # la barre, en bas
        barre = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        barre.get_style_context().add_class("barre")
        self.bouton_voix = Gtk.Button(label="🔇")
        self.bouton_voix.get_style_context().add_class("voix")
        self.bouton_voix.connect("clicked", self._basculer_voix)
        self.saisie = Gtk.Entry()
        self.saisie.set_placeholder_text("Pose ta question à Arthur…")
        self.saisie.connect("activate", lambda *_: self.envoyer())
        envoyer = Gtk.Button(label="ENVOYER")
        envoyer.get_style_context().add_class("envoyer")
        envoyer.connect("clicked", lambda *_: self.envoyer())
        barre.pack_start(self.bouton_voix, False, False, 0)
        barre.pack_start(self.saisie, True, True, 0)
        barre.pack_start(envoyer, False, False, 0)
        colonne.pack_end(barre, False, False, 0)

    # ---- on peut l attraper et le deplacer ---------------------------------
    def _deplacable(self):
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        def attraper(w, e):
            if e.button == 1:
                self.begin_move_drag(e.button, int(e.x_root), int(e.y_root), e.time)
            return False
        self.connect("button-press-event", attraper)
        # l image ne recoit pas les clics toute seule : on la met dans une
        # boite qui, elle, les recoit.
        try:
            self.dessin.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            self.dessin.connect("button-press-event", attraper)
        except Exception:
            pass

    # ---- parler au cockpit -------------------------------------------------
    def montrer_bulle(self, texte, pensee=""):
        self.etiquette_pensee.set_text(pensee[:160] if pensee else "")
        self.etiquette_pensee.set_visible(bool(pensee))
        self.etiquette_texte.set_text(texte)
        self.show_all()
        try:
            self.rouleau.get_vadjustment().set_value(0)   # on remonte en haut
        except Exception:
            pass
        if not pensee:
            self.etiquette_pensee.hide()

    def envoyer(self):
        question = self.saisie.get_text().strip()
        if not question:
            return
        self.saisie.set_text("")
        self.montrer_bulle("Haichi réfléchit…", "")
        threading.Thread(target=self._demander, args=(question,), daemon=True).start()

    def _demander(self, question):
        try:
            corps = json.dumps({"prompt": question}).encode("utf-8")
            r = urllib.request.Request(COCKPIT + "/api/nano-search", data=corps,
                                       headers={"Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(r, timeout=120).read().decode("utf-8"))
            texte = d.get("answer", "") or "(rien)"
            pensee = (d.get("thought") or "")[:150]
            source = d.get("source", "")
            if source:
                pensee = f"[{source}] " + pensee
        except Exception as e:
            texte, pensee = "Je n arrive pas à joindre le cockpit : " + str(e)[:70], ""
        GLib.idle_add(self.montrer_bulle, texte, pensee)
        if self.voix_allumee:
            threading.Thread(target=self._dire_a_voix_haute, args=(texte,), daemon=True).start()

    def _dire_a_voix_haute(self, texte):
        try:
            corps = json.dumps({"texte": texte[:1200], "jouer": True}).encode("utf-8")
            r = urllib.request.Request(COCKPIT + "/api/voix", data=corps,
                                       headers={"Content-Type": "application/json"})
            urllib.request.urlopen(r, timeout=90).read()
        except Exception:
            pass

    def _basculer_voix(self, _):
        self.voix_allumee = not self.voix_allumee
        self.bouton_voix.set_label("🔊" if self.voix_allumee else "🔇")
        ctx = self.bouton_voix.get_style_context()
        (ctx.add_class if self.voix_allumee else ctx.remove_class)("active")
        if self.voix_allumee:
            threading.Thread(target=self._dire_a_voix_haute,
                             args=("Ma voix est allumée.",), daemon=True).start()
        else:
            try:
                urllib.request.urlopen(
                    urllib.request.Request(COCKPIT + "/api/voix-stop", data=b"{}"),
                    timeout=5)
            except Exception:
                pass


if __name__ == "__main__":
    # On peut lui donner une question de depart :
    #   python3 haichi_avatar.py "qui est Victor"
    # Ca sert a prouver qu il repond VRAIMENT dans sa fenetre, pas seulement
    # qu un serveur rend 200.
    question_de_depart = " ".join(sys.argv[1:]).strip()
    # sur l ecran de DROITE (celui qui commence a 1920), en bas
    X = 1920 + 1920 - LARGEUR - 40
    Y = 1080 - HAUTEUR - 90
    h = Haichi()
    h.move(X, Y)
    h.show_all()
    h.etiquette_pensee.hide()
    if question_de_depart:
        h.saisie.set_text(question_de_depart)
        GLib.timeout_add(900, lambda: (h.envoyer(), False)[1])
    Gtk.main()
