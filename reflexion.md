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

