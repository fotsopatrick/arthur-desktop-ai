# -*- coding: utf-8 -*-
"""Le bouton « Rallumer Hachi » marche-t-il VRAIMENT ?

On ne se contente pas d un code 200. On ferme Hachi pour de bon, on appuie sur
le bouton, et on verifie que sa fenetre revient sur le bureau.
"""
import subprocess, time, json, urllib.request

def hachi_tourne():
    return subprocess.run(["pgrep", "-f", r"^python3 .*haichi_avatar.py"],
                          capture_output=True).returncode == 0

def fenetre_presente():
    s = subprocess.run(["wmctrl", "-l", "-x"], capture_output=True, text=True,
                       env={"DISPLAY": ":0", "XDG_RUNTIME_DIR": "/run/user/1000",
                            "PATH": "/usr/bin:/bin"}).stdout
    return "haichi_avatar" in s.lower() or "haichi-avatar" in s.lower()

rouges = 0
def dire(ok, quoi):
    global rouges
    print(("  VERT   " if ok else "  ROUGE  ") + quoi)
    if not ok: rouges += 1

print("  1. je ferme Hachi pour de bon")
subprocess.run(["pkill", "-f", r"^python3 .*haichi_avatar.py"])
time.sleep(3)
dire(not hachi_tourne(), "il est bien ferme")

print("  2. j appuie sur le bouton du cockpit")
req = urllib.request.Request("http://127.0.0.1:8790/api/hachi/rallumer",
                             data=b"{}", headers={"Content-Type": "application/json"})
d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
dire(d.get("ok") is True, "le cockpit dit : " + str(d.get("message")))

print("  3. j attends qu il revienne")
revenu = False
for _ in range(20):
    time.sleep(1)
    if hachi_tourne() and fenetre_presente():
        revenu = True; break
dire(revenu, "sa fenetre est revenue sur le bureau")

print("\nBILAN RALLUMAGE : %d rouge(s) sur 3" % rouges)
raise SystemExit(1 if rouges else 0)
