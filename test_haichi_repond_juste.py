# -*- coding: utf-8 -*-
"""Le test qui verifie qu'Haichi repond SUR LE BON SUJET.
Il n'attend pas un code 200 : il LIT la reponse et regarde de quoi elle parle."""
import json, re, urllib.request

ADRESSE = "http://127.0.0.1:8790/api/nano-search"

# question posee            -> un mot qui DOIT etre dans la reponse | mots INTERDITS
CAS = [
    ("qu est ce que la tour",   ["tour de contr"],            ["retrotranscription", "bourgeonnement"]),
    ("les agents de la tour",   ["braignak", "victor", "chlo"], ["retrotranscription"]),
    ("bonjour",                 ["salut", "ravi", "braignak"], ["je ne sais pas"]),
    ("la carte vivante",        ["carte vivante"],            ["retrotranscription"]),
    ("comment marche la prep",  ["je ne sais pas"], ["ténofovir", "vih", "charge virale"]),
    ("le vih",                  ["je ne sais pas"], ["indétectable", "prep", "transmission"]),
    ("hepatite",                ["je ne sais pas"], ["bulevirtide", "epclusa"]),
    # Le 17/09/2026 : Arthur dit maintenant « je n ai pas compris ta
    # demande », ce qui est MEILLEUR que « je ne sais pas » — il nomme
    # les mots qu il ne connait pas et demande une question. L epreuve
    # etait trop stricte : elle exigeait une formule, pas un aveu.
    ("xyzzy blurp",             ["je ne sais pas", "pas compris"], []),
]

def demander(q):
    corps = json.dumps({"prompt": q}).encode("utf-8")
    req = urllib.request.Request(ADRESSE, data=corps,
                                 headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
    brut = d.get("raw_output", "")
    m = re.search(r"<answer>(.*?)</answer>", brut, re.S)
    return (m.group(1).strip() if m else brut)

rouges = 0
for question, attendus, interdits in CAS:
    rep = demander(question)
    bas = rep.lower()
    ok_attendu = any(a in bas for a in attendus)
    ok_interdit = not any(i in bas for i in interdits)
    bon = ok_attendu and ok_interdit
    if not bon:
        rouges += 1
    print(("  VERT  " if bon else "  ROUGE ") + question)
    print("         reponse : " + rep[:110].replace("\n", " "))
    if not ok_attendu:
        print("         -> on attendait un de ces mots : " + str(attendus))
    if not ok_interdit:
        print("         -> mot interdit trouve : " + str(interdits))

print()
print("BILAN : %d rouge(s) sur %d" % (rouges, len(CAS)))
raise SystemExit(1 if rouges else 0)
