# Les compétences d'Arthur

Une compétence est un **mode d'emploi**, pas du code. Elle dit *quand* faire
une chose et *quels pièges sont déjà payés*.

| La compétence | À quoi elle sert |
|---|---|
| `video-narree` | fabriquer une vidéo commentée par une voix — et **la montrer** dans une page, jamais donner son nom |
| `kotodama` | ressortir ce que Patrick a demandé, groupé par thème, avec l'état de chacun |
| `redaction-histoire` | écrire un texte qui se tient, pour un article ou un dépôt |

## Les trois pièges de `video-narree`, payés le 17/09/2026

1. **ffmpeg dessine le retour à la ligne comme un carré vide.**
   L'essai qui tranche : deux lignes, la seconde sans retour à la ligne —
   seule la première portait un carré. La parade : **un dessin par ligne**.
2. **ffmpeg mange les espaces du début de ligne**, et les tableaux perdent
   leur alignement. La parade : l'espace insécable.
3. **ImageMagick refuse de lire un texte depuis un fichier** (règle de
   sécurité du système). La parade : ne pas passer par lui pour le texte.

Et la règle qui passe avant tout : **ne jamais écrire dans une image un
chiffre qu'on n'a pas mesuré.** Une fois la vidéo rendue, il ne se vérifie
plus.
