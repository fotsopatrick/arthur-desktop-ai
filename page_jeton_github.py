#!/usr/bin/env python3
"""La page ou Patrick range son jeton GitHub.

Pourquoi une page et pas un message : ne le 16/09/2026, d'une regle qu'il a
posee lui-meme — « la prochaine fois demande moi une clef depuis cette page ».
Un message se perd. Une page attend.

Ce qu'elle fait, et rien d'autre :
  - ranger le jeton dans ~/.secrets/jeton-github.txt, droits 600 ;
  - l'essayer pour de vrai aupres de GitHub et dire QUI il reconnait ;
  - dire ce que ce jeton a le droit de faire ;
  - l'effacer.

Elle n'ecoute que sur 127.0.0.1 : cette machine seule.
"""
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8797
COFFRE = os.path.expanduser("~/.secrets/jeton-github.txt")


def etat():
    try:
        with open(COFFRE, encoding="utf-8") as f:
            j = f.read().strip()
    except OSError:
        return {"posee": False, "apercu": "", "longueur": 0}
    if not j:
        return {"posee": False, "apercu": "", "longueur": 0}
    return {"posee": True, "apercu": "…" + j[-4:], "longueur": len(j)}


def ranger(jeton):
    jeton = (jeton or "").strip()
    if not jeton:
        return False, "Tu n'as rien colle dans la case."
    if " " in jeton or "\n" in jeton:
        return False, "Il y a un espace ou un retour a la ligne dedans."
    if not jeton.startswith(("ghp_", "github_pat_", "gho_", "ghs_")):
        return False, ("Un jeton GitHub commence par ghp_ ou github_pat_. "
                       "Celui-ci commence par « %s ». Verifie que tu as copie "
                       "le bon." % jeton[:8])
    if len(jeton) < 30:
        return False, ("Ca fait seulement %d caracteres. Un jeton GitHub est "
                       "bien plus long." % len(jeton))
    os.makedirs(os.path.dirname(COFFRE), exist_ok=True)
    os.chmod(os.path.dirname(COFFRE), 0o700)
    with open(COFFRE, "w", encoding="utf-8") as f:
        f.write(jeton + "\n")
    os.chmod(COFFRE, 0o600)
    return True, "Jeton range. Seul toi peux lire ce fichier."


def essayer():
    """Demande VRAIMENT a GitHub qui est ce jeton."""
    try:
        with open(COFFRE, encoding="utf-8") as f:
            jeton = f.read().strip()
    except OSError:
        return {"ok": False, "texte": "Aucun jeton dans le coffre."}
    if not jeton:
        return {"ok": False, "texte": "Aucun jeton dans le coffre."}

    d = urllib.request.Request("https://api.github.com/user", headers={
        "Authorization": "Bearer " + jeton,
        "Accept": "application/vnd.github+json",
        "User-Agent": "arthur",
    })
    try:
        with urllib.request.urlopen(d, timeout=25) as r:
            qui = json.loads(r.read())
            droits = r.headers.get("x-oauth-scopes", "")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"ok": False, "texte": ("GitHub refuse ce jeton (401). Il est "
                                           "peut-etre expire, ou mal copie.")}
        return {"ok": False, "texte": "GitHub repond %d." % e.code}
    except Exception as souci:
        return {"ok": False, "texte": "Je n'ai pas pu joindre GitHub : %s" % souci}

    peut = ("Il peut ecrire dans tes depots." if "repo" in droits
            else "⚠ Il ne peut PAS ecrire dans tes depots — il lui manque le "
                 "droit « repo ».")
    return {"ok": True,
            "texte": "GitHub te reconnait : %s. %s" % (qui.get("login", "?"), peut),
            "compte": qui.get("login")}


PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Le jeton GitHub</title><style>
*{box-sizing:border-box} body{margin:0;background:#0d1117;color:#e6edf3;
 font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
 display:flex;justify-content:center;padding:48px 20px}
