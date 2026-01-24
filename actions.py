# actions.py

MSG0 = "\nLa commande '{command_word}' ne prend pas de paramètre.\n"
MSG1 = "\nLa commande '{command_word}' prend 1 seul paramètre.\n"


class Actions:
    """
    Centralise toutes les actions possibles (go, look, take, drop, etc.).

    Chaque méthode est appelée via Command.action(game, words, nb_params).
    L'idée est simple : Actions ne stocke rien, elle utilise l'état du jeu (game).
    """

    @staticmethod
    def _build_direction_aliases(room):
        """
        Fabrique un dictionnaire d'alias de directions à partir des sorties réelles de la salle.

        Exemple :
        - si la salle a une sortie "O", alors on accepte "O", "OUEST"
        - si elle n'a pas de sortie "D", on n'accepte pas "D" / "BAS" / "DOWN"

        Retour :
            dict[str, str] : alias -> direction canonique (ex: "OUEST" -> "O")
        """
        if room is None or not hasattr(room, "exits") or not isinstance(room.exits, dict):
            return {}

        available = {str(d).strip().upper() for d, dest in room.exits.items() if d and dest is not None}

        synonyms = {
            "N": {"N", "NORD"},
            "S": {"S", "SUD"},
            "E": {"E", "EST"},
            "O": {"O", "OUEST"},
            "U": {"U", "UP", "HAUT"},
            "D": {"D", "DOWN", "BAS"},
        }

        aliases = {}
        for canon, syns in synonyms.items():
            if canon in available:
                for s in syns:
                    aliases[s] = canon

        return aliases

    @staticmethod
    def go(game, list_of_words, number_of_parameters):
        """
        go <direction>

        Déplace le joueur dans une direction.
        Directions acceptées : N/S/E/O/U/D + équivalents (nord, sud, ouest...),
        mais uniquement si la sortie existe réellement depuis la salle.
        """
        if len(list_of_words) != number_of_parameters + 1:
            cmd = list_of_words[0] if list_of_words else "go"
            print(MSG1.format(command_word=cmd))
            return False

        player = getattr(game, "player", None)
        if player is None or player.current_room is None:
            print("\nErreur : joueur ou salle courante introuvable.\n")
            return False

        direction_raw = str(list_of_words[1]).strip()
        if not direction_raw:
            print("\nDirection invalide.\n")
            return False

        aliases = Actions._build_direction_aliases(player.current_room)
        key = direction_raw.upper()

        if key not in aliases:
            print(f"\nDirection '{direction_raw}' non reconnue.\n")
            return False

        return bool(player.move(aliases[key]))

    @staticmethod
    def back(game, list_of_words, number_of_parameters):
        """back : revient à la salle précédente (via l'historique du joueur)."""
        if len(list_of_words) != number_of_parameters + 1:
            print(MSG0.format(command_word=list_of_words[0]))
            return False
        return bool(game.player.go_back())

    @staticmethod
    def check(game, list_of_words, number_of_parameters):
        """check : affiche l'inventaire du joueur."""
        if len(list_of_words) != number_of_parameters + 1:
            print(MSG0.format(command_word=list_of_words[0]))
            return False

        game.player.show_inventory()
        return True

    @staticmethod
    def look(game, list_of_words, number_of_parameters):
        """
        look
        look <cible>

        - sans cible : description de la salle + objets visibles + personnages présents
        - avec cible : décrit un objet (inventaire joueur / salle) ou un personnage (si présent)
        """
        player = game.player
        room = player.current_room

        # look
        if len(list_of_words) == 1:
            print(room.get_long_description())
            room.show_inventory()

            # Affiche les PNJ si ta Room a la méthode show_characters()
            if hasattr(room, "show_characters"):
                room.show_characters()

            return True

        # look <cible>
        if len(list_of_words) == 2:
            target = list_of_words[1].strip().lower()

            # 1) Objet dans l'inventaire joueur
            for it in getattr(player, "inventory", []):
                if getattr(it, "name", "").strip().lower() == target:
                    print("\n" + str(it) + "\n")
                    return True

            # 2) Objet dans la salle
            for it in getattr(room, "inventory", []):
                if getattr(it, "name", "").strip().lower() == target:
                    print("\n" + str(it) + "\n")
                    return True

            # 3) Personnage dans la salle (si Room.get_character existe)
            if hasattr(room, "get_character"):
                char = room.get_character(target)
                if char is not None:
                    # On affiche une description courte du perso
                    if hasattr(char, "describe"):
                        print("\n" + char.describe() + "\n")
                    else:
                        print(f"\n{char.name}\n")
                    return True

            print("\nJe ne vois pas ça ici.\n")
            return False

        print(MSG1.format(command_word=list_of_words[0]))
        return False

    @staticmethod
    def take(game, list_of_words, number_of_parameters):
        """take <objet> : ramasse un objet présent dans la salle."""
        if len(list_of_words) != number_of_parameters + 1:
            print(MSG1.format(command_word=list_of_words[0]))
            return False

        item_name = list_of_words[1].strip()
        if not item_name:
            print("\nQuel objet veux-tu prendre ?\n")
            return False

        player = game.player
        room = player.current_room

        item = None
        if hasattr(room, "pop_item_by_name"):
            item = room.pop_item_by_name(item_name)
        else:
            target = item_name.strip().lower()
            for i, it in enumerate(getattr(room, "inventory", [])):
                if getattr(it, "name", "").strip().lower() == target:
                    item = room.inventory.pop(i)
                    break

        if item is None:
            print(f"\nImpossible : '{item_name}' n'est pas ici.\n")
            return False

        player.add_item(item)
        print(f"\nVous avez pris l'objet '{item.name}'.\n")
        return True

    @staticmethod
    def t(game, list_of_words, number_of_parameters):
        """t <objet> : raccourci pour take."""
        return Actions.take(game, list_of_words, number_of_parameters)

    @staticmethod
    def history(game, list_of_words, number_of_parameters):
        """history : affiche l'historique des salles visitées."""
        if len(list_of_words) != number_of_parameters + 1:
            print(MSG0.format(command_word=list_of_words[0]))
            return False

        print(game.player.get_history())
        return True

    @staticmethod
    def drop(game, list_of_words, number_of_parameters):
        """drop <objet> : dépose un objet de l'inventaire dans la salle."""
        if len(list_of_words) != number_of_parameters + 1:
            cmd = list_of_words[0] if list_of_words else "drop"
            print(MSG1.format(command_word=cmd))
            return False

        item_name = list_of_words[1].strip()
        if not item_name:
            print("\nQuel objet veux-tu déposer ?\n")
            return False

        player = game.player
        room = player.current_room
        target = item_name.lower()

        item = None
        for i, it in enumerate(getattr(player, "inventory", [])):
            if getattr(it, "name", "").strip().lower() == target:
                item = player.inventory.pop(i)
                break

        if item is None:
            print(f"\nL'objet '{item_name}' n'est pas dans l'inventaire.\n")
            return False

        room.inventory.append(item)
        print(f"\nVous avez déposé l'objet '{item.name}'.\n")
        return True

    @staticmethod
    def quit(game, list_of_words, number_of_parameters):
        """quit : termine le jeu."""
        if len(list_of_words) != number_of_parameters + 1:
            print(MSG0.format(command_word=list_of_words[0]))
            return False

        print(f"\nMerci {game.player.name} d'avoir joué. Au revoir.\n")
        game.finished = True
        return True

    @staticmethod
    def help(game, list_of_words, number_of_parameters):
        """help : affiche toutes les commandes disponibles."""
        if len(list_of_words) != number_of_parameters + 1:
            print(MSG0.format(command_word=list_of_words[0]))
            return False

        print("\nVoici les commandes disponibles :")
        for command in game.commands.values():
            print("\t- " + str(command))
        print()
        return True

    @staticmethod
    def quests(game, list_of_words, number_of_parameters):
        """quests : liste toutes les quêtes connues."""
        if len(list_of_words) != 1:
            print(MSG0.format(command_word=list_of_words[0]))
            return False
        print(game.qm.list_quests())
        return True

    @staticmethod
    def quest(game, list_of_words, number_of_parameters):
        """quest <id> : affiche les détails d'une quête."""
        if len(list_of_words) != 2:
            print(MSG1.format(command_word=list_of_words[0]))
            return False
        print(game.qm.quest_details(list_of_words[1].strip()))
        return True

    @staticmethod
    def activate(game, list_of_words, number_of_parameters):
        """activate <id> : active/suit une quête."""
        if len(list_of_words) != 2:
            print(MSG1.format(command_word=list_of_words[0]))
            return False

        qid = list_of_words[1].strip()
        ok = game.qm.activate(qid)
        if not ok:
            print("\nQuête introuvable.\n")
            return False

        for u in game.qm.pop_updates():
            print(u)
        print()
        return True

    @staticmethod
    def rewards(game, list_of_words, number_of_parameters):
        """rewards : affiche les récompenses obtenues."""
        if len(list_of_words) != 1:
            print(MSG0.format(command_word=list_of_words[0]))
            return False
        print(game.qm.rewards())
        return True

    @staticmethod
    def talk(game, list_of_words, number_of_parameters):
        """
        talk <pnj>

        Permet de parler à un personnage présent dans la salle.
        Ça marche seulement si :
        - la Room possède get_character()
        - et si le PNJ est bien dans room.characters
        """
        if len(list_of_words) != number_of_parameters + 1:
            cmd = list_of_words[0] if list_of_words else "talk"
            print(MSG1.format(command_word=cmd))
            return False

        target = list_of_words[1].strip()
        if not target:
            print("\nÀ qui veux-tu parler ?\n")
            return False

        room = game.player.current_room
        if not hasattr(room, "get_character"):
            print("\nIl n'y a personne à qui parler ici.\n")
            return False

        char = room.get_character(target)
        if char is None:
            print("\nPersonne de ce nom ici.\n")
            return False

        char.talk(game)
        return True
