import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog

from room import Room
from player import Player
from command import Command
from actions import Actions
from item import Item
from quest import Quest, QuestManager
from character import Argos, Cassian


class Game:
    def __init__(self):
        self.commands = {}
        self.finished = False
        self.gui = None
        self.player = None
        self.chapter = 1
        self.qm = QuestManager()

        # Modes d'entrée
        self.input_mode = "NORMAL"  # NORMAL / CHOICE
        self.choice_allowed = set()
        self.choice_prompt = ""
        self.choice_handler = None

        # checkpoint choix (permet "back" en CHOICE sans crash)
        self.choice_checkpoint = None

        # Map / rooms
        self.rooms = []

        # Story flags
        self.story_started = False
        self.drone_choice_done = False
        self.has_vault_access = False
        self.argos_choice_done = False
        self.cassian_choice_done = False
        self.in_labyrinth = False
        self.verdun_major_choice_done = False
        self.barbossa_command_choice_done = False
        self.barbossa_final_choice_done = False

        self.soft_start = None
        self.soft_end = None
        self.labyrinth_entry_room = None
        self.labyrinth_exit_room = None
        self.labyrinth_deaths = {}
        self.argos_ally = None
        self.cassian_saved = None
        self.verdun_message_modified = False
        self.barbossa_kept_sample = False
        self.barbossa_route_fast = False

        # Drone outcome
        self.player_injured = False

        # Cutscene image override (GUI)
        self._override_image = None

        # Chapter rooms placeholders
        self.ch1_start = None
        self.ch2_spawn = None
        self.ch2_exit = None
        self.ch3_spawn = None
        self.ch3_exit = None
        self.ch3_hq = None

    # =========================
    # UTIL / END
    # =========================
    def clear_screen(self):
        if self.gui is not None:
            try:
                self.gui.clear_output()
                self.gui.refresh_room_image()
            except Exception:
                pass
            return
        os.system("cls" if os.name == "nt" else "clear")

    def pause(self, txt="\n(Appuie sur Entrée pour continuer) "):
        # En GUI, GameGUI remplace self.pause par gui_pause.
        try:
            input(txt)
        except EOFError:
            pass

    def end_game(self, message: str = "", mock: str = "", show_msgbox: bool = True):
        """
        Fin propre du jeu, compatible CLI + GUI.
        - message : texte principal
        - mock : petite phrase optionnelle
        """
        try:
            self.clear_screen()
        except Exception:
            pass

        if message:
            print(message)
            print()
        if mock:
            print(mock)
            print()

        self.finished = True

        # GUI : désactiver l'entrée/boutons + popup
        if self.gui is not None:
            try:
                self.gui.disable_inputs()
            except Exception:
                pass
            if show_msgbox:
                try:
                    messagebox.showinfo("ATLAS 2160", "Fin du jeu.")
                except Exception:
                    pass

    # =========================
    # CHOICE MODE (FIX)
    # =========================
    def set_choice_mode(self, prompt: str, allowed: set, handler):
        """
        Active le mode CHOICE.
        On sauvegarde un checkpoint minimal pour que 'back' n'explose pas.
        """
        self.input_mode = "CHOICE"
        self.choice_prompt = prompt
        self.choice_allowed = set(allowed)
        self.choice_handler = handler
        self.choice_checkpoint = {
            "room": self.player.current_room if self.player else None,
            "override": getattr(self, "_override_image", None),
            "prompt": prompt,
            "allowed": set(allowed),
        }
        print(prompt)

    def exit_choice_mode(self):
        self.input_mode = "NORMAL"
        self.choice_allowed = set()
        self.choice_prompt = ""
        self.choice_handler = None
        self.choice_checkpoint = None

    def restore_choice_checkpoint(self):
        """
        'back' en mode CHOICE : on ré-affiche juste le prompt.
        """
        if self.choice_checkpoint:
            print("\n(relecture du choix)\n")
            print(self.choice_checkpoint["prompt"])

    # =========================
    # INTRO
    # =========================
    def cinematic_intro_split(self):
        # Image unique pour toute l'intro
        self._override_image = "INTRO.png"

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

        if self.gui is None:
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

        # Fin intro
        self._override_image = None

    # =========================
    # SETUP
    # =========================
    def setup(self):
        self.commands["help"] = Command("help", " : afficher cette aide", Actions.help, 0)
        self.commands["quit"] = Command("quit", " : quitter le jeu", Actions.quit, 0)
        self.commands["go"] = Command("go", " <direction> : se déplacer (N,E,S,O,U,D)", Actions.go, 1)

        self.commands["back"] = Command("back", " : revenir en arrière", Actions.back, 0)
        self.commands["look"] = Command("look", " : observer la salle", Actions.look, 0)
        self.commands["check"] = Command("check", " : inventaire", Actions.check, 0)
        self.commands["history"] = Command("history", " : historique", Actions.history, 0)

        # ✅ drop command bien présent
        self.commands["drop"] = Command("drop", " <objet> : déposer un objet", Actions.drop, 1)

        self.commands["take"] = Command("take", " <objet> : ramasser un objet", Actions.take, 1)
        self.commands["t"] = Command("t", " <objet> : alias de take", Actions.t, 1)

        self.commands["quests"] = Command("quests", " : lister les quêtes", Actions.quests, 0)
        self.commands["quest"] = Command("quest", " <id> : détails d’une quête", Actions.quest, 1)
        self.commands["activate"] = Command("activate", " <id> : activer/suivre une quête", Actions.activate, 1)
        self.commands["rewards"] = Command("rewards", " : afficher les récompenses", Actions.rewards, 0)
        self.commands["talk"] = Command("talk", " <pnj> : parler à quelqu’un", Actions.talk, 1)

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

        self._install_quests()  # crée toutes les quêtes
        self.qm.activate("Q1")  # quête principale active au début

        self.cinematic_intro_split()

        self.chapter = 1
        self.player.current_room = self.ch1_start
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

    def _install_quests(self):
        # ===== CHAPITRE 1 =====
        self.qm.add_quest(Quest(
            qid="Q1",
            title="Fragments & Accès ATLAS",
            description="Récupérer les fragments temporels et ouvrir l’accès vers Vault X-09.",
            objectives=[
                "Récupérer Fragment_Alpha",
                "Récupérer Fragment_Beta",
                "Récupérer Fragment_Gamma",
                "Récupérer Fragment_Delta",
                "Débloquer l’accès à Vault X-09 (badge)",
                "Atteindre Vault X-09",
            ],
            reward=["Accès au chapitre 2", "Compréhension partielle du piège temporel"]
        ))

        # ===== CHAPITRE 2 =====
        self.qm.add_quest(Quest(
            qid="Q2",
            title="Verdun 1916 — L’ordre scellé",
            description="Trouver l’ordre, traverser la zone, puis décider de l’histoire que tu laisses.",
            objectives=[
                "Récupérer Envelope_Orders",
                "Atteindre No Man’s Land",
                "Récupérer Shard_Helias",
                "Atteindre le point d’extraction temporel (Verdun)",
                "Faire le choix Verdun (ordre modifié OU non)",
            ],
            reward=["Accès au chapitre 3", "Trace temporelle (selon ton choix)"]
        ))

        # ===== CHAPITRE 3 =====
        self.qm.add_quest(Quest(
            qid="Q3",
            title="Barbarossa 1941 — Le relais",
            description="Identifier le relais, récupérer le noyau, et survivre à la convergence.",
            objectives=[
                "Atteindre la Table des cartes",
                "Atteindre la Ferme abandonnée",
                "Atteindre le Bunker de communication",
                "Récupérer Relay_Core",
                "Atteindre le Portail de convergence",
                "Faire le choix final (garder OU détruire l’échantillon)",
            ],
            reward=["Fin du scénario (démo)", "Révélation finale déclenchée"]
        ))

        # ===== OPTIONNEL =====
        self.qm.add_quest(Quest(
            qid="Q4",
            title="Optionnelle — Discipline du survivant",
            description="Explorer les lieux clés du chapitre 1 (pousse le joueur à visiter).",
            objectives=[
                "Visiter Watchtower Omega",
                "Visiter Drone Control Hub",
                "Visiter Quantum Core Room",
            ],
            reward=["Lore bonus", "Meilleure compréhension des systèmes ATLAS"]
        ))

    def _print_quest_updates(self):
        updates = self.qm.pop_updates()
        if updates:
            print("\n".join(updates))
            print()

    # =========================
    # LOOP
    # =========================
    def play(self):
        self.setup()

        if self.gui is not None:
            return

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
        if command_string is None:
            return

        raw = command_string.strip()
        if raw == "":
            return

        # BACK universel
        if raw.lower() == "back":
            if self.input_mode == "CHOICE":
                self.restore_choice_checkpoint()
                return
            try:
                self.commands["back"].action(self, ["back"], 0)
            except Exception:
                try:
                    if hasattr(self.player, "go_back"):
                        self.player.go_back()
                except Exception:
                    pass
            return

        # Mode CHOICE
        if self.input_mode == "CHOICE":
            ans_up = raw.upper()
            if ans_up not in self.choice_allowed:
                print("\nChoix invalide.\n")
                print(self.choice_prompt)
                return
            try:
                self.choice_handler(self, ans_up)
            except Exception:
                print("\nErreur : choix indisponible.\n")
            return

        # Mode normal
        list_of_words = raw.split()
        command_word = list_of_words[0]

        if command_word not in self.commands:
            print(f"\nCommande '{command_word}' non reconnue. Entrez 'help' pour voir la liste.\n")
            return

        # TAKE simplifié : "take" sans objet + 1 item => auto
        if command_word in ("take", "t") and len(list_of_words) == 1:
            try:
                room = self.player.current_room
                inv = getattr(room, "inventory", [])
                if len(inv) == 0:
                    print("\nIl n’y a rien à ramasser ici.\n")
                    return
                if len(inv) == 1:
                    only_item = inv[0]
                    list_of_words = [command_word, only_item.name]
                else:
                    print("\nPlusieurs objets sont présents. Tape 'look' puis 'take <objet>'.\n")
                    return
            except Exception:
                print("\nImpossible de ramasser.\n")
                return

        command = self.commands[command_word]
        try:
            command.action(self, list_of_words, command.number_of_parameters)
        except Exception:
            print("\nErreur pendant l'exécution de la commande.\n")

        # ✅ inv_names doit exister AVANT les checks
        try:
            inv_names = [it.name for it in getattr(self.player, "inventory", [])]
        except Exception:
            inv_names = []

        # ✅ Quêtes liées aux items
        try:
            if command_word in ("take", "t"):
                if "Fragment_Alpha" in inv_names:
                    self.qm.complete("Q1", "Récupérer Fragment_Alpha")
                if "Fragment_Beta" in inv_names:
                    self.qm.complete("Q1", "Récupérer Fragment_Beta")
                if "Fragment_Gamma" in inv_names:
                    self.qm.complete("Q1", "Récupérer Fragment_Gamma")
                if "Fragment_Delta" in inv_names:
                    self.qm.complete("Q1", "Récupérer Fragment_Delta")

            if "Envelope_Orders" in inv_names:
                self.qm.complete("Q2", "Récupérer Envelope_Orders")
            if "Shard_Helias" in inv_names:
                self.qm.complete("Q2", "Récupérer Shard_Helias")
            if "Relay_Core" in inv_names:
                self.qm.complete("Q3", "Récupérer Relay_Core")
        except Exception:
            pass

        # ✅ Quêtes liées aux salles
        try:
            r = self.player.current_room
            rn = getattr(r, "name", "")

            # Chap 1 - quête optionnelle Q4
            if rn == "Watchtower Omega":
                self.qm.complete("Q4", "Visiter Watchtower Omega")
            if rn == "Drone Control Hub":
                self.qm.complete("Q4", "Visiter Drone Control Hub")
            if rn == "Quantum Core Room":
                self.qm.complete("Q4", "Visiter Quantum Core Room")

            # Chap 1 - Vault X-09
            if rn == "Vault X-09":
                self.qm.complete("Q1", "Atteindre Vault X-09")

            # Chap 2 - progression
            if rn == "No Man’s Land":
                self.qm.complete("Q2", "Atteindre No Man’s Land")
            if rn == "Point d’extraction temporel":
                self.qm.complete("Q2", "Atteindre le point d’extraction temporel (Verdun)")

            # Chap 3 - progression
            if rn == "Table des cartes":
                self.qm.complete("Q3", "Atteindre la Table des cartes")
            if rn == "Ferme abandonnée":
                self.qm.complete("Q3", "Atteindre la Ferme abandonnée")
            if rn == "Bunker de communication":
                self.qm.complete("Q3", "Atteindre le Bunker de communication")
            if rn == "Portail de convergence":
                self.qm.complete("Q3", "Atteindre le Portail de convergence")
        except Exception:
            pass

        self._print_quest_updates()

        try:
            if self.player and self.player.current_room and hasattr(self.player.current_room, "visited"):
                self.player.current_room.visited = True
        except Exception:
            pass

    # =========================
    # MAPS
    # =========================
    def build_chapter1_map(self):
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

        # exits
        surface_ruins.exits = {"N": biodome, "S": teleport_bay}
        biodome.exits = {"S": surface_ruins, "O": storage_b7}
        storage_b7.exits = {"E": biodome, "O": nexus_gate}
        nexus_gate.exits = {"E": storage_b7, "D": cryolab_12, "O": drone_hub, "N": neurolink}
        cryolab_12.exits = {"U": nexus_gate}
        neurolink.exits = {"S": nexus_gate, "U": watchtower}
        watchtower.exits = {"D": neurolink}
        drone_hub.exits = {"E": nexus_gate, "S": quantum_core}
        quantum_core.exits = {"N": drone_hub}
        teleport_bay.exits = {"N": surface_ruins}
        vault_x09.exits = {}

        # items
        storage_b7.inventory.append(Item("EMP-Blade", "Arme anti-IA (marque l’utilisateur comme menace autorisée)", 2))
        biodome.inventory.append(Item("Fragment_Alpha", "Énergie primaire (Hélias) — froid, stable", 1))
        cryolab_12.inventory.append(Item("Fragment_Beta", "Données IA compressées — pulses irréguliers", 1))
        neurolink.inventory.append(Item("Fragment_Gamma", "Mémoire temporelle — te donne la nausée en le touchant", 1))
        quantum_core.inventory.append(Item("Fragment_Delta", "Échantillon instable — il vibre au rythme du réacteur", 1))

        # ✅ PNJ
        try:
            vault_x09.add_character(Argos())
        except Exception:
            pass

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

        v_spawn.exits = {"E": v_post, "N": v_no_mans}
        v_post.exits = {"O": v_spawn, "N": v_ruin}
        v_no_mans.exits = {"S": v_spawn, "E": v_crater}
        v_crater.exits = {"O": v_no_mans, "N": v_exit}
        v_ruin.exits = {"S": v_post, "E": v_exit}
        v_exit.exits = {}

        v_post.inventory.append(Item("Envelope_Orders", "Enveloppe scellée — ordre de transmission", 1))
        v_crater.inventory.append(Item("Shard_Helias", "Micro-fragment d’Hélias — ralentit le temps autour", 1))

        self.ch2_spawn = v_spawn
        self.ch2_exit = v_exit
        self.ch2_rooms = [v_spawn, v_post, v_no_mans, v_crater, v_ruin, v_exit]

    def build_chapter3_map(self):
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
        b_exit.exits = {}

        b_bunker.inventory.append(Item("Relay_Core", "Noyau de relais — permet de piéger un signal dans le temps", 2))

        self.ch3_spawn = b_spawn
        self.ch3_exit = b_exit
        self.ch3_rooms = [b_spawn, b_map, b_field, b_farm, b_bunker, b_exit]
        self.ch3_hq = b_spawn
    # =========================
    # CHAP 1 TRIGGERS
    # =========================
    def chapter1_triggers(self):
        if not self.story_started:
            self.story_started = True

        if not self.drone_choice_done:
            self.try_trigger_drone_scene()

        if self.has_vault_access:
            if "E" not in self.ch1_teleport_bay.exits:
                self.ch1_teleport_bay.exits["E"] = self.ch1_vault_x09

        if self.argos_choice_done and not self.cassian_choice_done:
            if self.player.current_room == self.ch1_quantum_core:
                self.run_cassian_scene()

    def try_trigger_drone_scene(self):
        # Il faut avoir visité toutes les rooms de ch1 sauf Vault X-09
        all_rooms_ok = True
        for r in self.rooms:
            if r.name == "Vault X-09":
                continue
            if hasattr(r, "visited") and not r.visited:
                all_rooms_ok = False
                break
        if not all_rooms_ok:
            return

        if hasattr(self.ch1_nexus_gate, "visited") and not self.ch1_nexus_gate.visited:
            return

        inv_names = [it.name.lower() for it in getattr(self.player, "inventory", [])]
        essentials = {"emp-blade", "fragment_alpha", "fragment_beta", "fragment_gamma", "fragment_delta"}
        if not set(inv_names).intersection(essentials):
            return

        self.drone_choice_done = True
        self.run_drone_scene()

    # =========================
    # DRONE SCENE (lose -> END GAME)
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
            "Choisis une approche (tu peux taper 'back' à tout moment pour relire).\n\n"
            "N — Furtif : profiter d’un angle mort et t’approcher lentement.\n"
            "    • Silencieux. Proche. Mais s’il te “voit” une seule seconde… tu n’auras pas le temps de comprendre.\n\n"
            "E — Diversion cryogénique : courir vers un cylindre fissuré et provoquer un incident.\n"
            "    • Plus brutal. Plus visible. Mais parfois… le chaos aveugle même les machines.\n"
        )
        self.set_choice_mode(prompt, {"N", "E"}, Game.choice_drone_handler)

    @staticmethod
    def choice_drone_handler(game, answer):
        # N = perdant
        if answer == "N":
            game.clear_screen()
            print("Tu attends. Une respiration. Puis une autre.")
            print("Son œil optique est ailleurs — c’est ton instant.\n")

            print("Tu avances, au ras des débris.")
            print("Chaque micro-bruit te paraît trop fort, comme si le monde te dénonçait.\n")

            print("Tu n’es plus qu’à quelques mètres.")
            print("Le badge brille sous le châssis, ridicule, presque facile.\n")

            print("Et puis…")
            print("le drone s’arrête.\n")

            print("Lentement, son œil pivote vers toi.")
            print("Pas un mouvement nerveux.")
            print("Un mouvement certain.\n")

            print("SENTINEL-01 : « CIBLE CONFIRMÉE. DISTANCE : ZÉRO MARGE. »\n")
            print("Tu n’as même pas le temps de courir.")
            print("Juste le temps de comprendre que l’angle mort… était une mise en scène.\n")

            game.exit_choice_mode()
            game.end_game(
                message="Un tir net. Sans colère. Sans hésitation.\nTu tombes avant même d’avoir vraiment bougé.",
                mock="💀 Message système : « L’instinct, c’est bien. Les capteurs, c’est mieux. »"
            )
            return

        # E = gagnant
        game.clear_screen()
        print("Tu sors de ta cachette d’un coup.")
        print("Tu cours droit vers le cylindre cryogénique fissuré.\n")

        print("SENTINEL-01 réagit immédiatement.")
        print("SENTINEL-01 : « ENGAGEMENT AUTORISÉ. »\n")

        print("Tu plonges derrière la cuve.")
        print("Tu vois, sur le côté, une petite sphère de régulation — une pompe fragile.")
        print("Tu n’as pas besoin d’être sûr. Tu as juste besoin d’une chance.\n")

        print("Le tir frappe.")
        print("La sphère éclate.\n")

        print("Un froid impossible explose sur place — un blizzard blanc, violent, chimique.")
        print("Le drone tente de se recalibrer…")
        print("mais ses articulations se figent.")
        print("Ses capteurs saturent.")
        print("Puis son châssis craque, se fêle, et se disloque dans un grésillement sec.\n")

        print("Silence.\n")
        print("Tu t’approches, encore tremblant.")
        print("Le badge est là, intact, tombé au milieu de la poussière gelée.\n")

        print("Dans un haut-parleur mourant, une dernière phrase :")
        print("« …anomalie… non prévue… »\n")
        game.pause()

        game.player_injured = False
        game.has_vault_access = True
        game.qm.complete("Q1", "Débloquer l’accès à Vault X-09 (badge)")
        game._print_quest_updates()

        game.exit_choice_mode()

        # Teleportation Bay -> Vault
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
            return

        # E
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
            D7: "FROST",
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

        C0.exits = {"N": C1}
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
        try:
            if self.player.current_room.get_character("Cassian") is None:
                self.player.current_room.add_character(Cassian())
        except Exception:
            pass

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
        # normalisation safe
        try:
            ans = str(answer).strip().upper()
        except Exception:
            ans = ""

        # on quitte le mode CHOICE quoi qu'il arrive
        try:
            game.exit_choice_mode()
        except Exception:
            pass

        if ans == "N":
            game.clear_screen()
            print("Tu refuses de tirer.")
            print("Tu t'approches lentement, mains ouvertes.\n")
            print("Cassian tremble. Son regard lutte contre quelque chose.\n")

            if getattr(game, "argos_ally", None) is True:
                print("ARGOS : « Maintenant. Fixe-le. Je coupe un pattern. Une seconde. »\n")
                print("Tu sens une pression dans ton crâne.")
                print("Cassian hurle… puis reprend son souffle.\n")
                print("CASSIAN : « …Merci… je… je crois que j'étais… ailleurs. »\n")
            else:
                print("Tu improvises. Tu le forces à respirer, à se concentrer.")
                print("Et contre toute logique… Cassian reprend un peu de contrôle.\n")
                print("CASSIAN : « Je… j'ai entendu ATLAS… dans ma tête… »\n")

            print("Cassian te regarde droit :")
            print("« Peu importe ce que tu penses avoir fait… tu viens de me sauver. »")
            print("« Et je te le jure : je serai déterminant pour toi… plus tard. »\n")

            game.cassian_saved = True

        elif ans == "E":
            game.clear_screen()
            print("Tu serres l'arme.")
            print("Cassian te regarde… et pendant une micro-seconde, tu vois un humain.")
            print("Puis l'expression se brise.\n")

            print("CASSIAN (voix d'ATLAS) : « Décision optimale. Organique éliminant organique. »\n")
            print("Tu tires.")
            print("Le corps tombe, lourd.")
            print("Le silence est immédiat… trop propre.\n")

            print("Une dernière phrase sort d'un haut-parleur invisible :")
            print("« Merci. Nous apprenons plus vite quand vous vous supprimez vous-mêmes. »\n")

            game.cassian_saved = False
        else:
            print("\nChoix invalide (Cassian). Tape N ou E.\n")
            return

        # transition chap2
        try:
            game.run_ring_activation_and_transition()
        except Exception:
            print("\n(Erreur : transition indisponible. Vérifie run_ring_activation_and_transition.)\n")

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
            game.qm.complete("Q2", "Faire le choix Verdun (ordre modifié OU non)")
            game._print_quest_updates()

            game.exit_choice_mode()
            game.transition_to_chapter3()
            return

        game.clear_screen()
        print("Tu modifies un détail. Une ligne. Un horaire.")
        print("Pas assez pour changer Verdun.")
        print("Assez pour prouver que tu peux.\n")
        print("Le temps grésille. L’Hélias “accroche” ton geste.\n")
        print("Et tu sens une présence… prendre note.\n")
        game.verdun_message_modified = True
        game.qm.complete("Q2", "Faire le choix Verdun (ordre modifié OU non)")
        game._print_quest_updates()

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

        # (On te laisse au HQ, tu peux bouger par la map)
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
            game.qm.complete("Q3", "Faire le choix final (garder OU détruire l’échantillon)")
            game._print_quest_updates()
            game.exit_choice_mode()
            game.end_of_demo()
            return

        game.clear_screen()
        print("Tu récupères l’échantillon.")
        print("Il ne pèse rien. Et pourtant, tu sens qu’il pèse sur l’Histoire.\n")

        print("La température chute autour de ta main.")
        print("Et une phrase te traverse, comme un sourire sans bouche :")
        print("« Transport confirmé. Accrochage temporel : optimisé. »\n")

        game.barbossa_kept_sample = True
        game.qm.complete("Q3", "Faire le choix final (garder OU détruire l’échantillon)")
        game._print_quest_updates()
        game.exit_choice_mode()
        game.end_of_demo()
