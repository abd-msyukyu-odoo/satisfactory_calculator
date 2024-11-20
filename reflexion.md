logique pour sequencer recettes ET ingredients en "une" passe

```
loop sur les recettes
1- chercher recettes sans consommation
2- tous les produits et recettes de ce parcours se voient attribuer la sequence 1
3- creer un set des produits (pour la recherche) et un set de produits consommes (pour eviter les cycles)
4- chercher recettes qui consomment produits de sequence precedente
5- tous les produits et recettes se voient attribuer une sequence +1 (meme s'ils avaient deja une sequence)
6- refaire etape 3
7- fin quand aucune recette ne correspond a la recherche
```

```
ordonner les ingredients par sequence (sequence identique => alphabetique)
ordonner les recettes par sequence (2x) (sequence identique => alphabetique)
```

logique de dimensions

```
nommer le building pour chaque recette
indiquer la footprint pour chaque recette (valeur scale, round buildings up)
indiquer la hauteur pour chaque recette (fixe)
```

logique d'aggregation

```
aggreger les quantites de batiments identiques
```

logique de mapping A_def (recipes) and B_def (resources)

```
each id in A_def has an id in google sheet
each id in B_def has an id in google sheet
```

```
OR => could sort at entry point when parsing the recipes ?
	-> definitely the right decision, supposing that the solver does not alter the shape of the matrices
```

```
display[self.get_letter(self.s.A.shape[0] + 5)][ROW]
=> access to column right after the scaling
building name

next to multiplier and row, add dimensions
below multiplier: base surface area
next: scaled surface area
next: height of the building
```

```
pyramide: combien d'etages, quelle largeur par etage

=> tour centrale de circulation de ressources (+ escalier autour)
=> ressources de base puis on monte ?
```

### next

> caterium ingot (tempered caterium ingot)
> caterium ore
> reanimated sam
> quartz crystal (pure quartz crystal)
> silica (cheap silica)
> black powder (fine black powder)
> nobelisk 
> smokeless powder
> heavy oil residue ()
> petroleum coke
> polymer resin (heavy oil residue)
> fuel (unpackage fuel)
> crude oil
> compacted coal ()
> sulfur
> sam
> raw quartz
> water
> packaged water
> turbofuel ()
> plastic smart plating (change recipe)
> copper sheet (Steamed Copper Sheet)

computer (crystal computer) (10)
crystal oscillator (Insulated Crystal Oscillator) (10)
circuit board (silicon circuit board > caterium circuit board) (20)
quickwire (fused quickwire) (30)
ai limiter (plastic ai limiter) (10)
sam fluctuator (6.25 (node 150))
heavy modular frame (heavy encased frame) (10)
empty canister (coated iron canister) (10)
rifle ammo (10)
rubber (residual rubber + recycled rubber) (20)
plastic (recycled plastic) (20)
packaged fuel (diluted packaged fuel) (10)
packaged turbofuel (10)
modular engine (5)
adaptive control unit (1)

```
energie (4600 watts min)
possibility 5 power augmenters (100 computers = 12 tickets), 51 somersloop -> feasible

-> find all recipes:
OK - crystal computer
OK - fine black powder
OK - silicon circuit board
OK - insulated crystal oscillator
OK - pure quartz crystal
OK - plastic ai limiter
OK - tempered caterium ingot
residual rubber
OK - heavy oil residue
OK - recycled plastic
OK - recycled rubber
OK - diluted packaged fuel
OK - coated iron canister
OK - compacted coal
OK - turbofuel
OK - heavy encased frame
OK - wet concrete
OK - plastic smart plating
OK - steel rotor
OK - rigor motor
OK - silicon high-speed connector
polyester fabric (MAM)

-> find many energy boosters for overclock

-> create new blueprints (bigger + faster + newer)

-> fill geysers with energy thingy => no need for other energy thingy, or need less of them
```

#### simplified solver

