import csv
import numpy as np
from scipy.optimize import nnls
from ordered_set import OrderedSet
# from functools import reduce
from models.building import Building
from models.recipe import Recipe
from models.google_sheet import GoogleSheet

class Solver:
    def __init__(self):
        self.buildings, self.recipes = self.parse()
        self.output, self.power, self.resources, self.used_recipes = self.read_instructions()
        self.A, self.A_def, self.B, self.B_def, self.X = self.solve()

    def parse(self):
        buildings = {}
        recipes = {}

        # with open('data/recipes_formatted.csv', mode='w', newline='') as csv_file:
        # 	csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        # 	csv_writer.writeheader()
        # 	for row in rows:
        # 		csv_writer.writerow(row)

        with open('data/buildings.csv', mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            # fieldsname = csv_reader.fieldsnames
            for row in csv_reader:
                buildings[row["key"]] = Building(row)

        with open('data/recipes.csv', mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                duration = float(row["duration"])
                resources = {"+": {}, "-": {}}
                for i in range(1, 7):
                    if not row["resource" + str(i)]:
                        continue
                    quantity = float(row["quantity" + str(i)])
                    if quantity > 0:
                        resources["+"][row["resource" + str(i)]] = quantity / duration * 60
                    else:
                        resources["-"][row["resource" + str(i)]] = quantity / duration * 60
                row["resources"] = resources
                row["building"] = buildings[row["building"]]
                recipes[row["key"]] = Recipe(row)

        return buildings, recipes

    def read_instructions(self):
        '''
        resources[resource_key][+ | -] = recipe_key which has [+ | -] resource in it
        power = recipe_key which has a positive power output
        output = resource_key which is the desired output
        '''
        resources = {}
        power = set()
        output = {}
        used_recipes = {}

        def register_recipe(recipe):
            used_recipes[recipe.key] = recipe
            if recipe.building.power > 0:
                power.add(recipe.key)
            for resource in set().union(recipe.resources["+"].keys(), recipe.resources["-"].keys()):
                if resource not in resources:
                    resources[resource] = {"+": set(), "-": set()}
                if resource in recipe.resources["+"]:
                    resources[resource]["+"].add(recipe.key)
                if resource in recipe.resources["-"]:
                    resources[resource]["-"].add(recipe.key)

        with open('data/instructions.csv', mode='r') as csv_file:
            def cmd_out(argument):
                nonlocal output
                argument = argument.split('#')
                output[argument[0]] = float(argument[1])
            def cmd_recipe(argument):
                recipe = self.recipes[argument]
                register_recipe(recipe)
            cmd = {
                "out": cmd_out,
                "r": cmd_recipe,
            }
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                cmd[row["command"]](row["argument"])
        if len(resources) == 0:
            for recipe in self.recipes.values():
                register_recipe(recipe)

        return output, power, resources, used_recipes

    def compute_sequences(self):
        observed = set()  # prevent cycles
        batch = set()  # searching for recipes using these resources
        resources = {}  # sequence for each resource name
        recipes = {}  # sequence for each recipe name
        unproduced = set()  # every un-produced resource
        for resource, data in self.resources.items():
            resources[resource] = 1  # default sequence
            if len(data["+"]) == 0:
                unproduced.add(resource)
        for recipe, data in self.used_recipes.items():
            recipes[recipe] = 1  # default sequence
            if len(data.resources["-"]) == 0:
                batch = batch.union(data.resources["+"])
        batch = batch.union(unproduced)
        sequence = 2
        while len(batch) > 0:
            new_batch = set()
            for recipe, data in self.used_recipes.items():
                match = False
                for ingredient in data.resources["-"]:
                    if ingredient in batch:
                        match = True
                if match:
                    recipes[recipe] = sequence
                    for ingredient in data.resources["+"]:
                        resources[ingredient] = sequence
                        new_batch.add(ingredient)  # TODO this is vulnerable to cycles (infinite loop)
                        # for each recipe, register a recipe sequence, each resource in a batch should have a
                        # set of sequences of recipes (they are coming from)
                        # issue: we will now re-observe motor from rotors, but anything found from that will probably be already be found so nothing will come of it
                        # but this means that recipes which are made from motor should all have their sequence updated too, so actually they SHOULD be re-evaluated
                        # should actually keep a dict => recipes found from set of resources
                        # if a recipe (the same) is found from another resource, the products of that recipe get a green flag (and so-on to reevaluate everything with a greater sequence)
                        # meaning we should go over every found recipe, and remove the products of that recipe which was found because of something else
                        # meaning that when we find recipes through that product afterwards, they will be under the impression that they found a new producer and it will propagate
                        # this still protects against cycles, because 
            sequence += 1
            batch = new_batch
        def order_by_sequence(sequence_map):
            ordered = list(sequence_map.keys())
            def key(val):
                # reverse sequence order > alphabetical order
                return (-sequence_map[val], val)
            ordered.sort(key=key)
            return ordered
        return order_by_sequence(recipes), order_by_sequence(resources)

    def compute_matrices(self):
        ordered_recipes, ordered_resources = self.compute_sequences()
        A = []
        A_def = OrderedSet()
        B = []
        B_def = OrderedSet()
        allowedRecipes = set()
        # filter used recipes
        for resource, data in self.resources.items():
            if resource not in self.output and not (len(data["+"]) and len(data["-"])):
                continue
            for recipe in set().union(data["+"], data["-"]):
                allowedRecipes.add(recipe)
        for recipe in ordered_recipes:
            if recipe in allowedRecipes:
                A_def.add(recipe)  # add recipe definition in sequence order
        for resource in ordered_resources:
            data = self.resources[resource]
            if resource not in self.output and not (len(data["+"]) and len(data['-'])):
                continue
            elif resource in self.output:
                B.append(self.output[resource]) # [self.output[resource]]
            else:
                B.append(0) # [0]
            B_def.add(resource)  # add resource in sequence order
            vector = [0] * len(A_def)
            for sign in ['+', '-']:
                for recipe in data[sign]:
                    index = A_def.index(recipe)
                    vector[index] += self.recipes[recipe].resources[sign][resource] * self.recipes[recipe].consumption_ratio()
            A.append(vector)
        return A, A_def, B, B_def

    def solve(self):
        A, A_def, B, B_def = self.compute_matrices()
        A = np.array(A)
        B = np.array(B)
        X = nnls(A, B) # np.linalg.lstsq(A, B, rcond=None)
        return A, A_def, B, B_def, X

solution = Solver()
gs = GoogleSheet(solution)
