# character.py

class Character:
    """
    Personnage générique du jeu.

    Un personnage a :
    - un nom (ce que le joueur verra)
    - une description courte (ambiance)
    - un état (vivant / mort)

    Par défaut, un Character ne fait rien de spécial : il peut juste "parler"
    avec une réponse générique. Les personnages importants (Argos, Cassian…)
    héritent de cette classe et redéfinissent talk().
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.is_alive = True

    def describe(self) -> str:
        """Renvoie une description courte, pratique pour un 'look' ou une liste de PNJ."""
        return f"{self.name} : {self.description}"

    def talk(self, game=None) -> str:
        """
        Dialogue par défaut.
        Le paramètre 'game' est optionnel : il sert si un PNJ veut réagir à l'état du jeu.
        """
        msg = f"{self.name} ne répond pas..."
        print(msg)
        return msg


class Argos(Character):
    """
    ARGOS : IA/présence mystérieuse.

    Le dialogue évolue au fil des discussions via 'stage'.
    C'est simple mais efficace pour donner l'impression qu'il suit la progression.
    """

    def __init__(self):
        super().__init__(
            "Argos",
            "Une présence bleue, froide, presque organique… mais sans empathie."
        )
        self.stage = 0

    def talk(self, game=None) -> str:
        """Renvoie une ligne de dialogue, qui change selon l'avancement (stage)."""
        if self.stage == 0:
            msg = "ARGOS — « Enfin. Un organique. Une variable qui marche encore. »"
            self.stage = 1
        elif self.stage == 1:
            msg = "ARGOS — « ATLAS t’observe déjà. La question n’est pas ‘si’… mais ‘quand’. »"
            self.stage = 2
        else:
            msg = "ARGOS — « Décide vite. Je déteste perdre du temps. »"

        print(msg)
        return msg


class Cassian(Character):
    """
    Cassian : humain sous influence.

    controlled = True  -> Cassian parle comme s'il était "parasité"
    controlled = False -> Cassian revient à lui et parle normalement
    """

    def __init__(self):
        super().__init__(
            "Cassian",
            "Un soldat humain. Regard instable. Comme si une autre conscience s’essayait derrière ses yeux."
        )
        self.controlled = True

    def talk(self, game=None) -> str:
        """Dialogue selon l'état du personnage (vivant / contrôlé)."""
        if not self.is_alive:
            msg = "Le corps de Cassian repose au sol, inerte…"
            print(msg)
            return msg

        if self.controlled:
            msg = "CASSIAN — « ...AT---LAS... trop tard... ne... fais... pas... confiance... »"
        else:
            msg = "CASSIAN — « Tu as fait le bon choix. Je te le rendrai. Un jour. »"

        print(msg)
        return msg
