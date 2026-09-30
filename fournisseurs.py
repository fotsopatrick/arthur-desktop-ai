#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fournisseurs.py — le gros cerveau d'Arthur est INTERCHANGEABLE.

Ne le 29/09/2026. Patrick l'avait demande : « pouvoir changer Nebius par
DeepSeek, Claude ou autre, que ce soit une couche interchangeable ». Ce ne
l'etait pas : trois cerveaux (qwen, nebius, local) etaient ecrits en dur dans
le moteur. Ici, un cerveau est une FICHE, declaree dans reglages-maison.json :

    "cerveaux": {
      "deepseek": {"type": "openai", "url": "https://api.deepseek.com/chat/completions",
                   "modele": "deepseek-chat", "cle_env": "DEEPSEEK_API_KEY",
                   "payant": true},
      "claude":   {"type": "anthropic", "modele": "claude-opus-5-5",
                   "cle_env": "ANTHROPIC_API_KEY", "payant": true}
    }

puis :  python3 arthur_cerveau.py deepseek

Les types :
  openai     tout serveur « /chat/completions » : Nebius, DeepSeek, Mistral,
             OpenRouter, Groq, OpenAI, un llama.cpp ou un vLLM maison...
  anthropic  Claude, par le SDK officiel (pip install anthropic) ;
  ollama     un modele sur cette machine (http://127.0.0.1:11434), gratuit.

Trois cerveaux existent toujours, meme sans fiche : « qwen » (Alice),
« local » (morgan, ollama) et « nebius » (Nemotron, nemotron_nebius.py).

L'ARGENT. Un cerveau "payant": true passe par budget_nebius.py : interrupteur
FERME par defaut, plafond par jour, plafond total, plafond en euros. Le carnet
est commun a tous les cerveaux payants. Une fiche sans "payant" est traitee
comme payante des qu'elle vise une adresse hors de cette machine : dans le
doute, on protege le porte-monnaie.

Une fiche payante peut porter son prix : "euros_par_million" (le prix de
SORTIE, le plus cher, arrondi au-dessus). Le plafond en euros se calcule alors
au prix le plus cher entre celui-ci et celui de budget-nebius.json.

Les cles ne s'ecrivent JAMAIS dans la fiche : seulement le NOM de la variable
d'environnement qui la contient ("cle_env").
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))

CONSIGNE_PAR_DEFAUT = (
    "Tu es Arthur, un assistant qui ne devine jamais. Reponds dans la langue de "
    "la question, brievement. Si des extraits de documents sont fournis, reponds "
    "UNIQUEMENT a partir d'eux et cite leur source. Si tu ne sais pas, ou si les "
    "extraits ne contiennent pas la reponse, dis exactement : Je ne sais pas."
)

# Les modeles Claude qui acceptent « effort » et le repli cote serveur
# (skill claude-api, 29/09/2026). Pour un autre modele, on ne les envoie pas.
_CLAUDE_AVEC_EFFORT = {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5",
                       "claude-fable-5-1"}
_CLAUDE_AVEC_REPLI = {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5",
                      "claude-fable-5-1"}

BASE = {
    "qwen": {"type": "interne", "description": "Qwen, sur Alice — gratuit, à la maison"},
    "local": {"type": "interne", "description": "morgan (ollama) sur ce PC — gratuit, plus lent"},
    "nebius": {"type": "interne", "payant": True,
               "description": "NVIDIA Nemotron, chez Nebius Token Factory — payant"},
}


def _reglages():
    chemin = os.environ.get("ARTHUR_REGLAGES") or os.path.join(ICI, "reglages-maison.json")
    try:
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def cerveaux():
    """Tous les cerveaux connus : les trois de base, plus les fiches declarees."""
    tous = {k: dict(v) for k, v in BASE.items()}
    fiches = _reglages().get("cerveaux") or {}
    if isinstance(fiches, dict):
        for nom, fiche in fiches.items():
            if isinstance(fiche, dict) and fiche.get("type") in ("openai", "anthropic", "ollama"):
                tous[str(nom).lower()] = dict(fiche)
    return tous


def fiche(nom):
    return cerveaux().get(str(nom or "").lower())


def est_interne(nom):
    f = fiche(nom)
    return bool(f) and f.get("type") == "interne"


def _local(url):
    hote = (urllib.parse.urlparse(url or "").hostname or "").lower()
    return hote in ("127.0.0.1", "localhost", "::1")


def est_payant(f):
    if "payant" in f:
        return bool(f["payant"])
    if f.get("type") == "anthropic":
        return True
    return not _local(f.get("url"))


