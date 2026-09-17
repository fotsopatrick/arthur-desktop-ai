---
name: video-narree
description: Fabriquer une vidéo d'écran commentée par une voix — capture de l'écran, narration fabriquée chez Google, assemblage. À invoquer quand Patrick demande « fais une vidéo », « filme ce que tu fais », « avec une voix qui explique », ou une démonstration pour un hackathon.
---

# Fabriquer une vidéo d'écran avec une voix qui explique

## LE MUR À CONNAÎTRE AVANT DE COMMENCER

Le poste nomi tourne en **Wayland**. Wayland interdit à un programme de
filmer l'écran sans qu'un humain clique pour l'autoriser. Constaté le
04/09/2026 : `ffmpeg -f x11grab -i :1` rend une **image noire**, luminosité 0.

Trois chemins ont été essayés, et voilà ce qu'ils donnent :

| Chemin | Résultat |
|---|---|
| `ffmpeg` sur l'écran de Patrick | image noire, Wayland bloque |
| écran virtuel `Xvfb` + Chrome | **ça filme**, mais la page demande une connexion et les cookies ne se transportent pas : ils sont chiffrés par le trousseau |
| porte de pilotage de Chrome (port 9222) | fermée sur ce poste |

**Donc : la capture d'une page qui demande une connexion revient toujours à
Patrick.** Un clic, et un seul. Ne pas tourner autour pendant vingt minutes.

## LE CHEMIN QUI MARCHE, EN TROIS TEMPS

### 1. La narration — chez Google, et on les remercie

`gcloud` est déjà connecté sur nomi, projet `control-tower-hackathon`.
**Ne rien modifier dans ce projet** : on ne fait que demander une voix.

```sh
T=$(gcloud auth print-access-token)
curl -s -X POST -H "Authorization: Bearer $T" \
  -H "x-goog-user-project: control-tower-hackathon" \
  -H "Content-Type: application/json; charset=utf-8" -d @requete.json \
  "https://texttospeech.googleapis.com/v1/text:synthesize" -o reponse.json
```

Le fichier `requete.json` contient le texte, la voix et la vitesse :

```json
{"input":{"text":"..."},
 "voice":{"languageCode":"fr-FR","name":"fr-FR-Chirp3-HD-Charon"},
 "audioConfig":{"audioEncoding":"LINEAR16","sampleRateHertz":24000,
                "speakingRate":0.96}}
```

La réponse contient le son encodé en base64, dans le champ `audioContent` :
on le décode et on écrit un fichier `.wav`.

**Les voix.** `Chirp3-HD` sont les plus récentes de Google. Quarante-deux
voix françaises, hommes et femmes. `Charon` est une voix d'homme, posée.
Pour en voir la liste :
`https://texttospeech.googleapis.com/v1/voices?languageCode=fr-FR`

**On cite Google sous la vidéo.** Patrick y tient : la voix est fabriquée
avec Google Cloud Text-to-Speech, et on le dit.

### 2. La capture d'écran — un clic de Patrick

```
spectacle -R s
```
`-R` veut dire enregistrer, `s` veut dire un écran entier. Spectacle demande
quel écran, puis un bouton arrête. **Lui dire quoi filmer et combien de temps**
— la durée de la voix se lit avec :
`ffprobe -v error -show_entries format=duration -of csv=p=0 voix.wav`

### 3. L'assemblage

```sh
ffmpeg -y -i capture.mp4 -i voix.wav \
  -c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -shortest sortie.mp4
```
`-shortest` arrête au plus court des deux. Réussi quand `ffprobe` rend une
durée proche de celle de la voix.

## CE QU'IL NE FAUT PAS FAIRE

- **Pas de suite d'images**. Huit captures collées font un diaporama qui
  saute. Patrick l'a dit : « on dirait un gif ». Il veut une capture continue.
- **Pas de `pkill -f <mot>`** si la commande contient elle-même ce mot :
  elle se tue toute seule. Deux fois payé le 04/09. Passer par les numéros
  de processus.
