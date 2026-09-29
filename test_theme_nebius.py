#!/usr/bin/env python3
"""Preuve que le theme Nebius marche VRAIMENT, pas qu'il repond 200.

Chaque epreuve fait ce que Patrick ferait : elle CLIQUE un bouton, elle
CHOISIT dans un menu, elle POSE une clef — puis elle regarde ce qui a
change a l'ecran. Un serveur qui repond « 200 » ne prouve rien.

Lancer :  python3 ~/haichi/test_theme_nebius.py
"""
import importlib.util as _u
import json
import os
import sys
import urllib.request

_s = _u.spec_from_file_location("pilote", os.path.expanduser("~/outils/pilote-page.py"))
_p = _u.module_from_spec(_s); _s.loader.exec_module(_p)
Page = _p.Page

sys.path.insert(0, os.path.expanduser("~/haichi"))
import nemotron_nebius

def _chrome_est_pilotable():
    """Ce test CLIQUE dans le vrai Chrome. Sans sa porte de pilotage ouverte
    (le port 9222), il ne peut pas tourner. Mieux vaut le dire clairement
    que s'ecrouler : un test qui s'ecroule ressemble a un test qui echoue."""
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=3)
        return True
    except Exception:
        return False


if not _chrome_est_pilotable():
    print()
    print("  CE TEST NE PEUT PAS TOURNER — et ce n'est PAS un echec du code.")
    print()
    print("  Il a besoin de cliquer dans le vrai Chrome. Pour cela, Chrome doit")
    print("  etre lance avec sa porte de pilotage ouverte (le port 9222).")
    print("  En ce moment, personne ne repond sur cette porte.")
    print()
    print("  Pour la rouvrir, fermer Chrome puis le relancer ainsi :")
    print("     google-chrome --remote-debugging-port=9222 &")
    print()
    print("  Preuve que ca a marche : la commande suivante doit rendre un nom")
    print("  de navigateur, et pas une erreur :")
    print("     curl -s http://127.0.0.1:9222/json/version")
    print()
    sys.exit(2)          # 2 = impossible a lancer, different de 1 = echec


ARTHUR = "http://127.0.0.1:8790/haichi-flottant"
COCKPIT = "http://127.0.0.1:8790/"
CLEF = "http://127.0.0.1:8796"
COFFRE = os.path.expanduser("~/.secrets/cle-nebius.txt")

verts, rouges = [], []


def juge(titre, attendu, obtenu):
    bon = (attendu == obtenu) if not callable(attendu) else attendu(obtenu)
    (verts if bon else rouges).append(titre)
    print("  %s %-58s %s" % ("OK  " if bon else "RATE", titre, obtenu))


def citron(valeur):
    """Y a-t-il du citron Nebius la-dedans ?

    La valeur peut arriver de trois facons : « #e0ff4f », « rgb(224, 255, 79) »,
    ou un degrade entier qui contient plusieurs couleurs. On regarde TOUTES
    les couleurs trouvees, et il suffit qu'une seule soit du citron.
    Un citron, c'est beaucoup de rouge, encore plus de vert, peu de bleu.
    """
    import re
    texte = str(valeur)
    couleurs = []
    for h in re.findall(r"#([0-9a-fA-F]{6})", texte):
        couleurs.append((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)))
    for r, v, b in re.findall(r"rgba?\(\s*(\d+)\D+(\d+)\D+(\d+)", texte):
        couleurs.append((int(r), int(v), int(b)))
    for r, v, b in couleurs:
        if r > 150 and v > 200 and v > b + 60 and v >= r:
            return True
    return False


# ── 1. ARTHUR : on CLIQUE le bouton palette ───────────────────────────────
print("\n1) ARTHUR — je clique vraiment sur son bouton palette")
p = Page(ARTHUR + "?theme=nuit")
try:
    p.demander("localStorage.removeItem('arthur-decor'); 1")
    p.recharger()
    avant_decor = p.demander("document.documentElement.getAttribute('data-theme')")
    avant_corps = p.demander(
        "getComputedStyle(document.querySelector('.haichi-core')).backgroundImage")
    juge("au depart, Arthur est sous la nuit etoilee", "nuit", avant_decor)
    juge("au depart, Arthur n'est PAS citron", False, citron(avant_corps))

    p.demander("document.getElementById('btn-decor').click(); 1")
    apres_decor = p.demander("document.documentElement.getAttribute('data-theme')")
    apres_corps = p.demander(
        "getComputedStyle(document.querySelector('.haichi-core')).backgroundImage")
    juge("apres UN clic, le decor est nebius", "nebius", apres_decor)
    juge("apres UN clic, le corps d'Arthur est citron", True,
         citron(apres_corps))

    bouton = p.demander(
        "getComputedStyle(document.querySelector('.btn-send')).backgroundImage")
    juge("le bouton ENVOYER est citron lui aussi", True,
         citron(bouton))

    etoile = p.demander("(function(){var c=document.getElementById('etoiles');"
                        "return c && c.width>0 ? 'toile peinte' : 'toile vide';})()")
    juge("le ciel est bien repeint", "toile peinte", etoile)

    garde = p.demander("localStorage.getItem('arthur-decor')")
    juge("le choix est garde pour la prochaine fois", "nebius", garde)

    p.demander("history.replaceState(null,'',location.pathname); 1")
    p.recharger()
    juge("apres rechargement, Arthur est encore en nebius", "nebius",
         p.demander("document.documentElement.getAttribute('data-theme')"))

    p.demander("document.getElementById('btn-decor').click(); 1")
    juge("un clic de plus et il revient a la nuit", "nuit",
         p.demander("document.documentElement.getAttribute('data-theme')"))
