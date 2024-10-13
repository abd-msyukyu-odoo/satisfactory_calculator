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
