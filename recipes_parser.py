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

class Inventory:
    def __init__(self, solver, resources_sequence_map):
        self.resources_sequence_map = resources_sequence_map
        self.solver = solver
        self.OUT = {}
        self.IN = {}
        self.T_OUT = {}
        self.T_IN = {}
        self.available_resources = set()
        self.external_resources = set()
        self.pool = set(solver.used_recipes.keys())
        self.fill_inventory()

    def fill_inventory(self):
        for resource, data in self.solver.resources.items():
            self.T_OUT[resource] = len(data["+"])
            self.OUT[resource] = len(data["+"])
            self.T_IN[resource] = len(data["-"]) # amount of recipes needing a specific resource as input
            self.IN[resource] = len(data["-"]) # same as above, but will be reduced each time a recipe is elected

class Block:
    def __init__(self, solver, inventory):
        self.containers = OrderedSet()
        self.solver = solver
        self.inventory = inventory
        self.IN = {}
        self.MINOR_OUT = {}
        self.MAJOR_OUT = {}
        # self.available_resources = set()

    def add_recipe(self, recipe):
        for resource in recipe.resources["-"]:
            self.IN.setdefault(resource, 0)
            self.IN[resource] += 1
            self.inventory.IN[resource] -= 1
            if self.inventory.IN[resource] < 0:
                raise Exception("global current resources in is negative")
        max_resource_sequence = 0
        for resource in recipe.resources["+"]:
            sequence = self.inventory.resources_sequence_map[resource]
            if sequence > max_resource_sequence:
                max_resource_sequence = sequence
        for resource in recipe.resources["+"]:
            sequence = self.inventory.resources_sequence_map[resource]
            target = self.MINOR_OUT
            if sequence == max_resource_sequence:
                target = self.MAJOR_OUT
            target.setdefault(resource, 0)
            target[resource] += 1
            self.inventory.OUT[resource] -= 1
            if self.inventory.OUT[resource] < 0:
                raise Exception("global current resources out is negative")
        # self.available_resources |= set(recipe.resources["+"].keys()) | set(recipe.resources["-"].keys())
        self.inventory.available_resources |= set(recipe.resources["+"].keys())
        self.inventory.external_resources -= set(recipe.resources["+"].keys())
        self.containers.add(recipe.key)

    def add_block(self, block, as_container=True):
        for resource in block.IN:
            self.IN.setdefault(resource, 0)
            self.IN[resource] += 1
        for resource in block.MINOR_OUT:
            self.MINOR_OUT.setdefault(resource, 0)
            self.MINOR_OUT[resource] += 1
        for resource in block.MAJOR_OUT:
            self.MAJOR_OUT.setdefault(resource, 0)
            self.MAJOR_OUT[resource] += 1
        # self.available_resources |= block.available_resources
        if as_container:
            self.containers.add(block)

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

    def working_here(self, recipes_sequence_map, resources_sequence_map):
        def prepare_recipe_sets():
            fluid_recipes = set()
            for fluid in FLUIDS:
                if fluid in self.resources:
                    fluid_recipes |= self.resources[fluid]["+"] | self.resources[fluid]["-"]
            return set(self.used_recipes.keys()) - fluid_recipes, fluid_recipes

        def sort_recipes(recipes):
            if len(recipes) == 0:
                return []
            def fully_consume_things(recipe):
                count = 0
                for resource in recipe.resources["-"]:
                    if inventory.IN[resource] == 1:
                        count += 1
                    elif inventory.IN[resource] < 1:
                        raise Exception("trying to consume more than exists")
                return count
            def used_to_create_things(recipe):
                count = 0
                for resource in recipe.resources["+"]:
                    count += inventory.T_IN[resource]
                return count
            def created_using_things(recipe):
                return len(recipe.resources["-"])
            def get_tier(recipe):
                return recipes_sequence_map[recipe.key]
            def key(val):
                # fully consume X things (high) (=> no more recipe in either batch or target)
                    # overall => compute all IN for every used resource => associate to a counter -> if that counter is at 1 => this matches
                    # uses inventory.IN
                # used to create X things (low) (count for each output the amount of global recipes using that output and sum)
                    # uses recipe["+"] and inventory.T_IN
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
            return recipes

        def construct_base_blocks(section):
            recipes = []
            for recipe in section["pool"]:
                if len(self.recipes[recipe].resources["-"]) == 0:
                    for resource in self.recipes[recipe].resources["+"]:
                        inventory.available_resources.add(resource)
                    recipes.append(self.recipes[recipe])
            recipes = sort_recipes(recipes)
            for recipe in recipes:
                section["pool"].remove(recipe.key)
                inventory.pool.remove(recipe.key)
                block = Block(self, inventory)
                block.add_recipe(recipe)
                section["blocks"].append(block)

        def find_best_block(section, recipe, reverse = False):
            # associate with the best matching block
            # iterate over blocks
            # check number of matches (consumed vs available_resources in a block)
            # highest number of matches, then highest tiered matches, then order of block (highest tiered block)
            # major matches are considered before minor matches
            result = []
            idx = 0
            for block in section["blocks"]:
                # match = block.available_resources & set(recipe.resources["-"].keys())
                ingredients = set(recipe.resources["+" if reverse else "-"].keys())
                major_match = set(block.MAJOR_OUT.keys()) & ingredients
                full_match = (set(block.MAJOR_OUT.keys()) | set(block.MINOR_OUT.keys()) | set(block.IN.keys())) & ingredients
                # minor_match = (set(block.MINOR_OUT.keys()) & ingredients) - major_match
                result.append({
                    "major_match": major_match,
                    # "minor_match": minor_match,
                    "full_match": full_match,
                    "index": idx,
                })
                idx += 1
            def match_tier(match):
                match = list(match)
                match.sort(key=lambda val: -resources_sequence_map[val])
                return tuple(map(lambda val: -resources_sequence_map[val], match))
            def key(val):
                return (
                    (
                        -len(val["major_match"]),
                        -len(val["full_match"]),
                        # -len(val["minor_match"])
                    )
                    + match_tier(val["full_match"])
                    # + match_tier(val["major_match"])
                    # + match_tier(val["minor_match"])
                    + (val["index"],)
                )
            result.sort(key=key)
            block = section["blocks"][result[0]["index"]]
            return block

        # phase 1:
            # take recipes with all available ingredients
            # independent from blocks
            # will be associated with a block later (define criterion)
            # update IN and OUT values according to ingredients used in the new recipe
        def phase1(section, reverse = False):
            batch = set()
            for recipe_key in section["pool"]:
                recipe = self.recipes[recipe_key]
                if all(resource in inventory.available_resources for resource in recipe.resources["-"]):
                    batch.add(recipe)
            if len(batch) == 0:
                return None
            recipe = sort_recipes(batch)[0]
            block = find_best_block(section, recipe, reverse)
            # add recipe to block:
                # update IN, OUT, global current IN, global available_resources, block available_resources
            block.add_recipe(recipe)
            section["pool"].remove(recipe.key)
            inventory.pool.remove(recipe.key)
            # TODO ABD: niche optimization, skipping for now:
            # evaluate all fully consumed resources in the block
                # => block.IN[resource] == inventory.IN[resource]
            # search for each of such resource if another block fully outputs a subset of fully consumed resources
                # => block.OUT[resource] == inventory.OUT[resource], and all OUT keys are included in IN keys prio
            return recipe.key

        # phase 2:
            # same as phase1, but allowing X missing ingredients
            # make missing ingredient become available and add it to IN
            # will allow to create canisters in the end because packaged water will be made available
            # => unlock fuel
            # => unlock canister
            # => unlocks packaged water in reverse

            # identify recipes using OUT resources for all megablocks
            # sort recipes by amount of missing ingredients
            # only consider recipes with the lowest amount
            # take most needed RESOURCE for recipes with the lowest amount of missing ingredients
            # consider that RESOURCE available, and add it as IN for each megablock needing it
        def phase2(section):
            for i in range(1, 5):
                batch = {}
                for recipe_key in section["pool"]:
                    recipe = self.recipes[recipe_key]
                    missing = set()
                    for resource in recipe.resources["-"]:
                        if resource not in inventory.available_resources:
                            missing.add(resource)
                    if len(missing) == i:
                        batch[recipe_key] = missing
                if len(batch) == 0:
                    continue
                handled_recipes = set()
                aggregate = []
                pairs = list(batch.items())
                max_aggregate = 0
                for i, (recipe_key, missing) in enumerate(pairs):
                    recipes = set()
                    if recipe_key in handled_recipes:
                        continue
                    recipes.add(recipe_key)
                    handled_recipes.add(recipe_key)
                    for (recipe_key2, missing2) in pairs[i + 1:]:
                        if recipe_key2 in handled_recipes:
                            continue
                        if missing == missing2:
                            recipes.add(recipe_key2)
                            handled_recipes.add(recipe_key2)
                    aggregate.append(recipes)
                    max_aggregate = max(max_aggregate, len(recipes))
                aggregate = list(filter(lambda recipes: len(recipes) == max_aggregate, aggregate))
                # pick the best combination of missing ingredients
                # can mix the recipes and use the previous algo to choose the best recipe
                # or sort resources by descending tiers, and choose the combination with the lowest
                # first tier => create a more basic object first => potentially do more things
                def key(val):
                    missing = batch[list(val)[0]]
                    missing = list(missing)
                    missing.sort(key=lambda res: -resources_sequence_map[res])
                    return tuple(map(lambda res: resources_sequence_map[res], missing))
                aggregate.sort(key=key)
                # identify the most needed resources package
                # only keep recipes using these resources
                recipes_keys = aggregate[0] # best recipes to choose from
                # then, sort recipes like before
                # only difference is that these resources should be added as IN as well
                # and they should be added to a temporary inventory
                # temporary inventory should be emptied once a recipe outputs the resource afterwards
                recipe = sort_recipes(set(map(lambda recipe_key: self.recipes[recipe_key], recipes_keys)))[0]
                # block = find_best_block(section, recipe) # not needed to handle a block => will be done in phase1
                missing = batch[recipe.key]
                inventory.available_resources |= missing
                inventory.external_resources |= missing
                return recipe.key
            return None
        
        def phase3(section):
            for external_resource in inventory.external_resources:
                in_count = 0
                for block in section["blocks"]:
                    in_count += block.IN.get(external_resource) or 0
                if inventory.T_IN[external_resource] == in_count:
                    recipes = self.resources[external_resource]["+"] & inventory.pool
                    section["pool"] |= recipes


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
        inventory = Inventory(self, resources_sequence_map)

        construct_base_blocks(sections["fluids"])
        reverse = False
        while len(sections["fluids"]["pool"]) > 0:
            if phase1(sections["fluids"], reverse):
                if len(sections["fluids"]["pool"]) == 0:
                    reverse = True
                    phase3(sections["fluids"]) # phase3 could also be done right after phase2
                                               # but then reverse mode would have to be stored in another way
                continue
            elif phase2(sections["fluids"]):
                continue
            else:
                raise Exception("Unable to use a recipe in fluids")

        # TODO recursively add fully used resources in the fluids section
        # search for resources fully used in the fluids section
        # import all recipes creating these resources
            # do the same recursively for their ingredients until
                # they are not fully used (=> just inputs, phase2)
                # they are fully used (=> import recipe in the same block, repeat for ingredients)
        # eliminate resources added through phase2 from inventory.available_resources
        inventory.available_resources -= inventory.external_resources
        inventory.external_resources = set()

        sections["others"]["pool"] &= inventory.pool # some recipes could have ben extracted in reverse by fluids section
        construct_base_blocks(sections["others"])
        # create OUT set for the fluid section
        # create a block for each OUT
        fluid_resources = set()
        for block in sections["fluids"]["blocks"]:
            fluid_resources |= set(block.MAJOR_OUT.keys()) | set(block.MINOR_OUT.keys())
        fluid_resources -= FLUIDS
        for fluid_resource in fluid_resources:
            block = Block(self, inventory)
            block.MAJOR_OUT[fluid_resource] = 1
            sections["others"]["blocks"].append(block)

        # fluid_block = Block(self, inventory)
        # for block in sections["fluids"]["blocks"]:
        #     fluid_block.add_block(block, as_container=False)
        # sections["others"]["blocks"].append(fluid_block)
        while len(sections["others"]["pool"]):
            if phase1(sections["others"]):
                continue
            elif phase2(sections["others"]):
                continue
            else:
                raise Exception("Unable to use a recipe in others")
        blocks = []
        for block in sections["others"]["blocks"]:
            if len(block.containers) > 0:
                blocks.append(block)
        sections["others"]["blocks"] = blocks
        # TODO return ordered recipes following blocks
        return None

    def compute_sequences(self):
        batch = {}  # searching for recipes using these resources
        resources = {}  # sequence for each resource name
        recipes = {}  # sequence for each recipe name
        for resource, data in self.resources.items():
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
        self.working_here(recipes, resources)

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