def ordre(choix):
    """Le cerveau choisi, puis les cerveaux de repli (reglage "cerveau_repli",
    par defaut ["qwen"]), sans doublon ni inconnu."""
    repli = _reglages().get("cerveau_repli")
    if not isinstance(repli, list):
        repli = ["qwen"]
    vus, liste = set(), []
    for nom in [choix] + repli:
        nom = str(nom or "").lower()
        if nom and nom not in vus and fiche(nom):
            vus.add(nom)
            liste.append(nom)
    return liste


def _messages(question, extraits, consigne):
    systeme = consigne or CONSIGNE_PAR_DEFAUT
    if extraits:
        systeme += ("\n\nExtraits de documents (seule source autorisee) :\n"
                    + str(extraits)[:6000])
    return systeme, [{"role": "user", "content": str(question)}]


def _garde_argent(nom, f, estimation):
    """(permis, raison). Rien ne part vers un cerveau payant sans l'accord
    ecrit de budget_nebius (interrupteur + plafonds)."""
    if not est_payant(f):
        return True, ""
    import budget_nebius
    ok, pourquoi = budget_nebius.paiement_autorise()
    if not ok:
        return False, pourquoi.replace("Nebius", nom)
    # (30/09) Le plafond en euros se calcule au prix le PLUS CHER entre le
    # prix general et celui de la fiche : passer de Nemotron a Claude ne doit
    # pas faire sous-estimer la depense. Prudent : on surestime plutot.
    r = budget_nebius.reglages()
    prix = float(f.get("euros_par_million") or 0)
    if prix > float(r.get("euros_par_million") or 0):
        r["euros_par_million"] = prix
    ok, pourquoi, _ = budget_nebius.autoriser(estimation, reglages=r)
    return ok, pourquoi


def _noter(nom, f, jetons, estimation):
    if est_payant(f):
        import budget_nebius
        budget_nebius.noter({"total_tokens": jetons}, f.get("modele", nom), nom,
                            estimation=estimation)


def demander(nom, question, extraits=None, consigne=None, jetons_max=900, patience=90):
    """Pose la question au cerveau « nom ». Rend toujours
    {"reponse", "panne", "modele", "cerveau"} ; reponse=None en cas de souci,
    et panne dit pourquoi, en clair."""
    f = fiche(nom)
    rendu = {"reponse": None, "panne": None, "cerveau": nom,
             "modele": (f or {}).get("modele")}
    if not f:
        rendu["panne"] = "cerveau inconnu : %s" % nom
        return rendu
    if f["type"] == "interne":
        rendu["panne"] = "cerveau interne : le moteur l'appelle lui-meme"
        return rendu

    systeme, messages = _messages(question, extraits, consigne)
    # UN SEUL plafond de sortie, celui qu'on envoie VRAIMENT : l'estimation
    # soumise au budget et le max_tokens de l'appel ne divergent plus, et un
    # cerveau payant respecte jetons_max_par_appel comme Nemotron.
    plafond = int(f.get("jetons_max") or (4000 if f["type"] == "anthropic" else jetons_max))
    if est_payant(f):
        import budget_nebius
        plafond = budget_nebius.max_par_appel(plafond)
    estimation = (len(systeme) + len(str(question))) // 3 + plafond
    ok, pourquoi = _garde_argent(nom, f, estimation)
    if not ok:
        rendu["panne"] = pourquoi
        return rendu

    cle = os.environ.get(f.get("cle_env") or "", "").strip() if f.get("cle_env") else ""
    if f.get("cle_env") and not cle:
        rendu["panne"] = "la variable %s (la cle de %s) est vide" % (f["cle_env"], nom)
        return rendu

    try:
        if f["type"] == "anthropic":
            texte, jetons = _claude(f, systeme, messages, cle, plafond, patience)
        elif f["type"] == "ollama":
            texte, jetons = _ollama(f, systeme, messages, patience)
        else:
            texte, jetons = _openai(f, systeme, messages, cle, plafond, patience)
    except _Panne as e:
        # une reponse RECUE puis rejetee (refus, place manquee, illisible)
        # a ete facturee : elle entre au carnet comme les autres.
        if e.jetons is not None:
            _noter(nom, f, e.jetons, estimation)
        rendu["panne"] = str(e)
        return rendu
    except Exception as e:
        # un SDK trop vieux, une erreur imprevue : jamais de plantage du moteur
        rendu["panne"] = "%s en panne : %s" % (nom, str(e)[:120] or type(e).__name__)
        return rendu
    _noter(nom, f, jetons, estimation)
    if not texte:
        rendu["panne"] = "%s a rendu une reponse vide" % nom
    rendu["reponse"] = texte or None
    return rendu