```
- define the "cost of energy" in resources by hand (guesstimate)
- now, each recipe is entirely defined by resources
- also, each resource has its own cost in other resources too, based on energy, even water
- replace all water by its cost in other resources using energy (consider pumps as negligible, or add an energy constant per quantity to represent pumps), since it is illimited
=> now we have every recipe in terms of resources with no water
=> now, replace resources cost for every resources by the % of that resource compared to the world availability
=> now every recipe has a cost in % of other resources without taking water into account

=> take the energy solution using the new recipe scaling in %, and evaluate which resource us over-used and which resource is under-used
=> adapt/change the ratios of recipes through alternatives to approximately balance the solution
=> redo a full pass to re-evaluate the new %value for each resource in the energy solution
=> repeat process until solutions are balanced for energy (this process has a risk of artificially augmenting the amount of resources needed to do something for the sake of balancing, so a notion of overall cost should be maintained and minimised to avoid this issue)
	=> overall cost can be the hightest resource % (% of the most used resource) => maybe except uranium which must be used at 100% for energy? => yes (almost true except dark matter residue, but that can be obtained with other processes so can be omitted for simplicity)

=> energy balancing
	- replace water by its resource energy cost
	- use 100% of uranium
	- minimise max % usage of any other resource
	=> solution is the most balanced way to get energy.
	
=> there is no real concept of "resource cost", only "recipe cost", as almost every resource can be obtained multiple way

=> a great way to proceed and get somewhat of a "resource cost" is to take one (or multiple) end game resources and minimize max % LEFT usage of any other resource after max energy level is guaranteed (through uranium)
```

### bom

```
water (9 extrators, 2 pipes)
crude oil (1 impure, 1 pipe)
sulfur (1 miner, 1 lane)
sam (1 miner, 1 lane)
raw quartz(2 norm miners, 1 lane)
limestone (3 norm miners, 2 lanes)
iron ore (3 norm miners, 2 lanes)
copper ore (2 norm miners, 1 lane)
coal (2 norm miners + 1 impure, 2 lanes)
caterium (1 pure miner, 1 lane)

```

### floor 0

```
copper alloy ingot (foundry 5)
compacted coal (assembler 1)
cheap silica (assembler 5)
fine black powsder (assembler 1)
tempered caterium ingot (foundry 3)
silicon circuit board (assembler 5)
rifle ammo (assembler 1)
fused quickwire (assembler 9)
silicon high-speed connector (manufacturer 4)
plastic ai limiter (assembler 4)
insulated crystal oscillator (manufacturer 10)
crystal computer (assembler 4)

-1 iron ore (1 remain)
-split copper ore (1 remain)
-1 sulfur (0 remain)
-0 coal (2 remain, split for interior)
-1 raw quartz (0 remain, split for exterior)
-2 limestone (0 remain, split for exterior, check master belt position)
+1-1 compacted coal (0 remain, split for exterior)
+1-1 copper ingot (0 remain, split for exterior)
+1-1 silica (0 remain)
+1 black powder (1 remain, split for interior)
-1 caterium ore (0 remain)
-1 petroleum coke (0 remain)
+1-1 caterium ingot (0 remain)
-0 copper sheet (1 remain, split for interior)
+1 circuit board (1 remain, split for interior, split for output)
-1 smokeless powder (0 remain)
+1 rifle ammo (1 remain, output)
+2-2 quickwire (0 remain, split for output)
+1 high speed connector (1 remain, split for interior, split for output)
-0 plastic (1 remain, split for interior, split for output)
+1-1 ai limiter (0 remain, split for output)
-1 quartz crystal (0 remain)
-0 rubber (1 remain, split for interior, split for output)
+1 crystal oscillator (1 remain, split for interior, split for output)
--
unused exterior
packaged turbofuel (1 remain, output)
packaged fuel (1 remain, output)
-0 concrete (1 remain, split for interior, split for output)
canister (2 remain, output, input (exterior))
fabric (1 remain, interior)

6 raw resources
canister 2 belts
fabric 1 belt
black powder 1 belt
copper sheet 1 belt
crystal oscillator 1 belt
circuit board 1 belt
high speed circuit board 1 belt
plastic 1 belt
rubber 1 belt
concrete 1 belt
```

### floor1

