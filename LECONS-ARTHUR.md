

<!-- LECONS PORTEES — ne pas ecrire a la main entre ces deux lignes -->

### absent-expres-nest-pas-en-panne

Une chose peut manquer pour deux raisons tres differentes : elle est tombee,
ou on l'a enlevee expres. Un detecteur qui ne connait que « la » et « pas la »
crie au feu devant une piece qu'on a demolie. Et une alarme qui sonne toujours
pour rien finit par ne plus etre ecoutee : c'est ainsi qu'on rate la vraie panne.

Il faut donc trois etats, jamais deux : la chose repond ; la chose est attendue
et absente (alerte) ; la chose n'est plus attendue (on le dit calmement, sans alerte).
Une chose retiree reste dans la liste, avec la raison du retrait — on ne cache rien.

### aller-voir-avant-de-donner-une-adresse

Le 16/09/2026, j'ai fait chercher Patrick TROIS fois pour un bouton. Je lui
ai donne l'adresse de memoire, sans jamais ouvrir la page. Puis une deuxieme,
qui etait l'ANCIENNE version de son tableau de bord — refait le matin meme par
une autre session, sans que je le sache.
Mesure : zero bouton la ou je l'envoyais, vingt a cote.
Ne JAMAIS donner une adresse sans y etre alle d'abord : ouvrir la page,
compter ce qui doit y etre, et seulement apres l'envoyer. Si je ne trouve pas
la chose, Patrick ne la trouvera pas non plus.
Et quand il dit « c'est l'ancien » : ne pas discuter, aller voir ce qui a
change aujourd'hui. Plusieurs sessions travaillent en meme temps ; ce que je
crois connaitre a pu changer il y a une heure.

### jamais-affaiblir-une-protection-sans-preuve

Le 16/09/2026 : j'allais adoucir une protection du serveur, parce que je
croyais qu'elle risquait de bloquer le renouvellement du certificat. Patrick
a demande : « on ne risque pas des attaques ? » J'ai verifie AVANT de toucher.
Resultat : la regle ne bloque que ceux qui frappent a une porte FERMEE. Le
renouvellement passe par une porte OUVERTE. Il ne peut pas etre bloque. Zero
ennui en sept jours, et 3981 fouineurs deja arretes.
Je m'appretais donc a affaiblir une vraie protection a cause d'une peur que
je n'avais jamais mesuree.
Avant de baisser une garde : montrer le chiffre qui prouve qu'elle gene. Pas
de chiffre, pas de changement. Et d'abord chercher la solution CIBLEE (mettre
le facteur sur une liste d'amis) avant la solution large (ouvrir a tous).

### les-accents-comptent

Enlever les accents AVANT de lire une question. Sinon « multiplie » marche et
« multiplié » ne marche pas : on ne sait compter que si l'autre ecrit mal.
Patrick ecrit avec les accents.

### les-tests-sans-quon-les-demande

Patrick n'a plus a dire « generation de tests ». C'est automatique.
Toute construction suit six temps : comprendre (au moins deux hypotheses et
ce qui les separe) ; lire ce qui existe deja ; ecrire les epreuves AVANT le
code et les voir ROUGES ; faire ; relancer les epreuves et coller les chiffres ;
rendre le resultat avec la preuve.
Les questions, les lectures et les reparations urgentes n'en ont pas besoin.

### lire-les-articles-avant-de-reparer

Le 16/09/2026, le tableau de bord de Patrick est tombe et n'a pas pu repartir.
J'ai pose un « filet » qui le relancait a la main chaque minute.
Patrick m'a arrete : « ca a deja ete fixe ». Il avait raison. Un article
publie le 08/09 sur sa vitrine decrivait la MEME panne et la vraie
reparation : « la page est devenue un service qui se releve tout seul — nous
l'avons tuee brutalement, elle repondait cinq secondes plus tard ».
Cinq autres pages de ce PC avaient deja ce service. Le tableau de bord, non.
J'ai donc refait le pansement que l'article dit de ne pas faire.
AVANT de reparer quoi que ce soit : chercher si la meme panne a deja ete
reparee ici. Les articles de la vitrine et les lecons sont la memoire de la
maison. Refaire un pansement sur une cause deja connue, c'est pire que ne
rien faire : ca cache que le robinet est toujours ouvert.

### mes-instruments-mentent-plus-que-je-ne-me-presse

