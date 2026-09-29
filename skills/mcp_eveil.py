#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP ÉVEIL SYNTHÉTIQUE — absorbe l'état réel du système en UN JSON.

Remplace les 4–5 commandes bash séparées (git status, git log, ping,
docker ps) que l'agent lançait et devait parser une à une.

Sortie :
  {
    "timestamp": "2026-09-21T21:00:00+0200",
    "git": {
      "branch": "main",
      "clean": false,
      "modified": ["nano_moteur_ultra.py"],
      "untracked": ["nouveau.py"],
      "last_commits": [
        {"hash": "abc1234", "message": "feat: ..."}
      ]
    },
    "agents": {
      "alice": {"port": 8081, "status": "up", "latency_ms": 12},
      "arthur": {"port": 8080, "status": "down", "latency_ms": null}
    },
    "system": {
      "hostname": "mon-serveur",
      "load_1m": 0.42,
      "mem_used_pct": 62.3,
      "disk_used_pct": 41.7
    }
  }

Usage :
  python skills/mcp_eveil.py               # humain
  python skills/mcp_eveil.py --json        # agent
  python skills/mcp_eveil.py --repo /path  # repo spécifique
"""
import json
import os
import socket
import subprocess
import sys
import time


# ── Agents connus (port par défaut) ──────────────────────────────────────
DEFAULT_AGENTS = {
    "alice": 8081,
    "arthur": 8080,
    "braignak": 8082,
    "gamma": 8083,
}


def _run(cmd, cwd=None, timeout=10):
    """Lance une commande, rend stdout ou None."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           cwd=cwd, timeout=timeout)
        # rstrip seulement : l'espace de tete d'une ligne « git status
        # --porcelain » (« M fichier ») fait partie du format (29/09).
        return r.stdout.rstrip() if r.returncode == 0 else None
    except Exception:
        return None


def git_state(repo_path="."):
    """Rend l'état git du dépôt."""
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    if branch is None:
        return {"error": "pas un dépôt git"}

    status_raw = _run(["git", "status", "--porcelain"], cwd=repo_path) or ""
    modified = []
    untracked = []
    for line in status_raw.splitlines():
        if not line.strip():
            continue
        flag = line[:2]
        path = line[3:]
        if flag.strip().startswith("?"):
            untracked.append(path)
        else:
            modified.append(path)

    log_raw = _run(["git", "log", "--oneline", "-n", "3"], cwd=repo_path) or ""
    commits = []
    for line in log_raw.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:
            commits.append({"hash": parts[0], "message": parts[1]})

    return {
        "branch": branch,
        "clean": len(modified) == 0 and len(untracked) == 0,
        "modified": modified,
        "untracked": untracked,
        "last_commits": commits,
    }


def probe_agent(host, port, timeout=3):
    """Teste si un port TCP est ouvert. Rend (status, latency_ms)."""
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency = round((time.perf_counter() - t0) * 1000, 1)
            return "up", latency
    except (ConnectionRefusedError, OSError, socket.timeout):
        return "down", None


def agents_state(agents=None, host="127.0.0.1"):
    """Sonde tous les agents connus."""
    agents = agents or DEFAULT_AGENTS
    result = {}
    for name, port in agents.items():
        status, latency = probe_agent(host, port)
        result[name] = {"port": port, "status": status, "latency_ms": latency}
    return result


def system_state():
    """Rend l'état système basique (charge, RAM, disque)."""
    info = {"hostname": socket.gethostname()}

    # Load average
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
            info["load_1m"] = float(parts[0])
            info["load_5m"] = float(parts[1])
    except Exception:
        info["load_1m"] = None

    # Mémoire
    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mem[parts[0].rstrip(":")] = int(parts[1])
            total = mem.get("MemTotal", 1)
            avail = mem.get("MemAvailable", total)
            info["mem_used_pct"] = round((1 - avail / total) * 100, 1)
    except Exception:
        info["mem_used_pct"] = None

    # Disque
    try:
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        info["disk_used_pct"] = round((1 - free / total) * 100, 1) if total else None
    except Exception:
        info["disk_used_pct"] = None

    return info


def eveil(repo_path=".", agents=None, host="127.0.0.1"):
    """Produit le JSON d'éveil complet. Chaque section est déjà défensive ;
    ce blindage global n'existe que pour la panne qu'aucune des trois
    n'aurait prévue — règle absolue : zéro stacktrace Python rendue."""
    sortie = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    for cle, fabrique in (("git", lambda: git_state(repo_path)),
                          ("agents", lambda: agents_state(agents, host)),
                          ("system", system_state)):
        try:
            sortie[cle] = fabrique()
        except Exception as e:
            sortie[cle] = {"error": "section %s indisponible : %s" % (cle, e)}
    return sortie


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MCP Éveil Synthétique")
    parser.add_argument("--repo", default=".", help="Chemin du dépôt git")
    parser.add_argument("--json", action="store_true", help="Sortie JSON pure")
    parser.add_argument("--host", default="127.0.0.1", help="Hôte des agents")
    args = parser.parse_args()

    try:
        result = eveil(args.repo, host=args.host)
    except Exception as e:
        result = {"error": "mcp_eveil a échoué : %s" % e}

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
