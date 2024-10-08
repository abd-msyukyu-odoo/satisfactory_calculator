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
next step: 
```





```
pyramide: combien d'etages, quelle largeur par etage

=> tour centrale de circulation de ressources (+ escalier autour)
=> ressources de base puis on monte ?
```

#### floor 1 (11x11 121)

| recipe             | building    | amount               |
| ------------------ | ----------- | -------------------- |
| solid steel ingot  | foundry     | 19                   |
| concrete           | constructor | 12                   |
| copper alloy ingot | foundry     | 3                    |
| iron alloy ingot   | foundry     | 16 (50) (102 blocks) |

#### floor 2 (9x9 81)

| recipe           | building    | amount              |
| ---------------- | ----------- | ------------------- |
| steel beam       | constructor | 14                  |
| steel cast plate | foundry     | 4                   |
| steel rod        | constructor | 1                   |
| copper sheet     | constructor | 14 (33) (45 blocks) |

#### floor 3 (9x9 81)

| recipe     | building    | amount             |
| ---------- | ----------- | ------------------ |
| iron wire  | constructor | 28                 |
| steel pipe | constructor | 9 (37) (47 blocks) |

#### floor 4 (9x9 81)

| recipe              | building    | amount             |
| ------------------- | ----------- | ------------------ |
| stator              | assembler   | 7                  |
| steel screw         | constructor | 4                  |
| stitched iron plate | assembler   | 8                  |
| cable               | constructor | 1 (20) (43 blocks) |

#### floor 5 (9x9 81)

| recipe                  | building  | amount             |
| ----------------------- | --------- | ------------------ |
| automated wiring        | assembler | 1                  |
| copper rotor            | assembler | 5                  |
| steeled frame           | assembler | 5                  |
| encased industrial beam | assembler | 4 (15) (40 blocks) |

#### floor 6 (7x7 49)

| recipe              | building  | amount            |
| ------------------- | --------- | ----------------- |
| motor               | assembler | 2                 |
| smart plating       | assembler | 5                 |
| versatile framework | assembler | 2 (9) (31 blocks) |

height: 6x6 36 (36x4 -> 144x88x88)
test phone