```
iron alloy ingot (2 belts, - 2 iron ore (0 remain), - 1 copper ore (0 remain)) (12 foundry)
solid steel ingot (2 belts, -1.5 iron ingot (1 remain), -1.5 coal (1 remain)) (16 foundry)
gas filter (1 output, -0.5 coal (0 remain), -1 fabric (0 remain)) (1 manufacturer)
iron plate (1 belt, -0.5 iron ingot (1 remain), -0.5 steel ingot (2 remain)) (3 foundry)
coated iron canister (1 belt, -1 copper sheet (0 remain), -0.5 iron plate (1 remain)) (1 assembler)
stitched iron plate (1 belt, -0.5 iron plate (0 remain), -0.5 wire, (1 remain)) (5 assembler)
iron wire (1 belt, -0.5 iron ingot (0 remain)) (17 constructor)
steel pipe (1 belt, -1 steel ingot (1 remain)) (15 constructor)
nobelisk (1 output, -1 black powder (0 remain), 0.5 steel pipe (1 remain)) (1 assembler)

estimated area (133), 13x13 = 169 (79% capacity, 36 empty blocks)
estimated belt change -6+1 (-5) => 12 
```

```
floor2
178 estimated area left => 11x11 121 * 0.8 = 96
floor3
					  => 9x9 81 *0.7 = 56
floor4
					  => 7x7 63 *0.7 = 44
```

```
error for steel ingot => secondary belt should have 440 not 470 => target is 10, not 50
```

### floor2

```
reanimated sam (1 belt, -1 sam (0 remain))) (2 constructor)
steel beam (1 belt, -1 steel ingot (0 remain)) (8 constructor)
encased industrial beam (1 belt, -0.5 concrete (1 remain), -1 steel beam (0 remain)) (7 assembler)
steeled frame (1 belt, -0.5 steel pipe (1 remain), -0.5 reinforced iron plate (1 remain)) (10 assembler)
heavy encased frame (1 belt, -0.5 concrete (0 remain), -0.5 steel pipe (1 remain), -1 encased industrial beam (0 remain), -1 modular frame (0 remain)) (4 manufacturer)
current size: 84 (ok)

```

### floor3

```
sam fluctuator (1 belt, -1 reanimated sam (0 remain), -0.5 steel pipe (1 remain), -0.5 wire (1 remain)) (1 manufacturer)
stator (1 belt, -0.5 wire (1 remain), -0.5 steel pipe (1 remain)) (2 assembler)
rotor (1 belt, -0.5 wire (1 remain), -0.5 steel pipe (1 remain)) (2 assembler)
automated speed wiring (1 belt, -1 high speed connector (0 remain), -0.5 stator (1 remain), 0.5 wire (0 remain)) (1 manufacturer)
rigor motor (1 belt, -0.5 stator (0 remain), -0.5 rotor (1 remain), -0.5 crystal oscillator (1 remain)) (2 manufacturer)
plastic smart plating (1 belt, -0.5 plastic (0 remain), -0.5 reinforced iron plate (1 remain), -0.5 rotor (0 remain)) (2 manufacturer)
crystal computer (1 belt, -0.5 circuit board (1 remain), -0.5 crystal oscillator (0 remain)) (4 assembler)

current size: 56 (ok)
```

### floor4

```
modular engine
adaptive control unit

current size: 41 (ok)


```

### signals definitions

```
resource reserve (body) INPUT + OUTPUT (line)

signal reserve (body) main resource for signal (need special handling for overflow) | signal resource (can be partially filled) (line)

alternator (body) filler resource (line)

conveyor lifts INPUT + OUTPUT (body) => line is irrelevant


combinations:

resource reserve + resource reserve
resource reserve + resource reserve

signal reserve + main (= resource reserve)
signal reserve + signal (= signal reserve)

alternator + signal filler (= signal reserve)
alternator + main (=resource reserve)

INPUT
OUTPUT

colors:
resource reserve => BLACK
signal reserve => WHITE
alternator => BLUE
input => RED
output => GREEN
```

```
issues:
minimise bauxite =>
```

