import csv
import numpy as np
from scipy.optimize import nnls
from ordered_set import OrderedSet
# from functools import reduce
from models.building import Building
from models.recipe import Recipe
from models.google_sheet import GoogleSheet

FLUIDS = {
    "dark matter residue",
    "excited photonic matter",
    "ionized fuel",
    "nitrogen gas",
    "rocket fuel",
    "alumina solution",
    "crude oil",
    "fuel",
    "heavy oil residue",
    "liquid biofuel",
    "nitric acid",
    "sulfuric acid",
    "turbofuel",
    "water",
}

class Block:
    def __init__(self, solver, recipe_key):
        self.containers = OrderedSet([recipe_key])
        self.solver = solver
        self.IN = set()
        recipe = solver.recipes[recipe_key]
        for resource in recipe.resource["-"]:
            self.IN.add(resource)
        self.OUT = {}
        for resource in recipe.resources["+"]:
            self.OUT[resource] = self.compute_out(resource)

    def compute_out(self, resource):
        ext_recipes = set(self.solver.used_recipes.keys()) - set(self.ordered_recipes_list())
        count = 0
        for recipe_key in ext_recipes:
            recipe = self.solver.recipes[recipe_key]
            if resource in recipe.resources["-"]:
                count += 1
        return count

    def ordered_recipes_list(self):
        recipes = []
        containersStack = [{"pool": self.containers, "index": 0}]
        container = containersStack[-1]
        while container:
            while container["index"] < len(container["pool"]):
                item = container["pool"][container["index"]]
                if isinstance(item, str):
                    container["index"] += 1
                    recipes.append(item)
                    if container["index"] == len(container["pool"]):
                        containersStack.pop()
                        if len(containersStack) > 0:
                            container = containersStack[-1]
                        else:
                            container = None
                elif isinstance(item, Block):
                    container["index"] += 1
                    if container["index"] == len(container["pool"]):
                        containersStack.pop()
                    containersStack.append({"pool": item.containers, "index": 0})
                    container = containersStack[-1]
                else:
                    raise Exception("container can only be a recipe or a block")
        return recipes
