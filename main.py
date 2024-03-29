"""
An implementation of Nagel-Schreckenberg vehicular traffic automaton.
"""

__package__ = 'cage'


import cage

import random
try:
    from PIL import Image
except ImportError:
    Image = None
#Input the desired output path here VV
filepath = 'insert file path here'

#NaSch empty cell
NSEMPTY = -1

#Nasch Map
class NaschMap(cage.RadialMap):
    """A one-dimensional, radial map for NaSch model."""
    #NaschMap is a radial map, that means neighborhoods are radial,
    #with radius = vmax. However, in practice, real neighborhood is
    #more dynamic: it goes from the preceding vehicle to the one at
    #the front of certain cell, up to vmax cells in either
    #direction, but since CAGE don't consider for dynamic neighborhoods
    #is enough to use radial ones and limit them in populate or rule
    #methods in the rules classes
    def __init__(self, size, vmax):
        cage.RadialMap.__init__(self, size, vmax)
        self.background = NSEMPTY
        self.vmax = vmax

    def clone(self):
        return NaschMap(self.size, self.vmax)

#Nasch first 3 rules: speed modification rules
class NewspeedRule(cage.Rule):
    """Nagel & Schreckenberg 1st, 2nd and 3rd rules applied to
    change vehicle-cells' speed, empty cells remain untouched"""
    def __init__(self, vmax, p):
        random.seed()
        self.vmax = vmax
        self.p = p

    def populate(self, address):
        #include actual cell in neighborhood
        self.table = [self.map.get(address)]
        for i in range(self.map.neighborhood()):
            if i%2 != 0: #for speed use cells in front, thats even ones
                continue #in a radial neighborhood
            self.table.append(self.map.get(self.map.neighbors(address)[i]))

    def rule(self, address):
        #if empty cell, don't make speed calculations
        if self.table[0] == NSEMPTY:
            return self.table[0]

        #initial speed: actual state of cell
        vel = self.table[0]

        #Rule #1 (acceleration)
        vel = min(vel + 1, self.vmax)

        #Rule #2 (gap consideration)
        dist = 0
        ind = 0
        for i in self.table:
            if ind == 0:
                ind += 1
                continue
            if i == NSEMPTY:
                ind += 1
                dist += 1
                continue
            break

        vel = min(vel, dist)

        #Rule #3 (randomly slow vehicle)
        if random.random() < self.p:
            vel = max(vel - 1, 0)

        return vel

#Nasch 4th rule: movement rule
class MovementRule(cage.Rule):
    """Nagel & Schreckenberg 4th rule applied to each cell in the
    highway, so as to move vehicules or update empty cells.
    The state of a non-empty cell indicates a speed, so the cell most
    move forward leaving an empty cell behind, or maybe a preceding
    vehicule, with its new speed, will fall right into this empty cell,
    so it also has to update"""
    def __init__(self, vmax):
        self.vmax = vmax

    def populate(self, address):
        #include actual cell in neighborhood
        self.table = [self.map.get(address)]
        for i in range(self.map.neighborhood()):
            if i%2 == 0: #for movement, use cells in rear, that's odd ones
                continue #in a radial neighborhood
            self.table.append(self.map.get(self.map.neighbors(address)[i]))

    #Rule #4
    def rule(self, address):
        newpos = self.table[0]
        if newpos == 0:         #no movement, the cell remains the same
            return newpos
        elif newpos > 0:        #movement at certain positive speed,
            return NSEMPTY          #so the cell will turn empty
        else:                   #if empty, detect if the preceding vehicle
            dist = 0                #falls here
            for i in self.table:
                if i == NSEMPTY:    #continue until the detection of predecessor
                    dist += 1       #(also ignores actual cell)
                    continue
                elif i == 0:        #predecessor has speed=0, then no changes made
                    return newpos
                if dist == i:       #predecessor has speed=distance, it will fall here
                    return i
                dist += 1
        return newpos               #in any other case, change nothing

#Nasch Rule: speed & movement rules
class NaschRule(NewspeedRule, MovementRule):
    """Nagel & Schreckenberg Rules"""
    def __init__(self, vmax, p):
        self.move = False
        NewspeedRule.__init__(self, vmax, p)
        MovementRule.__init__(self, vmax)

    def rule(self, address):
        if self.move == False:
            NewspeedRule.populate(self, address)
            v = NewspeedRule.rule(self, address)
            return v
        else:
            MovementRule.populate(self, address)
            p = MovementRule.rule(self, address)
            return p

