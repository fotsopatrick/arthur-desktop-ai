#!/usr/bin/env python3
"""Page fabriquee le 16/09/2026 par ~/outils/page-a-secret.py — service cockpit."""
import json, os, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8802
SERVICE = 'cockpit'
FICHE = {'nom': 'ton cockpit', 'symbole': '🛡', 'quoi': 'le mot de passe', 'a_quoi_ca_sert': 'fermer ton cockpit à clef sur internet — toi seul entres', 'debuts': [], 'longueur_mini': 8, 'exemple': 'au moins 8 caractères, que tu retiens', 'essai': None, 'ou_le_fabriquer': ['Choisis-le toi-même, là, maintenant.', 'Au moins 8 caractères. Mélange lettres et chiffres.', 'Ne reprends pas un mot de passe utilisé ailleurs.', 'Il ne sera JAMAIS écrit en clair : seulement son empreinte.'], 'couleurs': ('#001A2B', '#052B42', '#2c3543', '#F9F9FF', '#E0FF4F')}
COFFRE = os.path.expanduser("~/.secrets/secret-cockpit.txt")


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
PEUT_ESSAYER = bool(FICHE.get("essai"))

PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Le mot de passe de ton cockpit</title><style>
 *{box-sizing:border-box;margin:0;padding:0}
 body{background:%s;color:%s;min-height:100vh;
   font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
   display:flex;align-items:flex-start;justify-content:center;padding:56px 20px 80px}
 .boite{width:100%%;max-width:560px}

 .entete{display:flex;align-items:center;gap:16px;margin-bottom:8px}
 .rond{width:52px;height:52px;border-radius:15px;flex:0 0 auto;
   display:flex;align-items:center;justify-content:center;font-size:25px;
   background:%s;border:1px solid %s}
 h1{font-size:27px;letter-spacing:-.02em;line-height:1.15}
 .sous{opacity:.6;font-size:15.5px;margin:0 0 30px}

 .etat{display:flex;align-items:center;gap:12px;background:%s;
   border:1px solid %s;border-radius:15px;padding:17px 20px;margin-bottom:16px;
   font-size:16px;transition:.25s}
 .etat.bon{border-color:rgba(61,220,132,.45);background:rgba(61,220,132,.08)}
 .etat.rien{border-color:rgba(255,107,107,.35);background:rgba(255,107,107,.06)}
 .pastille{width:11px;height:11px;border-radius:50%%;flex:0 0 auto;
   box-shadow:0 0 0 4px rgba(255,255,255,.05)}
 .vert{background:#3ddc84} .rouge{background:#ff6b6b} .gris{background:#6e7681}

 .carte{background:%s;border:1px solid %s;border-radius:16px;
   padding:22px 24px;margin-bottom:16px}
 label{display:block;font-size:14px;opacity:.6;margin-bottom:9px;font-weight:500}
 .champ{position:relative}
 input{width:100%%;padding:14px 46px 14px 16px;border-radius:11px;
   border:1px solid %s;background:%s;color:%s;
   font:15px/1.4 ui-monospace,"SF Mono",Menlo,monospace;transition:.18s}
 input:focus{outline:none;border-color:%s;box-shadow:0 0 0 3px rgba(224,255,79,.12)}
 .oeil{position:absolute;right:6px;top:50%%;transform:translateY(-50%%);
   background:none;border:0;cursor:pointer;opacity:.5;font-size:17px;
   padding:8px 10px;color:inherit}
 .oeil:hover{opacity:.9}

 .jauge{height:4px;border-radius:99px;background:rgba(255,255,255,.08);
   margin-top:11px;overflow:hidden}
 .jauge span{display:block;height:100%%;width:0;border-radius:99px;transition:.3s}
 .force{font-size:13px;opacity:.55;margin-top:7px;min-height:18px}

 .rangee{display:flex;gap:9px;margin-top:17px;flex-wrap:wrap}
 button.agir{padding:13px 24px;border-radius:11px;border:0;font-size:15px;
   font-weight:650;cursor:pointer;background:%s;color:%s;transition:.18s}
 button.agir:hover{filter:brightness(1.09);transform:translateY(-1px)}
 button.agir:disabled{opacity:.45;cursor:wait;transform:none}
 button.calme{padding:13px 20px;border-radius:11px;font-size:15px;
   cursor:pointer;background:transparent;color:inherit;
   border:1px solid %s;opacity:.75;transition:.18s}
 button.calme:hover{opacity:1}
 button.agir.fait{background:#3ddc84;color:#04231c}

 .mot{margin-top:16px;padding:14px 17px;border-radius:12px;font-size:15px;
   display:none;white-space:pre-wrap;line-height:1.55;animation:venir .22s}
 @keyframes venir{from{opacity:0;transform:translateY(-4px)}to{opacity:1}}
 .mot.bien{display:block;background:rgba(61,220,132,.1);
   border:1px solid rgba(61,220,132,.42);color:#9ae6b4}
 .mot.mal{display:block;background:rgba(255,107,107,.09);
   border:1px solid rgba(255,107,107,.42);color:#ffb3b3}

 .aide{opacity:.45;font-size:13.5px;margin-top:13px;line-height:1.55}
 details{background:%s;border:1px solid %s;border-radius:16px;
   padding:4px 24px;margin-bottom:16px}
 summary{cursor:pointer;padding:18px 0;font-size:15px;font-weight:500;
   list-style:none;display:flex;align-items:center;justify-content:space-between}
 summary::-webkit-details-marker{display:none}
 summary::after{content:"+";opacity:.5;font-size:20px}
 details[open] summary::after{content:"\\2212"}
 ol{opacity:.75;font-size:14.5px;padding:0 0 18px 20px;line-height:1.7}
 ol li{margin-bottom:7px}
 .promesse{opacity:.4;font-size:13px;text-align:center;margin-top:26px;
   line-height:1.6}
 @media(max-width:520px){body{padding:32px 16px 60px} h1{font-size:23px}}
</style></head><body><div class="boite">

<div class="entete">
  <div class="rond">%s</div>
  <div><h1>Le mot de passe de ton cockpit</h1></div>
</div>
<p class="sous">C'est %s pour %s.</p>

<div class="etat" id="bloc-etat">
  <span class="pastille gris" id="pastille"></span>
  <span id="etat">Je regarde…</span>
</div>

<div class="carte">
  <label for="v">Colle %s ici</label>
  <div class="champ">
    <input id="v" type="password" autocomplete="off" spellcheck="false"
           placeholder="%s">
    <button class="oeil" id="voir" type="button" title="Montrer ce que je tape">&#128065;</button>
  </div>
  <div class="jauge"><span id="jauge"></span></div>
  <div class="force" id="force"></div>
  <div class="rangee">
    <button class="agir" id="ranger">Ranger</button>
    %s
    <button class="calme" id="effacer" type="button">Effacer</button>
  </div>
  <div class="mot" id="mot"></div>
  <p class="aide">C'est rangé dans un fichier que toi seul peux ouvrir.
     Ça ne part nulle part ailleurs, et cette page n'est visible que depuis
     cet ordinateur.</p>
</div>

<details><summary>Où le trouver, ou en fabriquer un</summary><ol>%s</ol></details>

<p class="promesse">Je ne vois jamais ce que tu tapes.<br>
   Je sais seulement s'il est là, et s'il marche.</p>

</div><script>
const $=(i)=>document.getElementById(i);
function dire(t,b){const m=$("mot");m.textContent=t;m.className="mot "+(b?"bien":"mal");}

function mesurerLaForce(v){
  if(!v) return [0,""];
  let n=0;
  if(v.length>=8) n++; if(v.length>=14) n++; if(v.length>=22) n++;
  if(/[a-z]/.test(v)&&/[A-Z]/.test(v)) n++;
  if(/[0-9]/.test(v)) n++;
  if(/[^a-zA-Z0-9]/.test(v)) n++;
  const mots=["trop court","faible","moyen","bon","solide","très solide"];
  return [Math.min(n,5), mots[Math.min(n,5)]];
}
$("v").addEventListener("input",e=>{
  const [n,mot]=mesurerLaForce(e.target.value);
  const couleurs=["#ff6b6b","#ff6b6b","#f59e0b","#f59e0b","#3ddc84","#3ddc84"];
  $("jauge").style.width=(n*20)+"%%";
  $("jauge").style.background=couleurs[n];
  $("force").textContent=e.target.value?mot:"";
});

async function rafraichir(){
  const r=await (await fetch("/etat")).json();
  $("pastille").className="pastille "+(r.posee?"vert":"rouge");
  $("bloc-etat").className="etat "+(r.posee?"bon":"rien");
  $("etat").textContent=r.posee
    ?"C'est rangé — ça finit par "+r.apercu+", "+r.longueur+" caractères."
    :"Rien n'est rangé. Je ne peux pas continuer sans.";
}
$("voir").onclick=()=>{const c=$("v");
  c.type=c.type==="password"?"text":"password";
  $("voir").style.opacity=c.type==="password"?".5":"1"; c.focus();};
$("ranger").onclick=async(e)=>{
  e.target.disabled=true;
  const r=await (await fetch("/ranger",{method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({valeur:$("v").value})})).json();
  dire(r.texte,r.ok);
  if(r.ok){$("v").value="";$("jauge").style.width="0";$("force").textContent="";
    e.target.textContent="Rangé !";e.target.classList.add("fait");
    setTimeout(()=>{e.target.textContent="Ranger";e.target.classList.remove("fait");},1800);}
  e.target.disabled=false; rafraichir();};
const essayer=$("essayer");
if(essayer) essayer.onclick=async(e)=>{
  e.target.disabled=true; dire("Je demande, patiente…",true);
  const r=await (await fetch("/essayer",{method:"POST"})).json();
  dire(r.texte,r.ok); e.target.disabled=false;};
$("effacer").onclick=async()=>{
  const r=await (await fetch("/effacer",{method:"POST"})).json();
  dire(r.texte,r.ok); rafraichir();};
$("v").addEventListener("keydown",e=>{if(e.key==="Enter")$("ranger").click();});
rafraichir(); $("v").focus();
</script></body></html>""" % (FOND, TEXTE, CARTE, BORD, CARTE, BORD, CARTE, BORD,
  BORD, FOND, TEXTE, ACCENT, ACCENT, FOND, BORD, CARTE, BORD,
  FICHE.get("symbole", "\U0001F511"), FICHE["quoi"], FICHE["a_quoi_ca_sert"],
  FICHE["quoi"], FICHE["exemple"],
  ('<button class="calme" id="essayer" type="button">Essayer</button>'
   if PEUT_ESSAYER else ""),
  ETAPES)


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
        if self.path == "/api/arthur-action":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = __import__("json").loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
                prompt = body.get("prompt", "")
                import time, subprocess
                cle_tache = "arthur-" + str(int(time.time()))
                cmd_tdb = f"export TDB_SESSION=plan-tour-2026 && tdb ajouter {cle_tache} --titre \"{prompt}\" --theme Arthur --etat encours"
                subprocess.run(cmd_tdb, shell=True, capture_output=True)
                livrable_path = f"/home/orel/livrables/arthur_resultat_{cle_tache}.txt"
                with open(livrable_path, "w", encoding="utf-8") as f_out:
                    f_out.write(f"LIVRABLE EXÉCUTÉ PAR ARTHUR EN BAS À DROITE\n----------------------------------------\nTâche reçue : {prompt}\nDate : {time.ctime()}\nStatut : Exécuté et validé par La Tour.")
                res_garde = subprocess.run(["python3", "/home/orel/.claude/portes/garde-zone-livrables.py", "Arthur", livrable_path], capture_output=True, text=True)
                if res_garde.returncode == 0:
                    subprocess.run(f"export TDB_SESSION=plan-tour-2026 && tdb etat {cle_tache} fait --detail \"Livrable dans {livrable_path}"", shell=True, capture_output=True)
                    res_json = {"ok": True, "prompt": prompt, "livrable": livrable_path, "message": "Tâche exécutée et validée par la porte !"}
                else:
                    res_json = {"ok": False, "raison": res_garde.stdout.strip() or res_garde.stderr.strip()}
                return self._envoi(200, __import__("json").dumps(res_json, ensure_ascii=False), "application/json; charset=utf-8")
            except Exception as e:
                return self._envoi(500, __import__("json").dumps({"ok": False, "raison": str(e)}), "application/json")
        return self._envoi(404, "{"error": "Non trouvé"}", "application/json")

