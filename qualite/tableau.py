# -*- coding: utf-8 -*-
"""qualite/tableau.py — le tableau de bord des tests d'Arthur, en une page.

Une seule page HTML, SANS internet (ni police, ni bibliotheque, ni CDN) : les
donnees sont dans la page. Elle montre, d'un coup d'oeil :
  - ce qui est COUVERT, ce qui est INCOMPLET, ce qui n'a AUCUN TEST ;
  - quelles series de tests passent, echouent, ou sont sautees (et pourquoi) ;
  - pour chaque fichier : les lignes jamais executees, les fonctions jamais
    appelees, et les tests qui le couvrent.
Couleurs d'etat = toujours une icone ET un mot, jamais la couleur seule.
"""
import json


def ecrire(donnees, chemin):
    charge = json.dumps(donnees, ensure_ascii=False).replace("</", "<\\/")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(PAGE.replace("/*__DONNEES__*/null", charge))
    return chemin


PAGE = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Arthur — Tests</title>
<style>
:root{
  color-scheme:dark;
  --page:#001A2B; --surface:#052B42; --surface-2:#0a3552; --ring:rgba(249,249,255,.10);
  --ink:#F9F9FF; --ink-2:#b9c6d3; --muted:#8193a5; --grid:#16405c; --accent:#E0FF4F;
  --good:#0ca30c; --warn:#fab219; --crit:#d03b3b; --skip:#8193a5;
  --good-soft:rgba(12,163,12,.16); --warn-soft:rgba(250,178,25,.16); --crit-soft:rgba(208,59,59,.20);
  --code:#021f31;
}
@media (prefers-color-scheme: light){
  :root:where(:not([data-theme="dark"])){
    color-scheme:light;
    --page:#f3f5f7; --surface:#fcfcfb; --surface-2:#eef1f4; --ring:rgba(11,11,11,.10);
    --ink:#0b0b0b; --ink-2:#52514e; --muted:#6f6e69; --grid:#e1e0d9; --accent:#2a6b00;
    --good-soft:rgba(12,163,12,.12); --warn-soft:rgba(250,178,25,.20); --crit-soft:rgba(208,59,59,.12);
    --code:#f7f7f5;
  }
}
:root[data-theme="light"]{
  color-scheme:light;
  --page:#f3f5f7; --surface:#fcfcfb; --surface-2:#eef1f4; --ring:rgba(11,11,11,.10);
  --ink:#0b0b0b; --ink-2:#52514e; --muted:#6f6e69; --grid:#e1e0d9; --accent:#2a6b00;
  --good-soft:rgba(12,163,12,.12); --warn-soft:rgba(250,178,25,.20); --crit-soft:rgba(208,59,59,.12);
  --code:#f7f7f5;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--page);color:var(--ink);
  font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:20px 16px 60px}
header{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin-bottom:18px}
h1{font-size:22px;margin:0;letter-spacing:.2px}
h1 b{color:var(--accent)}
.meta{color:var(--muted);font-size:13px}
.chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--ring);border-radius:999px;
  padding:3px 10px;font-size:12px;color:var(--ink-2);background:var(--surface)}
