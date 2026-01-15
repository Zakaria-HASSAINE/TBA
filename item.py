# item.py

class Item:
    """Classe représentant un objet du jeu."""
    def __init__(self, name, description, weight=1):
        self.name = name
        self.description = description
        self.weight = weight

    def __str__(self):
        return f"{self.name} ({self.weight} kg) : {self.description}"