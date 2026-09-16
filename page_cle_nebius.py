#!/usr/bin/env python3
"""La page ou Patrick range la clef de Nebius.

Pourquoi une page a part et pas dans le cockpit : le 16/09/2026 une autre
session reorganisait le cockpit. Toucher a ses fichiers aurait casse son
travail. Cette page vit toute seule sur son port, elle ne depend de rien.

Ce qu'elle fait, et rien d'autre :
  - montrer si une clef est deja rangee (sans jamais la reafficher en entier) ;
  - en ranger une nouvelle dans ~/.secrets/cle-nebius.txt, droits 600 ;
  - l'essayer pour de vrai aupres de Nebius et dire ce qui revient ;
  - l'effacer.

Elle n'ecoute que sur 127.0.0.1 : cette machine seule. Rien du reseau de la
maison ne peut l'atteindre.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.expanduser("~/haichi"))
import nemotron_nebius  # noqa: E402

PORT = 8796
COFFRE = os.path.expanduser("~/.secrets/cle-nebius.txt")


def etat_du_coffre():
    """Rend ce qu'on peut dire de la clef SANS la montrer."""
    try:
        with open(COFFRE, "r", encoding="utf-8") as f:
            cle = f.read().strip()
    except OSError:
        return {"posee": False, "apercu": "", "longueur": 0}
    if not cle:
        return {"posee": False, "apercu": "", "longueur": 0}
    return {"posee": True,
            "apercu": "…" + cle[-4:],
            "longueur": len(cle)}


def ranger(cle):
    cle = (cle or "").strip()
    if not cle:
        return False, "Tu n'as rien colle dans la case."
    if len(cle) < 20:
        return False, ("Ca fait seulement %d caracteres. Une clef Nebius est "
                       "bien plus longue. Verifie que tu as copie la ligne "
                       "entiere." % len(cle))
    if " " in cle or "\n" in cle:
        return False, "Il y a un espace ou un retour a la ligne dedans."
    os.makedirs(os.path.dirname(COFFRE), exist_ok=True)
    os.chmod(os.path.dirname(COFFRE), 0o700)
    with open(COFFRE, "w", encoding="utf-8") as f:
        f.write(cle + "\n")
    os.chmod(COFFRE, 0o600)
    return True, "Clef rangee. Seul toi peux lire ce fichier."


def essayer():
    """Pose VRAIMENT une question a Nebius pour voir si la clef marche."""
    os.environ.pop("NEBIUS_API_KEY", None)   # on teste le coffre, pas l'ancien
    if not nemotron_nebius.est_pret():
        return {"ok": False, "texte": "Aucune clef dans le coffre."}
    d = nemotron_nebius.demander("Reponds seulement le mot : bonjour")
    if d.get("panne"):
        return {"ok": False, "texte": d["panne"]}
    return {"ok": True,
            "texte": "Nebius a repondu : « %s »  (en %s millisecondes)"
                     % (str(d.get("reponse", "")).strip()[:200], d.get("duree_ms"))}


PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>La clef de Nebius</title><style>
*{box-sizing:border-box} body{margin:0;background:#0e1116;color:#e7ecf3;
 font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
 display:flex;justify-content:center;padding:48px 20px}