```
train T variants:
TLBR
TRBL

	TOP-FORWARD BOTTOM-BACKWARD
	TOP-BACKWARD BOTTOM-FORWARD
	
BUT => no matter the case, forward is always on the right and backward is always on the left
	=> then an adaptator to right-TOP ou right-BOTTOM can be separate
	
	
up to 4 belts IN/OUT per station of 2 wagons
=> ideally would have a merge-splitter into 4 

2 belts into 1 smoother = always 1 full + 1 overflow without loss
split the full belt in 2 and the overflow in 2 and merge => 2 equal belts guaranteed no matter if there was 1 or 2 inputs

since there will never be more than 1 belt into a wagon => 2 input belts can be inserted in the mechanism and equally contribute
to both wagons

smoother => split both ways => station (merge happens in the container)


input (train incoming) => belts are already balanced, only have to merge outputs of container, but I don't know if they have prior
```

```
quartz caterium copper sulfur limestone (5) => slow lane

copper > limestone > quartz > caterium > sulfur

nitrogen gas > iron > bauxite > coal
```

```
can one station support 3 lanes at 2110.4005

```

```
resources to move below: TODO: define how many belts
nitrogen gas (2)
heavy modular frame (1)
heat sink (1)
motor (1)
aluminum casing (1)
copper ingot (1)
iron plate (1)
sulfur (1)
coal (1)
raw quartz (1)
bauxite (2)
BONUS limestone (1) (overflow from 1 belt)
SUM DOWN: 14
```

```
resources to move above: TODO: define how many belts
fused modular frame (1)
cooling system (1)
turbo rifle ammo (1)
plastic (2)
rubber (2)
aluminum ingot (1)
gas filter (1)
empty fluid tank (1)
BONUS concrete (1) (split into 2 lanes for increased concrete generation)
SUM CLIMBING: 11
```

```
resources to create below:
smokeless powder
black powder
aluminum ingot
aluminum casing
gas filter
empty fluid tank
```

```
bonus concrete:
use 401.878307 limestone (overflow) for pure concrete
need 334.89858916666666666666666666667 extra water
4 refineries
lowest at 3.3489858916666666666666666666667 efficiency
```

```
below floor:
27 down (from above) => ingredients for down (14) + final products from above (13)
11 UP (from below)
```

### NEW ALGOS

```
Objective: sort recipes in order to maximise output usage in the next input (minimise parallel belts)
	-> following the tree should also give an order for ingredients

acquired things = raw resources

create as many trees as there are things created from already acquired things
	-> combine recipes which create the same thing in the same tree
	-> recipes which create multiple things combien the trees for the multiple things
	-> if something is created by multiple routes and one route can not be created yet, don't create a tree for that yet
-> sort them (trees)
1- fully consume X things (x high is better => consume others) -> this criterion must consider partially consumed things
2- used to create X NEW things (x low is better => consume itself) -> this criterion must consider all products and their usage
3- created using X things (x high is better => consume others)
4- from tier x (x high is better => complete a subtree depth first)

Forcibly construct the first tree using all fluids => this will add the bias for the construction start inside the solid factory since
all products from refineries will be at the same grade as raw resources

same algo as above, but only create trees from recipes using a fluid
-> when all trees are stuck, consider all required missing ingredients, and evaluate if some are entirely required in current trees
-> if so, add that recipe to the tree, and evaluate again, with the resources. Once no ingredient is entirely required in current trees,
-> consider that ingredient available if it is not produced by a pending recipe with fluid (add required belts to the belts count), and continue.
-> if a product is created by a fluid machine, add all recipes producing that product in the tree (same as above), even if the other recipes do not consume a fluid.

The final "bus" entry is constituted by "extra ingredients" forcibly added + raw resources
	=> don't care about buses for now

Now, start the normal algo, but all resources created in the fluid section are already available
	=> don't care about buses and volume for now



-> idea: complete the first tree to the max => when blocked, advance the next tree
	-> when all trees are blocked -> incremental sudoku pose
		-> evaluate if a resource is entirely required in the lowest amount of trees and would unlock a new step
```

