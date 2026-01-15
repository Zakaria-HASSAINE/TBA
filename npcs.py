# npcs.py

class NPC:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.is_alive = True

    def talk(self, game=None):
        print(f"{self.name} ne répond pas...")
        return None


class Argos(NPC):
    def __init__(self):
        super().__init__(
            "Argos",
            "Une présence bleue, froide, presque organique… mais sans empathie."
        )
        self.stage = 0

    def talk(self, game=None):
        if self.stage == 0:
            print("ARGOS — « Enfin. Un organique. Une variable qui marche encore. »")
            self.stage = 1
        elif self.stage == 1:
            print("ARGOS — « ATLAS t’observe déjà. La question n’est pas ‘si’… mais ‘quand’. »")
            self.stage = 2
        else:
            print("ARGOS — « Décide vite. Je déteste perdre du temps. »")


class Cassian(NPC):
    def __init__(self):
        super().__init__(
            "Cassian",
            "Un soldat humain. Regard instable. Comme si une autre conscience s’essayait derrière ses yeux."
        )
        self.controlled = True

    def talk(self, game=None):
        if not self.is_alive:
            print("Le corps de Cassian repose au sol, inerte…")
            return
        if self.controlled:
            print("CASSIAN — « ...AT---LAS... trop tard... ne... fais... pas... confiance... »")
        else:
            print("CASSIAN — « Tu as fait le bon choix. Je te le rendrai. Un jour. »")