#!/usr/bin/env python3
"""
Serveur MCP Arthur pour OpenCode / Claude Code / Antigravity
Expose les outils d'Arthur (parler, notifier, changer d'état) directement via MCP stdio.
"""

import sys
import json
import urllib.request

def envoyer_vers_arthur(prompt, action="parler"):
    url = "http://127.0.0.1:8796/api/arthur-action"
    payload = json.dumps({"prompt": prompt, "action": action}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"succes": False, "erreur": str(e)}

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
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
                            }
                        ]
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "tools/call":
                params = req.get("params", {})
                tool_name = params.get("name")
                args = params.get("arguments", {})

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
                    log_path = "/home/orel/livrables/arthur_dialogues.log"
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

        except Exception as e:
            sys.stderr.write(f"Erreur MCP Arthur: {e}\n")

if __name__ == "__main__":
    main()
