```
(fuel burn time) = (initial fuel burn time) x (clock speed / 100) ^ (-1 / 1.3)

x/60 = 1/t

t = 60/x
x = 60/t
60 / [(60/(initial consumption rate)) * (clock speed / 100) ^ (-1 / 1.3)] = prod/min
= (initial consumption rate) / [(clock speed / 100) ^ (-1 / 1.3)] = prod/min

600 = 300 / (2.5) ^ (-1 / x)
2.5 ^ (-1 / x) = 1 / 2
log(1/2) = log(2.5 ^ (-1/x))
log(1/2) = (-1/x)*log(2.5)
x = -1 * log(2.5)/log(1/2)


https://satisfactory.gamepedia.com/Special:CargoQuery

recipeName=recipeName,craftedIn=craftedIn,crafting_recipes.craftingTime,product=product,productCount=productCount,product2=product2,productCount2=productCount2,ingredient1=ingredient1,quantity1=quantity1,ingredient2=ingredient2,quantity2=quantity2,ingredient3=ingredient3,quantity3=quantity3,ingredient4=ingredient4,quantity4=quantity4

_pageName=Page,product=product,experimental=experimental,unreleased=unreleased,alternateRecipe=alternateRecipe,mainRecipe=mainRecipe,recipeName=recipeName,craftedIn=craftedIn,inCraftBench=inCraftBench,inWorkShop=inWorkShop,productCount=productCount,productsPerMinute=productsPerMinute,product2=product2,productCount2=productCount2,productsPerMinute2=productsPerMinute2,product3=product3,productCount3=productCount3,productsPerMinute3=productsPerMinute3,product4=product4,productCount4=productCount4,productsPerMinute4=productsPerMinute4,quantity1=quantity1,ingredient1=ingredient1,quantity2=quantity2,ingredient2=ingredient2,quantity3=quantity3,ingredient3=ingredient3,quantity4=quantity4,ingredient4=ingredient4,quantity5=quantity5,ingredient5=ingredient5,quantity6=quantity6,ingredient6=ingredient6,quantity7=quantity7,ingredient7=ingredient7,quantity8=quantity8,ingredient8=ingredient8,quantity9=quantity9,ingredient9=ingredient9,quantity10=quantity10,ingredient10=ingredient10


experimental IS NOT NULL
AND craftedIn != "Build Gun"
AND craftedIn != "Equipment Workshop"
And unreleased = False
```



### Réflexion résolution des séquences de recettes

mode de base :

* hypothèse : une seule recette par résultat -> à généraliser pour de multiples recettes

* prendre la recette de la resource résultat
* ensuite, dans l'ordre, prendre les recettes impliquant les autres resources de la première recette
  -> pile de "resources" à traiter
  -> nécessite un dictionnaire resource -> recettes (liste)
* on annule la composante négative d'une recette en créant un coefficient pour la composante positive d'une autre recette

* à résoudre : comment faire le choix quand on a plusieurs recettes qui offrent une composante positive
  -> méthode du "reste" : on privilégie les recettes à une seule composante positive d'abord, on résout le plus possible. Si on a du utiliser une recette à double sortie, on la fixe et on essaye de la résoudre avec une autre recette à une composante
  -> dans le cas où on a une sortie double et une sortie simple, essayer de séparer les 2 valeurs en simulant un ingrédient différent (isolation du circuit, pour "assoiffer" la composante générée intérieurement)
* à résoudre : cas où plusieurs solutions sont possibles -> créer des embranchements pour chaque solution, avec chaque fois le focus sur "une recette" puis fallback sur les autres
* à résoudre : comment reconnaitre le "byproduct" du "product" d'une recette : le product ne peut être créé qu'à partir de cette recette, et le byproduct possède une autre source potentielle. Si les deux sont obtensibles autrement, créer un embranchement pour prioritiser l'un, puis l'autre.
* nécessite : dupliquer une recette
* méthode de comparaison des solutions -> supprimer les solutions identiques



structure de l'algo : 

#### parsing instructions

ingrédient à produire (aucun => énergie)
"keys" des recettes disponibles pour le calcul (aucune => toutes)

#### mise en place

création de l'arbre d'ordre d'ingredients. chaque ramification de l'arbre sera un arbre de recettes

pour chaque ingrédient, création de l'arbre d'ordre de recettes. chaque ramificaiton de l'arbre sera un résultat de calcul

un parent contient une liste de ses enfants, un enfant connait sont parent

#### résultat

pour chaque recette on a une liste de coefficients :

* coefficient principal (peut être bloqué)
* séquence de coefficients secondaires isolés (vidange)

pour chaque ingrédient, on a une ~~liste~~ de production/consommation -> uniquement le bilan, les résultats intermédiaires peuvent être calculés à partir des coefficients :

* bilan global (positif pour les outputs, négatif pour les inputs, nul pour les valeurs intermédiaires)
* pour chaque coefficient de recette, bilan pour la resource -> pas besoin d'être stocké -> peut être calculé facilement (normalement)

bilan du parent donne les directives pour les enfants



resolution du système sans les vidanges. Pour avoir le ratio vidange/source normale => calculer la contribution interne de toutes les machines produisant la resource dans des recettes à sorties multiples, et soustraire au résultat









un coefficient par recette suffit -> repartition entre les differentes vidanges => a partir de resources, les coefficients de toutes les recettes positives sauf la "principale"

decomposition en ingredients / produits pour permettre des doublons : produits identiques aux reactifs





```
AX = B
10_9 * 9_1 = 10_1

A^-1 * A * X = A^-1 * B
9_10 * 10_9 * 9_1 = 9_10 * 10_1
9_9 * 9_1 = 9_1
```