```
special order:
                # fully consume X things (high) (=> no more recipe in either batch or target)
                # used to create X things (low) (count for each output the amount of global recipes using that output and sum)
                # created using X things (high) (count ingredients)
                # have the highest sequence in recipes_sequences
                # alphabetical order

idea is to create sections which are sets of recipes which like to be bundled together following a series of criteria
- first section is "fluid"
	- artificial pre-batch of recipes, but still allowed to pick from main pool
	- start with sub-blocks for each raw resource following the special order thingy
		=> water should have a bad score because it is used everywhere
	- each sub block has a list of "IN" and "OUT", idea is to consume target recipes while maintaining "IN" and "OUT" low for each sub-block
	- every block should have a complete list of "IN" and "OUT", and "OUT" should count the amount of different recipes using that "OUT" (even if incorrect if multiple sources) => OUTSIDE OF THE BLOCK
	- once a sub block uses all "OUT" of another sub block, they can be merged together
	- sub blocks are allowed to use any available output from any other sub block (share)
	---
	- go forward in a sub-block with current available resources => search for recipes using these
		- if nothing is found:
			- identify recipes needing only i=1++ missing ingredient
			- priority if all recipes using that ingredient are present (fully consumed)
				-> allow picking a recipe from the main pool
					-> recursively iterate on its ingredients until either all of them are available, or rendered available with
					the next condition
			- priority for the most common needed ingredient
				-> add that ingredient to "IN" for every sub-block and consider it acquired for the section
		- if there is no recipe using all "OUT", block has ended
	- sub-block completed first is the one with the best recipe in the batch using the order heuristic, even if it was not the first sub-block initially
	- once a recipe is "elected" it gains a sequence number in its block, and an overall "election" sequence number


-> what I'm expecting from this is: one big sub-block for everything related to crude oil
-> many smaller blocks (1 aluminum, 1 limestone, 1 copper sheet, etc)
-> nitrogen should merge with bauxite


- then, sections are defined by space "volume"
	-> which are currently unknown lol, so later sections should be computed AFTER the results are out
```

```
associer une valeur a chaque IN pour savoir combien on consomme

associer une valeur a chaque OUT pour savoir combien on produit

apres avoir merge les in et les out, on peut regarder les autres blocks et voir si leurs OUT sont entierement consommés par nous (pas clair, 1 OUT =\= 1 IN, but ALL OUT == ALL IN)

associate with matching block:
	-> each block has available_resources set
	=> matching block is the block with the most available_resources present in the ingredients of a recipe
	
master blocks are re-ordered each time a recipe is selected => the block receiving the recipe becomes the first master block

choosing best block match evaluates the tier of the matching resources => use highest tier in priority
	=> unfortunately, water has a high tier because it is produced late?? -> but maybe it's a good thing, who knows
	=> also, it is highly improbable that the water block will be mixed with any other since it is used everywhere
	=> but how can we make it so that water recipes don't go into the water block because of the "high tier" :/
	
	
-> sort blocks based on their first recipe using the same algo
-> don't do the pivot thingy
-> consider tier of resource for block best match
```

```
go through recipes in order, add the sequence of the recipe creating an ingredient for the first time and don't update it again
```

