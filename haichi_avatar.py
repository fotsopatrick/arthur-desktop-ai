# --- TATOUAGE CRYPTOGRAPHIQUE INAMOVIBLE ---
# Signature: nominomi
# B64_PROOF = "bm9taW5vbWktcGF0cmljay1jcmVhdGlvbi1zb3V2ZXJhaW5lLTIwMjY="
# HASH_PROOF = "af6152e817c761ccf74e9430053b2bd172802a3df02fd8a9bc8a13a415d40433"

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

# HAICHI / ARTHUR — Nom de code : nominomi
SIGNATURE_NOMINOMI = "nominomi"

COCKPIT = "http://127.0.0.1:8790"
LARGEUR, HAUTEUR = 300, 380   # retreci le 17/09/2026 :
# Patrick : « diminue aussi leur taille, ils sont trop grands ».
# 430x560 mangeait un quart de son ecran pour un compagnon.
ACCUEIL = "Salut Patrick ! Je suis Arthur. Pose-moi une question."

FEUILLE_DE_STYLE = b"""
window { background-color: transparent; }

/* la bulle : son propre fond, bien net */
.bulle {
  background-color: rgba(22, 16, 8, 0.95);
  border: 1.5px solid rgba(245, 158, 11, 0.78);
  border-radius: 18px;
  padding: 9px 11px;
}
.bulle > * { background-color: transparent; }
.bulle scrollbar { background: transparent; }
.pensee { color: #7dd3a0; font-size: 10.5px; font-family: monospace; }
.texte  { color: #f5e6cf; font-size: 13.5px; }

/* la barre du bas : son propre fond aussi */
.barre {
  background-color: rgba(22, 16, 8, 0.95);
  border: 1.5px solid rgba(56, 189, 248, 0.45);
  border-radius: 24px;
  padding: 5px 6px;
}
entry {
  background: transparent; border: none; box-shadow: none;
  color: #f5e6cf; font-size: 13px; caret-color: #f0a531;
}
entry selection { background-color: rgba(56,189,248,.45); }
.envoyer {
  background-image: none;
  background-color: #b45309;
  color: #ffffff; font-weight: bold; font-size: 12px;
  border-radius: 20px; border: none; padding: 6px 14px;
}
.envoyer:hover { background-color: #f0a531; }
.voix {
  background-image: none; background-color: rgba(30,41,59,.9);
  color: #94a3b8; border-radius: 50%; border: 1px solid rgba(148,163,184,.45);
  padding: 4px 8px; font-size: 13px;
}
.voix.active { color: #f0a531; border-color: #f0a531;
               background-color: rgba(56,189,248,.18); }

/* L'ICONE DISCRETE POUR ABAISSER EN ROND (Patrick, 18/09/2026) :
   un icone a cote d'eux, discret, pour les abaisser en cercle ou les
   rouvrir. */
.rabattre {
  background-image: none; background-color: rgba(15,23,42,.55);
  color: #cbd5e1; border-radius: 50%; border: 1px solid rgba(148,163,184,.5);
  padding: 0; font-size: 11px; min-width: 12px; min-height: 12px;
}
.rabattre:hover { background-color: rgba(56,189,248,.4); color: #ffffff; }
.dessin-rond {
  background-color: rgba(10,18,32,.96);
  border: 1.5px solid rgba(56,189,248,.7);
  border-radius: 50%; padding: 2px;
}
"""


class ZoneTexte(Gtk.ScrolledWindow):
    """La case d'Arthur, en PLUSIEURS LIGNES (corrige le 18/09/2026).

    Avant, c'etait un Gtk.Entry : une seule ligne. Une spec collee sur
    plusieurs lignes etait coupee, et chaque morceau partait comme une demande
    separee — d'ou des apps absurdes et « le lien du site manquait ». Ici la
    zone accepte tout le texte : Entree envoie, Maj+Entree fait un retour a la
    ligne. On garde get_text()/set_text() pour que le reste du programme ne
    change pas.
    """

    def __init__(self):
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_min_content_height(46)
        self.set_max_content_height(96)
        self.set_shadow_type(Gtk.ShadowType.IN)
        self.vue = Gtk.TextView()
        self.vue.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.vue.set_accepts_tab(False)
        self.add(self.vue)

    def get_text(self):
        b = self.vue.get_buffer()
        return b.get_text(b.get_start_iter(), b.get_end_iter(), False)

    def set_text(self, texte):
        self.vue.get_buffer().set_text(texte or "")

    def grab_focus(self):
        self.vue.grab_focus()

    def grab_focus_without_selecting(self):
        self.vue.grab_focus()


