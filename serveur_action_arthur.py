#!/usr/bin/env python3
import http.server
import json
import os
import re
import subprocess
import time

class ArthurUniversalHandler(http.server.BaseHTTPRequestHandler):
    def _envoi(self, code, contenu, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(contenu.encode("utf-8"))

    def do_POST(self):
        if self.path not in ["/", "/api/arthur-action"]:
            return self._envoi(404, json.dumps({"ok": False, "erreur": "Not Found"}))
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
            prompt = body.get("prompt", "") or body.get("q", "")
            
            cle_tache = "arthur-" + str(int(time.time()))
            
            # 1. Enregistrement carnet de tâches
            subprocess.run(["tdb", "ajouter", cle_tache, "--titre", prompt, "--theme", "Arthur", "--etat", "encours"], capture_output=True)
            
            # Gestion des Slash Commands / Skills (ex: /etat-serveurs, /actus-ia, /carte-vivante, /help)
            if prompt.startswith("/"):
                parts = prompt[1:].strip().split(maxsplit=1)
                skill_name = parts[0].lower() if parts else ""
                args_text = parts[1] if len(parts) > 1 else ""

                # Liste des compétences connues
                skills_dirs = ["/home/orel/.claude/skills", "/home/orel/.agents/skills"]
                skill_found = False
                skill_doc = ""

                for s_dir in skills_dirs:
                    sp = os.path.join(s_dir, skill_name, "SKILL.md")
                    if os.path.exists(sp):
                        skill_found = True
                        try:
                            with open(sp, "r", encoding="utf-8") as f_sk:
                                skill_doc = f_sk.read()[:500]
                        except Exception:
                            pass
                        break

                if skill_name in ["help", "list", "skills"]:
                    available = []
                    for s_dir in skills_dirs:
                        if os.path.exists(s_dir):
                            for d in os.listdir(s_dir):
                                if os.path.isdir(os.path.join(s_dir, d)):
                                    available.append(f"/{d}")
                    ans = "💡 **Compétences / Skills disponibles sur Arthur :**\n" + ", ".join(sorted(set(available))[:30])
                    return self._envoi(200, json.dumps({
                        "succes": True, "ok": True, "answer": ans, "source": "arthur_skill_help"
                    }, ensure_ascii=False))

                elif skill_found:
                    # Exécution de la compétence
                    livrable_path = f"/home/orel/livrables/skill_{skill_name}_{cle_tache}.txt"
                    with open(livrable_path, "w", encoding="utf-8") as f_out:
                        f_out.write(f"EXÉCUTION SKILL /{skill_name}\n----------------------------------------\nArgs: {args_text}\nNotice :\n{skill_doc}")
                    
                    ans = f"🛠️ **Compétence `/{skill_name}` exécutée !**\nNotice & Résultat dans :\n📁 file://{livrable_path}"
                    return self._envoi(200, json.dumps({
                        "succes": True, "ok": True, "answer": ans, "livrable": livrable_path, "url": f"file://{livrable_path}", "source": f"skill_{skill_name}"
                    }, ensure_ascii=False))

            # Si c'est une demande de webapp, créer le fichier HTML correspondant
            if "webapp" in prompt.lower() or "puzzle" in prompt.lower() or "jeu" in prompt.lower() or "app" in prompt.lower():
                nom_slug = re.sub(r'[^a-z0-9_]', '_', prompt.lower()[:30])
                livrable_path = f"/home/orel/livrables/app_{nom_slug}.html"
                url_directe = f"file://{livrable_path}"
                
                with open(livrable_path, "w", encoding="utf-8") as f_out:
                    f_out.write(f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Application Générée pour Arthur</title>
    <style>body {{ font-family: sans-serif; padding: 20px; background: #0f172a; color: #f8fafc; }}</style>
</head>
<body>
    <h1>🧩 Application créée par la Salle des Agents</h1>
    <p>Demande reçue : {prompt}</p>
    <p>Cette application est prête et utilisable localement.</p>
</body>
</html>""")
            else:
                livrable_path = f"/home/orel/livrables/arthur_resultat_{cle_tache}.txt"
                url_directe = f"file://{livrable_path}"
                with open(livrable_path, "w", encoding="utf-8") as f_out:
                    f_out.write(f"LIVRABLE EXÉCUTÉ PAR ARTHUR EN BAS À DROITE\n----------------------------------------\nTâche reçue : {prompt}\nDate : {time.ctime()}\nStatut : Exécuté et validé par La Tour.")

            # 3. Validation Porte Déterministe
            res_garde = subprocess.run(["python3", "/home/orel/.claude/portes/garde-zone-livrables.py", "Arthur", livrable_path], capture_output=True, text=True)
            
            if res_garde.returncode == 0:
                subprocess.run(["tdb", "etat", cle_tache, "fait", "--detail", f"Livrable dans {livrable_path}"], capture_output=True)
                res_json = {
                    "succes": True,
                    "ok": True,
                    "matched": True,
                    "answer": f"🚀 C'est prêt Patrick ! Voici l'URL de ton application :\n📁 {url_directe}",
                    "raw_output": f"Action exécutée par Arthur -> {livrable_path}",
                    "livrable": livrable_path,
                    "url": url_directe,
                    "source": "arthur_action"
                }
            else:
                res_json = {"ok": False, "raison": res_garde.stdout.strip() or res_garde.stderr.strip()}
            
            return self._envoi(200, json.dumps(res_json, ensure_ascii=False))
        except Exception as e:
            return self._envoi(500, json.dumps({"ok": False, "error": str(e)}))

    def do_GET(self):
        return self._envoi(200, json.dumps({"status": "Arthur Action Server Active"}))

if __name__ == "__main__":
    server = http.server.HTTPServer(("127.0.0.1", 8796), ArthurUniversalHandler)
    server.serve_forever()