#Nasch Automaton
class NaschAutomaton(cage.SynchronousAutomaton, NaschRule):
    """Nagel & Schreckenberg vehicular traffic automaton"""
    states = 7

    def __init__(self, size, vmax, p):
        cage.SynchronousAutomaton.__init__(self, NaschMap(size, vmax))
        NaschRule.__init__(self, vmax, p)
        self.states = vmax + 2 #states = {0,1,..,vmax} U {empty cell}

    def update(self):   #the automata will update two times:
        self.move = False
        cage.SynchronousAutomaton.update(self)   #one for speed calculations
        self.move = True
        cage.SynchronousAutomaton.update(self)   #one for actual movement

#Image Player for Nasch
class NaschImagePlayer(cage.Player):
    def __init__(self, width, height):
        assert Image , "WARNING: no Image library loaded"
        cage.Player.__init__(self)
        self.width = width
        self.height = height
        self.image = Image.new('RGB', (width, height), (255, 255, 255))
        self.size = (width,)
        self.row = 0
        self.inited = 0

    def display(self):
        map = self.automaton.map
        col = (0, 0, 0)
        for x in range(map.length):
            val = map.get((x,))
            if val == NSEMPTY:          #empty cell: black
                col = (0, 0, 0)
            elif val == 0:              #stopped car: red
                col = (255, 0, 0)
            elif val == 1 or val == 2:  #'slow' car: orange
                col = (255, 128, 0)
            elif val == 3 or val == 4:  #'normal' car: yellow
                col = (255, 255, 0)
            elif val == 5:              #fast car: green
                col = (0, 255, 0)
            else:                       #invalid: white
                col = (255, 255, 255)
            self.image.putpixel((x, self.row), col)
        self.row += 1

    def main(self, automaton):
        cage.Player.main(self, automaton)
        assert self.automaton is not None
        assert self.automaton.map.dimension == 1 ###
        while self.row < self.height and self.automaton.running():
            self.display()
            self.automaton.update()
            self.automaton.between()
        self.finish(roadLength, iters, vmax, p, density)

    def finish(self, roadLength, iters, vmax, p, density):
        self.image.save(filepath+str(roadLength) + "x" + str(iters) + ", vmax=" + str(vmax) + ", p= " + str(p) + ", density=" + str(density)+'.png', 'PNG')



#-1 represent empty cells, 0 or positive integers represent vehicules at that given speed, with vmax as limit
# highway = [] #predermine positions and speeds in this array


###############For simulations with fixed number of cars and road length to have all cars be equidistant##################
# vmax = 5 # (30*1000/60/60)/7.5 = 1.111 cells/iter     #maximum speed of cars in cells per time interval
# p = 0.1                                                       #probability of random speed decrease by 1
# iters = 512    #240 seconds or 4 minutes                      #how many time intervals to run
# numCars = 22   
# roadLength = (vmax+1)*(numCars)                        #how long the road should be in cells
# density = 1 / float(vmax)   #22 vehicles/road length                       #car per cell
# print(density)


###############For simulations of fixed density###########################
vmax = 5                             #maximum speed of cars in cells per time interval
p = 0.4                              #probability of random speed decrease by 1
iters = 256                          #how many time intervals to run  
roadLength = 256                     #how long the road should be in cells
density = 0.24                       #car per cell
numCars = int(density*roadLength)


highway = [NSEMPTY]*roadLength

####### create a random row of cars, according to density from 0 to 1 ########
randPos = random.sample(range(0,len(highway),1), numCars) #spawn at random position
for pos in randPos:
    highway[pos] = random.randint(0,vmax) #spawn with random speed

# highway = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
# 0,0,0,0,0,0,0,0,
# 0,0,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,
# NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY,NSEMPTY]

########create a row of cars that spawns equidistantly, at max speed ########
# i = 0
# for pos in range(0, len(highway), vmax+1):
#     i = i + 1
#     highway[pos] = vmax
#     if i > numCars:
#         break

print("Number of cars to spawn: "+ str(numCars))
print("Filename: " + str(roadLength) + "x" + str(iters) + ", vmax=" + str(vmax) + ", p= " + str(p) + ", density=" + str(density)) #name of output file

def main():
    player = None
    try:
        player = NaschImagePlayer(len(highway), iters)
        automaton = NaschAutomaton(player.size, vmax, p)
        x = 0
        for c in highway:
            cage.PointInitializer((x,), c).initialize(automaton)
            x += 1
        player.main(automaton)
    except Exception as e:
        print(str(e))
    finally:
        player.done()

if __name__ == '__main__': main()
