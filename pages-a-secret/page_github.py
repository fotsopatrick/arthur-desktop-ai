#!/usr/bin/env python3
"""Page fabriquee le 16/09/2026 par ~/outils/page-a-secret.py — service github."""
import json, os, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8800
SERVICE = 'github'
FICHE = {'nom': 'GitHub', 'quoi': 'le jeton', 'a_quoi_ca_sert': 'me laisser deposer ton code chez GitHub', 'debuts': ['ghp_', 'github_pat_', 'gho_', 'ghs_'], 'longueur_mini': 30, 'exemple': 'il commence par ghp_ ou github_pat_', 'essai': {'adresse': 'https://api.github.com/user', 'entete': 'Authorization: Bearer {s}', 'qui': 'login'}, 'ou_le_fabriquer': ['Sur GitHub : ta photo en haut a droite, puis Settings.', 'Tout en bas a gauche : Developer settings.', 'Personal access tokens, puis Tokens (classic).', 'Bouton Generate new token (classic).', "Coche la case repo — c'est elle qui donne le droit de deposer du code. Sans elle, je ne pourrai pas publier.", 'Copie la ligne entiere. GitHub ne la remontrera plus jamais.'], 'couleurs': ('#0d1117', '#161b22', '#30363d', '#e6edf3', '#238636')}
COFFRE = os.path.expanduser("~/.secrets/secret-github.txt")


def etat():
    try:
        with open(COFFRE, encoding="utf-8") as f:
            v = f.read().strip()
    except OSError:
        return {"posee": False, "apercu": "", "longueur": 0}
    if not v:
        return {"posee": False, "apercu": "", "longueur": 0}
    return {"posee": True, "apercu": "…" + v[-4:], "longueur": len(v)}


def ranger(valeur):
    v = (valeur or "").strip()
    if not v:
        return False, "Tu n'as rien colle dans la case."
    if " " in v or "\n" in v:
        return False, "Il y a un espace ou un retour a la ligne dedans."
    debuts = FICHE.get("debuts") or []
    if debuts and not v.startswith(tuple(debuts)):
        return False, ("Un secret de %s commence par %s. Celui-ci commence par "
                       "« %s ». Verifie que tu as copie le bon."
                       % (FICHE["nom"], " ou ".join(debuts), v[:8]))
    if len(v) < FICHE.get("longueur_mini", 12):
        return False, ("Ca fait seulement %d caracteres. C'est bien plus long "
                       "que ca. Verifie que tu as copie la ligne entiere." % len(v))
    os.makedirs(os.path.dirname(COFFRE), exist_ok=True)
    os.chmod(os.path.dirname(COFFRE), 0o700)
    with open(COFFRE, "w", encoding="utf-8") as f:
        f.write(v + "\n")
    os.chmod(COFFRE, 0o600)
    return True, "C'est range. Seul toi peux lire ce fichier."


