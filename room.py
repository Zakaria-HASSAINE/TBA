"""
Module room — définition de la classe Room.

Représente un lieu du jeu. Chaque salle possède un nom, une petite
description et les sorties possibles vers d'autres salles.

La classe sert surtout à organiser la map et permettre au joueur
de se déplacer entre les différentes pièces.

Attributs
    name (str): Nom du lieu (ex : "Forêt", "Tour").
    description (str): Description du lieu.
    exits (dict): Dictionnaire associant une direction (str) à une instance de `Room`.

Méthodes principales
    get_exit(direction): Renvoie la salle dans la direction donnée ou None.
    get_exit_string(): Renvoie une chaîne listant les sorties disponibles.
    get_long_description(): Renvoie la description complète de la salle.
"""

class Room:
    """Classe représentant une salle du jeu."""

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.exits = {}

    def get_exit(self, direction):
        """Renvoie la Room reliée à `direction`, ou None si indisponible."""
        return self.exits.get(direction)

    def get_exit_string(self):
        """Construit et renvoie une chaîne listant les sorties valides."""
        exit_string = "Sorties: "
        parts = []
        for d, room in self.exits.items():
            if room is not None:
                parts.append(d)
        exit_string += ", ".join(parts)
        return exit_string

    def get_long_description(self):
        """Renvoie une description longue de la salle, incluant les sorties."""
        return f"\nVous êtes {self.description}\n\n{self.get_exit_string()}\n"
