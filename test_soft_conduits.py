from game import Game
from room import Room
from player import Player

# Setup minimal game state without interactive pauses
g = Game()
# build chapter1 rooms
g.build_chapter1_map()
# create player and attach
g.player = Player('Tester')
# mark argos choice done to simulate earlier choice
g.argos_choice_done = True
g.argos_ally = True

# Create soft conduit rooms as in start_soft_conduits (without pause/prints)
C0 = Room("Conduit Intratemporel", "un conduit test")
C1 = Room("Jonction Phasée", "jonction test")
C2 = Room("Salle des Anneaux", "anneaux test")
C0.exits = {"N": C1, "E": None, "O": None, "S": None}
C1.exits = {"S": C0, "N": C2, "E": C0, "O": C0}
C2.exits = {"S": C1}

# assign to game
g.soft_start = C0
g.soft_end = C2

# place player in C0 and simulate moves
g.player.current_room = C0
print('start room:', g.player.current_room.name)
# move to C1
m1 = g.player.move('N')
print('moved to:', g.player.current_room.name, 'result', m1)
# move to C2
m2 = g.player.move('N')
print('moved to:', g.player.current_room.name, 'result', m2)
# now call the check that should transition to quantum core
g.chapter1_check_special_paths()
print('after check, chapter:', g.chapter, 'current_room:', g.player.current_room.name)
print('quantum core room name expected:', g.ch1_quantum_core.name)