- **Ne pas manipuler le mot de passe de Patrick** pour ouvrir une session
  dans un navigateur d'essai.

## OÙ C'EST RANGÉ

Sur nomi : `~/.claude/skills/video-narree/`
Sur la tour : `~/.claude/skills/video-narree/`
Les morceaux déjà faits : `~/livrables/videos/`

---

## CE QUE LE 17/09/2026 A AJOUTÉ

### LA RÈGLE QUI PASSE AVANT TOUT : une vidéo se MONTRE

**Née d'une faute réelle.** J'ai fabriqué une vidéo de 158 secondes pour son
concours, et je lui ai donné son **nom** et son **poids**. Il ne l'a jamais
vue. Ses mots : *« fait un garde fou qui t'oblige à me montrer la vidéo dans
une page web »*, puis *« fait nous un truc à la YouTube »*, *« fais des
playlists par groupe »*.

**Donc, à la fin de toute fabrication de vidéo, sans exception :**

```sh
python3 ~/outils/montrer-la-video.py ma-video.mp4
```

Ça écrit une page à la YouTube — un grand lecteur en haut, toutes les vidéos
rangées en listes à côté, **un dossier = une liste** — et ça l'ouvre sur son
écran, à `http://127.0.0.1:8851/video`.
Réussi quand la sortie dit : **VIDEOS MONTREES**.

**Un garde mécanique l'exige** : `~/.claude/portes/garde-video-montree.py`.
Il refuse la fin du tour tant qu'une vidéo fabriquée dans les six dernières
heures n'a pas été montrée. Son épreuve : `bash ~/outils/test-video-montree.sh`
— 5 contrôles, tous verts.

### DEUX MURS QUI FERMENT LA CAPTURE D'ÉCRAN

| Le mur | Ce qu'il protège |
|---|---|
| Wayland | l'écran de Patrick ne se filme pas sans son clic |
| `garde-navigateur.py` | il refuse **Xvfb** — un écran caché où un Chrome invisible chaufferait le PC sans que personne le voie |

**Ne pas les désarmer.** La route qui reste : **dessiner les images
soi-même**, sans navigateur ni écran.

### DESSINER UNE VIDÉO SANS RIEN FILMER

Trois pièges mesurés le 17/09/2026, chacun payé d'un rendu raté :

1. **ffmpeg dessine le retour à la ligne comme un carré vide.**
   Essai qui tranche : un fichier de deux lignes, la seconde sans retour à la
   ligne — seule la première portait un carré.
   *La parade* : **un `drawtext` par ligne**, jamais de texte multi-lignes.
   Chaque ligne a son propre `y`, ce qui donne aussi le défilement.

2. **ffmpeg mange les espaces du début de ligne.**
   Les tableaux perdent leur alignement.
   *La parade* : remplacer les espaces de tête par l'**espace insécable**
   (` `), qu'il garde.

3. **ImageMagick refuse `label:@fichier`** — règle de sécurité du système.
   *La parade* : ne pas passer par ImageMagick pour le texte.

Le défilement continu, qui remplace la capture d'écran :

```
y=1080-VITESSE*t+RANG*PAS       VITESSE = (hauteur_du_texte + 1080) / durée
```

C'est un **générique de fin**, pas un diaporama : l'image bouge à chaque
image, donc Patrick ne dira pas « on dirait un gif ».

### LA VOIX, EN ANGLAIS

Pour un concours international : `en-US-Chirp3-HD-Charon`, `speakingRate` 1.0.
Mesuré : **465 mots donnent 158 secondes**. Pour viser 3 minutes sans
dépasser, écrire **entre 450 et 520 mots**.

### NE JAMAIS ÉCRIRE UN CHIFFRE QU'ON N'A PAS MESURÉ

La vidéo d'Arthur montre ses temps de réponse — 1192, 1200 et 1443
millisecondes. Ils viennent de **trois vraies questions posées dix minutes
avant le rendu**, pas du texte du dépôt. Un chiffre dans une image ne se
vérifie plus une fois la vidéo rendue.