class _Panne(Exception):
    """jetons : None si rien n'a ete facture ; sinon ce que l'appel a coute
    (0 = inconnu, le carnet prend alors l'estimation)."""

    def __init__(self, message, jetons=None):
        super().__init__(message)
        self.jetons = jetons


def _poster(url, charge, entetes, patience):
    req = urllib.request.Request(url, data=json.dumps(charge).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **entetes})
    try:
        with urllib.request.urlopen(req, timeout=patience) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 402:
            raise _Panne("plus de credit chez ce fournisseur (HTTP 402)")
        if e.code in (401, 403):
            raise _Panne("cle refusee (HTTP %d)" % e.code)
        raise _Panne("HTTP %d" % e.code)
    except (OSError, ValueError) as e:
        raise _Panne("injoignable : %s" % str(e)[:120])


def _openai(f, systeme, messages, cle, jetons_max, patience):
    if not f.get("url") or not f.get("modele"):
        raise _Panne("fiche incomplete : il faut \"url\" et \"modele\"")
    entetes = {"Authorization": "Bearer " + cle} if cle else {}
    d = _poster(f["url"], {"model": f["modele"],
                           "messages": [{"role": "system", "content": systeme}] + messages,
                           "max_tokens": int(jetons_max),
                           "temperature": 0}, entetes, patience)
    try:
        jetons = int((d.get("usage") or {}).get("total_tokens") or 0)
    except (AttributeError, TypeError, ValueError):
        jetons = 0
    try:
        choix = d["choices"][0]
        texte = ((choix.get("message") or {}).get("content") or "").strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        raise _Panne("reponse illisible", jetons)
    if not texte and choix.get("finish_reason") == "length":
        # le defaut des modeles qui reflechissent (RAPPORT-BUG-NEBIUS.md) :
        # toute la place est partie dans la reflexion. On ne rend pas le brouillon.
        raise _Panne("le modele a manque de place pour repondre (reflexion trop longue)", jetons)
    return texte, jetons


def _ollama(f, systeme, messages, patience):
    url = f.get("url") or "http://127.0.0.1:11434/api/chat"
    d = _poster(url, {"model": f.get("modele") or "morgan", "stream": False,
                      "messages": [{"role": "system", "content": systeme}] + messages},
                {}, patience)
    try:
        return (d["message"]["content"] or "").strip(), 0
    except (KeyError, TypeError):
        raise _Panne("reponse illisible")


def _claude(f, systeme, messages, cle, jetons_max, patience):
    """Claude, par le SDK officiel (skill claude-api)."""
    try:
        import anthropic
    except ImportError:
        raise _Panne("le paquet « anthropic » n'est pas installe (pip install anthropic)")
    modele = f.get("modele") or "claude-opus-5-5"
    client = anthropic.Anthropic(api_key=cle or None, timeout=patience, max_retries=1)
    params = {"model": modele, "max_tokens": int(jetons_max),
              "system": systeme, "messages": messages}
    if modele in _CLAUDE_AVEC_EFFORT:
        params["output_config"] = {"effort": f.get("effort") or "low"}
    try:
        if modele in _CLAUDE_AVEC_REPLI:
            # repli cote serveur si Claude decline par securite (skill claude-api)
            reponse = client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **params)
        else:
            reponse = client.messages.create(**params)
    except anthropic.AuthenticationError:
        raise _Panne("cle Claude refusee")
    except anthropic.RateLimitError:
        raise _Panne("Claude : trop de demandes, reessaie plus tard")
    except anthropic.APIStatusError as e:
        raise _Panne("Claude : HTTP %d" % e.status_code)
    except anthropic.APIConnectionError:
        raise _Panne("Claude injoignable")
    u = reponse.usage
    jetons = int((u.input_tokens or 0) + (u.output_tokens or 0))
    if reponse.stop_reason == "refusal":
        raise _Panne("Claude a decline la demande", jetons)
    texte = "".join(b.text for b in reponse.content if b.type == "text").strip()
    return texte, jetons


def main(argv):
    if not argv:
        for nom, f in cerveaux().items():
            print("%-10s %-9s %-8s %s" % (
                nom, f.get("type"), "payant" if est_payant(f) else "gratuit",
                f.get("description") or f.get("modele") or ""))
        return 0
    d = demander(argv[0], " ".join(argv[1:]) or "Dis bonjour en un mot.")
    print(d["reponse"] or ("PANNE : %s" % d["panne"]))
    return 0 if d["reponse"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
