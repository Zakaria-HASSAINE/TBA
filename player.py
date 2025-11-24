"""
Module player — définition de la classe Player.

Représente le joueur du jeu ; stocke son nom et la salle courante.
"""

class Player:
    """Classe représentant le joueur."""

    def __init__(self, name):
        self.name = name
        self.current_room = None

    def move(self, direction):
        """Tente de déplacer le joueur vers `direction`. Retourne True/False."""
        if self.current_room is None:
            print("\nLe joueur n'est dans aucune salle actuellement.\n")
            return False

        # Utiliser get_exit si disponible
        next_room = None
        try:
            next_room = self.current_room.get_exit(direction)
        except Exception:
            next_room = None

        if not next_room:
            print("\nAucune porte dans cette direction !\n")
            return False

        self.current_room = next_room
        print(self.current_room.get_long_description())
        return True
    

