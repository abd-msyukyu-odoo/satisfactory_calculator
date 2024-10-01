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
        self.output, self.power, self.resources = self.read_instructions()
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

        def register_recipe(recipe):
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
        if not len(resources):
            for recipe in self.recipes.values():
                register_recipe(recipe)

        return output, power, resources

    def compute_matrices(self):
        A = []
        A_def = OrderedSet()
        B = []
        B_def = OrderedSet()
        for resource, data in self.resources.items():
            if resource not in self.output and not (len(data["+"]) and len(data["-"])):
                continue
            for recipe in set().union(data["+"], data["-"]):
                A_def.add(recipe)
        for resource, data in self.resources.items():
            if resource not in self.output and not (len(data["+"]) and len(data['-'])):
                continue
            elif resource in self.output:
                B.append(self.output[resource]) # [self.output[resource]]
            else:
                B.append(0) # [0]
            B_def.add(resource)
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
