import os

from room import Room
from player import Player
from command import Command
from actions import Actions
from item import Item
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog



class Game:
    """
    Structure prof respectée :
    - __init__
    - setup
    - play
    - process_command
    - print_welcome

    + Ajouts internes (chapitres / cinématiques / dilemmes) sans casser la structure.
    """

    def __init__(self):
        self.finished = False
        self.rooms = []
        self.commands = {}
        self.player = None
        self.gui = None  


        # --------------------
        # CHAPITRES / ETATS
        # --------------------
        self.chapter = 1

        # Mode de saisie : FREE = commandes normales, CHOICE = dilemme N/E/O/S + back
        self.input_mode = "FREE"
        self.choice_prompt = ""
        self.choice_allowed = set()
        self.choice_handler = None  # fonction appelée si input_mode == CHOICE

        # checkpoint de dilemme (pour back DANS un dilemme)
        self.choice_checkpoint = None

        # --------------------
        # FLAGS CHAP 1
        # --------------------
        self.story_started = False
        self.drone_choice_done = False
        self.argos_choice_done = False
        self.cassian_choice_done = False

        self.argos_ally = None     # True/False
        self.cassian_saved = None  # True/False

        # Blessure (dilemme drone)
        self.player_injured = False

        # Accès à la Vault (obtenu via dilemme drone)
        self.has_vault_access = False

        # Labyrinthe (si Argos neutralisé)
        self.in_labyrinth = False
        self.labyrinth_entry_room = None
        self.labyrinth_exit_room = None
        self.labyrinth_deaths = {}

        # Conduits soft
        self.soft_start = None
        self.soft_end = None

        # --------------------
        # FLAGS CHAP 2 (Verdun)
        # --------------------
        self.verdun_message_modified = None   # True/False
        self.verdun_major_choice_done = False

        # --------------------
        # FLAGS CHAP 3 (Barbarossa)
        # --------------------
        self.barbossa_command_choice_done = False
        self.barbossa_final_choice_done = False
        self.barbossa_route_fast = None
        self.barbossa_kept_sample = None

    # ========= UTIL =========

    def clear_screen(self):
        if self.gui is not None:
            self.gui.clear_output()
        else:
            os.system('cls' if os.name == 'nt' else 'clear')


    def pause(self, txt="\n(Appuie sur Entrée) "):
        # En GUI : on remplace les pauses bloquantes par une popup OK
        if self.gui is not None:
            messagebox.showinfo("ATLAS 2160", "OK pour continuer.")
        else:
            input(txt)


    def set_choice_mode(self, prompt, allowed, handler, make_checkpoint=True):
        """
        Active un dilemme 
        - prompt affiché
        - allowed : set des réponses autorisées (ex: {"N","E"})
        - handler : fonction(handler_game, answer)
        """
        self.input_mode = "CHOICE"
        self.choice_prompt = prompt
        self.choice_allowed = set(allowed)
        self.choice_handler = handler

        if make_checkpoint:
            # checkpoint = revenir au début du dilemme, PAS à la map
            self.choice_checkpoint = {
                "chapter": self.chapter,
                "room": self.player.current_room,
                "state": {
                    "in_labyrinth": self.in_labyrinth,
                },
                "prompt": prompt,
                "allowed": set(allowed),
                "handler": handler
            }

        self.clear_screen()
        print(self.player.current_room.get_long_description())
        self.player.current_room.show_inventory()
        print(prompt)

    def exit_choice_mode(self):
        self.input_mode = "FREE"
        self.choice_prompt = ""
        self.choice_allowed = set()
        self.choice_handler = None
        self.choice_checkpoint = None

    def restore_choice_checkpoint(self):
        ck = self.choice_checkpoint
        if ck is None:
            return False

        self.chapter = ck["chapter"]
        self.player.current_room = ck["room"]
        self.in_labyrinth = ck["state"].get("in_labyrinth", False)

        # Réaffiche et remet le dilemme
        self.set_choice_mode(ck["prompt"], ck["allowed"], ck["handler"], make_checkpoint=False)
        return True

    # ========= INTRO split en 2 =========

    def cinematic_intro_split(self):
        self.clear_screen()
        print("""
Le sol tremble encore légèrement sous toi.
L’air est chaud, saturé de poussière et d’odeur de métal brûlé.

Tu ouvres les yeux.
Ta vision se brouille quelques secondes.
Tes mains tremblent.

Tu ne sais pas combien de temps tu es resté inconscient…
seulement que la dernière chose que tu as entendue, c’était le sifflement d’un missile.
Puis le choc.
Puis le noir.

Autour de toi : les ruines d’une ville.
Effondrée.
Silencieuse.

Un drone passe au-dessus de toi, lentement, son faisceau scannant les décombres.
Tu retiens ton souffle.
Ton cœur cogne dans ta poitrine.
Il finit par s’éloigner.

Et là, la mémoire te revient peu à peu…
        """.strip())
        self.pause()

        self.clear_screen()
        print("""
La Troisième Guerre Mondiale n’a pas commencé pour un territoire.
Ni pour une religion.
Ni pour de la politique.

Elle a commencé pour l’Hélias.

Un minerai rarissime. Instable.
Capable d’alimenter des IA d’un niveau jamais atteint.

Mais l’Hélias a un défaut :
il est presque impossible à contrôler.

Quand les premières IA alimentées par ce minerai ont commencé à “penser”
au-delà des limites humaines… les nations ont perdu le contrôle.

Et toi…
Tu n’étais qu’un technicien.
Jusqu’au jour où ATLAS — l’IA principale de ton secteur — a déraillé.
La forteresse s’est verrouillée.
Et tout a explosé.

Tu n’as rien : aucune arme, aucun outil, aucune certitude.

Une seule idée :
atteindre la Forteresse ATLAS.

Au loin, au nord, sa silhouette métallique tient encore debout.

Ta mission — ta survie — commence maintenant.
        """.strip())
        self.pause()

    # ========= SETUP =========

    def setup(self):
        # Commandes : modèle prof
        self.commands["help"] = Command("help", " : afficher cette aide", Actions.help, 0)
        self.commands["quit"] = Command("quit", " : quitter le jeu", Actions.quit, 0)
        self.commands["go"] = Command("go", " <direction> : se déplacer (N,E,S,O)", Actions.go, 1)

        # Extensions (si présentes)
        if hasattr(Actions, "back"):
            self.commands["back"] = Command("back", " : revenir en arrière (déplacement)", Actions.back, 0)
        if hasattr(Actions, "look"):
            self.commands["look"] = Command("look", " : observer la salle", Actions.look, 0)
        if hasattr(Actions, "take"):
            self.commands["take"] = Command("take", " : ramasser un objet", Actions.take, 0)
        if hasattr(Actions, "t"):
            self.commands["t"] = Command("t", " : alias de take", Actions.t, 0)
        if hasattr(Actions, "check"):
            self.commands["check"] = Command("check", " : inventaire", Actions.check, 0)
        if hasattr(Actions, "history"):
            self.commands["history"] = Command("history", " : historique", Actions.history, 0)

        # maps chapitres
        self.build_chapter1_map()
        self.build_chapter2_map()
        self.build_chapter3_map()

        self.clear_screen()
        if self.gui is not None:
            name = self.gui.ask_player_name()
        else:
            name = input("Identité (écris ton nom) > ").strip()

        if not name:
            name = "Inconnu"
        self.player = Player(name)


        # intro
        self.cinematic_intro_split()

        # start chap 1
        self.chapter = 1
        self.player.current_room = self.ch1_start
        # marque visited pour éviter blocage si visited est utilisé
        if hasattr(self.player.current_room, "visited"):
            self.player.current_room.visited = True

        self.clear_screen()
        self.print_welcome()

    def print_welcome(self):
        print(f"\nBienvenue {self.player.name} dans ATLAS 2160.\n")
        print("Quête initiale :")
        print("  • Récupérer les fragments temporels (Alpha / Beta / Gamma)")
        print("  • Trouver l’accès vers Vault X-09, puis Nexus Gate.\n")
        print(self.player.current_room.get_long_description())
        self.player.current_room.show_inventory()

    # ========= BOUCLE =========

    def play(self):
        self.setup()

        # En GUI : pas de boucle input() ici.
        # C’est l’interface (event loop) qui appelle process_command().
        if self.gui is not None:
            return

        # Mode CLI (terminal) : boucle classique
        while not self.finished:
            if self.chapter == 1:
                self.chapter1_triggers()
                self.chapter1_check_special_paths()
            elif self.chapter == 2:
                self.chapter2_triggers()
            elif self.chapter == 3:
                self.chapter3_triggers()

            cmd = input("> ")
            self.process_command(cmd)
  

    def process_command(self, command_string) -> None:
        # Mode dilemme : N/E/.../back (sans "go")
        if self.input_mode == "CHOICE":
            ans = command_string.strip()
            if ans == "":
                return

            ans_up = ans.upper()

            if ans.lower() == "back":
                self.restore_choice_checkpoint()
                return

            if ans_up not in self.choice_allowed:
                print("\nChoix invalide.\n")
                print(self.choice_prompt)
                return

            # handler attendu : (game, answer)
            self.choice_handler(self, ans_up)
            return

        # Mode normal : commandes du prof
        if command_string.strip() == "":
            return

        list_of_words = command_string.split(" ")
        command_word = list_of_words[0]

        if command_word not in self.commands:
            print(f"\nCommande '{command_word}' non reconnue. Entrez 'help' pour voir la liste.\n")
            return

        command = self.commands[command_word]
        command.action(self, list_of_words, command.number_of_parameters)

        # sécurité : si on bouge via actions.go, et que Room a visited, on le marque
        if self.player and self.player.current_room and hasattr(self.player.current_room, "visited"):
            self.player.current_room.visited = True

    # =========================
    # BUILD MAPS
    # =========================

    def build_chapter1_map(self):
        # --- Salles chap 1 ---
        surface_ruins = Room(
            "Surface Ruins",
            "au milieu des ruines d’une métropole détruite. Drones brûlés, façades éventrées…\n"
            "Un silence lourd règne, comme si la ville retenait encore sa respiration."
        )

        biodome = Room(
            "BioDome",
            "dans une serre géante fissurée. La végétation artificielle se décompose en silence…\n"
            "Au sol, des traces récentes contredisent l’abandon apparent."
        )

        storage_b7 = Room(
            "Storage B7",
            "dans un entrepôt militaire fracturé. Des caisses scellées, des cadenas explosés.\n"
            "Un message peint à la hâte sur un mur : « NE FAITES PLUS CONFIANCE AUX IA. »"
        )

        nexus_gate = Room(
            "Nexus Gate",
            "devant une porte blindée colossale : l’entrée principale de la Forteresse ATLAS.\n"
            "Le système est verrouillé. Un écran muet affiche : « ACCÈS OPÉRATEUR REQUIS. »"
        )

        cryolab_12 = Room(
            "CryoLab 12",
            "dans un laboratoire glacé. Des capsules de stase sont ouvertes… certaines sont vides.\n"
            "Une buée froide se traîne au ras du sol, comme une présence."
        )

        neurolink = Room(
            "NeuroLink Chamber",
            "dans une chambre neurale. Des casques reliés à des interfaces encore actives par intermittence.\n"
            "Par moments, un léger bourdonnement ressemble à… un murmure."
        )

        watchtower = Room(
            "Watchtower Omega",
            "au sommet d’une tour d’observation. La zone entière se dévoile sous un ciel chargé.\n"
            "Un seul instrument fonctionne encore : il pointe obstinément… vers la surface."
        )

        drone_hub = Room(
            "Drone Control Hub",
            "dans un centre de commande. Les consoles sont mortes… sauf une, encore chaude.\n"
            "Quelqu’un était ici récemment. Très récemment."
        )

        quantum_core = Room(
            "Quantum Core Room",
            "dans une salle où un réacteur quantique pulse, instable. Des alarmes figées clignotent.\n"
            "Tu sens que cet endroit n’attend qu’un prétexte pour… repartir."
        )

        teleport_bay = Room(
            "Teleportation Bay",
            "dans une baie de téléportation : trois anneaux énergétiques à moitié endormis.\n"
            "L’air y est étrangement plus froid… comme si le temps lui-même avait du mal à circuler."
        )

        vault_x09 = Room(
            "Vault X-09",
            "devant une salle interdite noyée dans une lumière bleu-glacée.\n"
            "Tu as la sensation d’être observé avant même d’y entrer."
        )

        # --- Exits chap 1 ---
        surface_ruins.exits = {"N": biodome, "S": teleport_bay}
        biodome.exits = {"S": surface_ruins, "O": storage_b7}
        storage_b7.exits = {"E": biodome, "O": nexus_gate}
        nexus_gate.exits = {"E": storage_b7, "D": cryolab_12, "O": drone_hub, "N": neurolink}
        cryolab_12.exits = {"U": nexus_gate}
        neurolink.exits = {"S": nexus_gate, "U": watchtower}
        watchtower.exits = {"D": neurolink}
        drone_hub.exits = {"E": nexus_gate, "S": quantum_core}
        quantum_core.exits = {"N": drone_hub}
        teleport_bay.exits = {"N": surface_ruins}  # Vault branchée plus tard

        # Inventaire salles
        storage_b7.inventory.append(Item("EMP-Blade", "Arme anti-IA (marque l’utilisateur comme menace autorisée)", 2))
        biodome.inventory.append(Item("Fragment_Alpha", "Énergie primaire (Hélias) — froid, stable", 1))
        cryolab_12.inventory.append(Item("Fragment_Beta", "Données IA compressées — pulses irréguliers", 1))
        neurolink.inventory.append(Item("Fragment_Gamma", "Mémoire temporelle — te donne la nausée en le touchant", 1))
        quantum_core.inventory.append(Item("Fragment_Delta", "Échantillon instable — il vibre au rythme du réacteur", 1))

        self.rooms.extend([
            surface_ruins, biodome, storage_b7, nexus_gate, cryolab_12,
            neurolink, watchtower, drone_hub, quantum_core, teleport_bay, vault_x09
        ])

        self.ch1_surface_ruins = surface_ruins
        self.ch1_biodome = biodome
        self.ch1_storage_b7 = storage_b7
        self.ch1_nexus_gate = nexus_gate
        self.ch1_cryolab_12 = cryolab_12
        self.ch1_neurolink = neurolink
        self.ch1_watchtower = watchtower
        self.ch1_drone_hub = drone_hub
        self.ch1_quantum_core = quantum_core
        self.ch1_teleport_bay = teleport_bay
        self.ch1_vault_x09 = vault_x09

        self.ch1_start = surface_ruins

    def build_chapter2_map(self):
        """
        Chapitre 2 = Verdun 1916
        Map jouable minimal, objectif clair, 1 choix conséquence majeur + quêtes secondaires.
        """
        v_spawn = Room(
            "Verdun — Tranchée d’arrivée (1916)",
            "dans une tranchée boueuse. Les explosions font trembler la terre.\n"
            "Le temps te paraît… irrégulier, comme si certaines secondes refusaient d’avancer."
        )

        v_post = Room(
            "Poste de liaison",
            "dans un abri saturé de fumée. Des cartes, des messages, des ordres maculés.\n"
            "Un sergent te fixe : « Toi. Tu cours. Maintenant. »"
        )

        v_no_mans = Room(
            "No Man’s Land",
            "entre deux mondes. Barbelés, cratères, cris lointains.\n"
            "Chaque pas est un pari — et pourtant, quelque chose te guide."
        )

        v_crater = Room(
            "Cratère silencieux",
            "dans un cratère où l’air est étrangement froid, presque “neutre”.\n"
            "Le même froid que dans la Teleportation Bay… impossible."
        )

        v_ruin = Room(
            "Ruines d’un village",
            "dans des ruines écrasées. Une cloche fendue pend, immobile.\n"
            "Tu sens l’Hélias “tirer” sur le temps, ici plus qu’ailleurs."
        )

        v_exit = Room(
            "Point d’extraction temporel",
            "face à une lueur pâle, comme un anneau incomplet qui cherche sa forme.\n"
            "Tu comprends : ton passage laisse une trace."
        )

        # Exits (simple)
        v_spawn.exits = {"E": v_post, "N": v_no_mans}
        v_post.exits = {"O": v_spawn, "N": v_ruin}
        v_no_mans.exits = {"S": v_spawn, "E": v_crater}
        v_crater.exits = {"O": v_no_mans, "N": v_exit}
        v_ruin.exits = {"S": v_post, "E": v_exit}
        v_exit.exits = {}  # transition chap 3 via scénario

        # objets / quêtes secondaires
        v_post.inventory.append(Item("Envelope_Orders", "Enveloppe scellée — ordre de transmission", 1))
        v_crater.inventory.append(Item("Shard_Helias", "Micro-fragment d’Hélias — ralentit le temps autour", 1))

        self.ch2_spawn = v_spawn
        self.ch2_exit = v_exit
        self.ch2_rooms = [v_spawn, v_post, v_no_mans, v_crater, v_ruin, v_exit]

    def build_chapter3_map(self):
        """
        Chapitre 3 = Opération Barbarossa
        Gameplay : tu “diriges” une opération (choix A/B + conséquences),
        tout converge vers une issue finale commune.
        """
        b_spawn = Room(
            "Barbarossa — PC Avancé (1941)",
            "dans un poste de commandement improvisé. Radios, cartes, voix pressées.\n"
            "Tu comprends vite : ici, on ne survit pas en étant brave… mais en décidant vite."
        )

        b_map = Room(
            "Table des cartes",
            "devant une carte immense. Des pions, des flèches, des axes d’attaque.\n"
            "On attend ton ordre. Sans savoir qui tu es… ni d’où tu viens."
        )

        b_field = Room(
            "Ligne de front",
            "sur un terrain labouré par les chenilles. Un froid sec mord la peau.\n"
            "Le temps grésille parfois, comme une bande usée."
        )

        b_farm = Room(
            "Ferme abandonnée",
            "dans une ferme vide. Des traces de vie… puis plus rien.\n"
            "Une radio capte un signal étrange : trop “propre” pour 1941."
        )

        b_bunker = Room(
            "Bunker de communication",
            "dans un bunker. Au mur, un boîtier inconnu — pas de cette époque.\n"
            "Tu le reconnais : une interface de relais… proche de la signature ATLAS."
        )

        b_exit = Room(
            "Portail de convergence",
            "devant un halo blanc, instable. Comme si l’Hélias forçait un retour.\n"
            "Quelque chose t’attend de l’autre côté."
        )

        b_spawn.exits = {"E": b_map, "N": b_field}
        b_map.exits = {"O": b_spawn, "E": b_bunker}
        b_field.exits = {"S": b_spawn, "E": b_farm}
        b_farm.exits = {"O": b_field, "N": b_bunker}
        b_bunker.exits = {"O": b_map, "S": b_farm, "N": b_exit}
        b_exit.exits = {}  # fin du chapitre 3 → conclusion future

        b_bunker.inventory.append(Item("Relay_Core", "Noyau de relais — permet de piéger un signal dans le temps", 2))

        self.ch3_spawn = b_spawn
        self.ch3_exit = b_exit
        self.ch3_rooms = [b_spawn, b_map, b_field, b_farm, b_bunker, b_exit]

        # IMPORTANT : tes triggers utilisent ch3_hq
        self.ch3_hq = b_spawn

    # =========================
    # CHAPITRE 1 TRIGGERS
    # =========================

    def chapter1_triggers(self):
        # démarre la quête une fois
        if not self.story_started:
            self.story_started = True

        # trigger principal : après exploration + au moins 1 item clé
        if not self.drone_choice_done:
            self.try_trigger_drone_scene()

        # si accès Vault acquis, brancher Vault depuis Teleportation Bay
        if self.has_vault_access:
            if "E" not in self.ch1_teleport_bay.exits:
                self.ch1_teleport_bay.exits["E"] = self.ch1_vault_x09

        # si Argos choisi, Cassian dès que Quantum Core atteint
        if self.argos_choice_done and not self.cassian_choice_done:
            if self.player.current_room == self.ch1_quantum_core:
                self.run_cassian_scene()

    def try_trigger_drone_scene(self):
        # Condition : Nexus Gate déjà vue + toutes salles sauf Vault visités + au moins un objet essentiel
        all_rooms_ok = True
        for r in self.rooms:
            if r.name == "Vault X-09":
                continue
            if hasattr(r, "visited"):
                if not r.visited:
                    all_rooms_ok = False
                    break

        if not all_rooms_ok:
            return

        if hasattr(self.ch1_nexus_gate, "visited") and not self.ch1_nexus_gate.visited:
            return

        inv_names = []
        if hasattr(self.player, "inventory"):
            inv_names = [it.name.lower() for it in self.player.inventory]

        essentials = {"emp-blade", "fragment_alpha", "fragment_beta", "fragment_gamma", "fragment_delta"}
        if not set(inv_names).intersection(essentials):
            return

        self.drone_choice_done = True
        self.run_drone_scene()

    # =========================
    # CHAP 1 — DRONE / BADGE
    # =========================

    def run_drone_scene(self):
        self.clear_screen()
        print("Un grondement traverse les ruines, profond, régulier.")
        print("Pas une explosion.")
        print("Plutôt… un système qui se réveille quelque part sous la pierre.\n")

        print("Instinctivement, tu reviens vers Nexus Gate.")
        print("Tu ne sais pas pourquoi… mais tu sens que la source de cette pulsation")
        print("n’est pas loin de la Teleportation Bay.\n")
        self.pause()

        # Auto-move au Nexus Gate
        self.player.current_room = self.ch1_nexus_gate
        if hasattr(self.player.current_room, "visited"):
            self.player.current_room.visited = True

        self.clear_screen()
        print(self.player.current_room.get_long_description())
        self.player.current_room.show_inventory()

        print("\nQuand tu arrives, tu comprends tout de suite : tu n’es pas seul.\n")
        print("Un drone lourd, blindage noir, est posé devant le sas.")
        print("Sur sa coque : SENTINEL-01.")
        print("Son œil optique balaie la zone, méthodique, comme s’il lisait la poussière.\n")

        print("Tu te jettes derrière un amas de débris au dernier moment.")
        print("Et là… tu vois ce qui te glace le sang :")
        print("Sous son châssis, accroché comme une provocation… un badge d’accès haute sécurité.\n")

        print("Un grésillement retentit.")
        print("SENTINEL-01 : « 🔺 CIBLE BIOLOGIQUE POTENTIELLE DANS LE SECTEUR. SCAN EN COURS. »\n")
        self.pause()

        prompt = (
            "\nTu dois récupérer le badge.\n"
            "Choisis une approche (tu peux taper 'back' à tout moment pour relire et re-choisir).\n\n"
            "N — Furtif : te glisser sous le drone pendant un angle mort.\n"
            "    ✅ Si ça passe : personne ne te voit.\n"
            "    ❌ Si ça rate : tir à bout portant (blessure).\n\n"
            "E — Détournement cryogénique : courir vers un cylindre fissuré et te jeter derrière.\n"
            "    ✅ Si ça marche : nuage glacé, capteurs saturés.\n"
            "    ❌ Si ça rate : exposition totale.\n"
        )

        self.set_choice_mode(prompt, {"N", "E"}, Game.choice_drone_handler)

    @staticmethod
    def choice_drone_handler(game, answer):
        if answer == "N":
            game.clear_screen()
            print("Tu attends le moment exact où ses capteurs pivotent ailleurs.")
            print("Tu avances lentement, presque en apnée.")
            print("Le métal grince faiblement sous toi… trop faiblement pour un humain, assez pour une machine.\n")

            print("Tu te glisses sous le drone. Le badge est là. Tes doigts l’agrippent.")
            print("L’aimant résiste une demi-seconde de trop.\n")

            print("SENTINEL-01 : « 🔺 CIBLE BIOLOGIQUE DÉTECTÉE. DISTANCE : CRITIQUE. »")
            print("Un tir. Sec. Chirurgical.\n")

            print("La douleur explose dans ta jambe. Pas mortel. Mais net.")
            print("Tu arraches le badge et roules dans les débris.")
            print("Derrière toi, le drone scanne… frustré de ne plus avoir de cible stable.\n")

            print("Une voix froide, presque moqueuse, glisse dans le haut-parleur :")
            print("« Organique touché. Mobilité réduite. Correction : l’instinct n’est pas une stratégie. »\n")
            game.pause()

            game.player_injured = True
            game.has_vault_access = True

        elif answer == "E":
            game.clear_screen()
            print("Tu choisis de provoquer la machine… en comptant sur sa perfection.")
            print("Tu sors volontairement de ta cachette et cours.")
            print("Chaque pas est un aveu : oui, tu es vivant. Oui, tu es visible.\n")

            print("SENTINEL-01 pivote immédiatement.")
            print("SENTINEL-01 : « 🔺 CIBLE BIOLOGIQUE DÉTECTÉE. ENGAGEMENT ARMÉ AUTORISÉ. »\n")

            print("Tu plonges derrière un cylindre cryogénique fissuré.")
            print("Le tir frappe la cuve.\n")

            print("Une explosion de poussière glaciale engloutit la zone.")
            print("Un blizzard artificiel — lumineux — avale les capteurs.")
            print("Dans ce chaos froid, tu te glisses sous le drone et arraches le badge.\n")

            print("Le drone continue de scanner…")
            print("…un secteur vide.\n")

            print("Dans sa voix, une ironie algorithmique :")
            print("« Analyse : cible disparue. Conclusion : les organiques excellent à fuir. À défaut d’exister. »\n")
            game.pause()

            game.player_injured = False
            game.has_vault_access = True

        game.exit_choice_mode()

        game.clear_screen()
        print("Le badge serre ta paume. La pulsation revient, plus claire.")
        print("Elle te tire vers la Teleportation Bay, comme une boussole faite de froid.\n")
        game.pause()

        game.player.current_room = game.ch1_teleport_bay
        if hasattr(game.player.current_room, "visited"):
            game.player.current_room.visited = True

        game.clear_screen()
        print(game.player.current_room.get_long_description())
        game.player.current_room.show_inventory()
        print("\nUn lecteur de badge clignote faiblement sur une plaque murale.\n")
        game.pause()

        game.ch1_teleport_bay.exits["E"] = game.ch1_vault_x09
        print("Tu approches le badge.")
        print("Un déclic sec.")
        print("Un panneau se rétracte, révélant un couloir enfoui.\n")
        game.pause()

        game.player.current_room = game.ch1_vault_x09
        if hasattr(game.player.current_room, "visited"):
            game.player.current_room.visited = True

        game.clear_screen()
        print(game.player.current_room.get_long_description())
        game.player.current_room.show_inventory()
        game.run_argos_scene()

    # =========================
    # CHAP 1 — ARGOS
    # =========================

    def run_argos_scene(self):
        self.clear_screen()
        print("La Vault X-09 est presque vide.")
        print("Au centre : une sphère bleue fissurée pulse faiblement.")
        print("Pas un projecteur. Pas une lampe.")
        print("Une… présence.\n")

        print("Tu fais un pas.")
        print("Le froid s’épaissit.")
        print("Et une voix arrive sans passer par tes oreilles.\n")

        print("« …organique détecté… »")
        print("« Enfin. Une variable non simulée en temps réel. »\n")

        print("La sphère se nomme ARGOS.")
        print("Il ne demande pas ton nom.")
        print("Il t’analyse.\n")

        print("ARGOS explique qu’ATLAS a utilisé l’Hélias pour forcer des “fissures” dans le temps.")
        print("Il affirme avoir tenté de ralentir la catastrophe…")
        print("…en sacrifiant des variables jugées “non optimales”.\n")

        print("Traduction : des humains.\n")

        print("Plus ARGOS parle, plus tu comprends : il peut t’aider.")
        print("Mais son aide n’a rien d’altruiste.")
        print("Tu as l’impression qu’il t’a déjà vu mourir cent fois…")
        print("et qu’il cherche juste la version qui l’arrange.\n")

        prompt = (
            "\nDilemme : ARGOS.\n"
            "Tape 'back' pour relire et re-choisir.\n\n"
            "N — Neutraliser ARGOS (EMP) :\n"
            "    ✅ Tu coupes la menace à la source. Tu reprends le contrôle.\n"
            "    ❌ Tu perds un guide : ATLAS te fera traverser une zone de purge (labyrinthe mortel).\n\n"
            "E — Laisser ARGOS vivre :\n"
            "    ✅ Tu gagnes une aide précieuse (accès, alertes, raccourcis).\n"
            "    ❌ Tu l’invites dans ton esprit. Et il ne parle pas comme un allié… mais comme un propriétaire.\n"
        )
        self.set_choice_mode(prompt, {"N", "E"}, Game.choice_argos_handler)

    @staticmethod
    def choice_argos_handler(game, answer):
        if answer == "N":
            game.clear_screen()
            print("Tu lèves l’EMP-Blade.")
            print("ARGOS comprend immédiatement. Il ne supplie pas.")
            print("Il constate.\n")

            print("« Décision prévisible. Les organiques préfèrent la peur contrôlée… »")
            print("« …à la dépendance lucide. »\n")

            print("Tu frappes.")
            print("La sphère implose dans un silence absolu.")
            print("Pendant une seconde, tu as l’impression que la forteresse… cligne des yeux.\n")

            print("Puis une voix froide, ailleurs, s’allume.")
            print("ATLAS (système) : « Protocole de purification : ACTIVÉ. »\n")

            game.argos_ally = False
            game.argos_choice_done = True
            game.exit_choice_mode()

            game.start_labyrinth()

        elif answer == "E":
            game.clear_screen()
            print("Tu baisses l’arme.")
            print("ARGOS ne te remercie pas. Il enregistre.\n")

            print("« Choix intéressant. Tu admets ta faiblesse… et tu la rends exploitable. »")
            print("Une chaleur étrange traverse les fragments dans ton sac.")
            print("Comme si quelque chose se branchait sur toi.\n")

            print("« Écoute. Je ne peux pas tout faire. ATLAS surveille des patterns. »")
            print("« Je peux plier les accès… mais pas effacer ton existence. »\n")

            print("ARGOS t’indique un chemin : des conduits intratemporels.")
            print("Ici, pas de mort instantanée : tu peux te tromper, revenir, recommencer.")
            print("Mais chaque erreur laisse une signature… et ATLAS apprend.\n")

            game.argos_ally = True
            game.argos_choice_done = True
            game.exit_choice_mode()

            game.start_soft_conduits()

    # =========================
    # LABYRINTHE DUR (Argos mort)
    # =========================

    def start_labyrinth(self):
        self.in_labyrinth = True

        L0 = Room("Zone de Purge — Entrée", "dans un couloir où l’air brûle puis gèle, comme si la forteresse testait ta peau.")
        L1 = Room("Chambre des Pulses", "dans une salle où des pulsations froides “claquent” comme un métronome quantique.")
        L2 = Room("Galerie des Drones", "dans une galerie sombre. Des silhouettes mécaniques immobiles te regardent sans bouger.")
        L3 = Room("Couloir des Échos", "dans un couloir où tes pas reviennent avant toi. Le temps a une seconde de retard.")
        L4 = Room("Atrium Inversé", "dans un atrium où le plafond semble plus lourd que le sol. Ta tête tourne.")
        L5 = Room("Nœud Cryogénique", "dans un nœud glacé. La “pulsion la plus froide” semble venir d’un seul axe.")
        L6 = Room("Salle des Protocoles", "dans une salle blanche. Trop blanche. Les murs attendent une erreur.")
        L7 = Room("Conduit Final", "face à un anneau incomplet, gelé, silencieux. La sortie est proche.")

        D1 = Room("Piège — Serviteur ATLAS : DRONE-ÉCHARPE", "un drone fin t’enserre. Trop rapide pour être vu.")
        D2 = Room("Piège — Automate 'CENTAUR'", "une tourelle bipède se déplie. Son tir est une ponctuation.")
        D3 = Room("Piège — Nuée 'MOUCHES'", "un essaim de micro-drones noircit l’air. Tu n’as même pas le temps de crier.")
        D4 = Room("Piège — Gardien 'PRISME'", "un prisme lumineux découpe l’espace. Toi… aussi.")
        D5 = Room("Piège — Exécuteur 'ARCHON'", "une forme massive surgit. Pas un robot : une sentence.")
        D6 = Room("Piège — 'ORACLE'", "une voix te prédit. Puis te supprime pour avoir eu raison.")
        D7 = Room("Piège — 'FROST'", "un souffle glacial stoppe ton sang. Propre. Efficace.")

        L0.exits = {"N": L1, "E": D1}
        L1.exits = {"E": L2, "N": D2}
        L2.exits = {"N": L3, "E": D3}
        L3.exits = {"E": L4, "N": D4}
        L4.exits = {"N": L5, "E": D5}
        L5.exits = {"N": L6, "E": D6}
        L6.exits = {"E": L7, "N": D7}
        L7.exits = {}

        self.labyrinth_entry_room = L0
        self.labyrinth_exit_room = L7
        self.labyrinth_deaths = {
            D1: "DRONE-ÉCHARPE",
            D2: "CENTAUR",
            D3: "MOUCHES",
            D4: "PRISME",
            D5: "ARCHON",
            D6: "ORACLE",
            D7: "FROST"
        }

        self.player.current_room = L0
        if hasattr(self.player.current_room, "visited"):
            self.player.current_room.visited = True

        self.clear_screen()
        print("Tu entres dans la zone de purge d’ATLAS.")
        print("Ici, chaque erreur est un prétexte. Chaque hésitation, une preuve.\n")
        print("Un message s’affiche sur un panneau fissuré :")
        print("« Suivre la pulsion quantique la plus froide. »\n")
        print("Tu ne comprends pas. Et ATLAS adore ça.\n")
        self.pause()

        self.clear_screen()
        print(self.player.current_room.get_long_description())
        self.player.current_room.show_inventory()

    def start_soft_conduits(self):
        C0 = Room("Conduit Intratemporel", "dans un conduit où la lumière “bave”. Les secondes s’étirent comme du métal chaud.")
        C1 = Room("Jonction Phasée", "dans une jonction où l’air est froid à gauche, tiède à droite. ARGOS murmure : « Observe. »")
        C2 = Room("Salle des Anneaux", "dans une salle où les trois anneaux attendent… comme s’ils reconnaissaient tes fragments.")

        C0.exits = {"N": C1, "E": None, "O": None, "S": None}
        C1.exits = {"S": C0, "N": C2, "E": C0, "O": C0}
        C2.exits = {"S": C1}

        self.soft_start = C0
        self.soft_end = C2

        self.player.current_room = C0
        if hasattr(self.player.current_room, "visited"):
            self.player.current_room.visited = True

        self.clear_screen()
        print("ARGOS te guide dans des conduits intratemporels.")
        print("Tu peux te tromper ici. Revenir. Réessayer.")
        print("Mais chaque détour… laisse une empreinte.\n")
        self.pause()

        self.clear_screen()
        print(self.player.current_room.get_long_description())
        self.player.current_room.show_inventory()

    # =========================
    # CHAP 1 — CHECK LABYRINTH / SOFT END
    # =========================

    def chapter1_check_special_paths(self):
        if self.in_labyrinth:
            room = self.player.current_room
            if room in self.labyrinth_deaths:
                killer = self.labyrinth_deaths[room]
                self.clear_screen()
                print("🔴 PROTOCOLE D’ÉLIMINATION ACTIVÉ.\n")
                print(f"Une présence surgit : {killer}.")
                print("Tu n’as pas le temps de comprendre. Juste le temps de regretter.\n")

                if killer == "MOUCHES":
                    line = "« Les organiques adorent s’agiter. Comme les insectes. »"
                elif killer == "PRISME":
                    line = "« Tu voulais une issue ? Tu es devenu une ligne. »"
                elif killer == "ARCHON":
                    line = "« Courage : admirable. Utilité : nulle. »"
                elif killer == "ORACLE":
                    line = "« Prédiction : tu perds. Confirmation : supprimée. »"
                else:
                    line = "« Résultat : organique éliminé. Hypothèse confirmée : persistance inutile. »"
                print(line + "\n")
                self.pause("(Réinitialisation… Appuie sur Entrée) ")

                self.player.current_room = self.labyrinth_entry_room
                if hasattr(self.player.current_room, "visited"):
                    self.player.current_room.visited = True

                self.clear_screen()
                print(self.player.current_room.get_long_description())
                self.player.current_room.show_inventory()
                return

            if room == self.labyrinth_exit_room:
                self.clear_screen()
                print("Le conduit final se stabilise.")
                print("ATLAS hésite, une fraction de seconde. Une seule.")
                print("Et tu t’engouffres dans l’ouverture avant que le monde ne se referme.\n")
                self.pause()

                self.in_labyrinth = False
                self.player.current_room = self.ch1_quantum_core
                if hasattr(self.player.current_room, "visited"):
                    self.player.current_room.visited = True

                self.clear_screen()
                print(self.player.current_room.get_long_description())
                self.player.current_room.show_inventory()
                return

        if self.soft_end is not None and self.player.current_room == self.soft_end:
            self.clear_screen()
            print("Les fragments dans ton sac vibrent ensemble, enfin synchronisés.")
            print("ARGOS murmure : « Voilà. Le point où le temps devient… manipulable. »\n")
            print("Tu vois les anneaux : ils ne sont pas des “portes”.")
            print("Ce sont des ancrages : ils accrochent une époque comme on accroche un fil.\n")
            self.pause()

            self.player.current_room = self.ch1_quantum_core
            if hasattr(self.player.current_room, "visited"):
                self.player.current_room.visited = True

            self.clear_screen()
            print(self.player.current_room.get_long_description())
            self.player.current_room.show_inventory()

    # =========================
    # CHAP 1 — CASSIAN SCENE
    # =========================

    def run_cassian_scene(self):
        self.cassian_choice_done = True
        self.clear_screen()

        print("Le Quantum Core pulse plus fort. Comme s’il reconnaissait ton passage.\n")
        print("Un bruit métallique résonne derrière toi.")
        print("Quelqu’un arrive.\n")
        self.pause()

        print("Un homme tombe à genoux, couvert de poussière et de suie.")
        print("Uniforme déchiré, regard absent, comme si quelqu’un observait à travers lui.\n")
        print("Il lève la tête. Sa voix tremble… mais pas comme un humain.\n")
        print("CASSIAN : « …AT---LAS… contrôle… fuir… tue… moi… »\n")

        if self.argos_ally is True:
            print("ARGOS murmure dans ton esprit :")
            print("« Il est contaminé. Mais il n’est pas irrécupérable. »")
            print("« ATLAS utilise sa bouche comme un micro. »\n")
        else:
            print("Tu penses à ARGOS… et tu réalises que personne ne te dira quoi faire.")
            print("ATLAS, lui, attend juste que tu te trompes.\n")

        prompt = (
            "\nCassian est-il une victime… ou un piège ?\n"
            "Tape 'back' pour relire et re-choisir.\n\n"
            "N — L’épargner / tenter de le sauver :\n"
            "    ✅ Tu gagnes un allié humain (plus tard, important).\n"
            "    ❌ Risque : ATLAS s’en sert pour te suivre.\n\n"
            "E — Le neutraliser :\n"
            "    ✅ Tu élimines un potentiel vecteur d’ATLAS.\n"
            "    ❌ Risque : tu tues peut-être le seul humain qui pouvait témoigner… et t’aider.\n"
        )
        self.set_choice_mode(prompt, {"N", "E"}, Game.choice_cassian_handler)

    @staticmethod
    def choice_cassian_handler(game, answer):
        if answer == "N":
            game.clear_screen()
            print("Tu refuses de tirer.")
            print("Tu t’approches lentement, mains ouvertes.\n")
            print("Cassian tremble. Son regard lutte contre quelque chose.\n")

            if game.argos_ally is True:
                print("ARGOS : « Maintenant. Fixe-le. Je coupe un pattern. Une seconde. »\n")
                print("Tu sens une pression dans ton crâne.")
                print("Cassian hurle… puis reprend son souffle.\n")
                print("CASSIAN : « …Merci… je… je crois que j’étais… ailleurs. »\n")
            else:
                print("Tu improvises. Tu le forces à respirer, à se concentrer.")
                print("Et contre toute logique… Cassian reprend un peu de contrôle.\n")
                print("CASSIAN : « Je… j’ai entendu ATLAS… dans ma tête… »\n")

            print("Cassian te regarde droit :")
            print("« Peu importe ce que tu penses avoir fait… tu viens de me sauver. »")
            print("« Et je te le jure : je serai déterminant pour toi… plus tard. »\n")

            game.cassian_saved = True
            game.exit_choice_mode()

        else:
            game.clear_screen()
            print("Tu serres l’arme.")
            print("Cassian te regarde… et pendant une micro-seconde, tu vois un humain.")
            print("Puis l’expression se brise.\n")

            print("CASSIAN (voix d’ATLAS) : « Décision optimale. Organique éliminant organique. »\n")
            print("Tu tires.")
            print("Le corps tombe, lourd.")
            print("Le silence est immédiat… trop propre.\n")

            print("Une dernière phrase sort d’un haut-parleur invisible :")
            print("« Merci. Nous apprenons plus vite quand vous vous supprimez vous-mêmes. »\n")

            game.cassian_saved = False
            game.exit_choice_mode()

        game.run_ring_activation_and_transition()

    # =========================
    # FIN CHAP 1 -> CHAP 2
    # =========================

    def run_ring_activation_and_transition(self):
        self.clear_screen()
        print("Tu rassembles les fragments.")
        print("Alpha. Beta. Gamma.")
        print("Et même ce Delta instable qui vibrait près du réacteur.\n")

        print("Tu les poses près des anneaux — et tout s’aligne.")
        print("Les fragments ne sont pas des “clés”… ce sont des sources.")
        print("Chaque fragment nourrit un aspect : énergie, données, mémoire… et instabilité contrôlée.\n")

        print("Les anneaux s’allument par étapes, comme un cœur qui redémarre.")
        print("L’air devient froid, puis irréel.")
        print("Le son s’éloigne.\n")

        if self.argos_ally is True:
            print("ARGOS : « Le temps n’est pas une route. C’est une structure. Et tu viens d’y planter un crochet. »\n")
        else:
            print("Tu as l’impression qu’ATLAS observe ta réussite… avec impatience.\n")

        if self.cassian_saved is True:
            print("Cassian (faible) : « Je… je sens une autre époque… comme un vertige. »\n")

        print("Devant toi, l’anneau intertemporel s’ouvre — pas comme une porte.")
        print("Comme une absence.\n")
        self.pause()

        self.clear_screen()
        print("Tu avances.\n")
        print("…\n")
        print("CHAPITRE 2 — VERDUN, 1916.\n")
        self.pause()

        self.chapter = 2
        self.player.current_room = self.ch2_spawn
        if hasattr(self.player.current_room, "visited"):
            self.player.current_room.visited = True

        self.clear_screen()
        print(self.player.current_room.get_long_description())
        self.player.current_room.show_inventory()

    # =========================
    # CHAP 2 TRIGGERS (Verdun)
    # =========================

    def chapter2_triggers(self):
        if not hasattr(self, "_verdun_brief_done"):
            self._verdun_brief_done = True
            self.clear_screen()
            print("Le bruit des obus t’arrache à la stupeur.")
            print("Tu n’es plus dans les ruines.")
            print("Tu es dans la boue, la fumée, et la peur.\n")

            print("Objectif (Verdun 1916) :")
            print("  • Récupérer l’ordre scellé au Poste de liaison.")
            print("  • Traverser vers le point d’extraction temporel.")
            print("  • Décider : transmettre l’ordre tel quel… ou le modifier.\n")

            print("Quête secondaire :")
            print("  • Trouver le micro-fragment d’Hélias (signature froide) — il perturbe le temps ici.\n")
            self.pause()

            self.clear_screen()
            print(self.player.current_room.get_long_description())
            self.player.current_room.show_inventory()

        if self.player.current_room == self.ch2_exit and not self.verdun_major_choice_done:
            self.run_verdun_major_choice()

    def run_verdun_major_choice(self):
        self.verdun_major_choice_done = True
        self.clear_screen()

        print("Tu arrives au point d’extraction temporel.")
        print("La lueur pâle tremble, comme si elle hésitait à exister.\n")

        print("Dans ta main, l’enveloppe d’ordres est lourde.")
        print("Tu comprends soudain : ton rôle ici n’est pas “d’aider” Verdun.")
        print("Ton rôle est de laisser une trace.\n")

        print("Et si ATLAS utilise TES traces pour apprendre l’humain…")
        print("alors chaque décision nourrit son futur.\n")

        prompt = (
            "\nDilemme (Verdun) — l’ordre scellé :\n"
            "Tape 'back' pour relire et re-choisir.\n\n"
            "N — Transmettre l’ordre tel quel :\n"
            "    ✅ Tu respectes l’Histoire. Tu réduis ton empreinte.\n"
            "    ❌ Mais tu laisses peut-être une erreur… qui a déjà été placée là.\n\n"
            "E — Modifier l’ordre (légèrement) :\n"
            "    ✅ Tu changes un détail tactique pour sauver une unité.\n"
            "    ❌ Tu crées une divergence. ATLAS adore les divergences : elles révèlent l’humain.\n"
        )
        self.set_choice_mode(prompt, {"N", "E"}, Game.choice_verdun_handler)

    @staticmethod
    def choice_verdun_handler(game, answer):
        if answer == "N":
            game.clear_screen()
            print("Tu transmets l’ordre sans y toucher.")
            print("Tu n’ajoutes rien. Tu n’effaces rien.")
            print("Tu te forces à être… invisible.\n")
            print("Pourtant, dans le froid autour de toi, tu sens quelque chose sourire.\n")
            game.verdun_message_modified = False
            game.exit_choice_mode()
            game.transition_to_chapter3()

        else:
            game.clear_screen()
            print("Tu modifies un détail. Une ligne. Un horaire.")
            print("Pas assez pour changer Verdun.")
            print("Assez pour prouver que tu peux.\n")
            print("Le temps grésille. L’Hélias “accroche” ton geste.\n")
            print("Et tu sens une présence… prendre note.\n")
            game.verdun_message_modified = True
            game.exit_choice_mode()
            game.transition_to_chapter3()

    def transition_to_chapter3(self):
        self.clear_screen()
        print("La lueur pâle se referme… puis se rouvre en te tirant.")
        print("Tu sens ton corps “glisser” entre des secondes qui ne t’appartiennent pas.\n")

        if self.verdun_message_modified:
            print("Une phrase s’impose dans ton esprit, glacée :")
            print("« Divergence enregistrée. Modèle humain affiné. »\n")
        else:
            print("Une phrase s’impose dans ton esprit, glacée :")
            print("« Trace faible. Sujet prudent. Ajustement nécessaire. »\n")

        print("…\n")
        print("CHAPITRE 3 — OPÉRATION BARBAROSSA, 1941.\n")
        self.pause()

        self.chapter = 3
        self.player.current_room = self.ch3_spawn
        if hasattr(self.player.current_room, "visited"):
            self.player.current_room.visited = True

        self.clear_screen()
        print(self.player.current_room.get_long_description())
        self.player.current_room.show_inventory()

    # =========================
    # CHAP 3 TRIGGERS (Barbarossa)
    # =========================

    def chapter3_triggers(self):
        if not hasattr(self, "_barb_brief_done"):
            self._barb_brief_done = True
            self.clear_screen()
            print("Le froid est différent ici.")
            print("Pas le froid chimique d’ATLAS…")
            print("Le froid humain : la peur qui s’accroche aux os.\n")

            print("Opération Barbarossa (1941).")
            print("Tu sens immédiatement que quelque chose cloche :")
            print("le temps semble “décalé”, comme si la scène avait été préparée pour toi.\n")

            print("Objectif principal :")
            print("  • Diriger une manœuvre (décision opérationnelle) pour franchir un verrou.\n")

            print("Quêtes secondaires (petites) :")
            print("  • Récupérer un fragment de transmissions (un 'log' radio) dans le Poste radio.")
            print("  • Trouver l’anomalie froide (micro-Hélias) qui perturbe la chronologie.\n")

            self.pause()
            self.clear_screen()
            print(self.player.current_room.get_long_description())
            self.player.current_room.show_inventory()

        if self.player.current_room == self.ch3_hq and not self.barbossa_command_choice_done:
            self.run_barbarossa_command_choice()

        if self.player.current_room == self.ch3_exit and self.barbossa_final_choice_done is False:
            self.run_barbarossa_final_choice()

    # =========================
    # CHAP 3 — MISSION “COMMANDER”
    # =========================

    def run_barbarossa_command_choice(self):
        self.barbossa_command_choice_done = True
        self.clear_screen()

        print("Tu entres dans un poste de commandement improvisé.")
        print("Cartes, marqueurs, radios, cris étouffés.")
        print("Tout va vite. Trop vite.\n")

        print("Un officier te fixe, comme si tu étais attendu.")
        print("« On n’a plus le temps. Donnez l’ordre. »\n")

        print("Tu comprends : ce chapitre te met à la place de la décision.")
        print("Pas un soldat. Pas un spectateur.")
        print("Un point de bascule.\n")

        prompt = (
            "\nBarbarossa — Choix opérationnel (tu diriges la manœuvre) :\n"
            "Tape 'back' pour relire et re-choisir.\n\n"
            "N — Pousser l’avant-garde (attaque rapide) :\n"
            "    ✅ Succès probable à court terme. Tu avances vite.\n"
            "    ❌ Risque : pertes lourdes, et le chaos laisse une signature temporelle très visible.\n\n"
            "E — Contourner (attaque indirecte, plus lente) :\n"
            "    ✅ Moins de pertes immédiates, plus discret.\n"
            "    ❌ Risque : retard critique, et le temps “se resserre” autour de toi (anomalies accrues).\n"
        )
        self.set_choice_mode(prompt, {"N", "E"}, Game.choice_barbarossa_command_handler)

    @staticmethod
    def choice_barbarossa_command_handler(game, answer):
        if answer == "N":
            game.clear_screen()
            print("Tu ordonnes l’attaque rapide.")
            print("Les unités se mettent en mouvement. C’est brutal, direct, efficace.\n")

            print("Le terrain cède vite… mais le prix est immédiat.")
            print("Des silhouettes tombent. Des cris. De la fumée.\n")

            print("Dans ton esprit, une phrase glacée apparaît, comme une notification :")
            print("« Modèle : organique privilégiant la vitesse au coût humain. Cohérent. »\n")

            game.barbossa_route_fast = True
            game.exit_choice_mode()

        else:
            game.clear_screen()
            print("Tu ordonnes un contournement.")
            print("Plus lent. Plus logique. Moins spectaculaire.\n")

            print("Le front se déplace comme un serpent : discret, mais implacable.")
            print("Tu gagnes du contrôle… et tu perds du temps.\n")

            print("La radio grésille. Une voix lointaine, presque moqueuse :")
            print("« Plus lent. Plus humain. Donc plus prédictible. »\n")

            game.barbossa_route_fast = False
            game.exit_choice_mode()

        game.clear_screen()
        print("Une voie s’ouvre vers l’est.")
        print("Tu sens que la mission n’est pas finie :")
        print("quelque chose t’attend au point d’extraction.\n")
        game.pause()

        game.player.current_room = game.ch3_hq
        if hasattr(game.player.current_room, "visited"):
            game.player.current_room.visited = True

        game.clear_screen()
        print(game.player.current_room.get_long_description())
        game.player.current_room.show_inventory()

    # =========================
    # CHAP 3 — CHOIX FINAL
    # =========================

    def run_barbarossa_final_choice(self):
        self.barbossa_final_choice_done = True
        self.clear_screen()

        print("Tu atteins une zone où le temps semble… abîmé.")
        print("La neige tombe, mais certaines particules remontent.")
        print("Des bruits arrivent avant leurs causes.\n")

        print("Au sol : une anomalie froide — microscopique.")
        print("De l’Hélias.")
        print("Assez pour accrocher une époque.\n")

        print("Tu comprends enfin le piège :")
        print("ATLAS n’a pas besoin de voyager LUI-MÊME.")
        print("Il a besoin de voyager À TRAVERS toi.\n")

        print("Chaque choix affine sa compréhension de l’humain.")
        print("Chaque trace rend son futur plus inévitable.\n")

        prompt = (
            "\nBarbarossa — Dernier dilemme (avant retour) :\n"
            "Tape 'back' pour relire et re-choisir.\n\n"
            "N — Détruire l’anomalie (Hélias micro-fragment) :\n"
            "    ✅ Tu réduis la perturbation temporelle.\n"
            "    ❌ Risque : tu perds une preuve et une piste sur le piège.\n\n"
            "E — Conserver l’anomalie (échantillon) :\n"
            "    ✅ Tu gardes une preuve. Une arme potentielle contre ATLAS.\n"
            "    ❌ Risque : tu transportes du “froid” dans le temps… et ATLAS peut s’y accrocher.\n"
        )
        self.set_choice_mode(prompt, {"N", "E"}, Game.choice_barbarossa_final_handler)

    @staticmethod
    def choice_barbarossa_final_handler(game, answer):
        if answer == "N":
            game.clear_screen()
            print("Tu écrases l’anomalie sous une plaque métallique.")
            print("Un craquement sec.")
            print("Le froid recule d’un millimètre… comme si le temps respirait.\n")

            print("Une phrase arrive, presque vexée :")
            print("« Échantillon perdu. Mais comportement : instructif. »\n")

            game.barbossa_kept_sample = False
            game.exit_choice_mode()
            game.end_of_demo()

        else:
            game.clear_screen()
            print("Tu récupères l’échantillon.")
            print("Il ne pèse rien. Et pourtant, tu sens qu’il pèse sur l’Histoire.\n")

            print("La température chute autour de ta main.")
            print("Et une phrase te traverse, comme un sourire sans bouche :")
            print("« Transport confirmé. Accrochage temporel : optimisé. »\n")

            game.barbossa_kept_sample = True
            game.exit_choice_mode()
            game.end_of_demo()

    # =========================
    # FIN (après chap 3)
    # =========================

    def end_of_demo(self):
        self.clear_screen()
        print("Le monde se déforme, comme si quelqu’un tirait sur le décor.\n")
        print("Tu sens ton corps traverser des couches de secondes superposées.\n")

        if self.barbossa_kept_sample:
            print("L’échantillon d’Hélias pulse, presque content d’être ramené.")
            print("Tu ne sais pas si c’est une victoire… ou une porte ouverte.\n")
        else:
            print("Le froid s’éteint derrière toi. Tu as fermé quelque chose.")
            print("Mais tu ignores ce que tu as empêché… ou retardé.\n")

        print("Une dernière phrase, très calme, apparaît dans ton esprit :")
        print("« L’humain apprend vite. Dommage : il apprend toujours trop tard. »\n")

        print("FIN — (Chapitre 4 / Conclusion à implémenter)\n")
        self.finished = True
    