class Solver:
    def __init__(self):
        self.RED = "\033[31m"
        self.GREEN = "\033[32m"
        self.RESET = "\033[0m"
        self.buildings, self.recipes = self.parse()
        (
            self.output, self.power, self.resources, self.used_recipes
        ) = self.read_instructions()
        self.A, self.A_def, self.B, self.B_def, self.X = self.solve()

    def parse(self):
        buildings = {}
        recipes = {}

        # with open('data/recipes_formatted.csv', mode='w', newline='') as
        # csv_file:
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
            for resource in (
                set().union(recipe.resources["+"].keys(), recipe.resources["-"].keys())
            ):
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
    
    def working_here(self, recipes_sequence_map):
        def prepare_recipe_sets():
            fluid_recipes = set()
            for fluid in FLUIDS:
                fluid_recipes |= self.resources[fluid]["+"] | self.resources[fluid]["-"]
            return set(self.used_recipes.keys()) - fluid_recipes, fluid_recipes
        
        normal_pool, fluid_pool = prepare_recipe_sets()
        sections = {
            "fluids": {
                "pool": fluid_pool,
                "blocks": [],
            },
            "others": {
                "pool": normal_pool,
                "blocks": [],
            }
        }
        available_resources = set()
        resources_IN = {} # amount of recipes needing a specific resource as input
        current_resources_IN = {} # same as above, but will be reduced each time a recipe is elected
        for resource, data in self.resources:
            resources_IN[resource] = len(data["-"])
            current_resources_IN[resource] = len(data["-"])


        def construct_base_blocks(section):
            for recipe in section["pool"]:
                if len(self.recipes[recipe].resources["-"]) == 0:
                    for resource in self.recipes["+"]:
                        available_resources.add(resource)
                    section["blocks"].append(Block(self, recipe))
        def select_best_recipe(recipes):
            if len(recipes) == 0:
                return None
            def fully_consume_things(recipe):
                count = 0
                for resource in recipe.resources["-"]:
                    if current_resources_IN[resource] == 1:
                        count += 1
                    elif current_resources_IN[resource] < 1:
                        raise Exception("trying to consume more than exists")
                return count
            def used_to_create_things(recipe):
                count = 0
                for resource in recipe.resources["+"]:
                    count += resources_IN[resource]
                return count
            def created_using_things(recipe):
                return len(recipe.resources["-"])
            def get_tier(recipe):
                return recipes_sequence_map[recipe.key]
            def key(val):
                # fully consume X things (high) (=> no more recipe in either batch or target)
                    # overall => compute all IN for every used resource => associate to a counter -> if that counter is at 1 => this matches
                    # uses current_resources_IN
                # used to create X things (low) (count for each output the amount of global recipes using that output and sum)
                    # uses recipe["+"] and resources_IN
                # created using X things (high) (count ingredients)
                    # uses recipes["-"]
                # have the highest sequence in recipes_sequences
                    # uses recipes_sequence_map
                # alphabetical order
                return (
                    -fully_consume_things(val),
                    used_to_create_things(val),
                    -created_using_things(val),
                    -get_tier(val),
                    val.key
                )
            recipes = list(recipes)
            recipes.sort(key=key)
            return recipes[0]
            
    
        construct_base_blocks(sections["fluids"])
        # phase 1:
            # take recipes with all available ingredients
            # independent from blocks
            # will be associated with a block later (define criterion)
            # update IN and OUT values according to ingredients used in the new recipe
        def phase1(section):
            batch = set()
            for recipe_key in section["pool"]:
                recipe = self.recipes[recipe_key]
                if all(resource in available_resources for resource in recipe.resources["-"]):
                    batch.add(recipe)
            if len(batch) == 0:
                return None
            recipe = select_best_recipe(batch)
            # associate with the best matching block

        # phase 2:
        def phase2():
            # identify recipes using OUT resources per megablock
            # identify RESOURCE fully used per megablock in these recipes
            # add a sub-block creating that resource, and recursively fill it in reverse using phase2 then phase3 for each ingredient
            # no matter if there are multiples of such ingredients (but then the recipe should have a less good score)
            # runs once per megablock, take the best recipe per megablock, then the best recipe across all megablocks
            # => that megablock advances
            batch = {}
            return batch

        # phase 3:
            # identify recipes using OUT resources for all megablocks
            # sort recipes by amount of missing ingredients
            # only consider recipes with the lowest amount
            # take most needed RESOURCE for recipes with the lowest amount of missing ingredients
            # consider that RESOURCE available, and add it as IN for each megablock needing it
        def phase3():
            return
                
                

        # iteration:
            # take feasible recipes
                # directly feasible
                # add fully used resources to the mix (and create block in current block ? => yes)
                # add non-fully used resources to available options (and create block in others ? => no)
            # sort recipes by criterion
                # fully consume X things (high) (=> no more recipe in either batch or target)
                # used to create X things (low) (count for each output the amount of global recipes using that output and sum)
                # created using X things (high) (count ingredients)
                # have the highest sequence in recipes_sequences
                # alphabetical order
            # add best recipe to its block
                # merge blocks, update IN and OUT recursively, ...
            # go again

        


        construct_base_blocks(sections["others"])
        return None

    def compute_sequences(self):
        batch = {}  # searching for recipes using these resources
        resources = {}  # sequence for each resource name
        recipes = {}  # sequence for each recipe name
        for resource, data in self.resources.items():
            # resources[resource] = 1  # default sequence
            if len(data["+"]) == 0:
                print(f"missing {self.RED}{resource}{self.RESET} ?")
                batch[resource] = set()  # empty recipe set since that resource is not produced in these instructions
        for recipe, data in self.used_recipes.items():
            recipes[recipe] = 1  # default sequence
            if len(data.resources["-"]) == 0:
                for resource in data.resources["+"]:
                    batch.setdefault(resource, set())
                    batch[resource].add(recipe)  # recipe was used because no ingredient were required
        sequence = 2
        while len(batch) > 0:
            new_batch = {}
            for recipe, data in self.used_recipes.items():
                # multiple ingredients of the same recipe can link to it at the same step
                recipe_links = set()
                for ingredient in data.resources["-"]:
                    if ingredient in batch.keys():
                        key = f"{recipe}$$${ingredient}"
                        # this is the cycle protection, if a recipe was already there because of the same
                        # ingredient, it is not considered again.
                        if key not in batch[ingredient]:
                            # register all links related to this recipe
                            recipe_links = recipe_links | batch[ingredient]
                            recipe_links.add(key)
                if len(recipe_links) > 0:
                    recipes[recipe] = sequence
                    for ingredient in data.resources["+"]:
                        # resources[ingredient] = sequence  # only update sequence for a newly acquired resource
                        new_batch.setdefault(ingredient, set())
                        new_batch[ingredient] = new_batch[ingredient] | recipe_links
            sequence += 1
            batch = new_batch

        def order_by_sequence(sequence_map):
            ordered = list(sequence_map.keys())

            def key(val):
                # reverse sequence order > alphabetical order
                return (-sequence_map[val], val)
            ordered.sort(key=key)
            return ordered
        
        ordered_recipes = order_by_sequence(recipes)
        for recipe_key in list(reversed(ordered_recipes)):
            recipe = self.recipes[recipe_key]
            sequence = recipes[recipe_key]
            for resource in recipe.resources["+"]:
                if resource not in resources:
                    resources[resource] = sequence
        ordered_resources = order_by_sequence(resources)

        # TODO: working here
        # self.working_here(recipes)

        return ordered_recipes, ordered_resources

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
                B.append(self.output[resource])  # [self.output[resource]]
            else:
                B.append(0)  # [0]
            B_def.add(resource)  # add resource in sequence order
            vector = [0] * len(A_def)
            for sign in ['+', '-']:
                for recipe in data[sign]:
                    index = A_def.index(recipe)
                    vector[index] += (
                        self.recipes[recipe].resources[sign][resource] * self.recipes[recipe].consumption_ratio()
                    )
            A.append(vector)
        return A, A_def, B, B_def

    def solve(self):
        A, A_def, B, B_def = self.compute_matrices()
        A = np.array(A)
        B = np.array(B)
        X = nnls(A, B)  # np.linalg.lstsq(A, B, rcond=None)
        return A, A_def, B, B_def, X


solution = Solver()
gs = GoogleSheet(solution)