.boite{width:100%;max-width:620px}
h1{font-size:28px;margin:0 0 6px} .sous{color:#93a2b8;margin:0 0 28px}
.carte{background:#171c24;border:1px solid #242c38;border-radius:14px;
 padding:22px;margin-bottom:18px}
.etat{display:flex;align-items:center;gap:10px;font-size:17px}
.pastille{width:11px;height:11px;border-radius:50%;flex:0 0 auto}
.vert{background:#3ddc84} .rouge{background:#ff6b6b} .gris{background:#5a6675}
label{display:block;font-size:14px;color:#93a2b8;margin:0 0 8px}
input{width:100%;padding:13px 15px;border-radius:10px;border:1px solid #2c3543;
 background:#0e1116;color:#e7ecf3;font:15px ui-monospace,monospace}
input:focus{outline:none;border-color:#4a8cff}
.rangee{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
button{padding:12px 20px;border-radius:10px;border:0;font-size:15px;
 font-weight:600;cursor:pointer;background:#4a8cff;color:#fff}
button.gris{background:#2c3543;color:#cfd8e6}
button:disabled{opacity:.5;cursor:wait}
.mot{margin-top:16px;padding:13px 15px;border-radius:10px;font-size:15px;
 display:none;white-space:pre-wrap}
.mot.bien{display:block;background:#12301f;border:1px solid #2c5f3e;color:#9ae6b4}
.mot.mal{display:block;background:#301418;border:1px solid #5f2c34;color:#ffb3b3}
.aide{color:#7e8da3;font-size:14px;margin:8px 0 0}
.aide a{color:#6ea8ff}
ol{color:#a9b6c9;font-size:15px;padding-left:22px;margin:10px 0 0}
</style></head><body><div class="boite">

<h1>La clef de Nebius</h1>
<p class="sous">C'est le mot de passe qui donne a Arthur le droit de parler
au gros cerveau. Sans elle, il repond avec son petit moteur seulement.</p>

<div class="carte">
  <div class="etat"><span class="pastille gris" id="pastille"></span>
    <span id="etat">Je regarde…</span></div>
</div>

<div class="carte">
  <label for="cle">Colle la clef ici, puis clique sur Ranger</label>
  <input id="cle" type="password" autocomplete="off" spellcheck="false"
         placeholder="elle commence souvent par eyJ…">
  <div class="rangee">
    <button id="ranger">Ranger la clef</button>
    <button id="voir" class="gris" type="button">Montrer ce que je tape</button>
    <button id="essayer" class="gris" type="button">Essayer la clef</button>
    <button id="effacer" class="gris" type="button">Effacer</button>
  </div>
  <div class="mot" id="mot"></div>
  <p class="aide">Elle est rangee dans un fichier que toi seul peux ouvrir.
     Elle ne part nulle part ailleurs, et cette page n'est visible que depuis
     cet ordinateur.</p>
</div>

<div class="carte">
  <label>Ou trouver cette clef</label>
  <ol>
    <li>Va sur <a href="https://studio.nebius.com/" target="_blank"
        rel="noopener">studio.nebius.com</a> et connecte-toi.</li>
    <li>Clique sur ton nom, en haut a droite.</li>
    <li>Choisis « API keys », puis le bouton qui cree une clef.</li>
    <li>Copie la ligne entiere. Nebius ne la remontrera plus jamais apres.</li>
  </ol>
</div>

</div><script>
const $ = (i)=>document.getElementById(i);
function dire(txt, bien){ const m=$('mot'); m.textContent=txt;
  m.className = 'mot ' + (bien ? 'bien':'mal'); }
async function rafraichir(){
  const r = await (await fetch('/etat')).json();
  $('pastille').className = 'pastille ' + (r.posee ? 'vert':'rouge');
  $('etat').textContent = r.posee
    ? 'Une clef est rangee (elle finit par ' + r.apercu + ', ' + r.longueur + ' caracteres).'
    : "Aucune clef rangee. Arthur ne peut pas appeler le gros cerveau.";
}
$('voir').onclick = ()=>{ const c=$('cle');
  c.type = c.type==='password' ? 'text':'password';
  $('voir').textContent = c.type==='password' ? 'Montrer ce que je tape':'Cacher';
};
$('ranger').onclick = async ()=>{
  const r = await (await fetch('/ranger',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({cle: $('cle').value})})).json();
  dire(r.texte, r.ok); if(r.ok) $('cle').value=''; rafraichir();
};
$('essayer').onclick = async (e)=>{
  e.target.disabled=true; dire("J'appelle Nebius, patiente…", true);
  const r = await (await fetch('/essayer',{method:'POST'})).json();
  dire(r.texte, r.ok); e.target.disabled=false;
};
$('effacer').onclick = async ()=>{
  const r = await (await fetch('/effacer',{method:'POST'})).json();
  dire(r.texte, r.ok); rafraichir();
};
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
            return self._envoyer(json.dumps(etat_du_coffre()))
        self.send_error(404)

    def do_POST(self):
        taille = int(self.headers.get("Content-Length") or 0)
        brut = self.rfile.read(taille) if taille else b"{}"
        try:
            donnees = json.loads(brut or b"{}")
        except json.JSONDecodeError:
            donnees = {}

        if self.path == "/ranger":
            ok, texte = ranger(donnees.get("cle"))
            return self._envoyer(json.dumps({"ok": ok, "texte": texte}))
        if self.path == "/essayer":
            return self._envoyer(json.dumps(essayer()))
        if self.path == "/effacer":
            try:
                os.remove(COFFRE)
                return self._envoyer(json.dumps(
                    {"ok": True, "texte": "Clef effacee."}))
            except FileNotFoundError:
                return self._envoyer(json.dumps(
                    {"ok": True, "texte": "Il n'y avait deja rien."}))
        self.send_error(404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("La clef de Nebius  ->  http://127.0.0.1:%d" % PORT, flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Poste).serve_forever()