finally:
    p.demander("localStorage.removeItem('arthur-decor'); 1")
    p.fermer()


# ── 2. COCKPIT : on CHOISIT dans le vrai menu ─────────────────────────────
print("\n2) COCKPIT — je choisis Nebius dans le vrai menu deroulant")
p = Page(COCKPIT, attente=4)
try:
    p.demander("localStorage.removeItem('cockpit_theme'); 1")
    p.recharger(4)
    choix = p.demander(
        "Array.from(document.getElementById('select-theme').options)"
        ".map(function(o){return o.value;}).join(',')")
    juge("les 7 decors sont proposes", 7, len(choix.split(",")))
    juge("nebius est dans la liste", True, "nebius" in choix)

    p.demander("var s=document.getElementById('select-theme');"
               "s.value='nebius'; s.dispatchEvent(new Event('change')); 1")
    juge("apres le choix, le cockpit est en nebius", "nebius",
         p.demander("document.documentElement.getAttribute('data-theme')"))
    juge("son accent est devenu citron", True,
         citron(p.demander(
             "getComputedStyle(document.documentElement)"
             ".getPropertyValue('--cyan').trim()")))

    p.recharger(4)
    juge("apres rechargement, le cockpit garde nebius", "nebius",
         p.demander("document.documentElement.getAttribute('data-theme')"))
    juge("le menu affiche bien Nebius, il ne ment pas", "nebius",
         p.demander("document.getElementById('select-theme').value"))

    juge("les deux nouveaux boutons sont dans la page", True,
         p.demander("document.body.innerText.indexOf('La clef de Nebius')>=0 && "
                    "document.body.innerText.indexOf('couleurs Nebius')>=0"))
finally:
    p.demander("localStorage.removeItem('cockpit_theme'); 1")
    p.fermer()


# ── 3. LA CLEF : on la POSE par la page, et on appelle VRAIMENT Nebius ─────
print("\n3) LA CLEF — je la pose par la page, puis j'appelle vraiment Nebius")
avait = open(COFFRE).read() if os.path.exists(COFFRE) else None
try:
    def poste(chemin, corps=None):
        d = urllib.request.Request(
            CLEF + chemin, method="POST",
            data=json.dumps(corps or {}).encode(),
            headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(d, timeout=90).read())

    fausse = "neb_" + "z" * 40
    r = poste("/ranger", {"cle": fausse})
    juge("la page accepte une clef de bonne forme", True, r["ok"])
    juge("le fichier existe vraiment sur le disque", True, os.path.exists(COFFRE))
    juge("seul Patrick peut le lire (droits 600)", "600",
         oct(os.stat(COFFRE).st_mode)[-3:])

    os.environ.pop("NEBIUS_API_KEY", None)
    juge("Arthur retrouve la clef tout seul", fausse,
         nemotron_nebius.cle_du_moment())

    reponse = poste("/essayer")
    juge("l'appel part VRAIMENT chez Nebius et revient",
         lambda t: ("401" in str(t) or "403" in str(t) or "nvalid" in str(t)
                    or "uthenticat" in str(t) or reponse.get("ok")),
         reponse["texte"][:120])

    e = poste("/effacer")
    juge("la page sait effacer la clef", False, os.path.exists(COFFRE))
finally:
    if avait is not None:
        open(COFFRE, "w").write(avait)
        os.chmod(COFFRE, 0o600)

print("\n" + "=" * 68)
print("  %d epreuves passees, %d ratees" % (len(verts), len(rouges)))
for r in rouges:
    print("   RATE : " + r)
print("=" * 68)
sys.exit(1 if rouges else 0)
