# room.py

class Room:
    """
    Représente un lieu du jeu.

    Une salle contient :
    - un nom (affiché dans l'interface)
    - une description (texte d'ambiance)
    - des sorties (N/E/S/O/U/D) vers d'autres salles
    - un inventaire d'objets (items au sol)
    - une liste de personnages présents (PNJ / personnages)
    - un flag 'visited' utile pour les déclencheurs de scénario
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

        self.exits = {}         # ex: {"N": other_room, "S": None}
        self.inventory = []     # liste d'Item posés dans la salle
        self.characters = []    # liste de Character présents ici
        self.visited = False

    # -------------------------
    # Déplacements
    # -------------------------
    def get_exit(self, direction):
        """Retourne la salle associée à une direction (N/E/S/O/U/D), ou None si impossible."""
        if direction is None:
            return None
        try:
            return self.exits.get(str(direction).strip().upper())
        except Exception:
            return None

    def get_exit_string(self) -> str:
        """Retourne une chaîne lisible listant les sorties réellement accessibles."""
        exits_ok = []
        try:
            for d, dest in self.exits.items():
                if dest is not None:
                    exits_ok.append(str(d))
        except Exception:
            pass

        if not exits_ok:
            return "Sorties: aucune"

        return "Sorties: " + ", ".join(exits_ok)

    def get_long_description(self) -> str:
        """Texte affiché quand on arrive dans la salle."""
        return f"\nVous êtes {self.description}\n\n{self.get_exit_string()}\n"

    # -------------------------
    # Objets (items)
    # -------------------------
    def show_inventory(self):
        """Affiche les objets posés dans la salle."""
        if not self.inventory:
            print("\nIl n'y a rien ici.\n")
            return

        print("\nOn voit :")
        for it in self.inventory:
            print(f"  - {it}")
        print()

    def pop_item_by_name(self, item_name: str):
        """
        Retire et renvoie un item de la salle par son nom (insensible à la casse).
        Utile pour la commande 'take'. Renvoie None si l'objet n'est pas trouvé.
        """
        if not item_name:
            return None

        target = item_name.strip().lower()

        for i, it in enumerate(self.inventory):
            try:
                if it.name.strip().lower() == target:
                    return self.inventory.pop(i)
            except Exception:
                continue

        return None

    # -------------------------
    # Personnages (PNJ)
    # -------------------------
    def add_character(self, character) -> bool:
        """Ajoute un personnage dans la salle."""
        try:
            self.characters.append(character)
            return True
        except Exception:
            return False

    def get_character(self, name: str):
        """Retourne un personnage par son nom (insensible à la casse), ou None si absent."""
        if not name:
            return None

        target = name.strip().lower()

        for c in self.characters:
            try:
                if c.name.strip().lower() == target:
                    return c
            except Exception:
                continue

        return None

    def show_characters(self):
        """Affiche la liste des personnages présents dans la salle."""
        if not self.characters:
            return

        print("\nPersonnes ici :")
        for c in self.characters:
            try:
                print(f"  - {c.name}")
            except Exception:
                print("  - (personne)")
        print()