```
issue when choosing block => available_resources from the block is used as a criterion, but preferably we would like to only consider outputs
	=> that itself will also be an issue for byproducts
=> add notion of MINOR and MAJOR output for a recipe
	-> solo = major
	-> multi => major is the highest tier resource produced, others are minor
	-> when choosing a block, prefer a major output over a minor one
	
-> debug is at pure quartz recipe

=> either:
	don't count minor OUT at all => not good
	
	
model default: available resource means that it will match a recipe using that resource, even if the available resource is not enough to fill the demand
	=> either: wait the full result before ordering, and consider quantities

either: split minor and major
	-> len(major_match) > len(minor_match) > major_match_tier > minor_match_tier > block index
	=> more major match but less match overall => better pick
	=> same major match but less match overall => minor match wins
	=> same major match same minor match => take best major_match tier
	=> 
	
	
=> create a block named after "fluids" section at the highest index with all outputs/inputs from fluids ?
=> it will be greedy for recipes since it potentially will have a lot of matches
=> if I don't do that, recipes will randomly be assigned
	=> I have to do that
	
TODO now: -> logic to grep recipes fully used in fluids section
=> maybe it would have been better to create one block per OUT ingredient instead of one giga-block for the entire fluid section ?
=> this will let more opportunities to create sub-blocks
	=> sub-blocks will be more linked to each other
=> definitely better

-> some recipes can be extracted directly from that result
	-> not perfect, because aluminum ingots still chose to build other things from that block
-> blocks can be simplified (remove base resources)


How to grep: ALL IN are in the "fluids" section => take ALL OUT remaining recipes in the global pool and continue phase1 and phase2 on fluids => this is phase3 actually :)
	-> only issue is that this time, we match on inputs of a block based on outputs of a recipe (reverse)
		-> so actually it isn't phase1 and phase2
		-> extra phase
		
		

change display to use blocks, maybe sort blocks ?


TODO NEXT -> use that order for recipes, and display blocks in the google sheet
-> once the result is out:
	-> allocate blocks by volume (split and combine blocks)
	-> custom compute buses:
		- special buses format for fluids (horizontal)
		- special buses format between volumes (vertical)
```

```
new algo:
sections should be blocks too, they should each have a pool
-> sub-blocks have the same pool as their parent ? => maybe not needed

-> compute the best recipes per section with a new sorting algo using results data
	-> then run the previous algo inside a block to join similar ingredients together

fluids exception:
	-> identify all fluid recipes first and put them in the fluids section -> no volume constraint
	-> run a custom algorithm to grep recipes from the main pool, to minimise total amount of belts connection to the outside
	-> no need for backtracking algo anymore, everything is decided before the existing algo runs
```

```
todo in order:
- define expression of block volumes and expression ->
	-> volume of a floor: big pyramid - small pyramid
	
	1: 28 - 21 (approx)
	2: 21 - 14
	3: 14 - 0
	4: 22 - 15
	5: 15 - 8
	output: 8 - 0 (irrelevant)
	fluids: inf
	
1-2, 1-5 | 2-3 2-1 | 3-4 3-2 | 4-3 | 5-6 5-1 | 6-output 6-5 | output-fluids output-6 | fluids-output


need to keep track of which lane is used and from where it came from
	-> meaning that we should also choose lanes that are closer first and then others
		=> self.lanes already exist => create a function which will weight all lanes accordingly
		
get_lanes computation must be complexified

-> get_recipe_effect can get the list of all sections having something to contribute
	-> therefore it is easy to get the distance compared to the current section using the dijkstra result
	-> recipe.lanes["+"] is weighted as from the current floor
	-> recipe.lanes["-"] must be related to an existing lane["+"] which will be taken into account in the residual amount of lanes ?
	=> therefore counting lanes is done at the same time as counting resources
	=> we are also not really counting "lanes", but a score now
```

```
each section knows its external lanes individually, but some external lanes can be recombined with external lanes of neighbours, etc
-> external lanes is a useless metric, because it could have to be split between every path depending on the situation

I actually need assignations for every quantity, and that would also help the better recipe algo

=> if possible, take a resource from the closest section which provides any amount
=> if possible, provide a resource to the closest section which needs any amount

=> register these quantities along paths
=> paths DO NOT merge + and - quantities
=> what if a later better provider appear ? => assignations would have to be "simplified"

=> do assignations at the end of the algo instead, once every recipe was allocated

=> for each known resource:
	- identify the smallest + -> fully consume it in the closest - and continue until fully exhausted
		- identify the next smallest - -> fully consume 
		=> fill paths with all these interactions
			-> for the path natural direction, use the alphabetical order, then alter signs relative to that
	=> once all paths are filled => convert to lanes (orientation => depends on name)
	
```

```
32 max lanes at once :D
-> define heuristic to populate belts

-> start with fluids actually

=> ideal situation would be unwrapping:
	-> circular = onion
	-> lanes stack = "turn right"

=> separate "IN" and "OUT" busses ? -> I have enough lanes for that
```

