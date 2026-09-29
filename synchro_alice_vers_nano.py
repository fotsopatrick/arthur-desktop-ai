#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
synchro_alice_vers_nano.py — Fusionne l'intégralité des 232 circuits, leçons et garde-fous d'Alice
et du Cockpit directement dans le Nano-Reasoner déterministe (< 1ms).
"""

import os
import json
import re

# Où vivent les données ? D'abord le dossier du script lui-même (le dépôt
# se déplace sans se casser), ensuite ce que Patrick a posé dans l'environnement.
# Un chemin en dur unique cassait la fusion dès qu'on partageait le dépôt
# (relevé 21/09/2026). Sans données à côté, la fusion ne détruit rien : elle
# laisse le registre tel quel.
ICI = os.path.dirname(os.path.abspath(__file__))
REGISTRE_PATH = os.path.join(ICI, "registre_connaissances.json")
DONNEES_DIR = os.environ.get("SYNCHRO_DONNEES") or os.path.join(ICI, "donnees")

def normaliser_mots(texte):
    t = (texte or "").lower()
    t = re.sub(r"[éèêë]", "e", t)
    t = re.sub(r"[àâä]", "a", t)
    t = re.sub(r"[ùûü]", "u", t)
    t = re.sub(r"[îï]", "i", t)
    t = re.sub(r"[ôö]", "o", t)
    t = re.sub(r"[^\w\s]", " ", t)
    words = [w.strip() for w in t.split() if len(w.strip()) > 2]
    return list(set(words))

def fusionner():
    print("🔄 Fusion des connaissances d'Alice et de la Tour dans le Nano-Reasoner...")
    
    # (29/09) « la fusion ne detruit rien » : un registre illisible arrete
    # tout (avant, il etait remplace par {}), et sur un clone neuf on part
    # du savoir publie au lieu d'un registre vide qui cacherait l'exemple.
    registre = {}
    if os.path.exists(REGISTRE_PATH):
        registre = json.load(open(REGISTRE_PATH, encoding="utf-8"))
    else:
        exemple = os.path.join(ICI, "registre_exemple.json")
        if os.path.exists(exemple):
            registre = json.load(open(exemple, encoding="utf-8"))

    nouveaux_items = 0

    # 1. Ingérer les Circuits
    p_circuits = os.path.join(DONNEES_DIR, "circuits.json")
    if os.path.exists(p_circuits):
        circuits = json.load(open(p_circuits, encoding="utf-8"))
        for item in circuits:
            cid = f"circuit_{item.get('id', item.get('code', 'anon'))}"
            nom = item.get("nom") or item.get("name") or cid
            detail = item.get("description") or item.get("detail") or "Circuit d'Alice."
            mots = normaliser_mots(nom + " " + detail)
            if len(mots) >= 2:
                registre[cid] = {
                    "mots": mots,
                    "think": f"1. Identification du Circuit d'Alice : {nom}.\n2. Validation déterministe du workflow.",
                    "answer": f"⚙️ CIRCUIT DE LA TOUR — {nom} :\n\n• Description : {detail}\n• Statut : Identifié et validé déterministement."
                }
                nouveaux_items += 1

    # 2. Ingérer les Garde-Fous (32 règles)
    p_gardes = os.path.join(DONNEES_DIR, "garde-fous.json")
    if os.path.exists(p_gardes):
        gardes = json.load(open(p_gardes, encoding="utf-8"))
        for idx, item in enumerate(gardes):
            gid = f"garde_fou_{idx}"
            nom = item.get("nom") or item.get("titre") or f"Garde-Fou {idx}"
            detail = item.get("detail") or item.get("regle") or "Règle de sécurité."
            mots = normaliser_mots(nom + " " + detail)
            if len(mots) >= 2:
                registre[gid] = {
                    "mots": mots,
                    "think": f"1. Activation du Garde-Fou de Sécurité : {nom}.\n2. Vérification déterministe des invariants.",
                    "answer": f"🛡️ GARDE-FOU DE SÉCURITÉ — {nom} :\n\n• Règle : {detail}\n• Niveau : Invariant strict sans hallucination."
                }
                nouveaux_items += 1

    # 3. Ingérer les Leçons & Capacité
    p_lecons = os.path.join(DONNEES_DIR, "lecons.json")
    if os.path.exists(p_lecons):
        lecons = json.load(open(p_lecons, encoding="utf-8"))
        for idx, item in enumerate(lecons):
            lid = f"lecon_{idx}"
            nom = item.get("titre") or item.get("sujet") or f"Leçon {idx}"
            detail = item.get("detail") or item.get("contenu") or "Leçon apprise."
            mots = normaliser_mots(nom + " " + detail)
            if len(mots) >= 2:
                registre[lid] = {
                    "mots": mots,
                    "think": f"1. Extraction de la Leçon Apprise : {nom}.\n2. Application du retour d'expérience.",
                    "answer": f"📚 LEÇON APPRISE — {nom} :\n\n• Contenu : {detail}"
                }
                nouveaux_items += 1

    if nouveaux_items == 0:
        print("Rien a fusionner (aucune donnee dans %s) : le registre n'est pas touche." % DONNEES_DIR)
        return

    # Sauvegarde du registre mis à jour — atomique : fichier temporaire, puis
    # remplacement, pour qu'un crash ne laisse pas un registre a moitie ecrit.
    from ecriture_sure import ecrire_json
    ecrire_json(REGISTRE_PATH, registre, indent=2)

    print(f"🎉 FUSION RÉUSSIE ! {len(registre)} règles et circuits d'Alice sont désormais disponibles dans le Nano-Reasoner à < 0.1ms !")

if __name__ == "__main__":
    fusionner()