button.theme{background:var(--surface);color:var(--ink);border:1px solid var(--ring);border-radius:10px;padding:6px 10px;cursor:pointer}
.grid{display:grid;gap:12px}
.hero{grid-template-columns:minmax(260px,1.3fr) repeat(4,minmax(150px,1fr))}
@media(max-width:980px){.hero{grid-template-columns:1fr 1fr}}
@media(max-width:560px){.hero{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:14px;padding:16px}
.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.6px}
.big{font-size:52px;font-weight:700;line-height:1.05;margin:6px 0 4px}
.val{font-size:30px;font-weight:700;margin:4px 0}
.sub{color:var(--ink-2);font-size:13px}
.meter{position:relative;height:10px;background:var(--surface-2);border-radius:6px;overflow:hidden;margin-top:12px}
.meter>i{position:absolute;inset:0 auto 0 0;border-radius:6px}
.meter .seuil{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--ink)}
.seg{display:flex;height:10px;border-radius:6px;overflow:hidden;gap:2px;margin:10px 0 8px;background:var(--surface-2)}
.seg>i{display:block;height:100%}
.leg{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:13px;color:var(--ink-2)}
.st{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
.dot{width:10px;height:10px;border-radius:50%;display:inline-block;flex:0 0 auto}
.good{color:var(--good)} .warn{color:var(--warn)} .crit{color:var(--crit)} .skip{color:var(--skip)}
.bg-good{background:var(--good)} .bg-warn{background:var(--warn)} .bg-crit{background:var(--crit)} .bg-skip{background:var(--skip)}
.pill{display:inline-flex;align-items:center;gap:5px;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.pill.good{background:var(--good-soft)} .pill.warn{background:var(--warn-soft)} .pill.crit{background:var(--crit-soft)}
.pill.skip{background:var(--surface-2)}
.tabs{display:flex;gap:6px;margin:22px 0 12px;flex-wrap:wrap;border-bottom:1px solid var(--ring)}
.tab{background:none;border:none;color:var(--ink-2);padding:10px 14px;font:inherit;cursor:pointer;border-bottom:2px solid transparent}
.tab[aria-selected=true]{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}
.f{background:var(--surface);border:1px solid var(--ring);color:var(--ink-2);border-radius:999px;padding:5px 12px;cursor:pointer;font:inherit;font-size:13px}
.f[aria-pressed=true]{color:var(--ink);border-color:var(--accent)}
input[type=search]{background:var(--surface);border:1px solid var(--ring);color:var(--ink);border-radius:10px;padding:7px 11px;font:inherit;min-width:220px;flex:1 1 220px;max-width:360px}
/* la carte */
.groupe{margin:0 0 18px}
.groupe h3{font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin:0 0 8px;font-weight:600}
.tuiles{display:flex;flex-wrap:wrap;gap:6px}
.tuile{position:relative;min-width:120px;border-radius:10px;padding:10px 10px 12px;cursor:pointer;
  background:var(--surface);border:1px solid var(--ring);overflow:hidden;text-align:left;color:var(--ink);font:inherit}
.tuile:hover,.tuile:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.tuile .n{font-size:13px;font-weight:600;word-break:break-all;padding-right:16px}
.tuile .p{font-size:20px;font-weight:700;margin-top:4px}
.tuile .fond{position:absolute;left:0;bottom:0;height:4px}
.tuile .icone{position:absolute;right:8px;top:8px;font-size:13px}
/* tables */
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--grid);vertical-align:middle}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.5px;cursor:pointer;user-select:none;white-space:nowrap}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tr.lien{cursor:pointer} tr.lien:hover td{background:var(--surface-2)}
.mini{display:inline-block;width:110px;height:8px;background:var(--surface-2);border-radius:5px;overflow:hidden;vertical-align:middle;margin-right:8px}
.mini>i{display:block;height:100%;border-radius:5px}
.pct{display:inline-block;min-width:4.2em;text-align:right}
.scroll{overflow-x:auto}
/* series */
details.serie{background:var(--surface);border:1px solid var(--ring);border-radius:12px;margin:0 0 8px}
details.serie>summary{list-style:none;cursor:pointer;padding:12px 14px;display:grid;
  grid-template-columns:auto 1fr auto;gap:10px;align-items:center}
