#!/usr/bin/env python3
"""
Démon Autonome d'Arthur pour la Surveillance des Livrables.
Tourne en tâche de fond indépendante de tout agent IA.
Pousse automatiquement tout nouveau livrable HTML/fichier dans la bulle d'Arthur.
"""

import os
import time
import json
import urllib.request

LIVRABLES_DIR = "/home/orel/livrables"
ARTHUR_ACTION_URL = "http://127.0.0.1:8796/api/arthur-action"
SEEN_FILE = "/home/orel/haichi/.livrables_vus.json"

def charger_fichiers_vus():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def sauver_fichiers_vus(vus):
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(vus), f)
    except Exception:
        pass

def notifier_arthur(chemin_fichier):
    url_file = f"file://{chemin_fichier}"
    nom_fichier = os.path.basename(chemin_fichier)
    msg = f"🚀 Nouveau livrable disponible !\n📁 Lien direct : {url_file}"
    
    payload = json.dumps({
        "prompt": msg,
        "action": "parler"
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(
            ARTHUR_ACTION_URL,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            pass
    except Exception as e:
        pass

def surveiller():
    vus = charger_fichiers_vus()
    sauver_fichiers_vus(vus)
    while True:
        try:
            if os.path.exists(LIVRABLES_DIR):
                for racine, dossiers, fichiers in os.walk(LIVRABLES_DIR):
                    for f in fichiers:
                        if f.endswith(".html") or f.endswith(".pdf") or f.endswith(".txt"):
                            full_path = os.path.abspath(os.path.join(racine, f))
                            if full_path not in vus:
                                vus.add(full_path)
                                sauver_fichiers_vus(vus)
                                notifier_arthur(full_path)
        except Exception:
            pass
        time.sleep(3)

if __name__ == "__main__":
    surveiller()
