class Player:
    """Classe représentant le joueur."""

    def __init__(self, name):
        self.name = name
        self.current_room = None
        self.inventory = []  # liste d'Item

    def move(self, direction):
        if self.current_room is None:
            print("\nLe joueur n'est dans aucune salle actuellement.\n")
            return False

        try:
            next_room = self.current_room.get_exit(direction)
        except Exception:
            next_room = None

        if not next_room:
            print("\nAucune porte dans cette direction !\n")
            return False

        self.current_room = next_room

        # Marque visited si présent
        if hasattr(self.current_room, "visited"):
            self.current_room.visited = True

        print(self.current_room.get_long_description())
        return True
