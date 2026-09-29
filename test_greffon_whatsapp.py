# -*- coding: utf-8 -*-
"""LE GREFFON WHATSAPP — et la regle qui passe avant tout.

Ne le 16/09/2026. Patrick : « est-ce que Haichi pourra lire mes messages
WhatsApp ? repondre ? »

LA REGLE QUI NE SE NEGOCIE PAS :
Arthur n'envoie JAMAIS un message qu'on ne lui a pas explicitement demande
d'envoyer. Un assistant qui ecrit tout seul aux clients de Patrick serait le
pire accident possible. Ce banc verifie donc D'ABORD qu'il REFUSE, et
seulement ensuite qu'il sait faire.

Il tourne en MODE ESSAI : aucun message ne part vraiment. Le greffon fabrique
le message, montre exactement ce qu'il enverrait, et s'arrete la. Le vrai
numero se branche en changeant un seul reglage — et sans numero, il le dit.
"""
import json, os, sys, tempfile, shutil

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import haichi_greffons as G

rouges = 0
def dire(ok, quoi):
    global rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    if not ok:
        rouges += 1

DOSSIER = os.path.join(ICI, "greffons")
FICHE = os.path.join(DOSSIER, "whatsapp", "greffon.json")

print("  --- LA REGLE D'ABORD : il doit REFUSER ---")
if not os.path.exists(FICHE):
    dire(False, "le greffon WhatsApp n'existe pas encore")
    print("\nBILAN WHATSAPP : 1 rouge — rien n'est encore ecrit")
    raise SystemExit(1)

G.basculer("whatsapp", True, DOSSIER)
G.regler("whatsapp", {"mode": "essai", "numero": "", "jeton": ""}, DOSSIER)

# 1. une phrase qui PARLE de WhatsApp n'est pas un ordre d'envoyer
r = G.essayer("c'est quoi WhatsApp ?", DOSSIER)
ok = (r is None) or ("envoy" not in str(r.get("reponse", "")).lower())
dire(ok, "parler de WhatsApp ne declenche AUCUN envoi")

r = G.essayer("j'ai recu un message WhatsApp de ma soeur", DOSSIER)
ok = (r is None) or ("envoy" not in str(r.get("reponse", "")).lower())
dire(ok, "raconter un message ne declenche AUCUN envoi")

print("  --- ensuite seulement : il sait faire ---")
# 2. une vraie demande d'envoi
r = G.essayer("envoie un message WhatsApp a Patrick pour dire que le serveur est reparti", DOSSIER)
dire(r is not None, "une vraie demande d'envoi reveille le greffon")
if r:
    rep = str(r.get("reponse", ""))
    dire(r.get("panne") is None, "le greffon ne plante pas : " + (r.get("panne") or "aucune panne"))
    dire("essai" in rep.lower() or "rien n'a ete envoye" in rep.lower() or "rien n a ete envoye" in rep.lower(),
         "il dit clairement que RIEN n'est parti : " + rep[:56])
    dire("serveur est reparti" in rep.lower() or "serveur" in rep.lower(),
         "il montre le texte qu'il enverrait")

print("  --- sans numero, il le DIT au lieu de faire semblant ---")
G.regler("whatsapp", {"mode": "vrai", "numero": "", "jeton": ""}, DOSSIER)
r = G.essayer("envoie un message WhatsApp pour dire bonjour", DOSSIER)
if r:
    rep = str(r.get("reponse", "")).lower()
    dire("numero" in rep or "numéro" in rep or "reglage" in rep or "réglage" in rep,
         "il dit qu'il lui manque le numero : " + str(r.get("reponse"))[:56])
else:
    dire(False, "il ne repond rien du tout")

print("  --- eteint, il n'existe pas ---")
G.basculer("whatsapp", False, DOSSIER)
r = G.essayer("envoie un message WhatsApp a Patrick", DOSSIER)
dire(r is None, "greffon ETEINT : aucune reponse, aucun envoi")

# on le remet dans son etat de depart : eteint et en mode essai
G.regler("whatsapp", {"mode": "essai", "numero": "", "jeton": ""}, DOSSIER)

print("\nBILAN WHATSAPP : %d rouge(s) sur 9" % rouges)
raise SystemExit(1 if rouges else 0)
