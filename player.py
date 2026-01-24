# player.py


class Player:
    """
    Représente le joueur.

    Le joueur possède :
    - un nom
    - une position actuelle (room)
    - un inventaire
    - un historique de déplacements (pour la commande back)
    """

    def __init__(self, name: str):
        self.name = name
        self.current_room = None

        # Objets que le joueur transporte
        self.inventory = []

        # Historique des salles visitées (utilisé pour "back")
        self.history = []

    def get_history(self) -> str:
        """
        Retourne l'historique des salles déjà visitées.

        On n'affiche pas la salle actuelle,
        seulement celles par lesquelles le joueur est passé avant.
        """
        if not self.history:
            return "\nVous n'avez encore visité aucune autre pièce.\n"

        lines = ["\nVous avez déjà visité les pièces suivantes :"]

        for room in self.history:
            # On privilégie la description, sinon le nom
            if hasattr(room, "description"):
                lines.append(f"  - {room.description}")
            else:
                lines.append(f"  - {room.name}")

        lines.append("")
        return "\n".join(lines)

    def move(self, direction: str) -> bool:
        """
        Déplace le joueur dans une direction donnée.

        - Vérifie si une sortie existe
        - Sauvegarde la position actuelle
        - Met à jour la nouvelle salle
        """

        if self.current_room is None:
            print("\nLe joueur n'est dans aucune salle actuellement.\n")
            return False

        direction = direction.upper()

        next_room = self.current_room.get_exit(direction)

        if not next_room:
            print("\nAucune porte dans cette direction !\n")
            return False

        # On garde la salle actuelle pour pouvoir revenir en arrière
        self.history.append(self.current_room)

        # Déplacement effectif
        self.current_room = next_room

        # Marque la salle comme visitée si l'attribut existe
        if hasattr(self.current_room, "visited"):
            self.current_room.visited = True

        # Affichage après déplacement
        print(self.current_room.get_long_description())
        print(self.get_history())

        return True

    def go_back(self) -> bool:
        """
        Revient à la salle précédente (commande back).

        Utilise l'historique sauvegardé.
        """
        if not self.history:
            print("\nImpossible de revenir en arrière.\n")
            return False

        # On récupère la dernière salle visitée
        self.current_room = self.history.pop()

        if hasattr(self.current_room, "visited"):
            self.current_room.visited = True

        print(self.current_room.get_long_description())
        print(self.get_history())

        return True

    def show_inventory(self):
        """
        Affiche le contenu de l'inventaire du joueur.
        (commande check)
        """
        if not self.inventory:
            print("\nInventaire : (vide)\n")
            return

        print("\nInventaire :")

        for item in self.inventory:
            print(f"  - {item.name}")

        print()

    def add_item(self, item) -> bool:
        """
        Ajoute un objet à l'inventaire.

        Retourne True si l'ajout a réussi.
        """
        self.inventory.append(item)
        return True
