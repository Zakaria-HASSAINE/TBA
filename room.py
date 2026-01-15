class Room:
    """Classe représentant une salle du jeu."""

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.exits = {}

        # Ajouts minimaux pour ton jeu
        self.inventory = []   # liste d'Item
        self.visited = False  # utile pour tes triggers

    def get_exit(self, direction):
        return self.exits.get(direction)

    def get_exit_string(self):
        exit_string = "Sorties: "
        parts = []
        for d, room in self.exits.items():
            if room is not None:
                parts.append(d)
        exit_string += ", ".join(parts)
        return exit_string

    def show_inventory(self):
        if not self.inventory:
            print("\nObjets ici : (aucun)")
            return
        print("\nObjets ici :")
        for it in self.inventory:
            try:
                print(f"  - {it.name}")
            except Exception:
                print("  - (objet)")

    def get_long_description(self):
        return f"\nVous êtes {self.description}\n\n{self.get_exit_string()}\n"
