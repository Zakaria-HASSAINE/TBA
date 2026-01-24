# item.py


class Item:
    """
    Représente un objet que le joueur peut trouver, examiner ou ramasser.

    Chaque objet possède :
    - un nom
    - une description
    - un poids (optionnel, pour plus tard si tu veux gérer l’inventaire)
    """

    def __init__(self, name, description, weight=1):
        self.name = name
        self.description = description
        self.weight = weight

    def __str__(self):
        """
        Texte affiché quand on montre l'objet dans l'inventaire ou dans la salle.
        """
        return f"{self.name} ({self.weight} kg) : {self.description}"

    def short_name(self):
        """
        Renvoie le nom de l'objet en version simplifiée.

        Utile pour comparer facilement avec ce que tape le joueur
        (commande take, drop, etc).
        """
        try:
            return self.name.strip().lower()
        except Exception:
            return ""

    def describe(self):
        """
        Affiche la description complète de l'objet (commande look).
        """
        try:
            print(f"\n{self.name} :\n{self.description}\n")
        except Exception:
            print("\nImpossible d'examiner cet objet.\n")
