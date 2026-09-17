#!/usr/bin/env python3
"""
Arthur Companion pour OpenCode
Permet à OpenCode de synchroniser l'état d'Arthur sur le bureau en temps réel
(Début de tâche, Réflexion, Succès avec livrable, Demande d'intervention humaine).
"""

import os
import sys
import json
import urllib.request

ARTHUR_ACTION_URL = "http://127.0.0.1:8796/api/arthur-action"

class ArthurOpenCodeCompanion:
    def __init__(self, agent_name="Arthur-OpenCode"):
        self.agent_name = agent_name

    def notifier_etat(self, etat, message, livrable_path=None):
        """
        Envoyer un changement d'état d'OpenCode vers l'avatar Arthur
        Etats possibles: 'travail', 'succes', 'erreur', 'attente_validation'
        """
        payload = {
            "prompt": message,
            "action": "parler",
            "source": self.agent_name,
            "meta": {
                "etat": etat,
                "livrable": livrable_path
            }
        }
        try:
            req = urllib.request.Request(
                ARTHUR_ACTION_URL,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            return {"succes": False, "erreur": str(e)}

    def debut_tache(self, nom_tache):
        msg = f"🚀 OpenCode démarre : {nom_tache}"
        return self.notifier_etat("travail", msg)

    def fin_tache(self, nom_tache, livrable_url=None):
        msg = f"✅ OpenCode a terminé : {nom_tache}"
        if livrable_url:
            msg += f"\n📁 Livrable : {livrable_url}"
        return self.notifier_etat("succes", msg, livrable_path=livrable_url)

    def alerte(self, explication):
        msg = f"⚠️ Attention Patrick, OpenCode signale : {explication}"
        return self.notifier_etat("attente_validation", msg)

if __name__ == "__main__":
    companion = ArthurOpenCodeCompanion()
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        text = sys.argv[2] if len(sys.argv) > 2 else "Notification OpenCode"
        if cmd == "start":
            companion.debut_tache(text)
        elif cmd == "done":
            companion.fin_tache(text, sys.argv[3] if len(sys.argv) > 3 else None)
        elif cmd == "alert":
            companion.alerte(text)
    else:
        print("Usage: python3 arthur_opencode_companion.py [start|done|alert] [message] [livrable]")
