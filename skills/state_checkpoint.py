#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STATE CHECKPOINTING — sauvegarde et reprise d'état pour la boucle beelzebuth.

L'agent peut reprendre son cycle à l'étape N si une erreur réseau,
un crash ou un timeout interrompt le processus.

Le fichier .agent_state.json contient :
  {
    "cycle": "beelzebuth",
    "step": 3,
    "step_name": "tests_d_abord",
    "timestamp": "2026-09-21T21:00:00+0200",
    "data": { ... },  // données accumulées
    "history": [
      {"step": 1, "step_name": "eveil", "status": "done", "ts": "..."},
      {"step": 2, "step_name": "analyse", "status": "done", "ts": "..."},
      {"step": 3, "step_name": "tests_d_abord", "status": "running", "ts": "..."}
    ]
  }

Usage :
  from skills.state_checkpoint import Checkpoint
  cp = Checkpoint("beelzebuth", state_dir=".")
  cp.load()  # charge l'état existant ou crée un état neuf
  if cp.current_step < 3:
      # reprendre à l'étape 3
      cp.advance("tests_d_abord", data={"fichiers": [...]})
  cp.save()
"""
import json
import os
import time


# Les 7 temps de beelzebuth
BEELZEBUTH_STEPS = [
    "eveil",
    "analyse_sage",
    "tests_d_abord",
    "materialisation",
    "sceaux_controle",
    "restitution",
    "retenue",
]


class Checkpoint:
    """Gestionnaire de checkpoints pour un cycle d'agent."""

    def __init__(self, cycle_name="beelzebuth", state_dir=None,
                 state_file=None):
        self.cycle_name = cycle_name
        self.state_dir = state_dir or "."
        self.state_file = state_file or os.path.join(
            self.state_dir, ".agent_state.json")
        self.state = None

    def _empty_state(self):
        """Crée un état vierge."""
        return {
            "cycle": self.cycle_name,
            "step": 0,
            "step_name": "",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "data": {},
            "history": [],
            "version": 1,
        }

    def load(self):
        """Charge l'état depuis le fichier. Crée un état neuf si absent."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    self.state = json.load(f)
                # Vérifier que c'est le bon cycle
                if self.state.get("cycle") != self.cycle_name:
                    self.state = self._empty_state()
                return True
            except (json.JSONDecodeError, OSError):
                self.state = self._empty_state()
                return False
        else:
            self.state = self._empty_state()
            return False

    def save(self):
        """Sauvegarde l'état sur disque."""
        if self.state is None:
            self.state = self._empty_state()

        self.state["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

        return self.state_file

    @property
    def current_step(self):
        """Numéro de l'étape courante (0 = pas commencé)."""
        return (self.state or {}).get("step", 0)

    @property
    def current_step_name(self):
        """Nom de l'étape courante."""
        return (self.state or {}).get("step_name", "")

    def advance(self, step_name, data=None, status="running"):
        """Avance à l'étape suivante et enregistre.

        Args:
            step_name: nom de l'étape (ex: "eveil", "tests_d_abord")
            data: données à accumuler dans state["data"]
            status: "running", "done", "error", "skipped"
        """
        if self.state is None:
            self.load()

        # Marquer l'étape précédente comme "done" si elle était "running"
        if self.state["history"]:
            last = self.state["history"][-1]
            if last.get("status") == "running":
                last["status"] = "done"
                last["ts_done"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

        step_num = self.state["step"] + 1
        self.state["step"] = step_num
        self.state["step_name"] = step_name

        entry = {
            "step": step_num,
            "step_name": step_name,
            "status": status,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        self.state["history"].append(entry)

        if data:
            self.state["data"].update(data)

        self.save()
        return step_num

    def mark_done(self, result_data=None):
        """Marque l'étape courante comme terminée."""
        if self.state and self.state["history"]:
            self.state["history"][-1]["status"] = "done"
            self.state["history"][-1]["ts_done"] = time.strftime(
                "%Y-%m-%dT%H:%M:%S%z")
        if result_data:
            self.state["data"].update(result_data)
        self.save()

    def mark_error(self, error_msg):
        """Marque l'étape courante comme en erreur."""
        if self.state and self.state["history"]:
            self.state["history"][-1]["status"] = "error"
            self.state["history"][-1]["error"] = str(error_msg)[:500]
        self.save()

    def should_resume_from(self, step_name):
        """Rend True si l'agent doit REPRENDRE à partir de cette étape.

        C'est le cas si l'étape est la dernière enregistrée ET qu'elle
        n'est pas marquée "done".
        """
        if not self.state or not self.state["history"]:
            return True  # Rien n'a commencé, on commence par la première

        last = self.state["history"][-1]
        if last["step_name"] == step_name and last["status"] != "done":
            return True
        return False

    def is_step_done(self, step_name):
        """Rend True si cette étape est déjà terminée."""
        for entry in (self.state or {}).get("history", []):
            if entry["step_name"] == step_name and entry["status"] == "done":
                return True
        return False

    def reset(self):
        """Remet le cycle à zéro."""
        self.state = self._empty_state()
        self.save()

    def summary(self):
        """Rend un résumé lisible de l'état."""
        if not self.state:
            return "Pas d'état chargé."

        lines = [f"Cycle: {self.state['cycle']}"]
        lines.append(f"Étape: {self.state['step']} ({self.state['step_name']})")
        lines.append(f"Dernière MAJ: {self.state['timestamp']}")

        for h in self.state.get("history", []):
            icon = {"done": "✅", "running": "⏳", "error": "❌",
                    "skipped": "⏭️"}.get(h["status"], "?")
            lines.append(f"  {icon} {h['step']}.{h['step_name']} [{h['status']}]")

        return "\n".join(lines)
