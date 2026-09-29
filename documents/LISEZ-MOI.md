# documents/ — ce qu'Arthur peut lire sur cette machine

Pose ici des fichiers `.md` ou `.txt` : Arthur les cherche (`rag_local.py`,
recherche BM25, sans réseau) quand aucune règle écrite ne répond.

- Il ne répond qu'avec ce qu'il trouve, **en citant le fichier**.
- Si les extraits ne contiennent pas au moins deux mots importants de la
  question, il dit « je ne sais pas ».
- Ce fichier-ci n'est pas lu (les LISEZ-MOI sont ignorés).

Autres dossiers : `"rag_dossiers": ["~/notes", "~/docs"]` dans
`reglages-maison.json`, ou la variable `ARTHUR_DOCUMENTS=~/notes:~/docs`.
