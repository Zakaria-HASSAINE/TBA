# command.py


class Command:
    """
    Représente une commande utilisable dans le jeu.

    Une commande, c'est :
    - un mot-clé (ex: "go", "look", "take")
    - une petite phrase d'aide (affichée dans help)
    - une fonction à appeler (action)
    - un nombre de paramètres attendus

    Exemple :
        Command("go", " <direction> : se déplacer", Actions.go, 1)
    """

    def __init__(self, command_word, help_string, action, number_of_parameters):
        self.command_word = command_word
        self.help_string = help_string
        self.action = action
        self.number_of_parameters = number_of_parameters

    def __str__(self):
        """
        Affichage lisible dans la commande 'help'.

        On s'assure que help_string est bien précédé d'un espace, pour éviter
        les sorties du type : "go<direction>".
        """
        hs = self.help_string if self.help_string.startswith(" ") else " " + self.help_string
        return f"{self.command_word}{hs}"