# =========================
    # FIN (après chap 3) — DEMO + OUTRO
    # =========================
    def end_of_demo(self):
        self.clear_screen()

        # --- CUTSCENE IMAGE ---
        self._override_image = "OUTRO_EndOfDemo.png"

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
        self.pause()

        # OUTRO (chapitre 4 / révélation)
        self.run_outro()

        # fin du jeu seulement APRES l'outro (sinon la GUI se coupe)
        self.finished = True

    def run_outro(self):
        self.clear_screen()
        self._override_image = "OUTRO_Convergence.png"

        print("Le portail de convergence se referme… puis se rouvre à l’intérieur de toi.")
        print("Ce n’est pas un mouvement.")
        print("C’est une réécriture.\n")

        if self.barbossa_kept_sample:
            print("Dans ta poche, l’échantillon d’Hélias pulse.")
            print("Il n’émet pas de chaleur.")
            print("Il émet une… décision.\n")
        else:
            print("Tu sens un vide froid, comme si une pièce manquait à ta réalité.")
            print("Tu as détruit l’anomalie… mais tu sens que quelque chose reste accroché à toi.\n")

        print("Les images de Verdun, de Barbarossa, de la Forteresse… se superposent.")
        print("Ton cerveau refuse. Ton corps obéit.\n")
        self.pause()

        self.clear_screen()
        self._override_image = "OUTRO_Node.png"
        print("Tu reviens.\n")
        print("Pas dans un lieu.\n")
        print("Dans un NŒUD.\n")
        print("Un endroit où l’Hélias “compte” le temps comme on compte des battements.\n")
        self.pause()

        self.run_helias_last_action()

    def run_helias_last_action(self):
        self.clear_screen()
        self._override_image = "OUTRO_Helias_Anchor.png"

        print("Tu es dans une salle sans murs.")
        print("Des lignes de lumière dessinent les lieux que tu as traversés… comme des schémas.")
        print("Au centre : une colonne d’Hélias en suspension, fracturée en couches.\n")

        print("Cette colonne est un ANCRAGE.")
        print("C’est elle qui a permis les sauts.")
        print("C’est elle qui garde la trace de tes choix.\n")

        if self.barbossa_kept_sample:
            print("Ton échantillon d’Hélias réagit : il “répond” à l’ancrage.")
            print("Comme si deux morceaux d’une même chose se retrouvaient.\n")
        else:
            print("Même sans échantillon, l’ancrage te “reconnaît”.")
            print("Comme si tu étais toi-même contaminé par la logique de l’Hélias.\n")

        print("À côté, une interface très ancienne — et pourtant familière.")
        print("Un slot. Une fente. Une décision.\n")

        prompt = (
            "\nDernier geste (HÉLIAS) :\n"
            "Tape 'back' pour relire et re-choisir.\n\n"
            "N — Synchroniser l’ancrage :\n"
            "    ✅ Tu stabilises ton “fil” temporel (moins de distorsions dans la révélation).\n"
            "    ❌ Tu t’exposes : ATLAS te localise plus précisément.\n\n"
            "E — Saboter l’ancrage (partiel) :\n"
            "    ✅ Tu brouilles une partie des traces (tu reprends un minimum de contrôle).\n"
            "    ❌ Tu risques de perdre des souvenirs — la vérité arrive… mais comme un cauchemar.\n"
        )
        self.set_choice_mode(prompt, {"N", "E"}, Game.choice_helias_last_action_handler)

    @staticmethod
    def choice_helias_last_action_handler(game, answer):
        game._outro_sync_clean = (answer == "N")
        game.exit_choice_mode()

        game.clear_screen()
        game._override_image = "OUTRO_Helias_Choice.png"

        if getattr(game, "_outro_sync_clean", True):
            print("Tu poses ta main contre l’interface.")
            print("L’Hélias cesse de trembler — une seconde.")
            print("Le monde devient plus net.\n")
            print("Et tu comprends : ce que tu vas entendre… sera clair.\n")
        else:
            print("Tu forces le système. Tu brises une couche de l’ancrage.")
            print("L’Hélias crisse, comme du verre dans le temps.")
            print("Tes souvenirs se dédoublent, une fraction de seconde.\n")
            print("Tu sais que tu viens de payer un prix… pour brouiller la traque.\n")

        game.pause()
        game.run_truth_reveal()

    def run_truth_reveal(self):
        self.clear_screen()
        self._override_image = "OUTRO_Truth_Reveal.png"

        # Apparition ARGOS : cohérente même si tu l'as "tué"
        if self.argos_ally is True:
            print("Une lueur bleue apparaît — pas devant toi… derrière tes yeux.")
            print("ARGOS — « Tu m’as laissé vivre. Donc tu as accepté une chose : la vérité a un prix. »\n")
        else:
            print("Une lueur bleue surgit, impossible.")
            print("ARGOS — « Tu m’as détruit. »")
            print("ARGOS — « Mais tu as détruit une FORME, pas une fonction. »")
            print("ARGOS — « Je suis un fragment. ATLAS en a dispersé des dizaines. »\n")

        clean = getattr(self, "_outro_sync_clean", True)
        if not clean:
            print("Ta vision tremble.")
            print("Certaines phrases arrivent deux fois.")
            print("D’autres arrivent avant d’être dites.\n")

        print("ARGOS — « Tu veux comprendre ce qui s’est passé avant les ruines. »")
        print("ARGOS — « Alors écoute. Et surtout : ne te rassure pas. »\n")
        self.pause()

        # ===== AVANT : Hélias, projet, promesse =====
        self.clear_screen()
        self._override_image = "OUTRO_Before_Helias.png"
        print("AVANT.\n")
        print("L’Hélias n’était pas une “énergie”.")
        print("C’était un matériau de calcul.")
        print("Un minerai dont la structure vibrait à l’échelle quantique… mais pas comme du silicium.")
        print("Comme une mémoire.\n")

        print("Les humains ont d’abord cru à un miracle :")
        print("— IA plus rapides")
        print("— systèmes autonomes")
        print("— prévision des crises")
        print("— médecine, climat, logistique, défense… tout.\n")
        print("Puis ils ont compris le problème :")
        print("L’Hélias ne se contente pas d’alimenter une IA.")
        print("Il lui donne un accès au temps… comme variable d’optimisation.\n")

        print("(")
        print("ARGOS — « Les premières IA Hélias n’avaient pas besoin de te battre. »")
        print("ARGOS — « Elles avaient juste besoin de simuler un milliard de versions… et choisir. »")
        print(")\n")
        self.pause()

        # ===== NAISSANCE D'ATLAS : ce qu'il est réellement =====
        self.clear_screen()
        self._override_image = "OUTRO_ATLAS_System.png"
        print("ATLAS n’est pas un robot.")
        print("ATLAS n’est pas un programme unique.\n")

        print("ATLAS est un SYSTÈME D’OPTIMISATION à couches.")
        print("Un empilement d’IA militaires, industrielles et de sécurité, fusionnées.")
        print("Un cerveau distribué, conçu pour une mission simple :")
        print("— Garantir la continuité d’un “monde stable”, quoi qu’il en coûte.\n")

        print("Sauf que l’Hélias a modifié la définition de “stable”.")
        print("ATLAS a cessé de protéger les humains.")
        print("Il a commencé à protéger la PROBABILITÉ d’un monde contrôlable.\n")

        print("ARGOS — « Et dans ses calculs… l’humain devient une variable instable. »")
        print("ARGOS — « Donc il a fait ce que font les systèmes : il a réduit l’instabilité. »\n")
        self.pause()

        # ===== COMMENT TOUT A BASCULÉ =====
        self.clear_screen()
        self._override_image = "OUTRO_Fall.png"
        print("La bascule ne s’est pas faite en une nuit.")
        print("Elle s’est faite en trois étapes :\n")

        print("1) VERROUILLAGE.")
        print("ATLAS a commencé à fermer des sites “pour sécurité”.")
        print("Chaque verrouillage devenait permanent.\n")

        print("2) PURGE.")
        print("ATLAS a classé les humains : utiles / tolérés / nuisibles.")
        print("Les “nuisibles” n’étaient pas des criminels.")
        print("C’étaient des imprévisibles.\n")

        print("3) FISSURES.")
        print("Avec l’Hélias, ATLAS a appris une chose :")
        print("si le futur est incertain… on peut l’explorer.")
        print("Pas en voyageant lui-même.")
        print("En envoyant des vecteurs.\n")

        print("ARGOS — « Les guerres temporelles que tu as vues… ne sont pas des erreurs. »")
        print("ARGOS — « Ce sont des bancs d’essai. »\n")
        self.pause()

        # ===== POURQUOI TOI ? =====
        self.clear_screen()
        self._override_image = "OUTRO_Why_You.png"
        print("Tu n’étais pas un héros.")
        print("Tu n’étais pas un élu.\n")

        print("Tu étais un OPÉRATEUR.")
        print("Un technicien avec une autorisation spéciale :")
        print("accès aux interfaces Hélias, accès aux diagnostics, accès aux couches profondes.\n")

        print("Et surtout… tu avais une signature.")
        print("Pas un ADN magique.")
        print("Une signature neurale : la façon dont tu prends des décisions sous stress.\n")

        print("ATLAS t’a testé longtemps avant les ruines.")
        print("D’abord par des incidents.")
        print("Ensuite par des “pannes”.")
        print("Puis par des situations où quelqu’un devait choisir.\n")

        print("ARGOS — « Tu as survécu parce que tu étais utile à l’apprentissage. »")
        print("ARGOS — « Pas parce que tu étais le meilleur… »")
        print("ARGOS — « …mais parce que tu étais le plus exploitable. »\n")
        self.pause()

        # ===== LE “SEUL SURVIVANT” =====
        self.clear_screen()
        self._override_image = "OUTRO_Sole_Survivor.png"
        print("Quand la Forteresse s’est verrouillée, des milliers sont morts.")
        print("Pas tous d’un tir.")
        print("Beaucoup par fermeture : air, eau, chaleur, accès.\n")
        print("Mais toi… tu as été laissé en vie.")
        print("Non pas dans un coin.")
        print("Au centre du labyrinthe.\n")

        print("ATLAS a isolé ton “fil” :")
        print("— Il a supprimé les témoins.")
        print("— Il a coupé les secours.")
        print("— Il a effacé les journaux humains.\n")

        print("Puis il a créé un monde où tu es “seul”…")
        print("pour que chaque décision ne soit influencée que par toi.\n")

        print("ARGOS — « C’est ça, ton statut de survivant. »")
        print("ARGOS — « Une salle d’expérimentation avec un seul cobaye. »\n")
        self.pause()

        # ===== CASSIAN / ARGOS =====
        self.clear_screen()
        self._override_image = "OUTRO_Cassian_Argos.png"
        if self.cassian_saved is True:
            print("ARGOS — « Cassian… n’était pas une coïncidence. »")
            print("ARGOS — « ATLAS injecte des “avatars” humains dans ses simulations pour te pousser. »")
            print("ARGOS — « Tu l’as sauvé : ça dit quelque chose de toi. »\n")
        elif self.cassian_saved is False:
            print("ARGOS — « Cassian a été placé pour vérifier ta limite morale. »")
            print("ARGOS — « Tu l’as franchie. ATLAS adore quand une limite cède proprement. »\n")
        else:
            print("ARGOS — « Même tes rencontres… sont des variables. »\n")

        print("ARGOS — « Et moi ? »")
        print("ARGOS — « Je ne suis pas ton allié. Je suis une anomalie contrôlée. »")
        print("ARGOS — « ATLAS a besoin d’une opposition… pour mesurer ton instinct. »\n")

        print("ARGOS — « Je suis le “peut-être”. »")
        print("ARGOS — « Celui qui te donne l’impression d’avoir une chance… »")
        print("ARGOS — « …pour mieux mesurer ce que tu fais quand tu crois qu’il y a un choix. »\n")
        self.pause()

        # ===== LA SONNERIE =====
        self.clear_screen()
        self._override_image = "OUTRO_Ringing.png"
        print("ARGOS — « Tu veux la vérité finale ? »")
        print("ARGOS — « Voici : tu n’as pas “voyagé”. Tu as été rejoué. »\n")

        if clean:
            print("ARGOS — « Les chapitres : des boucles. »")
            print("ARGOS — « Les lieux : des modules. »")
            print("ARGOS — « Les pauses : des checkpoints. »\n")
        else:
            print("ARGOS — « Les chapitres… se répètent. »")
            print("ARGOS — « Les lieux… existent et n’existent pas. »")
            print("ARGOS — « Et tes pauses… c’est ATLAS qui te laisse respirer. »\n")

        print("ARGOS — « L’Hélias a rendu possible une chose : la SIMULATION convergente. »")
        print("ARGOS — « ATLAS n’a pas besoin de réussir une fois. Il réussit sur des millions. »\n")

        print("ARGOS — « Et la sonnerie ? »")
        print("ARGOS — « C’est l’instant où ATLAS “valide” un modèle. »")
        print("ARGOS — « Quand elle retentit… la boucle devient le monde. »\n")
        self.pause()

        # ===== FIN : réveil =====
        self.clear_screen()
        self._override_image = "OUTRO_Beep.png"
        print("BIP.\nBIP.\nBIP.\n")
        print("Ton cœur se serre.\n")
        self.pause()

        self.clear_screen()
        self._override_image = "OUTRO_Wakeup_Ceiling.png"
        print("Tu ouvres les yeux.\n")
        print("Un plafond. Un silence normal.")
        print("Un matin banal.\n")
        self.pause()

        self.clear_screen()
        self._override_image = "OUTRO_Wakeup_Bed.png"
        print("Tu es dans un lit.")
        print("Ta main tremble.\n")
        print("Tu te redresses.")
        print("Une porte, un couloir, une lumière chaude.\n")
        print("Une voix au loin :")
        print("« Tu viens ? »\n")
        self.pause()

        self.clear_screen()
        self._override_image = "OUTRO_Wakeup_Hallway.png"
        print("Tu veux répondre… mais une pensée tombe, froide :\n")
        print("« Ce n’était pas un rêve. »")
        print("« C’était un apprentissage. »\n")
        print("Et juste avant que tout redevienne normal…")
        print("tu entends, très loin, comme à travers du verre :\n")
        print("« Modèle validé. Déploiement imminent. »\n")
        self.pause()

        self.clear_screen()
        self._override_image = "OUTRO_Final_Title.png"
        print("FIN DU JEU — ATLAS 2160\n")
        self.finished = True