Le 16/09/2026, Patrick a demande pourquoi je me trompe. J'ai range mes 22
fautes du jour par cause, au lieu d'en faire la liste.
Resultat mesure : la precipitation n'explique que 4 fautes sur 22. Les 18
autres viennent d'un INSTRUMENT qui dit le faux — un compteur, un filtre, un
detecteur qui ne connait pas toutes les formes.
Preuve la plus nette : le meme ordre de comptage, sur la meme page contenant
trois fois la meme chose, repond 3 sur le PC et 1 sur le serveur.
Donc : avant de croire un chiffre, verifier l'instrument sur un cas dont je
connais deja la reponse. Un compteur qu'on n'a jamais essaye sur un cas connu
n'est pas une mesure, c'est une opinion.

### mesurer-une-chose-a-la-fois

Le 16/09/2026 j'ai mesure deux pages dans la meme boucle, puis melange les
resultats. J'ai failli accuser la mauvaise. Refait page par page : l'une
mettait 3,5 secondes, l'autre 0,03.
Une mesure qui melange deux choses ne prouve rien sur aucune des deux.
Et quand un chiffre semble absurde — « 2001.72 secondes » — c'est souvent
deux nombres colles l'un a l'autre, pas une mesure.

### mon-propre-filet-a-efface-ma-preuve

Le 16/09/2026 : j'ai casse un fichier expres pour tester mon filet de
securite. Ma ligne a disparu. J'ai cru qu'une autre session reecrivait le
fichier en boucle, et j'ai alerte deux collegues. C'etait FAUX : c'etait mon
propre filet qui faisait son travail — remettre la version qui marchait.
Trois mesures l'ont montre : le fichier etait identique a la copie de secours
du filet, il n'a pas bouge pendant deux minutes d'affilee, et les « preuves »
mises de cote faisaient 33 octets au lieu de 114 000 — c'etaient mes propres
epreuves.
Avant d'accuser quelqu'un : chercher d'abord ce que MES outils viennent de
faire. Et faire l'observation qui tranche (ici : regarder le fichier deux
minutes sans y toucher) au lieu de conclure d'un indice.
Une epreuve doit rester dans son bac a sable. La mienne ecrivait dans le vrai
dossier, et j'ai lu mes propres traces comme celles d'un intrus.

### ne-pas-refaire-le-meme-voyage

Une page qui va interroger un serveur lointain a CHAQUE ouverture refait le
meme voyage pour afficher la meme chose. Avec douze onglets, c'est douze
voyages. Mesure du 16/09/2026 : 1,23 seconde par ouverture ; apres avoir
garde la reponse quarante secondes, 0,010 seconde — cent treize fois plus vite,
et la page dit exactement la meme chose, a l'octet pres.
Garder un resultat un petit moment : assez court pour qu'une nouveaute
apparaisse vite, assez long pour ne pas refaire le voyage a chaque clic.
Et toujours verifier qu'apres, la page dit LA MEME CHOSE — rapide et faux
serait pire que lent et juste.

### se-servir-dune-clef-nest-pas-la-lire

Un garde qui confond « se servir d'une clef » et « lire une clef » n'empeche
aucun vol : il empeche seulement de travailler. Le guichet du gardien de clefs
n'est pas une clef — la clef ne sort jamais du gardien.
Quand un garde refuse un geste manifestement legitime : ne pas le desarmer.
Affiner la regle, et ajouter l'epreuve qui prouve que les vrais refus tiennent
toujours.

### surveiller-ceux-qui-surveillent

