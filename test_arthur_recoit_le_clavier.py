#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ON DOIT POUVOIR ECRIRE A ARTHUR, ET NE JAMAIS PERDRE SON TEXTE.

DEUX FAUTES DITES PAR PATRICK LE 17/09/2026, mot pour mot :
  « impossible d ecrire a haichi, mon message est efface »
  « quand je clique sur envoyer c est efface, et ca met directement le / »

CE QUE CA VEUT DIRE, ET POURQUOI.

1. LE CLAVIER PART AILLEURS. Sa fenetre n a pas de barre de titre
   (set_decorated False) et ne figure pas dans la barre des taches
   (set_skip_taskbar_hint True). Beaucoup de bureaux ne donnent PAS le
   clavier a une fenetre pareille quand on clique dedans : les touches
   restent dans la fenetre d avant — le terminal — ou le caractere « / »
   ouvre le menu des commandes. C est exactement ce que Patrick voit.
   La parade : reclamer le clavier POUR DE VRAI au clic, pas seulement
   dire qu on l accepte.

2. SON TEXTE EST EFFACE AVANT D ETRE ENVOYE. L ancien code vidait la case
   tout de suite. Si l envoi rate, la phrase est perdue et il faut la
   retaper. On garde la phrase de cote, et on la REMET si ca rate.

CE QUE CETTE EPREUVE NE PROUVE PAS, ET QUI EST DIT ICI : elle lit le code.
Elle ne tape pas au clavier sur un vrai bureau. Seul Patrick, en tapant,
prouvera que le clavier arrive. L epreuve empeche la faute de revenir ; elle
ne remplace pas son essai.
"""
import os
import re
import sys

verts = 0
rouges = 0


def juge(ok, quoi):
    global verts, rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    if ok:
        verts += 1
    else:
        rouges += 1


F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "haichi_avatar.py")
code = open(F, encoding="utf-8").read() if os.path.exists(F) else ""

print("1) LA FENETRE RECLAME-T-ELLE LE CLAVIER POUR DE VRAI ?")
juge("set_accept_focus(True)" in code,
     "elle dit qu elle accepte le clavier")
juge(bool(re.search(r"set_type_hint", code)),
     "elle dit QUEL genre de fenetre elle est (sinon le bureau decide seul)")
juge(bool(re.search(r"\.present\(\)|present_with_time", code)),
     "elle se met devant quand on lui parle")
# On mesure le GESTE, pas l orthographe. Premier jet du 17/09/2026 :
# l epreuve exigeait « get_window().focus( » colle en un seul morceau, alors
# que le code met la fenetre dans une variable avant — ce qui est plus lisible.
# Une epreuve qui impose une facon d ecrire mesure le style, pas le resultat.
juge(bool(re.search(r"get_window\(\)", code)) and bool(re.search(r"\.focus\(Gdk\.CURRENT_TIME\)", code)),
     "elle reclame le clavier au bureau, explicitement")
# Meme correction : le geste est ecrit UNE fois dans une fonction, et cette
# fonction est branchee a TROIS endroits. C est mieux que de le recopier
# trois fois. On compte donc les BRANCHEMENTS, pas les copies.
juge("def reprendre_le_clavier" in code and "grab_focus()" in code
     and code.count("reprendre_le_clavier") >= 4,
     "la case prend le curseur — au demarrage, au clic dans la case, et au clic ailleurs")
juge(bool(re.search(r'connect\(\s*["\']button-press-event', code)),
     "un clic n importe ou dans la fenetre ramene le clavier")

print("2) SON TEXTE EST-IL A L ABRI ?")
juge(bool(re.search(r"_dernier_texte|remettre_le_texte|restaurer_le_texte", code)),
     "il garde la phrase de cote avant d envoyer")
avant_envoi = code.find('self.saisie.set_text("")')
lance = code.find("threading.Thread(target=self._demander")
juge(avant_envoi == -1 or (lance != -1 and avant_envoi > lance),
     "la case n est videe QU APRES que l envoi est parti")

print("")
print("  %d verts, %d rouges" % (verts, rouges))
sys.exit(0 if rouges == 0 else 1)
