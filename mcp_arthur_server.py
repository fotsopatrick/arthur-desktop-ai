#!/usr/bin/env python3
"""
Serveur MCP Arthur pour OpenCode / Claude Code / Antigravity
Expose les outils d'Arthur (parler, notifier, changer d'état) directement via MCP stdio.
"""

import os
import sys
import json
import urllib.request

REPO = os.path.dirname(os.path.abspath(__file__))

def _repondre(msg_id, texte):
    resp = {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {
            "content": [{"type": "text", "text": texte}]
        }
    }
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()


def _erreur(msg_id, code, message):
    """(29/09) Toute requete qui porte un id recoit une reponse : sans elle,
    le client MCP attend pour toujours (methode inconnue, outil inconnu,
    exception)."""
    if msg_id is None:
        return
    sys.stdout.write(json.dumps({
        "jsonrpc": "2.0", "id": msg_id,
        "error": {"code": code, "message": message},
    }) + "\n")
    sys.stdout.flush()


def envoyer_vers_arthur(prompt, action="parler"):
    # (24/09) le cockpit répond lui-même, par le moteur à étages, derrière son jeton ;
    # l'ancien serveur 8796 (sans jeton, ouvert à toute page web) n'est plus lancé.
    sys.path.insert(0, REPO)
    import jeton_cockpit
    url = "http://127.0.0.1:8790/api/nano-search"
    payload = json.dumps({"prompt": prompt}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers=jeton_cockpit.entetes())
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"succes": False, "erreur": str(e)}

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        req = None
        try:
            req = json.loads(line)
            method = req.get("method")
            msg_id = req.get("id")

            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "arthur-mcp", "version": "1.0.0"}
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": [
                            {
                                "name": "arthur_parler",
                                "description": "Fait parler l'avatar flottant d'Arthur sur le bureau de Patrick.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {"type": "string", "description": "Le texte qu'Arthur doit dire dans sa bulle."}
                                    },
                                    "required": ["message"]
                                }
                            },
                            {
                                "name": "arthur_lire_dialogues",
                                "description": "Lit les derniers dialogues et réponses d'Arthur sur le bureau de Patrick.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "lignes": {"type": "integer", "description": "Nombre de lignes du journal à lire (défaut: 50)"}
                                    }
                                }
                            },
                            # ── OUTILS MCP LOCAUX (21/09/2026) ──
                            {
                                "name": "eveil_systeme",
                                "description": "Éveil synthétique : rend l'état complet du système (git, agents, charge, RAM, disque) en JSON structuré. Remplace git status + ping + df.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "repo": {"type": "string", "description": "Chemin du dépôt git (défaut : le dépôt d'Arthur)"}
                                    }
                                }
                            },
                            {
                                "name": "analyse_banc",
                                "description": "Lance le banc de tests pytest et rend un JSON structuré des résultats (total, verts, rouges, détail des échecs). Remplace pytest en bash.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string", "description": "Répertoire des tests (défaut: tests/)"},
                                        "pattern": {"type": "string", "description": "Pattern des fichiers de test (défaut: test_*.py)"}
                                    }
                                }
                            },
                            {
                                "name": "refactor",
                                "description": "Recherche-et-remplace structuré dans les fichiers, en streaming (jamais en RAM). Rend un JSON des modifications. Remplace sed/grep.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "glob": {"type": "string", "description": "Pattern glob des fichiers (ex: '*.py')"},
                                        "target": {"type": "string", "description": "Chaîne ou regex à chercher"},
                                        "replace": {"type": "string", "description": "Chaîne de remplacement"},
                                        "regex": {"type": "boolean", "description": "Interpréter target comme regex (défaut: false)"},
                                        "dry_run": {"type": "boolean", "description": "Simuler sans modifier (défaut: true — passer false pour écrire)"}
                                    },
                                    "required": ["glob", "target", "replace"]
                                }
                            },
                            {
                                "name": "apprendre_savoir",
                                "description": "Apprend un fait au moteur (format mots -> answer + source + date + confiance) par le mur de confiance. Rend un JSON verdict (valide/refuse). Une fiche sans source datée ou contredisant une fiche plus fiable est refusée.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "question": {"type": "string"},
                                        "reponse": {"type": "string"},
                                        "source": {"type": "string", "description": "URL ou référence de la source"},
                                        "date": {"type": "string", "description": "Date de capture AAAA-MM-JJ"}
                                    },
                                    "required": ["question", "reponse", "source", "date"]
                                }
                            },
                            {
                                "name": "arthur_cerveau",
                                "description": "Voir ou changer le gros cerveau d'Arthur (couche 3) : qwen (Alice, gratuit), nebius (NVIDIA Nemotron chez Nebius, payant), local (ollama sur ce PC). Sans argument : rend le cerveau actuel. Actif dès la question suivante.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "cerveau": {"type": "string", "enum": ["qwen", "nebius", "local"]}
                                    }
                                }
                            }
                        ]
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "tools/call":
                params = req.get("params") or {}
                tool_name = params.get("name")
                args = params.get("arguments") or {}

                if tool_name == "arthur_parler":
                    msg = args.get("message", "")
                    res = envoyer_vers_arthur(msg, "parler")
                    resp = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Arthur a parlé : {json.dumps(res)}"}]
                        }
                    }
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()

                elif tool_name == "arthur_lire_dialogues":
                    nb_lignes = args.get("lignes", 50)
                    log_path = os.path.expanduser("~/livrables/arthur_dialogues.log")
                    contenu = ""
                    try:
                        if os.path.exists(log_path):
                            with open(log_path, "r", encoding="utf-8") as f:
                                lines = f.readlines()
                                contenu = "".join(lines[-nb_lignes:])
                        else:
                            contenu = "Aucun dialogue enregistré pour le moment."
                    except Exception as e:
                        contenu = f"Erreur de lecture: {e}"

                    resp = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": contenu}]
                        }
                    }
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()

                elif tool_name == "eveil_systeme":
                    repo = args.get("repo") or REPO
                    from skills.mcp_eveil import eveil
                    data = eveil(os.path.expanduser(repo))
                    _repondre(msg_id, json.dumps(data, ensure_ascii=False, indent=2))

                elif tool_name == "analyse_banc":
                    path = args.get("path", "tests/") or "tests/"
                    pattern = args.get("pattern", "test_*.py") or "test_*.py"
                    from skills.mcp_analyse_banc import run_pytest
                    data = run_pytest(path, pattern)
                    _repondre(msg_id, json.dumps(data, ensure_ascii=False, indent=2))

                elif tool_name == "refactor":
                    from skills.mcp_refactor import refactor
                    data = refactor(
                        args.get("glob", ""),
                        args.get("target", ""),
                        args.get("replace", ""),
                        use_regex=bool(args.get("regex", False)),
                        dry_run=bool(args.get("dry_run", True)),
                        base_dir=REPO,
                    )
                    _repondre(msg_id, json.dumps(data, ensure_ascii=False, indent=2))

                elif tool_name == "arthur_cerveau":
                    sys.path.insert(0, REPO)
                    import arthur_cerveau
                    if args.get("cerveau"):
                        _ok, texte = arthur_cerveau.choisir(args["cerveau"])
                    else:
                        texte = arthur_cerveau.etat()
                    _repondre(msg_id, texte)

                elif tool_name == "apprendre_savoir":
                    from skills.mcp_learn import apprendre
                    data = apprendre(
                        args.get("question", ""),
                        args.get("reponse", ""),
                        args.get("source", ""),
                        args.get("date", ""),
                    )
                    _repondre(msg_id, json.dumps(data, ensure_ascii=False, indent=2))

                else:
                    _erreur(msg_id, -32602, "outil inconnu : %s" % tool_name)

            elif method == "ping":
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {}}) + "\n")
                sys.stdout.flush()

            elif msg_id is not None:
                _erreur(msg_id, -32601, "methode inconnue : %s" % method)

        except Exception as e:
            sys.stderr.write(f"Erreur MCP Arthur: {e}\n")
            # une ligne qui n'est meme pas du JSON n'a pas d'id a qui repondre
            _erreur(req.get("id") if isinstance(req, dict) else None,
                    -32603, "erreur interne : %s" % str(e)[:200])

if __name__ == "__main__":
    main()