class Haichi(Gtk.Window):
    def __init__(self):
        # Le 17/09/2026 : cette ligne manquait. Sans elle, la fenetre n est
        # pas construite, et lui donner un titre plante aussitot :
        #   RuntimeError: object of type Haichi is not initialized
        # Arthur ne demarrait donc plus du tout, et son bouton « Rallumer »
        # disait « il revient » sans que rien ne revienne.
        super().__init__()
        self.set_title("Arthur-Avatar")
        self.set_keep_above(True)
        self.set_accept_focus(True)
        self.set_default_size(LARGEUR, HAUTEUR)
        self.set_decorated(False)          # aucune barre de titre
        self.set_keep_above(True)          # toujours devant
        self.set_skip_taskbar_hint(True)   # pas dans la barre des taches
        # LE CLAVIER. Faute du 17/09/2026, dite par Patrick : « impossible
        # d ecrire a haichi, mon message est efface, et ca met directement
        # le / ». Une fenetre SANS barre de titre et ABSENTE de la barre des
        # taches ne recoit pas le clavier quand on clique dedans : les
        # touches restent dans la fenetre d avant — le terminal — ou « / »
        # ouvre le menu des commandes.
        # « J accepte le clavier » ne suffit pas : il faut le RECLAMER.
        # On se declare fenetre de dialogue, ce qui dit au bureau qu on
        # attend une frappe.
        self.stick()                       # sur tous les bureaux
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
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
        self._colonne = colonne

        # la bulle, en haut
        self.boite_bulle = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.etiquette_pensee = Gtk.Label(xalign=0); self.etiquette_pensee.set_line_wrap(True)
        # la laisse : le texte revient a la ligne au bout de
        # 34 signes au lieu de s etaler (Patrick, 17/09/2026 :
        # « leur fenetre de chat trop large »)
        self.etiquette_pensee.set_max_width_chars(34)
        self.etiquette_pensee.set_width_chars(28)
        self.etiquette_pensee.get_style_context().add_class("pensee")
        self.etiquette_texte = Gtk.Label(xalign=0); self.etiquette_texte.set_line_wrap(True)
        # la laisse : le texte revient a la ligne au bout de
        # 34 signes au lieu de s etaler (Patrick, 17/09/2026 :
        # « leur fenetre de chat trop large »)
        self.etiquette_texte.set_max_width_chars(34)
        self.etiquette_texte.set_width_chars(28)
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
        rouleau.set_min_content_height(110)
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
        self.dessin.set_size_request(150, 166)
        # L'ICONE DISCRETE POUR ABAISSER EN ROND (Patrick, 18/09/2026).
        self.bouton_rabattre = Gtk.Button(label="▽")
        self.bouton_rabattre.get_style_context().add_class("rabattre")
        self.bouton_rabattre.set_tooltip_text("Abaisser en rond / rouvrir")
        self.bouton_rabattre.set_relief(Gtk.ReliefStyle.NONE)
        self.bouton_rabattre.connect("clicked", lambda *_: self._basculer_rabattu())
        self.rabattu = False
        surcouche = Gtk.Overlay()
        surcouche.add(self.dessin)
        surcouche.add_overlay(self.bouton_rabattre)
        self.bouton_rabattre.set_halign(Gtk.Align.END)
        self.bouton_rabattre.set_valign(Gtk.Align.START)
        self.bouton_rabattre.set_margin_top(4)
        self.bouton_rabattre.set_margin_end(4)
        colonne.pack_start(surcouche, False, False, 0)
        self._surcouche = surcouche
        self._demarrer_animation("arthur")
        self._ouvrir_la_boite("arthur")

        # la barre, en bas
        barre = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        barre.get_style_context().add_class("barre")
        self.bouton_voix = Gtk.Button(label="🔇")
        self.bouton_voix.get_style_context().add_class("voix")
        self.bouton_voix.connect("clicked", self._basculer_voix)
        # ---- LE BOUTON DE LA BOUCHE (Patrick, 17/09/2026) ----
        # Ses mots : « leur bouche qui parle, via un simple bouton, a
        # rajouter apres le volume ». Il est donc pose juste a cote, et il
        # marche pareil : un clic pour eteindre, un clic pour rallumer.
        # Le texte est ecrit en toutes lettres : cette machine n'a pas de
        # police pour les petits dessins, ils s'afficheraient en carres vides.
        # Un dessin, comme le volume juste a cote : une bouche ouverte quand
        # elle bouge, une bouche cousue quand elle est arretee. La machine a
        # bien la police qu'il faut (Noto Color Emoji, verifie le 17/09/2026).
        self.bouton_bouche = Gtk.Button(label="\U0001F444")
        self.bouton_bouche.get_style_context().add_class("voix")
        self.bouton_bouche.set_tooltip_text(
            "La bouche bouge quand il parle. Clic pour l'arreter.")
        self.bouton_bouche.get_style_context().add_class("active")
        self.bouton_bouche.connect("clicked", self._basculer_bouche)

        # LA MEME BARRE QUE BRAIGNAK (Patrick, 18/09/2026) : « identique ».
        # Meme champ, memes gestes, meme completion que Braignak.
        self.saisie = Gtk.Entry()
        self.saisie.set_placeholder_text("Pose ta question a Arthur…")
        self.saisie.connect("activate", lambda *_: self.envoyer())
        self.saisie.connect("button-press-event",
                            lambda *_: self.reprendre_le_clavier())
        self.connect("button-press-event",
                     lambda *_: self.reprendre_le_clavier())
        self.connect("map-event", lambda *_: self.reprendre_le_clavier())

        # --- Autosuggestion / Completion des Slash Commands (comme Braignak) ---
        completion = Gtk.EntryCompletion()
        model_completion = Gtk.ListStore(str)
        skills_connaissances = [
            "/actus-ia", "/agent-ssh", "/analyse", "/berzerk", "/carte-vivante",
            "/cast", "/circuits", "/concordance", "/courrier", "/delegation-actions",
            "/etat-serveurs", "/fusion-sessions", "/geole-infinie", "/imprimer",
            "/intrusions", "/kotodama", "/mes-outils", "/mode-twitch", "/navigateur",
            "/nommage", "/ovh", "/pilotage-ia", "/poids-disque", "/presentation",
            "/protection", "/proteger-une-page", "/rapport", "/recherche", "/restauration",
            "/sage", "/scan", "/snapshot", "/tempest-projection", "/tests-solides",
            "/video-narree", "/help"
        ]
        for sk in sorted(skills_connaissances):
            model_completion.append([sk])
        completion.set_model(model_completion)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_popup_completion(False)
        self.saisie.set_completion(completion)

        envoyer = Gtk.Button(label="ENVOYER")
        envoyer.get_style_context().add_class("envoyer")
        envoyer.connect("clicked", lambda *_: self.envoyer())
        barre.pack_start(self.bouton_voix, False, False, 0)
        barre.pack_start(self.bouton_bouche, False, False, 0)
        barre.pack_start(self.saisie, True, True, 0)
        barre.pack_start(envoyer, False, False, 0)
        colonne.pack_end(barre, False, False, 0)
        self._barre = barre

    # ---- l'abaisser en rond, ou le rouvrir ---------------------------------
    def _basculer_rabattu(self):
        """Abaisse l'avatar en un petit rond, ou le rouvre.

        Ne le 18/09/2026, demande de Patrick : un icone a cote d'eux,
        discret, pour les abaisser en cercle ou les rouvrir.
        """
        try:
            try:
                open("/tmp/avatar-rabattu.log", "a").write(
                    "arthur toggle -> rabattu=%s\n" % (not self.rabattu))
            except Exception:
                pass
            if not self.rabattu:
                self.rouleau.hide()
                self._barre.hide()
                # PETIT ROND (Patrick, 18/09/2026) : « la taille d'un double
                # d'un bouton connecte en ligne ». Avant 58/74, trop gros.
                self.dessin.set_size_request(24, 24)
                self.dessin.get_style_context().add_class("dessin-rond")
                # ON RETIRE LES MARGES : sans ca, la fenetre ne descend pas
                # sous (dessin + 20 px de marge) et reste « grosse ».
                for cote in ("start", "end", "top", "bottom"):
                    getattr(self._colonne, "set_margin_" + cote)(0)
                self.resize(28, 28)
                self.bouton_rabattre.set_label("△")
                self.bouton_rabattre.set_tooltip_text("Rouvrir")
                self.rabattu = True
            else:
                self.dessin.set_size_request(150, 166)
                self.dessin.get_style_context().remove_class("dessin-rond")
                for cote in ("start", "end", "top", "bottom"):
                    getattr(self._colonne, "set_margin_" + cote)(10)
                self.rouleau.show()
                self._barre.show()
                self.resize(LARGEUR, HAUTEUR)
                self.bouton_rabattre.set_label("▽")
                self.bouton_rabattre.set_tooltip_text("Abaisser en rond / rouvrir")
                self.rabattu = False
        except Exception:
            pass

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
    def reprendre_le_clavier(self, *_):
        """Ramene le clavier dans la case de saisie, pour de vrai."""
        try:
            self.present()
            fen = self.get_window()
            if fen is not None:
                fen.focus(Gdk.CURRENT_TIME)
        except Exception:
            pass
        try:
            self.saisie.grab_focus()
            self.saisie.grab_focus_without_selecting()
        except Exception:
            pass
        return False

    # ---- LE VISAGE QUI BOUGE (17/09/2026) ----
    # Avant, la fenetre affichait UNE SEULE image fixe. C'est pour ca que
    # Patrick n'a jamais vu Arthur bouger : ce n'etait pas une panne, c'etait
    # une photo dans un cadre. Maintenant on fait DEFILER plusieurs images,
    # comme un dessin anime.
    def _demarrer_animation(self, qui):
        import importlib.util
        import time
        chemin = os.path.expanduser("~/outils/visages-animes.py")
        if not os.path.exists(chemin):
            return                  # pas d'animation : la photo fixe reste
        s = importlib.util.spec_from_file_location("visages", chemin)
        self._visages = importlib.util.module_from_spec(s)
        s.loader.exec_module(self._visages)
        self._visages.fabriquer_les_images(qui)
        self._qui = qui
        # Deux graines differentes, sinon les deux clignent EN MEME TEMPS —
        # et deux visages qui clignent ensemble font tout de suite faux.
        self._graine = 1 if qui == "arthur" else 2
        self._debut = time.time()
        self._parle_jusqua = 0.0
        self._image_posee = None
        # Vingt battements par seconde : assez pour qu'un clin d'oeil se voie,
        # assez peu pour ne pas faire travailler la machine.
        GLib.timeout_add(50, self._battement)

    def _battement(self):
        import time
        if not hasattr(self, "_visages"):
            return False            # False = on arrete de battre
        t = time.time() - self._debut
        if not getattr(self, "_bouche_allumee", True):
            return True        # eteint : on ne touche a rien
        etat = "parle" if time.time() < self._parle_jusqua else "repos"
        nom = self._visages.image_du_moment(t, etat, self._graine)
        # On ne recharge l'image QUE si elle change vraiment. Sinon on ferait
        # travailler la machine vingt fois par seconde pour rien.
        if nom != self._image_posee:
            self.dessin.set_from_file(self._visages.chemin_image(self._qui, nom))
            self._image_posee = nom
        # LA RESPIRATION : le corps monte et descend de deux points a peine.
        # ON NE LA REDEMANDE QUE SI ELLE A VRAIMENT CHANGE.
        # Faute mesuree le 17/09/2026 : cette ligne etait jouee VINGT FOIS PAR
        # SECONDE. Chaque fois, la fenetre devait refaire tout son calcul de
        # placement. Resultat : Arthur mettait 16 a 21 SECONDES a repondre,
        # alors que son cerveau repond en 1 seconde. Patrick abandonnait avant
        # lui, et croyait qu'il ne savait pas repondre.
        haut = int(166 + self._visages.respiration(t))
        # NE PAS REDIMENSIONNER QUAND C'EST RABATTU (18/09/2026) : l'animation
        # remettait le dessin a 150 de large VINGT FOIS PAR SECONDE, ce qui
        # regonflait la taille minimale de la fenetre. Le rond restait gros.
        if not self.rabattu and haut != getattr(self, "_haut_pose", None):
            self.dessin.set_size_request(150, haut)
            self._haut_pose = haut
        return True                 # True = on recommence au prochain battement

    def parler_pendant(self, texte):
        """Fait bouger la bouche le temps de dire ce texte.

        On compte environ quatorze lettres par seconde — la vitesse d'une
        parole tranquille. Un texte deux fois plus long fait donc bouger la
        bouche deux fois plus longtemps.
        """
        import time
        if not hasattr(self, "_visages"):
            return
        self._parle_jusqua = time.time() + max(1.0, min(20.0,
                                                        len(texte or "") / 14.0))


    # ---- LE CARNET DE PAROLE (17/09/2026) ----
    # Patrick : « je viens d'ecrire aux deux, ils n'ont pas su repondre ».
    # Impossible de lui dire pourquoi : ils ne gardaient AUCUNE trace de ce
    # qu'on leur disait. Sans trace, on devine — et deviner est interdit ici.
    def _noter(self, sens, texte, detail=""):
        try:
            import importlib.util as _iu, os as _os
            if not hasattr(self, "_carnet"):
                ch = _os.path.expanduser("~/outils/paroles-des-agents.py")
                if not _os.path.exists(ch):
                    self._carnet = None
                else:
                    _s = _iu.spec_from_file_location("paroles", ch)
                    self._carnet = _iu.module_from_spec(_s)
                    _s.loader.exec_module(self._carnet)
            if self._carnet:
                self._carnet.noter("arthur", sens, texte, detail)
        except Exception:
            pass          # un carnet ne doit jamais faire taire un agent

    # ---- LA BOITE AUX LETTRES (Patrick, 17/09/2026) ----
    # Ses mots : « trouve un moyen d'ecrire dans leur chat devant moi ».
    # On regarde un fichier toutes les secondes. Si une phrase y a ete
    # deposee, on l'affiche dans le chat et on repond — exactement comme si
    # Patrick l'avait tapee. On ne lui prend JAMAIS le clavier : il l'a deja
    # subi ce matin, son texte partait dans le terminal.
    def _ouvrir_la_boite(self, qui):
        try:
            import importlib.util as _iu, os as _os
            ch = _os.path.expanduser("~/outils/boite-aux-lettres.py")
            if not _os.path.exists(ch):
                return
            _s = _iu.spec_from_file_location("boite", ch)
            self._boite = _iu.module_from_spec(_s)
            _s.loader.exec_module(self._boite)
            self._boite_qui = qui
            # On vide ce qui trainait AVANT d'ouvrir : sinon la fenetre
            # repondrait d'un coup a tout l'historique en redemarrant.
            self._boite.ramasser(qui)
            GLib.timeout_add(1000, self._relever_la_boite)
        except Exception:
            pass

    def _relever_la_boite(self):
        try:
            for phrase in self._boite.ramasser(self._boite_qui):
                self.saisie.set_text(phrase)
                self.envoyer()
        except Exception:
            pass
        return True          # True = on regarde encore dans une seconde

    def montrer_bulle(self, texte, pensee=""):
        self.parler_pendant(texte)
        self._noter("rendu", texte, pensee)
        import re
        import html
        self.etiquette_pensee.set_text(pensee[:160] if pensee else "")
        self.etiquette_pensee.set_visible(bool(pensee))
        
        # Echappement XML/HTML pour Pango
        texte_clean = html.escape(texte)
        
        # Transformation des URLs en liens cliquables Pango HTML
        url_pattern = re.compile(r'(https?://[^\s]+|file://[^\s]+)')
        texte_markup = url_pattern.sub(r'<a href="\1"><span foreground="#2563eb" underline="single">\1</span></a>', texte_clean)
        
        try:
            self.etiquette_texte.set_use_markup(True)
            self.etiquette_texte.set_markup(texte_markup)
        except Exception:
            self.etiquette_texte.set_text(texte)

        self.show_all()
        try:
            self.rouleau.get_vadjustment().set_value(0)   # on remonte en haut
        except Exception:
            pass
        if not pensee:
            self.etiquette_pensee.hide()

    def _touche_saisie(self, widget, event):
        """Entree ENVOIE ; Maj+Entree fait un retour a la ligne.

        Corrige le 18/09/2026 : sans ca, une spec multi-lignes ne pouvait pas
        etre saisie, et partait en morceaux.
        """
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if event.state & Gdk.ModifierType.SHIFT_MASK:
                return False          # Maj+Entree : on laisse passer (nouvelle ligne)
            self.envoyer()
            return True               # Entree seul : on envoie
        return False

    def envoyer(self):
        question = self.saisie.get_text().strip()
        if not question:
            # Case vide : on ne perd rien, mais on reprend le clavier — c est
            # souvent qu il a tape ailleurs sans le savoir.
            self.reprendre_le_clavier()
            return
        # SA PHRASE EST MISE DE COTE AVANT TOUT. Faute du 17/09/2026 :
        # l ancien code vidait la case tout de suite. Si l envoi ratait, la
        # phrase etait perdue et il fallait la retaper.
        self._dernier_texte = question
        self.montrer_bulle("Haichi réfléchit…", "")
        try:
            threading.Thread(target=self._demander,
                             args=(question,), daemon=True).start()
        except Exception as ex:
            # L envoi n est meme pas parti : on lui rend sa phrase.
            self.saisie.set_text(self._dernier_texte)
            self.montrer_bulle("Je n ai pas pu partir chercher : "
                               + str(ex)[:70], "")
            self.reprendre_le_clavier()
            return
        # L envoi EST parti : maintenant seulement on vide la case de façon stricte.
        self.saisie.set_text("")
        # Empêche tout signal/complétion résiduelle de remettre "/" dans le champ
        GLib.idle_add(lambda: self.saisie.set_text(""))
        self.reprendre_le_clavier()

    # ------------------------------------------------------------------
    # COMMENT ARTHUR CHERCHE — refait le 17/09/2026, apres trois fautes.
    #
    # 1. IL COUPAIT LA ROUTE. Son premier serveur (porte 8796) repond
    #    {"erreur": "inconnu"} : il REPOND, il ne plante pas. L ancien code
    #    ne se rabattait sur le cockpit que si ca PLANTAIT. Un « je ne sais
    #    pas » poli n est pas une panne — donc le cockpit, qui avait la
    #    reponse, n etait jamais appele. Mesure : le cockpit rend
    #    « Oulan-Bator » en 1,5 seconde pour la meme question.
    #    C est la lecon connue : un code 200 ne veut pas dire que c est ouvert.
    #
    # 2. IL RESTAIT MUET pendant toute la recherche. Patrick : « il doit dire
    #    je cherche et je te reponds ». Quatre secondes de silence font croire
    #    que c est casse.
    #
    # 3. IL NE MONTRAIT PAS SON TRAVAIL. Maintenant il dit quel etage a
    #    repondu, combien de temps, et ce qu il a lu.
    # ------------------------------------------------------------------

    # Ce qui n est PAS une vraie reponse. Un serveur peut repondre poliment
    # sans rien dire : on continue alors vers l etage suivant.
    RIEN_DE_VRAI = ("", "(rien)", "inconnu", "je ne sais pas", "erreur")

    def _est_une_vraie_reponse(self, d):
        """Rend le texte si la reponse en est une, sinon None.

        On refuse : une fiche qui porte « erreur », un texte vide, et les
        formules creuses. Tout le reste passe."""
        if not isinstance(d, dict):
            return None
        if d.get("erreur"):
            return None
        texte = (d.get("answer") or d.get("reponse") or d.get("raw_output") or "").strip()
        if not texte:
            return None
        if texte.strip(" .!").lower() in self.RIEN_DE_VRAI:
            return None
        return texte

    def _demander(self, question):
        import time
        self._noter("recu", question)
        etages = []          # ce qu il a essaye, dans l ordre, avec le temps

        # ---- ETAGE 1 : le serveur d action, tout pres et tres rapide -----
        depart = time.time()
        try:
            corps = json.dumps({"prompt": question, "action": "parler"}).encode("utf-8")
            r = urllib.request.Request("http://127.0.0.1:8796/api/arthur-action",
                                       data=corps,
                                       headers={"Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(r, timeout=10).read().decode("utf-8"))
        except Exception as ex:
            d = {"erreur": str(ex)[:60]}
        ms = int((time.time() - depart) * 1000)
        texte = self._est_une_vraie_reponse(d)
        etages.append(("mes outils", ms, "trouve" if texte else "rien"))
        if texte:
            pensee = (d.get("thought") or d.get("source") or "mes outils")[:150]
            GLib.idle_add(self.montrer_bulle, texte,
                          self._raconter_comment(etages, pensee))
            self._peut_etre_a_voix_haute(texte)
            return

        # ---- IL LE DIT AVANT DE MONTER ----------------------------------
        # La montee prend entre 1,5 et 11 secondes (mesure). On ne laisse
        # jamais Patrick devant un silence : il saurait pas si c est casse.
        GLib.idle_add(self.montrer_bulle,
                      "Je cherche, un instant — je te reponds.",
                      "mes outils n ont rien - je monte au grand modele")

        # ---- ETAGE 2 : le cockpit, qui monte jusqu a Nemotron ------------
        depart = time.time()
        try:
            corps = json.dumps({"prompt": question}).encode("utf-8")
            r = urllib.request.Request(COCKPIT + "/api/nano-search", data=corps,
                                       headers={"Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(r, timeout=120).read().decode("utf-8"))
        except Exception as ex:
            d = {"erreur": str(ex)[:70]}
        ms = int((time.time() - depart) * 1000)
        texte = self._est_une_vraie_reponse(d)
        etages.append(("le grand modele", ms, "trouve" if texte else "rien"))

        if texte:
            pensee = (d.get("thought") or d.get("source") or "")[:150]
            GLib.idle_add(self.montrer_bulle, texte,
                          self._raconter_comment(etages, pensee))
            self._peut_etre_a_voix_haute(texte)
            return

        # ---- ETAGE 3 : L AVEU. Jamais une invention. --------------------
        # Si les deux etages n ont rien de vrai, Arthur le DIT, et il dit
        # aussi ce qu il a essaye. Un aveu qui explique vaut mieux qu un
        # aveu nu.
        raison = (d.get("erreur") or "les deux etages n ont rien trouve")
        aveu = "Je ne sais pas, et je ne vais pas inventer. " + str(raison)[:90]
        GLib.idle_add(self.montrer_bulle, aveu, self._raconter_comment(etages, ""))
        self._peut_etre_a_voix_haute(aveu)

    def _raconter_comment(self, etages, pensee):
        """Ce qu il a FAIT, et COMMENT — pas seulement le resultat.

        Demande de Patrick le 17/09/2026 : « son ecran doit montrer ce qu il
        a fait et comment ». On rend une ligne courte, lisible d un coup."""
        bouts = ["%s %d ms %s" % (nom, ms, resultat) for nom, ms, resultat in etages]
        total = sum(ms for _, ms, _ in etages)
        ligne = " -> ".join(bouts) + "  (en tout %d ms)" % total
        return (pensee + " | " + ligne) if pensee else ligne

    def _peut_etre_a_voix_haute(self, texte):
        if getattr(self, "voix_allumee", False):
            threading.Thread(target=self._dire_a_voix_haute,
                             args=(texte,), daemon=True).start()

    def _dire_a_voix_haute(self, texte):
        try:
            corps = json.dumps({"texte": texte[:1200], "jouer": True}).encode("utf-8")
            r = urllib.request.Request(COCKPIT + "/api/voix", data=corps,
                                       headers={"Content-Type": "application/json"})
            urllib.request.urlopen(r, timeout=90).read()
        except Exception:
            pass

    def _basculer_bouche(self, *_):
        """Allume ou eteint le mouvement de la bouche et des yeux.

        Eteint, le dessin revient a son image d'origine, exactement comme
        avant : rien ne bouge, rien n'est perdu.
        """
        self._bouche_allumee = not getattr(self, "_bouche_allumee", True)
        self.bouton_bouche.set_label(
            "\U0001F444" if self._bouche_allumee else "\U0001F910")
        ctx = self.bouton_bouche.get_style_context()
        (ctx.add_class if self._bouche_allumee else ctx.remove_class)("active")
        if not self._bouche_allumee:
            self._image_posee = None
            try:
                import os as _os
                self.dessin.set_from_file(self._visages.ORIGINE[self._qui])
                self.dessin.set_size_request(150, 166)
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