def essayer():
    essai = FICHE.get("essai")
    try:
        with open(COFFRE, encoding="utf-8") as f:
            v = f.read().strip()
    except OSError:
        v = ""
    if not v:
        return {"ok": False, "texte": "Rien dans le coffre."}
    if not essai:
        return {"ok": True, "texte": ("C'est range (%d caracteres). Je ne sais pas "
                "encore essayer ce service tout seul, alors je ne te promets pas "
                "qu'il marche." % len(v))}
    nom, _, val = essai["entete"].partition(": ")
    d = urllib.request.Request(essai["adresse"],
        headers={nom: val.format(s=v), "User-Agent": "arthur",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(d, timeout=25) as r:
            corps = r.read()
            entetes = dict(r.headers)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"ok": False, "texte": "%s refuse ce secret (401). Il est "
                     "peut-etre expire, ou mal copie." % FICHE["nom"]}
        return {"ok": False, "texte": "%s repond %d." % (FICHE["nom"], e.code)}
    except Exception as souci:
        return {"ok": False, "texte": "Je n'ai pas pu joindre %s : %s"
                 % (FICHE["nom"], souci)}

    mot = "%s accepte ton secret." % FICHE["nom"]
    if essai.get("qui"):
        try:
            qui = json.loads(corps).get(essai["qui"])
            if qui:
                mot = "%s te reconnait : %s." % (FICHE["nom"], qui)
        except ValueError:
            pass
    droits = entetes.get("x-oauth-scopes", "")
    if SERVICE == "github":
        mot += (" Il peut ecrire dans tes depots." if "repo" in droits
                else " ⚠ Il ne peut PAS ecrire dans tes depots — il lui "
                     "manque le droit « repo ».")
    return {"ok": True, "texte": mot}


FOND, CARTE, BORD, TEXTE, ACCENT = FICHE["couleurs"]
ETAPES = "".join("<li>%s</li>" % e for e in FICHE["ou_le_fabriquer"])

PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Le jeton de GitHub</title><style>
*{box-sizing:border-box} body{margin:0;background:%s;color:%s;
 font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
 display:flex;justify-content:center;padding:48px 20px}
.boite{width:100%%;max-width:620px}
h1{font-size:28px;margin:0 0 6px} .sous{opacity:.65;margin:0 0 28px}
.carte{background:%s;border:1px solid %s;border-radius:14px;padding:22px;
 margin-bottom:18px}
.etat{display:flex;align-items:center;gap:10px;font-size:17px}
.pastille{width:11px;height:11px;border-radius:50%%;flex:0 0 auto}
.vert{background:#3fb950} .rouge{background:#f85149} .gris{background:#6e7681}
label{display:block;font-size:14px;opacity:.65;margin:0 0 8px}
input{width:100%%;padding:13px 15px;border-radius:10px;border:1px solid %s;
 background:%s;color:%s;font:15px ui-monospace,monospace}
input:focus{outline:none;border-color:%s}
.rangee{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
button{padding:12px 20px;border-radius:10px;border:0;font-size:15px;
 font-weight:600;cursor:pointer;background:%s;color:%s}
button.gris{background:%s;color:%s;border:1px solid %s}
button:disabled{opacity:.5;cursor:wait}
.mot{margin-top:16px;padding:13px 15px;border-radius:10px;font-size:15px;
 display:none;white-space:pre-wrap}
.mot.bien{display:block;background:#0f2a16;border:1px solid #2ea043;color:#7ee787}
.mot.mal{display:block;background:#2d1113;border:1px solid #f85149;color:#ffa198}
.aide{opacity:.5;font-size:14px;margin:8px 0 0}
ol{opacity:.75;font-size:15px;padding-left:22px;margin:10px 0 0}
ol li{margin-bottom:7px}
</style></head><body><div class="boite">
<h1>Le jeton de GitHub</h1>
<p class="sous">C'est %s pour %s.</p>
<div class="carte"><div class="etat">
  <span class="pastille gris" id="pastille"></span><span id="etat">Je regarde…</span>
</div></div>
<div class="carte">
  <label for="v">Colle %s ici, puis clique sur Ranger</label>
  <input id="v" type="password" autocomplete="off" spellcheck="false" placeholder="%s">
  <div class="rangee">
    <button id="ranger">Ranger</button>
    <button id="voir" class="gris" type="button">Montrer ce que je tape</button>
    <button id="essayer" class="gris" type="button">Essayer</button>
    <button id="effacer" class="gris" type="button">Effacer</button>
  </div>
  <div class="mot" id="mot"></div>
  <p class="aide">C'est range dans un fichier que toi seul peux ouvrir. Ca ne
     part nulle part ailleurs, et cette page n'est visible que d'ici.</p>
</div>
<div class="carte"><label>Si tu dois en fabriquer un</label><ol>%s</ol></div>
</div><script>
const $=(i)=>document.getElementById(i);
function dire(t,b){const m=$('mot');m.textContent=t;m.className='mot '+(b?'bien':'mal');}
async function rafraichir(){
  const r=await (await fetch('/etat')).json();
  $('pastille').className='pastille '+(r.posee?'vert':'rouge');
  $('etat').textContent=r.posee
    ?'C\\'est range (ca finit par '+r.apercu+', '+r.longueur+' caracteres).'
    :"Rien n'est range. Je ne peux pas continuer sans.";}
$('voir').onclick=()=>{const c=$('v');c.type=c.type==='password'?'text':'password';
  $('voir').textContent=c.type==='password'?'Montrer ce que je tape':'Cacher';};
$('ranger').onclick=async()=>{const r=await (await fetch('/ranger',{method:'POST',
  headers:{'Content-Type':'application/json'},body:JSON.stringify({valeur:$('v').value})})).json();
  dire(r.texte,r.ok); if(r.ok)$('v').value=''; rafraichir();};
$('essayer').onclick=async(e)=>{e.target.disabled=true;dire("Je demande, patiente…",true);
  const r=await (await fetch('/essayer',{method:'POST'})).json();
  dire(r.texte,r.ok);e.target.disabled=false;};
$('effacer').onclick=async()=>{const r=await (await fetch('/effacer',{method:'POST'})).json();
  dire(r.texte,r.ok);rafraichir();};
rafraichir();
</script></body></html>""" % (FOND, TEXTE, CARTE, BORD, BORD, FOND, TEXTE, ACCENT,
  ACCENT, FOND, CARTE, TEXTE, BORD, FICHE["quoi"], FICHE["a_quoi_ca_sert"],
  FICHE["quoi"], FICHE["exemple"], ETAPES)


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
        if self.path == "/service":
            return self._envoyer(json.dumps({"service": SERVICE}))
        self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            d = json.loads(self.rfile.read(n) if n else b"{}")
        except ValueError:
            d = {}
        if self.path == "/ranger":
            ok, texte = ranger(d.get("valeur"))
            return self._envoyer(json.dumps({"ok": ok, "texte": texte}))
        if self.path == "/essayer":
            return self._envoyer(json.dumps(essayer()))
        if self.path == "/effacer":
            try:
                os.remove(COFFRE)
                return self._envoyer(json.dumps({"ok": True, "texte": "Efface."}))
            except FileNotFoundError:
                return self._envoyer(json.dumps({"ok": True, "texte": "Il n'y avait rien."}))
        self.send_error(404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("%s -> http://127.0.0.1:%d" % ('Le jeton de GitHub', PORT), flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Poste).serve_forever()
