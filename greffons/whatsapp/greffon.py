# -*- coding: utf-8 -*-
"""GREFFON WHATSAPP — Arthur envoie un message, mais JAMAIS tout seul.

Ne le 16/09/2026, d'une question de Patrick : « est-ce que Haichi pourra lire
mes messages WhatsApp ? repondre ? »

LA REGLE QUI PASSE AVANT TOUT, et qui est ecrite dans le code, pas dans une
promesse : Arthur n'envoie que si on le lui DEMANDE, avec un verbe d'envoi.
Parler de WhatsApp, raconter un message recu, poser une question dessus — rien
de tout ca ne declenche quoi que ce soit.

Pourquoi c'est vital : un assistant qui ecrit tout seul aux clients de Patrick
serait le pire accident possible. Ici, il faut une phrase qui commence par
« envoie », « envoyer », « previens », « ecris ».

DEUX MODES :
  essai (par defaut) — il fabrique le message, le MONTRE, et n'envoie rien ;
  vrai              — il envoie pour de bon, par la porte officielle de Meta.

En mode vrai, il lui faut trois reglages donnes par Meta : le numero, le jeton
et l'identifiant d'expediteur. S'il en manque un, il le DIT au lieu de faire
semblant — c'est la meme regle que pour ses reponses : on n'invente pas.

CE GREFFON NE LIT PAS LES CONVERSATIONS PERSONNELLES DE PATRICK. Il passe par
la porte officielle de Meta, celle des numeros professionnels. Lire un compte
personnel demanderait de passer par WhatsApp Web, ce qui est contre les regles
de WhatsApp et fait bannir le compte.
"""
import json
import re
import unicodedata
import urllib.request

# Les verbes qui, seuls, autorisent un envoi.
VERBES_D_ENVOI = ["envoie", "envoyer", "envoi", "previens", "prevenir",
                  "ecris", "ecrire", "transmets", "transmettre"]


def _sans_accent(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _est_un_ordre_d_envoi(question):
    """Vrai seulement si la phrase DEMANDE d'envoyer."""
    plat = _sans_accent(question)
    return any(re.search(r"\b" + v, plat) for v in VERBES_D_ENVOI)


def _extraire_le_texte(question):
    """Ce qu'Arthur doit ecrire dans le message."""
    plat = question.strip()
    for marqueur in [" pour dire que ", " pour dire ", " disant que ", " disant ",
                     " avec le texte ", " : ", " que "]:
        i = plat.lower().find(marqueur)
        if i > 0:
            return plat[i + len(marqueur):].strip(" .\"'")
    return plat


def _extraire_le_destinataire(question):
    plat = question
    m = re.search(r"\b(?:a|à|au|aux)\s+([A-ZÉÈÀÂÎÔÛ][\w'’-]+)", plat)
    if m:
        return m.group(1)
    m = re.search(r"\b(\+?\d[\d\s().-]{7,})", plat)
    if m:
        return re.sub(r"[^\d+]", "", m.group(1))
    return None


def repondre(question, reglages):
    reglages = reglages or {}

    # ---- LA REGLE : sans ordre explicite, on ne fait RIEN -----------------
    if not _est_un_ordre_d_envoi(question):
        return ("Je ne touche pas à WhatsApp tant qu'on ne me demande pas "
                "d'envoyer quelque chose. Dis-moi par exemple : « envoie un "
                "message WhatsApp à Patrick pour dire que le serveur est reparti ».")

    texte = _extraire_le_texte(question)
    qui = _extraire_le_destinataire(question)
    mode = str(reglages.get("mode", "essai")).lower()

    apercu = ("📱 Voici le message que j'enverrais :\n\n"
              f"   à       : {qui or '(personne indiquée)'}\n"
              f"   texte   : « {texte} »\n")

    # ---- MODE ESSAI : on montre, on n'envoie pas -------------------------
    if mode != "vrai":
        return (apercu + "\n⚠️ Mode ESSAI : RIEN N'A ÉTÉ ENVOYÉ. "
                "Pour envoyer pour de bon, passe le réglage « mode » à « vrai ».")

    # ---- MODE VRAI : il faut les trois reglages de Meta ------------------
    manquants = [c for c in ("numero", "jeton", "identifiant_expediteur")
                 if not str(reglages.get(c, "")).strip()]
    if manquants:
        return (apercu + "\n❌ Je ne peux pas envoyer : il me manque le réglage « "
                + " », « ".join(manquants) + " ». "
                "Ces trois-là sont donnés par Meta quand tu ouvres un numéro "
                "professionnel. Je préfère te le dire plutôt que faire semblant.")

    if not qui:
        return (apercu + "\n❌ Je ne sais pas à qui l'envoyer. "
                "Donne-moi un numéro, en clair.")

    # ---- l'envoi, par la porte officielle de Meta ------------------------
    url = ("https://graph.facebook.com/v21.0/"
           + str(reglages["identifiant_expediteur"]).strip() + "/messages")
    charge = json.dumps({
        "messaging_product": "whatsapp",
        "to": re.sub(r"[^\d+]", "", qui) or str(reglages["numero"]),
        "type": "text",
        "text": {"body": texte},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=charge, headers={
        "Authorization": "Bearer " + str(reglages["jeton"]).strip(),
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            reponse = json.loads(r.read().decode("utf-8"))
        ident = (reponse.get("messages") or [{}])[0].get("id", "(sans numéro)")
        return apercu + f"\n✅ Envoyé. Numéro du message : {ident}"
    except Exception as e:
        return apercu + f"\n❌ L'envoi a échoué : {str(e)[:130]}"