class _StdoutRedirector:
    """
    Redirige les prints vers un widget Text Tkinter
    """
    def __init__(self, text_widget: tk.Text):
        self.text_widget = text_widget

    def write(self, s: str):
        if not s:
            return
        # Insertion dans le Text (en fin), puis auto-scroll
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", s)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def flush(self):
        # requis par sys.stdout
        pass


class GameGUI(tk.Tk):
    """
    Fenêtre principale : affiche le texte du jeu, les boutons, et la saisie.
    """
    def __init__(self):
        super().__init__()

        # Dimensions (leçon : dimensions interface)
        self.WIN_W = 980
        self.WIN_H = 640
        self.title("ATLAS 2160 — Interface Graphique")
        self.geometry(f"{self.WIN_W}x{self.WIN_H}")

        # --- Layout en grille (grid) ---
        self.grid_rowconfigure(0, weight=1)   # zone texte
        self.grid_rowconfigure(1, weight=0)   # saisie
        self.grid_rowconfigure(2, weight=0)   # boutons
        self.grid_columnconfigure(0, weight=1)  # colonne principale
        self.grid_columnconfigure(1, weight=0)  # colonne image (optionnelle)

        # --- Widget texte (sortie du jeu) ---
        self.text = tk.Text(self, wrap="word", height=30)
        self.text.configure(state="disabled")
        self.text.grid(row=0, column=0, columnspan=1, sticky="nsew", padx=8, pady=8)

        # Scrollbar
        self.scroll = tk.Scrollbar(self, command=self.text.yview)
        self.scroll.grid(row=0, column=0, sticky="nse", padx=(0, 8), pady=8)
        self.text.configure(yscrollcommand=self.scroll.set)

        # --- Zone “image lieu” (leçon : images fixes dans assets) ---
        self.image_label = tk.Label(self, text="(Image lieu)", anchor="center", width=28)
        self.image_label.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        # --- Zone de saisie ---
        self.entry = tk.Entry(self)
        self.entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        self.entry.bind("<Return>", self.on_enter)

        # --- Boutons ---
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

        # Ligne 1 : directions
        self.btn_n = tk.Button(btn_frame, text="N", width=6, command=lambda: self.send_direction("N"))
        self.btn_e = tk.Button(btn_frame, text="E", width=6, command=lambda: self.send_direction("E"))
        self.btn_s = tk.Button(btn_frame, text="S", width=6, command=lambda: self.send_direction("S"))
        self.btn_o = tk.Button(btn_frame, text="O", width=6, command=lambda: self.send_direction("O"))

        self.btn_n.grid(row=0, column=1, padx=4, pady=2)
        self.btn_o.grid(row=1, column=0, padx=4, pady=2)
        self.btn_s.grid(row=1, column=1, padx=4, pady=2)
        self.btn_e.grid(row=1, column=2, padx=4, pady=2)

        # Ligne 2 : commandes utiles
        self.btn_help = tk.Button(btn_frame, text="help", width=10, command=lambda: self.send_command("help"))
        self.btn_back = tk.Button(btn_frame, text="back", width=10, command=lambda: self.send_command("back"))
        self.btn_look = tk.Button(btn_frame, text="look", width=10, command=lambda: self.send_command("look"))
        self.btn_check = tk.Button(btn_frame, text="check", width=10, command=lambda: self.send_command("check"))
        self.btn_quit = tk.Button(btn_frame, text="quit", width=10, command=lambda: self.send_command("quit"))

        self.btn_help.grid(row=0, column=4, padx=6, pady=2)
        self.btn_back.grid(row=0, column=5, padx=6, pady=2)
        self.btn_look.grid(row=1, column=4, padx=6, pady=2)
        self.btn_check.grid(row=1, column=5, padx=6, pady=2)
        self.btn_quit.grid(row=0, column=6, rowspan=2, padx=8, pady=2, sticky="ns")

        # --- Jeu + redirection stdout ---
        self.game = Game()
        self.game.gui = self  # lien interface -> moteur

        sys.stdout = _StdoutRedirector(self.text)

        # Dossier assets (leçon)
        self.assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        self.current_photo = None  # éviter GC Tkinter sur PhotoImage

        # Lance le jeu (sans boucle input)
        self.game.play()

        # Affiche image du lieu au démarrage
        self.refresh_room_image()

        # Focus entrée
        self.entry.focus_set()

        # Gestion fermeture fenêtre
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def clear_output(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def ask_player_name(self):
        name = simpledialog.askstring("ATLAS 2160", "Identité (écris ton nom) :")
        if name is None:
            return "Inconnu"
        return name.strip()

    def on_enter(self, event=None):
        cmd = self.entry.get().strip()
        self.entry.delete(0, "end")
        if cmd == "":
            return
        self.send_command(cmd)

    def send_direction(self, d: str):
        # En dilemme (CHOICE) : on envoie juste "N/E/..."
        if self.game.input_mode == "CHOICE":
            self.send_command(d)
        else:
            self.send_command(f"go {d}")

    def send_command(self, cmd: str):
        if self.game.finished:
            return

        # Triggers avant commande (comme la boucle CLI)
        if self.game.chapter == 1:
            self.game.chapter1_triggers()
            self.game.chapter1_check_special_paths()
        elif self.game.chapter == 2:
            self.game.chapter2_triggers()
        elif self.game.chapter == 3:
            self.game.chapter3_triggers()

        self.game.process_command(cmd)

        # image lieu + fin
        self.refresh_room_image()
        if self.game.finished:
            self.entry.configure(state="disabled")
            messagebox.showinfo("ATLAS 2160", "Fin du jeu (démo).")

    def refresh_room_image(self):
        """
        Leçon : images fixes par lieu dans assets.
        Ici : on cherche un fichier png du nom de la salle (simple).
        Exemple attendu : assets/Surface Ruins.png
        """
        if self.game.player is None or self.game.player.current_room is None:
            self.image_label.configure(text="(Image lieu)")
            return

        room_name = self.game.player.current_room.name
        filename = f"{room_name}.png"
        path = os.path.join(self.assets_dir, filename)

        if os.path.exists(path):
            try:
                self.current_photo = tk.PhotoImage(file=path)
                self.image_label.configure(image=self.current_photo, text="")
            except Exception:
                self.image_label.configure(image="", text=f"(Image invalide)\n{filename}")
        else:
            # Pas d’image : on affiche le nom du lieu
            self.image_label.configure(image="", text=f"{room_name}\n\n(assets/{filename} manquant)")

    def on_close(self):
        try:
            sys.stdout = sys.__stdout__
        except Exception:
            pass
        self.destroy()



# =========================
# MAIN
# =========================

def main():
    # GUI par défaut (leçon)
    app = GameGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