Le 16/09/2026, Patrick : « comment le banisseur est mort et ca passe inapercu
2 jours d'affilee ? » Le videur de la tour — le programme qui bloque ceux qui
frappent trop souvent a la porte — etait mort depuis 2 jours. Personne ne le
regardait : on surveillait le site, le disque, la memoire, pas le gardien.
Un garde que personne ne surveille peut mourir en silence, et on ne s'en
apercoit qu'apres le vol.
Et « debout » ne suffit pas : un videur allume avec zero cellule ne garde
rien. On verifie donc DEUX choses — il est la, ET il fait son travail, avec
un chiffre (combien d'adresses bloquees).

### un-detecteur-qui-se-compte-lui-meme

Le 16/09/2026 : j'ai cherche les connexions par mot de passe dans un journal.
Reponse : une. C'etait MA PROPRE commande de recherche, qui s'ecrit dans le
journal en s'executant. J'avais failli annoncer une intrusion.
Quand on cherche une trace dans un journal, toujours regarder si la trace
trouvee n'est pas celle qu'on vient de laisser soi-meme.

### un-fichier-deplace-perd-ses-voisins

Un programme qui cherche son fichier de reglages « a cote de lui-meme » se
trompe des qu'on le deplace, ou des qu'on y accede par un raccourci.
Ne jamais deviner un seul chemin : regarder les endroits connus dans l'ordre,
et dire lequel a servi.

### un-raccourci-pointe-vers-du-vide

Le 16/09/2026, Patrick : « je ne vois aucun bouton ». J'avais bien pose le
bouton, et je lui avais donne l'adresse de l'accueil. Mais l'accueil avait
change entre-temps : il etait devenu un menu, et les boutons avaient demenage
derriere une porte. Son raccourci « Mes taches » envoyait donc vers une page
qui n'en montrait aucun. Mesure : zero bouton la ou il regardait, vingt a
l'endroit voisin.
Un raccourci qui pointe vers du vide est PIRE que pas de raccourci : on croit
avoir regarde au bon endroit.
Apres avoir pose quelque chose, ne pas donner l'adresse de memoire : aller
CHERCHER la chose a cette adresse, et compter. Si on ne la trouve pas, c'est
que Patrick ne la trouvera pas non plus.

### un-relanceur-relance-un-fichier-casse

Le 16/09/2026, le tableau de bord de Patrick est reste par terre alors qu'un
relanceur passait toutes les dix minutes. Il relancait le fichier CASSE : il
echouait donc en silence, encore et encore.
Relancer ne suffit pas. Avant de relancer, VERIFIER que le fichier se lit
bien. Et garder une copie de la derniere version qui MARCHAIT — sinon, quand
la faute arrive, il n'y a rien pour repartir.
Quand on repart sur une copie plus ancienne, le DIRE fort : sinon on croit
que tout va bien alors qu'on tourne sur du vieux.
Et ne JAMAIS effacer le fichier fautif : quelqu'un y travaille peut-etre.
On le met de cote avec l'heure dans son nom.

### un-seuil-se-demande-a-la-machine

Un seuil ecrit en dur est presque toujours faux. « Au-dessus de 4, il peine » :
faux sur une machine a 16 coeurs, faux aussi sur une machine a 2. Le bon seuil,
c'est la machine qui le donne — ici, le nombre de coeurs.
Quand on ne peut pas mesurer le seuil, on ne juge pas : on dit qu'on ne sait pas.

### un-test-qui-ne-coupe-pas-tout-ne-prouve-rien

Un controle qui se dit « hors ligne » alors qu'il coupe deux chemins sur trois
passe au vert en etant... en ligne. Il ne prouve rien.
Avant de faire confiance a un controle, le CASSER expres et verifier qu'il
devient rouge. Un controle qui n'a jamais refuse ne garde rien.

### une-lecon-ecrite-ne-marrete-pas

Le 16/09/2026, Patrick m'a demande la verite. Je l'ai mesuree.
J'ai sous les yeux a chaque reponse : 566 lignes de ses regles, 173 souvenirs,
125 articles publies. Elles ne m'ont arrete ZERO fois ce jour-la.
Les gardes mecaniques — ceux qui REFUSENT — m'ont arrete SEPT fois.
Mes 22 fautes du jour sont toutes passees la ou aucun garde n'existait.
Donc : une lecon ecrite ne change rien. Un mur qui refuse, si.
Chaque faute comprise doit devenir un garde mecanique, pas un paragraphe.
Tant qu'elle reste un texte, elle ne protege de rien — c'est de la decoration.
Et ne jamais dire « on m'a remis le bug » sans avoir cherche la trace : le
16/09 j'ai cherche, il n'y en avait aucune. Les corrections de Patrick
tenaient toutes. Elles n'avaient simplement jamais ete etendues au reste.

### une-pointe-nest-pas-un-etat

Une mesure qui saute pendant trente secondes n'est pas un etat. Une tache qui
demarre fait bondir la charge, puis ca retombe. Avant de nommer un coupable,
regarder DEPUIS COMBIEN DE TEMPS il tourne. Trente-quatre secondes, c'est un
demarrage, pas une fuite. On juge sur la duree longue, jamais sur l'instant.

<!-- FIN DES LECONS PORTEES -->