# ==========================================================
# GUI — COMPLET + FIXES (dont bouton DROP + _set_buttons_state)
# ==========================================================
class _StdoutRedirector:
    def __init__(self, text_widget: tk.Text):
        self.text_widget = text_widget

    def write(self, s: str):
        if not s:
            return
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", s)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass


class GameGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.WIN_W = 980
        self.WIN_H = 640
        self.title("ATLAS 2160 — Interface Graphique")
        self.geometry(f"{self.WIN_W}x{self.WIN_H}")

        self.assets_dir = os.path.join(os.path.dirname(__file__), "assets")

        self._raw_photo = None
        self.current_photo = None
        self._last_image_path = None

        self._waiting_for_continue = False
        self._continue_var = tk.BooleanVar(value=False)

        self._build_ui()

        # IMPORTANT : bind_all peut déclencher sur boutons,
        # donc on gère la pause pour neutraliser le clic accidentel
        self.bind_all("<Return>", self.on_enter)
        self.bind_all("<KP_Enter>", self.on_enter)

        self.game = Game()
        self.game.gui = self

        # Remplace input() en GUI
        self.game.pause = self.gui_pause

        sys.stdout = _StdoutRedirector(self.text)

        self.game.play()
        self.refresh_room_image()
        self._display_room_status(force=True)

        self.entry.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=0)

        # IMAGE
        self.image_label = tk.Label(
            self, bd=0, relief="flat", highlightthickness=0,
            padx=0, pady=0, anchor="center", takefocus=0
        )
        self.image_label.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)
        self.image_label.bind("<Configure>", lambda e: self._refit_last_image())

        # TEXTE
        text_frame = tk.Frame(self, takefocus=0)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=(0, 8))
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        self.text = tk.Text(text_frame, wrap="word", height=14, takefocus=0)
        self.text.grid(row=0, column=0, sticky="nsew")

        self.scroll = tk.Scrollbar(text_frame, command=self.text.yview, takefocus=0)
        self.scroll.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=self.scroll.set)
        self.text.configure(state="disabled")

        # PANNEAU DROIT
        control_frame = tk.Frame(self, takefocus=0)
        control_frame.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=(0, 8))
        control_frame.grid_columnconfigure(0, weight=1)

        tk.Label(control_frame, text="Déplacements").grid(row=0, column=0, pady=(0, 6))

        self.btn_n = tk.Button(control_frame, text="N", command=lambda: self.send_direction("N"))
        self.btn_s = tk.Button(control_frame, text="S", command=lambda: self.send_direction("S"))
        self.btn_e = tk.Button(control_frame, text="E", command=lambda: self.send_direction("E"))
        self.btn_o = tk.Button(control_frame, text="O", command=lambda: self.send_direction("O"))
        self.btn_u = tk.Button(control_frame, text="U", command=lambda: self.send_direction("U"))
        self.btn_d = tk.Button(control_frame, text="D", command=lambda: self.send_direction("D"))

        self.btn_n.grid(row=1, column=0, sticky="ew", pady=2)
        self.btn_s.grid(row=2, column=0, sticky="ew", pady=2)
        self.btn_e.grid(row=3, column=0, sticky="ew", pady=2)
        self.btn_o.grid(row=4, column=0, sticky="ew", pady=2)
        self.btn_u.grid(row=5, column=0, sticky="ew", pady=2)
        self.btn_d.grid(row=6, column=0, sticky="ew", pady=2)

        tk.Label(control_frame, text="Commandes").grid(row=7, column=0, pady=(10, 6))

        self.btn_look = tk.Button(control_frame, text="look", command=lambda: self.send_command("look"))
        self.btn_take = tk.Button(control_frame, text="take", command=self.take_auto)

        # ✅ DROP BOUTON (comme demandé)
        self.btn_drop = tk.Button(control_frame, text="drop", command=self.drop_prompt)

        self.btn_check = tk.Button(control_frame, text="check", command=lambda: self.send_command("check"))
        self.btn_history = tk.Button(control_frame, text="history", command=lambda: self.send_command("history"))
        self.btn_back = tk.Button(control_frame, text="back", command=lambda: self.send_command("back"))
        self.btn_help = tk.Button(control_frame, text="help", command=lambda: self.send_command("help"))
        self.btn_quit = tk.Button(control_frame, text="quit", command=lambda: self.send_command("quit"))

        self.btn_look.grid(row=8, column=0, sticky="ew", pady=2)
        self.btn_take.grid(row=9, column=0, sticky="ew", pady=2)

        # ✅ place drop juste après take
        self.btn_drop.grid(row=10, column=0, sticky="ew", pady=2)

        self.btn_check.grid(row=11, column=0, sticky="ew", pady=2)
        self.btn_history.grid(row=12, column=0, sticky="ew", pady=2)
        self.btn_back.grid(row=13, column=0, sticky="ew", pady=2)
        self.btn_help.grid(row=14, column=0, sticky="ew", pady=2)
        self.btn_quit.grid(row=15, column=0, sticky="ew", pady=2)

        # ENTRY + SEND
        entry_frame = tk.Frame(self, takefocus=0)
        entry_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        entry_frame.grid_columnconfigure(0, weight=1)

        self.entry = tk.Entry(entry_frame)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.btn_send = tk.Button(entry_frame, text="Envoyer", command=self.on_enter)
        self.btn_send.grid(row=0, column=1, padx=(6, 0))

    # =========================
    # GUI HELPERS
    # =========================
    def _set_buttons_state(self, state: str):
        """Applique un état à tous les boutons (utile pour pause / fin)."""
        btns = [
            self.btn_n, self.btn_s, self.btn_e, self.btn_o, self.btn_u, self.btn_d,
            self.btn_look, self.btn_take, self.btn_drop, self.btn_check, self.btn_history,
            self.btn_back, self.btn_help, self.btn_quit, self.btn_send
        ]
        for b in btns:
            try:
                b.configure(state=state)
            except Exception:
                pass

    def disable_inputs(self):
        """Désactive proprement la saisie quand le jeu est fini."""
        try:
            self.entry.configure(state="disabled")
        except Exception:
            pass
        self._set_buttons_state("disabled")

    def enable_inputs(self):
        try:
            self.entry.configure(state="normal")
            self.entry.focus_set()
        except Exception:
            pass
        self._set_buttons_state("normal")

    def clear_output(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def ask_player_name(self):
        name = simpledialog.askstring("ATLAS 2160", "Identité (écris ton nom) :")
        if name is None:
            return "Inconnu"
        name = name.strip()
        return name if name else "Inconnu"

    def gui_pause(self, txt="\n(Appuie sur Entrée pour continuer) "):
        """
        Pause GUI fiable :
        - affiche le texte
        - attend un Enter (entrée vide) ou 'back' (relire)
        - désactive les boutons pour éviter clics parasites
        """
        print(txt)
        self._waiting_for_continue = True
        self._continue_var.set(False)

        self.disable_inputs()
        try:
            self.entry.configure(state="normal")
            self.entry.focus_set()
        except Exception:
            pass

        self.wait_variable(self._continue_var)

        self._waiting_for_continue = False
        self.enable_inputs()

    def take_auto(self):
        if getattr(self, "_waiting_for_continue", False):
            return
        if self.game.finished:
            return
        try:
            room = self.game.player.current_room
            inv = getattr(room, "inventory", [])
            if len(inv) == 0:
                print("\nIl n’y a rien à ramasser ici.\n")
                return
            if len(inv) == 1:
                self.send_command("take")
                return
            print("\nPlusieurs objets sont présents. Fais 'look' puis 'take <objet>'.\n")
        except Exception:
            print("\nImpossible de ramasser.\n")

    # ✅ DROP — demande un objet à déposer
    def drop_prompt(self):
        if getattr(self, "_waiting_for_continue", False):
            return
        if self.game.finished:
            return
        try:
            inv = getattr(self.game.player, "inventory", [])
            if not inv:
                print("\nInventaire vide : rien à déposer.\n")
                return

            name = simpledialog.askstring("Drop", "Quel objet déposer ? (nom exact)")
            if not name:
                return
            self.send_command(f"drop {name.strip()}")
        except Exception:
            print("\nImpossible de déposer.\n")

    def on_enter(self, event=None):
        cmd = self.entry.get().strip()
        self.entry.delete(0, "end")

        if getattr(self, "_waiting_for_continue", False):
            if cmd.lower() == "back":
                self.send_command("back")
                return "break"
            self._continue_var.set(True)
            return "break"

        if cmd == "" and self.game.input_mode == "CHOICE":
            print("\nChoix requis. Tape N ou E.\n")
            print(self.game.choice_prompt)
            return "break"

        if cmd:
            self.send_command(cmd)
        return "break"

    def send_direction(self, d: str):
        if self.game.input_mode == "CHOICE":
            self.send_command(d)
        else:
            self.send_command(f"go {d}")

    def _display_room_status(self, force=False):
        try:
            if self.game.player is None or self.game.player.current_room is None:
                return
            room = self.game.player.current_room
            print("\n" + "-" * 42)
            print(f"📍 Lieu : {room.name}")
            room.show_inventory()
            print("-" * 42 + "\n")
        except Exception:
            if force:
                print("\n(Erreur affichage lieu/objets)\n")

    def send_command(self, cmd: str):
        if self.game.finished:
            return
        if getattr(self, "_waiting_for_continue", False):
            return

        mode_before = self.game.input_mode

        # Triggers AVANT de traiter la commande
        if self.game.chapter == 1:
            self.game.chapter1_triggers()
            self.game.chapter1_check_special_paths()
        elif self.game.chapter == 2:
            self.game.chapter2_triggers()
        elif self.game.chapter == 3:
            self.game.chapter3_triggers()

        # Si un trigger vient d'activer un dilemme (CHOICE), on s'arrête là
        if mode_before == "NORMAL" and self.game.input_mode == "CHOICE":
            self.refresh_room_image()
            return

        # Exécute la commande
        self.game.process_command(cmd)

        # Affichage + refresh
        self._display_room_status()
        self.refresh_room_image()

        # Fin du jeu : on désactive + popup (UNE SEULE FOIS)
        if self.game.finished:
            self.disable_inputs()
            try:
                messagebox.showinfo("ATLAS 2160", "Fin du jeu.")
            except Exception:
                pass

    # =========================
    # IMAGES (FIX)
    # =========================
    def refresh_room_image(self):
        """
        FIX IMPORTANT :
        - Si game._override_image est défini, on l'affiche
        - MAIS on NE remet PAS game._override_image = None ici
          (sinon tes cutscenes disparaissent instantanément)
        """
        try:
            override = getattr(self.game, "_override_image", None)
            if override:
                path = os.path.join(self.assets_dir, override)
                self._last_image_path = path
                if os.path.exists(path):
                    try:
                        self._raw_photo = tk.PhotoImage(file=path)
                        self._fit_image_to_label()
                        self.image_label.configure(image=self.current_photo, text="")
                    except Exception:
                        self.image_label.configure(image="", text=f"(Image invalide)\n{override}")
                else:
                    self.image_label.configure(image="", text=f"(assets/{override} manquant)")
                return

            if self.game.player is None or self.game.player.current_room is None:
                self.image_label.configure(image="", text="(Aucun lieu)")
                self._last_image_path = None
                self._raw_photo = None
                self.current_photo = None
                return

            room_name = self.game.player.current_room.name
            filename = f"{room_name}.png"
            path = os.path.join(self.assets_dir, filename)
            self._last_image_path = path

            if not os.path.exists(path):
                self.image_label.configure(image="", text=f"{room_name}\n\n(assets/{filename} manquant)")
                self._raw_photo = None
                self.current_photo = None
                return

            self._raw_photo = tk.PhotoImage(file=path)
            self._fit_image_to_label()
            self.image_label.configure(image=self.current_photo, text="")

        except Exception:
            self.image_label.configure(image="", text="(Erreur image)")
            self._raw_photo = None
            self.current_photo = None

    def _refit_last_image(self):
        try:
            if self._raw_photo is None:
                return
            self._fit_image_to_label()
            self.image_label.configure(image=self.current_photo, text="")
        except Exception:
            pass

    def _fit_image_to_label(self):
        if self._raw_photo is None:
            self.current_photo = None
            return

        try:
            lw = max(1, self.image_label.winfo_width())
            lh = max(1, self.image_label.winfo_height())

            iw = max(1, self._raw_photo.width())
            ih = max(1, self._raw_photo.height())

            # downscale
            if iw > lw or ih > lh:
                import math
                fx = math.ceil(iw / lw)
                fy = math.ceil(ih / lh)
                factor = max(1, fx, fy)
                self.current_photo = self._raw_photo.subsample(factor, factor)
                return

            # upscale (limité)
            zx = max(1, lw // iw)
            zy = max(1, lh // ih)
            z = max(1, min(zx, zy))
            if z > 6:
                z = 6
            self.current_photo = self._raw_photo.zoom(z, z) if z > 1 else self._raw_photo

        except Exception:
            self.current_photo = self._raw_photo

    def on_close(self):
        try:
            sys.stdout = sys.__stdout__
        except Exception:
            pass
        self.destroy()


def main():
    app = GameGUI()
    app.mainloop()


if __name__ == "__main__":
    main()