.boite{width:100%;max-width:620px}
h1{font-size:28px;margin:0 0 6px} .sous{color:#8b949e;margin:0 0 28px}
.carte{background:#161b22;border:1px solid #30363d;border-radius:14px;
 padding:22px;margin-bottom:18px}
.etat{display:flex;align-items:center;gap:10px;font-size:17px}
.pastille{width:11px;height:11px;border-radius:50%;flex:0 0 auto}
.vert{background:#3fb950} .rouge{background:#f85149} .gris{background:#6e7681}
label{display:block;font-size:14px;color:#8b949e;margin:0 0 8px}
input{width:100%;padding:13px 15px;border-radius:10px;border:1px solid #30363d;
 background:#0d1117;color:#e6edf3;font:15px ui-monospace,monospace}
input:focus{outline:none;border-color:#388bfd}
.rangee{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
button{padding:12px 20px;border-radius:10px;border:0;font-size:15px;
 font-weight:600;cursor:pointer;background:#238636;color:#fff}
button.gris{background:#21262d;color:#c9d1d9;border:1px solid #30363d}
button:disabled{opacity:.5;cursor:wait}
.mot{margin-top:16px;padding:13px 15px;border-radius:10px;font-size:15px;
 display:none;white-space:pre-wrap}
.mot.bien{display:block;background:#0f2a16;border:1px solid #2ea043;color:#7ee787}
.mot.mal{display:block;background:#2d1113;border:1px solid #f85149;color:#ffa198}
.aide{color:#6e7681;font-size:14px;margin:8px 0 0}
ol{color:#8b949e;font-size:15px;padding-left:22px;margin:10px 0 0}
ol li{margin-bottom:7px} b{color:#e6edf3}
</style></head><body><div class="boite">

<h1>Le jeton GitHub</h1>
<p class="sous">C'est le mot de passe qui me laisse deposer ton code chez
GitHub. Sans lui, je ne peux rien publier.</p>

<div class="carte">
  <div class="etat"><span class="pastille gris" id="pastille"></span>
    <span id="etat">Je regarde…</span></div>
</div>

<div class="carte">
  <label for="j">Colle le jeton ici, puis clique sur Ranger</label>
  <input id="j" type="password" autocomplete="off" spellcheck="false"
         placeholder="il commence par ghp_ ou github_pat_">
  <div class="rangee">
    <button id="ranger">Ranger le jeton</button>
    <button id="voir" class="gris" type="button">Montrer ce que je tape</button>
    <button id="essayer" class="gris" type="button">Essayer</button>
    <button id="effacer" class="gris" type="button">Effacer</button>
  </div>
  <div class="mot" id="mot"></div>
  <p class="aide">Il est range dans un fichier que toi seul peux ouvrir. Il ne
     part nulle part ailleurs, et cette page n'est visible que d'ici.</p>
</div>

<div class="carte">
  <label>Si tu dois en fabriquer un</label>
  <ol>
    <li>Sur GitHub : ta photo en haut a droite → <b>Settings</b>.</li>
    <li>Tout en bas a gauche : <b>Developer settings</b>.</li>
    <li><b>Personal access tokens</b> → <b>Tokens (classic)</b>.</li>
    <li>Bouton <b>Generate new token (classic)</b>.</li>
    <li>Coche la case <b>repo</b> — c'est elle qui donne le droit de deposer
        du code. Sans elle, je ne pourrai pas publier.</li>
    <li>Copie la ligne entiere. GitHub ne la remontrera plus jamais.</li>
  </ol>
</div>

</div><script>
const $=(i)=>document.getElementById(i);
function dire(t,b){const m=$('mot');m.textContent=t;m.className='mot '+(b?'bien':'mal');}
async function rafraichir(){
  const r=await (await fetch('/etat')).json();
  $('pastille').className='pastille '+(r.posee?'vert':'rouge');
  $('etat').textContent=r.posee
    ? 'Un jeton est range (il finit par '+r.apercu+', '+r.longueur+' caracteres).'
    : "Aucun jeton range. Je ne peux pas publier ton code.";
}
$('voir').onclick=()=>{const c=$('j');
  c.type=c.type==='password'?'text':'password';
  $('voir').textContent=c.type==='password'?'Montrer ce que je tape':'Cacher';};
$('ranger').onclick=async()=>{
  const r=await (await fetch('/ranger',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({jeton:$('j').value})})).json();
  dire(r.texte,r.ok); if(r.ok) $('j').value=''; rafraichir();};
$('essayer').onclick=async(e)=>{
  e.target.disabled=true; dire("Je demande a GitHub, patiente…",true);
  const r=await (await fetch('/essayer',{method:'POST'})).json();
  dire(r.texte,r.ok); e.target.disabled=false;};
$('effacer').onclick=async()=>{
  const r=await (await fetch('/effacer',{method:'POST'})).json();
  dire(r.texte,r.ok); rafraichir();};
rafraichir();
</script></body></html>"""


class Poste(BaseHTTPRequestHandler):
    def _envoyer(self, corps, type_="application/json"):
        if not isinstance(corps, bytes):
            corps = corps.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", type_ + "; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._envoyer(PAGE, "text/html")
        if self.path == "/etat":
            return self._envoyer(json.dumps(etat()))
        self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        brut = self.rfile.read(n) if n else b"{}"
        try:
            d = json.loads(brut or b"{}")
        except json.JSONDecodeError:
            d = {}
        if self.path == "/ranger":
            ok, texte = ranger(d.get("jeton"))
            return self._envoyer(json.dumps({"ok": ok, "texte": texte}))
        if self.path == "/essayer":
            return self._envoyer(json.dumps(essayer()))
        if self.path == "/effacer":
            try:
                os.remove(COFFRE)
                return self._envoyer(json.dumps({"ok": True, "texte": "Jeton efface."}))
            except FileNotFoundError:
                return self._envoyer(json.dumps({"ok": True, "texte": "Il n'y avait rien."}))
        self.send_error(404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("Le jeton GitHub  ->  http://127.0.0.1:%d" % PORT, flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Poste).serve_forever()