details.serie>summary::-webkit-details-marker{display:none}
.serie .titre{font-weight:600;word-break:break-all}
.serie .res{color:var(--ink-2);font-size:13px;margin-top:2px}
.serie .corps{padding:0 14px 14px;border-top:1px solid var(--grid)}
.ep{display:flex;gap:8px;padding:5px 0;border-bottom:1px dashed var(--grid);font-size:13px}
.ep:last-child{border-bottom:none}
pre.sortie{max-height:260px;overflow:auto;background:var(--code);border-radius:8px;padding:10px;font-size:12px;white-space:pre-wrap}
/* fichier */
.fiche-tete{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
.fiche-grille{display:grid;grid-template-columns:320px minmax(0,1fr);gap:12px;margin-top:12px}
.fiche-grille>*,.fiche-tete>*{min-width:0}
.fiche-tete select{max-width:100%}
@media(max-width:900px){.fiche-grille{grid-template-columns:minmax(0,1fr)}}
.liste{max-height:560px;overflow:auto}
.fn{display:flex;justify-content:space-between;gap:8px;padding:6px 4px;border-bottom:1px solid var(--grid);font-size:13px;cursor:pointer}
.fn:hover{background:var(--surface-2)}
.fn code{word-break:break-all}
.source{background:var(--code);border-radius:12px;border:1px solid var(--ring);max-height:640px;overflow:auto;
  font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.ligne{display:grid;grid-template-columns:54px 1fr;white-space:pre;border-left:4px solid transparent}
.ligne .no{color:var(--muted);text-align:right;padding-right:12px;user-select:none}
.ligne.c{border-left-color:var(--good)}
.ligne.m{border-left-color:var(--crit);background:var(--crit-soft)}
.ligne.x{border-left-color:var(--skip);opacity:.55}
.ligne.cible{outline:2px solid var(--accent)}
.vide{color:var(--muted);padding:24px;text-align:center}
.tip{position:fixed;pointer-events:none;z-index:9;background:var(--surface-2);color:var(--ink);border:1px solid var(--ring);
  border-radius:10px;padding:8px 10px;font-size:13px;box-shadow:0 6px 18px rgba(0,0,0,.35);max-width:280px;display:none}
svg text{fill:var(--muted);font-size:11px}
.aide{color:var(--ink-2);font-size:13px;margin:6px 0 0}
a{color:var(--accent)}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1><b>Arthur</b> — tests &amp; couverture</h1>
      <div class="meta" id="meta"></div>
    </div>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <span class="chip" title="pytest vient de vendor/, la mesure est écrite en Python standard">◆ tout vient du dépôt</span>
      <button class="theme" id="theme" aria-label="Changer de thème">◐ thème</button>
    </div>
  </header>

  <section class="grid hero" id="hero"></section>
  <section class="card" id="evolution" style="margin-top:12px;display:none"></section>

  <nav class="tabs" role="tablist">
    <button class="tab" role="tab" data-v="carte" aria-selected="true">Carte</button>
    <button class="tab" role="tab" data-v="modules" aria-selected="false">Modules</button>
    <button class="tab" role="tab" data-v="tests" aria-selected="false">Tests</button>
    <button class="tab" role="tab" data-v="fichier" aria-selected="false">Fichier</button>
  </nav>
  <main id="vue"></main>
</div>
<div class="tip" id="tip"></div>

<script>
const D = /*__DONNEES__*/null;
const $ = (s, r=document) => r.querySelector(s);
const el = (tag, attrs={}, ...enfants) => {
  const e = document.createElement(tag);
  for (const [k,v] of Object.entries(attrs)) {
    if (k === "class") e.className = v; else if (k === "style") e.style.cssText = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v);
  }
  for (const c of enfants.flat()) if (c != null) e.append(c.nodeType ? c : document.createTextNode(String(c)));
  return e;
};
const ETAT = {
  "couvert":   {cls:"good", ic:"✓", mot:"Couvert"},
  "incomplet": {cls:"warn", ic:"!", mot:"Incomplet"},
  "sans test": {cls:"crit", ic:"✗", mot:"Sans test"},
};
const SERIE = {
  vert:  {cls:"good", ic:"✓", mot:"Passe"},
  rouge: {cls:"crit", ic:"✗", mot:"Échoue"},
  saute: {cls:"skip", ic:"~", mot:"Sautée"},
};
const pill = (o) => el("span", {class:"pill "+o.cls}, o.ic+" "+o.mot);
const couleurPct = (p, touche) => !touche ? "var(--crit)" : (p >= D.seuil ? "var(--good)" : "var(--warn)");
const T = D.totaux;

/* ---------- thème ---------- */
(() => {
  let t = null; try { t = localStorage.getItem("arthur-theme"); } catch(e) {}
  if (t) document.documentElement.dataset.theme = t;
  $("#theme").onclick = () => {
    const sombre = getComputedStyle(document.documentElement).colorScheme.includes("dark");
    const n = sombre ? "light" : "dark";
    document.documentElement.dataset.theme = n;
    try { localStorage.setItem("arthur-theme", n); } catch(e) {}
  };
})();

/* ---------- infobulle ---------- */
const tip = $("#tip");
function montrerTip(ev, html) {
  tip.replaceChildren(...html); tip.style.display = "block";
  const x = Math.min(ev.clientX + 14, innerWidth - tip.offsetWidth - 8);
  const y = Math.min(ev.clientY + 14, innerHeight - tip.offsetHeight - 8);
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
const cacherTip = () => tip.style.display = "none";

/* ---------- en-tête et tuiles ---------- */
$("#meta").textContent = `Mesuré le ${D.date.replace("T"," à ")} · Python ${D.python} · ${D.duree} s · seuil « couvert » : ${D.seuil} %`;

function tuileKPI(label, valeur, sous, extra) {
  return el("div", {class:"card"}, el("div", {class:"label"}, label),
    el("div", {class:"val"}, valeur), el("div", {class:"sub"}, sous), extra || null);
}
function segments(parts) {
  const total = parts.reduce((a,p)=>a+p.n,0) || 1;
  return el("div", {class:"seg", role:"img", "aria-label": parts.map(p=>p.n+" "+p.mot).join(", ")},
    parts.filter(p=>p.n).map(p => el("i", {class:"bg-"+p.cls, style:`width:${100*p.n/total}%`})));
}
function legende(parts) {
  return el("div", {class:"leg"}, parts.map(p => el("span", {class:"st"},
    el("span", {class:"dot bg-"+p.cls}), `${p.ic} ${p.n} ${p.mot}`)));
}
(() => {
  const h = $("#hero");
  const pc = T.pourcent;
  h.append(el("div", {class:"card"},
    el("div", {class:"label"}, "Couverture du code d'Arthur"),
    el("div", {class:"big"}, pc.toLocaleString("fr-FR") + " %"),
    el("div", {class:"sub"}, `${T.couvertes.toLocaleString("fr-FR")} lignes exécutées sur ${T.lignes.toLocaleString("fr-FR")}`),
    el("div", {class:"meter", role:"img", "aria-label":`${pc} % couvert, seuil ${D.seuil} %`},
      el("i", {style:`width:${pc}%;background:${couleurPct(pc, T.couvertes)}`}),
      el("span", {class:"seuil", style:`left:${D.seuil}%`, title:"seuil " + D.seuil + " %"}))));
  const mods = [{n:T.couverts,cls:"good",ic:"✓",mot:"couverts"},{n:T.incomplets,cls:"warn",ic:"!",mot:"incomplets"},{n:T.sans_test,cls:"crit",ic:"✗",mot:"sans test"}];
  h.append(tuileKPI("Modules", T.modules, "fichiers de code mesurés", el("div", {}, segments(mods), legende(mods))));
  const ser = [{n:T.series_vertes,cls:"good",ic:"✓",mot:"passent"},{n:T.series_rouges,cls:"crit",ic:"✗",mot:"échouent"},{n:T.series_sautees,cls:"skip",ic:"~",mot:"sautées"}];
  h.append(tuileKPI("Séries de tests", T.series, "fichiers de tests lancés", el("div", {}, segments(ser), legende(ser))));
  h.append(tuileKPI("Épreuves", T.epreuves.toLocaleString("fr-FR"), `${T.epreuves_vertes.toLocaleString("fr-FR")} passent (chaque vérification compte)`));
  h.append(tuileKPI("Fonctions jamais appelées", T.fonctions_jamais, `sur ${T.fonctions} fonctions`,
    el("div", {class:"meter"}, el("i", {style:`width:${T.fonctions ? 100*T.fonctions_jamais/T.fonctions : 0}%;background:var(--crit)`}))));
})();

/* ---------- évolution ---------- */
(() => {
  const H = (D.historique || []);
  if (H.length < 2) return;
  const box = $("#evolution"); box.style.display = "block";
  box.append(el("div", {class:"label"}, "Couverture, mesure après mesure"));
  const W = 1000, Ht = 150, g = {l:48, r:12, t:12, b:22};
  const x = i => g.l + i * (W - g.l - g.r) / (H.length - 1);
  const y = v => g.t + (100 - v) * (Ht - g.t - g.b) / 100;
  const ns = "http://www.w3.org/2000/svg";
  const s = document.createElementNS(ns, "svg");
  s.setAttribute("viewBox", `0 0 ${W} ${Ht}`); s.setAttribute("width","100%"); s.setAttribute("role","img");
  s.setAttribute("aria-label", "Couverture de " + H[0].pourcent + " % à " + H[H.length-1].pourcent + " %");
  const mk = (t, a) => { const e = document.createElementNS(ns, t); for (const k in a) e.setAttribute(k, a[k]); s.append(e); return e; };
  for (const v of [0, 50, 100]) {
    mk("line", {x1:g.l, x2:W-g.r, y1:y(v), y2:y(v), stroke:"var(--grid)", "stroke-width":1});
    mk("text", {x:g.l-6, y:y(v)+4, "text-anchor":"end"}).textContent = v + " %";
  }
  mk("line", {x1:g.l, x2:W-g.r, y1:y(D.seuil), y2:y(D.seuil), stroke:"var(--muted)", "stroke-dasharray":"4 4"});
  mk("path", {d: H.map((p,i)=>(i?"L":"M")+x(i)+" "+y(p.pourcent)).join(""), fill:"none", stroke:"var(--accent)", "stroke-width":2});
  const der = H[H.length-1];
  mk("circle", {cx:x(H.length-1), cy:y(der.pourcent), r:4, fill:"var(--accent)"});
  const croix = mk("line", {y1:g.t, y2:Ht-g.b, stroke:"var(--muted)", "stroke-width":1, visibility:"hidden"});
  const zone = mk("rect", {x:g.l, y:0, width:W-g.l-g.r, height:Ht, fill:"transparent"});
  zone.addEventListener("mousemove", ev => {
    const r = s.getBoundingClientRect();
    const i = Math.max(0, Math.min(H.length-1, Math.round(((ev.clientX - r.left) * W / r.width - g.l) / ((W-g.l-g.r)/(H.length-1)))));
    croix.setAttribute("x1", x(i)); croix.setAttribute("x2", x(i)); croix.setAttribute("visibility","visible");
    const p = H[i];
    montrerTip(ev, [el("b", {}, p.date.replace("T"," ")), el("br"), `Couverture : ${p.pourcent} %`, el("br"), `Séries : ${p.vertes} passent · ${p.rouges} échouent`]);
  });
  zone.addEventListener("mouseleave", () => { croix.setAttribute("visibility","hidden"); cacherTip(); });
  box.append(s);
})();

/* ---------- navigation ---------- */
let vueCourante = "carte", fichierCourant = null;
const vues = {carte, modules, tests, fichier};
function aller(v, arg) {
  vueCourante = v;
  if (v === "fichier" && arg !== undefined) fichierCourant = arg;
  document.querySelectorAll(".tab").forEach(b => b.setAttribute("aria-selected", b.dataset.v === v));
  const m = $("#vue"); m.replaceChildren(); vues[v](m);
  try { history.replaceState(null, "", "#" + v + (v === "fichier" && fichierCourant ? ":" + fichierCourant : "")); } catch(e) {}
}
document.querySelectorAll(".tab").forEach(b => b.onclick = () => aller(b.dataset.v));

const parFichier = Object.fromEntries(D.modules.map(m => [m.fichier, m]));
const seriesParModule = {};
for (const m of D.modules) for (const t of m.tests) (seriesParModule[t] = seriesParModule[t] || []).push(m.fichier);

/* un nom court, avec son dossier quand deux fichiers portent le même nom */
const nomsVus = {};
for (const x of D.modules) { const n = x.fichier.split("/").pop(); nomsVus[n] = (nomsVus[n] || 0) + 1; }
function nomCourt(f) {
  const p = f.split("/"), n = p.pop();
  return nomsVus[n] > 1 && p.length ? p[p.length-1] + "/" + n : n;
}

/* ---------- vue : carte ---------- */
function carte(m) {
  m.append(el("p", {class:"aide"}, "Chaque tuile est un fichier du code d'Arthur ; sa largeur suit sa taille (lignes exécutables). Clique pour voir ses lignes."));
  const groupes = {};
  for (const x of D.modules) (groupes[x.groupe] = groupes[x.groupe] || []).push(x);
  const ordre = Object.keys(groupes).sort((a,b) => (a==="coeur"?-1:b==="coeur"?1:a.localeCompare(b)));
  const maxL = Math.max(...D.modules.map(x => x.executables), 1);
  for (const g of ordre) {
    const liste = groupes[g].sort((a,b) => b.executables - a.executables);
    const cov = liste.reduce((a,x)=>a+x.couvertes,0), exe = liste.reduce((a,x)=>a+x.executables,0);
    const sec = el("section", {class:"groupe"}, el("h3", {}, `${g === "coeur" ? "cœur (racine)" : g + "/"} · ${exe ? Math.round(100*cov/exe) : 100} %`));
    const tuiles = el("div", {class:"tuiles"});
    for (const x of liste) {
      const e = ETAT[x.verdict];
      const t = el("button", {class:"tuile", style:`flex:${Math.max(1, Math.sqrt(x.executables/maxL)*10)} 1 ${120 + 80*Math.sqrt(x.executables/maxL)}px`,
          "aria-label": `${x.fichier} : ${x.pourcent} %, ${e.mot}`,
          onclick: () => aller("fichier", x.fichier)},
        el("span", {class:"icone " + e.cls}, e.ic),
        el("div", {class:"n"}, nomCourt(x.fichier)),
        el("div", {class:"p " + e.cls}, x.pourcent + " %"),
        el("div", {class:"sub"}, `${x.couvertes}/${x.executables} lignes`),
        el("span", {class:"fond bg-" + e.cls, style:`width:${x.pourcent}%`}));
      t.addEventListener("mousemove", ev => montrerTip(ev, [el("b", {}, x.fichier), el("br"),
        `${e.ic} ${e.mot} · ${x.pourcent} %`, el("br"),
        `${x.fonctions.filter(f=>f.etat==="jamais appelee").length} fonction(s) jamais appelée(s) sur ${x.fonctions.length}`, el("br"),
        `${x.tests.length} série(s) de tests le touchent`]));
      t.addEventListener("mouseleave", cacherTip);
      tuiles.append(t);
    }
    sec.append(tuiles); m.append(sec);
  }
}

/* ---------- vue : modules ---------- */
let filtreModule = "tous", triModule = {cle:"pourcent", sens:1}, rechercheModule = "";
function modules(m) {
  const filtres = [["tous","Tous", D.modules.length],["couvert","✓ Couverts",T.couverts],["incomplet","! Incomplets",T.incomplets],["sans test","✗ Sans test",T.sans_test]];
  const barre = el("div", {class:"bar"},
    filtres.map(([k,lib,n]) => el("button", {class:"f", "aria-pressed": filtreModule===k,
      onclick: () => { filtreModule = k; aller("modules"); }}, `${lib} (${n})`)),
    el("input", {type:"search", placeholder:"Chercher un fichier…", value: rechercheModule,
      oninput: ev => { rechercheModule = ev.target.value; remplir(); }}));
  m.append(barre);
  const cols = [["verdict","État"],["fichier","Fichier"],["pourcent","Couverture"],["lignes","Lignes"],["jamais","Fonctions jamais appelées"],["tests","Séries qui le touchent"]];
  const tbody = el("tbody");
  const table = el("table", {}, el("thead", {}, el("tr", {}, cols.map(([k,lib]) =>
    el("th", {class: ["pourcent","lignes","jamais","tests"].includes(k) ? "num" : "",
      onclick: () => { triModule = {cle:k, sens: triModule.cle===k ? -triModule.sens : 1}; remplir(); }},
      lib + (triModule.cle===k ? (triModule.sens>0 ? " ▲" : " ▼") : ""))))), tbody);
  const valeur = (x,k) => k==="lignes" ? x.executables : k==="jamais" ? x.fonctions.filter(f=>f.etat==="jamais appelee").length
    : k==="tests" ? x.tests.length : k==="verdict" ? ["sans test","incomplet","couvert"].indexOf(x.verdict) : x[k];
  function remplir() {
    const q = rechercheModule.toLowerCase();
    const rows = D.modules.filter(x => (filtreModule==="tous" || x.verdict===filtreModule) && x.fichier.toLowerCase().includes(q))
      .sort((a,b) => { const va = valeur(a,triModule.cle), vb = valeur(b,triModule.cle);
        return (va>vb?1:va<vb?-1:0) * triModule.sens; });
    tbody.replaceChildren(...rows.map(x => {
      const e = ETAT[x.verdict]; const jamais = valeur(x,"jamais");
      return el("tr", {class:"lien", tabindex:0, onclick: () => aller("fichier", x.fichier),
          onkeydown: ev => { if (ev.key === "Enter") aller("fichier", x.fichier); }},
        el("td", {}, pill(e)),
        el("td", {}, el("code", {}, x.fichier)),
        el("td", {class:"num"}, el("span", {class:"mini"}, el("i", {style:`width:${x.pourcent}%;background:${couleurPct(x.pourcent, x.couvertes)}`})), el("span", {class:"pct"}, x.pourcent + " %")),
        el("td", {class:"num"}, `${x.couvertes} / ${x.executables}`),
        el("td", {class:"num " + (jamais ? "crit" : "")}, jamais ? `✗ ${jamais}` : "—"),
        el("td", {class:"num"}, x.tests.length || "—"));
    }));
    if (!rows.length) tbody.append(el("tr", {}, el("td", {colspan:6, class:"vide"}, "Aucun fichier ne correspond.")));
  }
  remplir();
  m.append(el("div", {class:"card scroll", style:"padding:4px 8px"}, table));
}

/* ---------- vue : tests ---------- */
let filtreSerie = "tous";
function tests(m) {
  const n = k => D.series.filter(s => s.etat === k).length;
  m.append(el("div", {class:"bar"},
    [["tous","Toutes",D.series.length],["rouge","✗ Échouent",n("rouge")],["saute","~ Sautées",n("saute")],["vert","✓ Passent",n("vert")]]
      .map(([k,lib,c]) => el("button", {class:"f", "aria-pressed": filtreSerie===k, onclick: () => { filtreSerie = k; aller("tests"); }}, `${lib} (${c})`))));
  const ordre = {rouge:0, saute:1, vert:2};
  const liste = D.series.filter(s => filtreSerie==="tous" || s.etat===filtreSerie)
    .sort((a,b) => ordre[a.etat]-ordre[b.etat] || a.id.localeCompare(b.id));
  for (const s of liste) {
    const e = SERIE[s.etat];
    const couvre = seriesParModule[s.id] || [];
    const vertes = s.epreuves.filter(x=>x.etat==="vert").length;
    const d = el("details", {class:"serie"},
      el("summary", {},
        pill(e),
        el("div", {}, el("div", {class:"titre"}, s.id),
          el("div", {class:"res"}, s.raison ? "→ " + s.raison : (s.resume || ""))),
        el("div", {class:"sub", style:"text-align:right"}, `${s.epreuves.length ? vertes + "/" + s.epreuves.length + " épreuves · " : ""}${s.duree} s`)));
    const corps = el("div", {class:"corps"});
    if (s.resume && s.raison) corps.append(el("p", {class:"aide"}, s.resume));
    corps.append(el("p", {class:"aide"}, couvre.length ? "Touche : " : "Ne touche aucun fichier du code d'Arthur.",
      ...couvre.map((f,i) => [i ? ", " : "", el("a", {href:"#", onclick: ev => { ev.preventDefault(); aller("fichier", f); }}, f)])));
    if (s.epreuves.length) {
      const liste = el("div", {});
      for (const x of s.epreuves) {
        const ee = SERIE[x.etat] || SERIE.saute;
        liste.append(el("div", {class:"ep"}, el("span", {class:ee.cls, style:"min-width:1.2em"}, ee.ic),
          el("span", {}, x.nom, x.detail ? el("div", {class:"sub"}, x.detail) : null)));
      }
      corps.append(liste);
    }
    if (s.etat !== "vert") corps.append(el("pre", {class:"sortie"}, s.sortie.slice(-3000)));
    d.append(corps); m.append(d);
  }
  if (!liste.length) m.append(el("div", {class:"vide"}, "Aucune série dans ce filtre."));
}

/* ---------- vue : fichier ---------- */
function fichier(m) {
  const x = parFichier[fichierCourant] || D.modules.slice().sort((a,b)=>a.pourcent-b.pourcent)[0];
  fichierCourant = x.fichier;
  const choix = el("select", {class:"f", "aria-label":"Choisir un fichier", onchange: ev => aller("fichier", ev.target.value)},
    D.modules.slice().sort((a,b)=>a.fichier.localeCompare(b.fichier)).map(y =>
      el("option", Object.assign({value:y.fichier}, y.fichier===x.fichier ? {selected:""} : {}), `${ETAT[y.verdict].ic} ${y.fichier} — ${y.pourcent} %`)));
  const e = ETAT[x.verdict];
  const manquees = new Set(x.manquees), exclues = new Set();
  for (const r of x.exclusions) for (let i = r.lignes[0]; i <= r.lignes[1]; i++) exclues.add(i);
  const executees = x.executables - x.manquees.length;
  m.append(el("div", {class:"card fiche-tete"},
    el("div", {}, el("div", {class:"label"}, "Fichier"), el("div", {style:"font-size:18px;font-weight:700;word-break:break-all"}, x.fichier),
      el("div", {class:"sub"}, `${executees} lignes exécutées sur ${x.executables} · ${x.fonctions.length} fonctions · ${x.tests.length} série(s) de tests`)),
    el("div", {style:"display:flex;gap:10px;align-items:center;flex-wrap:wrap"}, pill(e),
      el("span", {class:"val " + e.cls}, x.pourcent + " %"), choix)));

  const gauche = el("div", {class:"grid", style:"align-content:start"});
  const fns = x.fonctions.slice().sort((a,b) => a.pourcent - b.pourcent || a.ligne - b.ligne);
  const etatsFn = {"jamais appelee":{cls:"crit",ic:"✗"}, "partielle":{cls:"warn",ic:"!"}, "complete":{cls:"good",ic:"✓"}};
  gauche.append(el("div", {class:"card"},
    el("div", {class:"label"}, `Fonctions (${fns.filter(f=>f.etat==="jamais appelee").length} jamais appelées)`),
    fns.length ? el("div", {class:"liste"}, fns.map(f => { const ef = etatsFn[f.etat];
      return el("div", {class:"fn", onclick: () => viser(f.ligne), title: f.etat},
        el("span", {}, el("span", {class:ef.cls}, ef.ic + " "), el("code", {}, f.nom)),
        el("span", {class:"sub " + ef.cls}, f.pourcent + " %")); }))
      : el("div", {class:"vide"}, "Aucune fonction.")));
  gauche.append(el("div", {class:"card"}, el("div", {class:"label"}, "Séries qui le touchent"),
    x.tests.length ? x.tests.map(t => { const s = D.series.find(y=>y.id===t) || {etat:"saute"};
      return el("div", {class:"fn", onclick: () => { filtreSerie = "tous"; aller("tests"); }},
        el("code", {}, t), el("span", {class:SERIE[s.etat].cls}, SERIE[s.etat].ic)); })
      : el("div", {class:"vide crit"}, "✗ Aucun test ne touche ce fichier.")));
  if (x.exclusions.length) gauche.append(el("div", {class:"card"}, el("div", {class:"label"}, "Exclu de la mesure"),
    x.exclusions.map(r => el("div", {class:"sub"}, `lignes ${r.lignes[0]}–${r.lignes[1]} : ${r.pourquoi}`))));

  const src = el("div", {class:"source", tabindex:0, "aria-label":"Code source avec la couverture"});
  x.source.forEach((txt, i) => {
    const n = i + 1;
    const cls = manquees.has(n) ? "m" : exclues.has(n) ? "x" : "";
    src.append(el("div", {class:"ligne " + cls, id:"L"+n}, el("span", {class:"no"}, n), txt || " "));
  });
  for (const n of x.lignes_couvertes) { const l = $("#L"+n, src); if (l) l.classList.add("c"); }
  const droite = el("div", {},
    el("div", {class:"bar"},
      el("span", {class:"st"}, el("span", {class:"dot bg-good"}), "✓ exécutée"),
      el("span", {class:"st"}, el("span", {class:"dot bg-crit"}), "✗ jamais exécutée"),
      el("span", {class:"st"}, el("span", {class:"dot bg-skip"}), "exclue"),
      x.manquees.length ? el("button", {class:"f", onclick: () => viser(x.manquees[0])}, "→ première ligne manquée") : null),
    src);
  function viser(n) {
    src.querySelectorAll(".cible").forEach(e => e.classList.remove("cible"));
    const l = $("#L"+n, src); if (!l) return;
    l.classList.add("cible"); src.scrollTop = l.offsetTop - 80;
  }
  m.append(el("div", {class:"fiche-grille"}, gauche, droite));
}

/* ---------- départ (et adresse # : favoris, bouton retour) ---------- */
function depuisAdresse() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (h.startsWith("fichier:")) aller("fichier", h.slice(8));
  else aller(vues[h] ? h : "carte");
}
addEventListener("hashchange", depuisAdresse);
depuisAdresse();
</script>
</body>
</html>
"""
