# TBA

Ce repo contient la première version (minimale) du jeu d’aventure TBA.

Les lieux sont au nombre de 6. Il n'y a pas encore d’objets ni de personnages autres que le joueur et très peu d’interactions. Cette première version sert de base à ce qui va suivre, et sera améliorée au fur et à mesure.


## Structuration

Il y a pour le moment 5 modules contenant chacun une classe.

- `game.py` / `Game` : description de l'environnement, interface avec le joueur ;
- `room.py` / `Room` : propriétés génériques d'un lieu  ;
- `player.py` / `Player` : le joueur ;
- `command.py` / `Command` : les consignes données par le joueur ;
- `actions.py` / `Action` : les interactions entre .


Initialisation du dépôt Git – Leçon 1.
## Navigation et carte personnalisée

Le jeu utilise une carte structurée permettant une navigation fluide entre les différentes zones.
Les actions disponibles pour le joueur ont été améliorées afin de rendre l’exploration plus intuitive
et éviter les erreurs de parcours.
## Historique et commande de retour

Le jeu intègre désormais un système d’historique permettant au joueur
de revenir en arrière via une commande dédiée.  
Cela améliore l’expérience utilisateur et évite de bloquer la progression.
## Objets et gestion de l’inventaire

Le jeu intègre un système d’objets récupérables et un inventaire permettant
au joueur de stocker, consulter et utiliser les éléments collectés au cours
de l’exploration.
## Personnages non-joueurs (PNJ) et interactions

Le jeu inclut des personnages non-joueurs avec lesquels le joueur peut
interagir. Ces interactions enrichissent la narration et influencent
la progression au cours de l’aventure.
## Quêtes

Le jeu propose un système de quêtes permettant de guider le joueur
à travers différents objectifs et d’enrichir la progression narrative.
