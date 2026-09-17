#!/usr/bin/env python3
# GARDE-FOU (Stop hook) — une session ne DONNE PAS une commande à taper à Patrick.
# Elle doit AJOUTER UN BOUTON à sa page des tâches (ajouter-tache.py), sinon ce
# garde refuse la fin du tour. Demande de Patrick (06/09/2026) : « plus de
# commandes à taper — des boutons verts ».
#
# Contrat Stop hook : imprimer {"decision":"block","reason":...} = bloquer.
import os
import json, sys, os, re, unicodedata, time

# LA MAISON EST FIXE (06/09/2026). Une session peut tourner sous root :
# expanduser("~") rendait alors /root, et ce garde ne trouvait plus ses
# fichiers — il repondait "aucun code defini" alors que le code etait pose.
# Un garde qui ne trouve pas ses fichiers ne garde rien.
MAISON = os.path.expanduser("~orel")


# DEUX CARNETS, PAS UN (trouve le 16/09/2026).
# Ce garde ne regardait que ~/taches/taches.json. Mais ajouter-tache.py, le
# programme qui POSE les boutons, ecrit dans ~/cockpit-generique/taches.json.
# Le garde ne voyait donc jamais les boutons poses. Il regarde les deux.
TOUS_LES_CARNETS = [
    os.path.join(MAISON, "taches/taches.json"),
    os.path.join(MAISON, "cockpit-generique/taches.json"),
    os.path.join(MAISON, "briques/page-actions/actions.json"),  # la brique reutilisable
]
TACHES = TOUS_LES_CARNETS[0]

def sansaccents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn').lower()

def dernier_message_assistant(chemin):
    txt = ""
    try:
        for ligne in open(chemin, encoding="utf-8", errors="replace"):
            try: d = json.loads(ligne)
            except Exception: continue
            if d.get("type") != "assistant": continue
            c = (d.get("message") or {}).get("content")
            if isinstance(c, list):
                t = " ".join(x.get("text", "") for x in c
                             if isinstance(x, dict) and x.get("type") == "text")
            else:
                t = str(c or "")
            if t.strip(): txt = t
    except Exception:
        return ""
    return txt

# Signes clairs que je demande à Patrick de TAPER/LANCER une commande lui-même.
COMMANDE_A_TAPER = [
    r'```[^\n]*\n\s*!\s',                    # un bloc de code avec le prefixe "! " (lancer dans la session)
    r'\bcolle (ceci|ca|cette commande|la commande)\b',
    r'\btape (ceci|ca|cette commande|la commande)\b',
    r'\blance (cette commande|la commande)\b',
    r'\bexecute (cette commande|la commande)\b',
    r'\bdans ton terminal\b',
]

def bouton_ajoute_recemment():
    """Un bouton a-t-il ete pose dans les 3 dernieres minutes, OU QUE CE SOIT ?"""
    for carnet in TOUS_LES_CARNETS:
        try:
            if (time.time() - os.path.getmtime(carnet)) < 180:
                return True
        except OSError:
            continue
    return False

def main():
    try:
        hook = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)
    tp = hook.get("transcript_path") or ""
    if not tp or not os.path.exists(tp):
        sys.exit(0)
    msg = dernier_message_assistant(tp)
    norm = sansaccents(msg)
    demande_commande = any(re.search(p, norm) for p in COMMANDE_A_TAPER) or re.search(r'```[^\n]*\n\s*!\s', msg)

    # ── LA REGLE QUI MANQUAIT (16/09/2026) ──────────────────────────────
    # Ce garde n'attrapait que « tape cette commande ». Mais toute la journee
    # du 16/09 j'ai fabrique des pages qui s'ouvrent dans un navigateur — la
    # clef de Nebius, le jeton GitHub, le mot de passe, le village — et je
    # n'ai jamais donne ni bouton ni adresse. J'ecrivais « ouvre ton
    # troisieme onglet » ou « bascule avec Alt+Tab ».
    # Ses mots : « le lien stp et pourquoi tu me l'as pas donne ??? ya pas
    # un garde fou qui te force a faire ca ?? ».
    # Une chose qu'on fabrique et qui s'ouvre repart avec son bouton.
    A_FABRIQUE_UNE_PAGE = [
        r'\b(la page|le village|la salle|le tableau|l\'?atelier)[^.!?]{0,40}?\b(est|sont|a ete) (ouvert|allum|pos|fabriqu|pret|en ligne)',
        r'\bj\'?ai (fabriqu|ecrit|monte|construit|pose|prepar)[^.!?]{0,30}?\b(page|salle|village|vue|tableau|atelier)',
        r'\b(elle|il) (est|tourne) (maintenant )?(ouvert|allum|en ligne|sur ton ecran)',
        r'\bbascule (dessus|avec|sur)',
        r'\b(ouvre|va sur|regarde) (ton|le) (troisieme |deuxieme |premier )?onglet',
        r'\balt ?\+ ?tab\b',
        r'\brecharge (la page|avec ctrl)',
    ]
    UNE_ADRESSE = r'https?://(127\.0\.0\.1|localhost|192\.168\.\d+\.\d+|[a-z0-9-]+\.[a-z]{2,})'
    a_fabrique = any(re.search(p, norm) for p in A_FABRIQUE_UNE_PAGE)
    donne_l_adresse = bool(re.search(UNE_ADRESSE, msg))

    if a_fabrique and not donne_l_adresse and not bouton_ajoute_recemment():
        print(json.dumps({
            "decision": "block",
            "reason": (
                "GARDE DES BOUTONS — REFUS.\n\n"
                "Tu viens de fabriquer une chose qui s'ouvre dans un navigateur, "
                "et tu ne donnes NI son adresse NI un bouton.\n\n"
                "Patrick ne la retrouvera pas demain. Il l'a dit le 16/09/2026 :\n"
                "  « le lien stp et pourquoi tu me l'as pas donne ??? »\n\n"
                "Une fenetre ouverte derriere une autre n'est pas un lien. "
                "« Bascule avec Alt+Tab » non plus.\n\n"
                "FAIS L'UN DES DEUX, PUIS RECRIS TON MESSAGE :\n\n"
                "  1. Pose un bouton avec la BRIQUE reutilisable :\n"
                "       python3 ~/briques/page-actions/poser-action.py <id> \"<titre>\" \\\n"
                "         \"<ce que ca fait>\" \"DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 "
                "xdg-open <adresse>\"\n\n"
                "  2. Ou ecris son adresse EN ENTIER dans ta reponse, "
                "http:// compris.\n"
            ),
        }))
        sys.exit(0)

    if demande_commande and not bouton_ajoute_recemment():
        print(json.dumps({
            "decision": "block",
            "reason": ("GARDE boutons : tu donnes une commande a taper a Patrick. "
                       "INTERDIT — il en a marre de taper. Transforme ce geste en BOUTON, "
                       "avec la BRIQUE reutilisable (page a actions) :\n"
                       "  python3 ~/briques/page-actions/poser-action.py <id> \"<titre>\" \"<detail>\" \"<la commande>\"\n"
                       "Le bouton apparait sur la page a actions (127.0.0.1:8835). "
                       "(Alternative : ~/taches/ajouter-tache.py pour la page « Mes taches ».) "
                       "Reecris ton message sans commande a taper.")
        }, ensure_ascii=False))
    sys.exit(0)

if __name__ == "__main__":
    main()
