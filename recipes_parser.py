import csv
import numpy as np
import math
from scipy.optimize import nnls
from scipy.sparse.csgraph import dijkstra
from ordered_set import OrderedSet
# from functools import reduce
from models.building import Building
from models.recipe import Recipe, MARGIN
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

CONTRARY = {
    "+": "-",
    "-": "+",
    "0": "1",
    "1": "0",
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

class Path:
    def __init__(self, sections):
        def key(val):
            return (val,)
        self._sections = tuple(sorted(sections, key=key))
        self.state = {}
        self.lanes = {"+": {}, "-": {}}
        self.lanes_count = 0
        self.layers = {}

    @property
    def sections(self):
        return self._sections

    def __str__(self):
        return '#'.join(self.sections)

    def __eq__(self, other):
        if isinstance(other, Path):
            return str(self) == str(other)
        return False

    def __hash__(self):
        return hash(str(self))

class Section:
    def __init__(self, name, solver, inventory):
        self.name = name
        self.inventory = inventory
        self.solver = solver
        self.blocks = []
        self.full_pool = set()
        self.pool = set()
        self.volume = float('inf')
        self.paths = {}
        self.lanes = {"+": {}, "-": {}}
        self.resources = {"+": OrderedSet(), "-": OrderedSet(), "pool": OrderedSet()}
        # TODO ABD consider OUT command (for extra bins)
        # use belts format (to be defined)

    def add_recipe(self, recipe_key):
        recipe = self.solver.recipes[recipe_key]
        self.pool.add(recipe_key)
        self.full_pool.add(recipe_key)
        self.inventory.pool.remove(recipe_key)
        for sign in ["+", "-"]:
            for resource, quantity in recipe.lanes[sign].items():
                self.lanes[sign].setdefault(resource, 0)
                self.lanes[sign][resource] += quantity

    def compute_current_volume(self):
        volume = 0
        for recipe_key in self.full_pool:
            recipe = self.solver.recipes[recipe_key]
            volume += recipe.compute_virtual_volume()
        return volume

    def compute_state(self):
        resources = {}
        for resource in (set(self.lanes["+"].keys()) | set(self.lanes["-"].keys())):
            resources[resource] = 0
        for resource, quantity in self.lanes["+"].items():
            resources[resource] += quantity
        for resource, quantity in self.lanes["-"].items():
            resources[resource] -= quantity
        def null_equivalent(value):
            return (
                (value == 0)
                or (value < 0 and value > 0 - MARGIN)
                or (value > 0 and value < 0 + MARGIN)
            )
        resources = {resource: quantity for resource, quantity in resources.items() if not null_equivalent(quantity)}
        return resources

    @staticmethod
    def get_lanes(resources):
        external_lanes = {"+": {}, "-": {}}
        lanes = 0
        for resource, quantity in resources.items():
            if quantity < 0 - MARGIN:
                amount = math.ceil(abs(quantity) - MARGIN)
                lanes += amount
                external_lanes["-"][resource] = amount
            elif quantity > 0 + MARGIN:
                amount = math.ceil(quantity - MARGIN)
                lanes += amount
                external_lanes["+"][resource] = amount
        return lanes, external_lanes

    @staticmethod
    def combine_states(resources1, resources2):
        resources = {}
        keys1 = set(resources1.keys())
        keys2 = set(resources2.keys())
        for key in keys1 | keys2:
            resources[key] = resources1.get(key, 0) + resources2.get(key, 0)
        return resources

    def get_external_lanes(self):
        return Section.get_lanes(self.compute_state())

    def get_recipe_effect(self, recipe_key, distance_data=None):
        # TODO issue: each section state is evaluated as if untouched by other section states
        # maybe a section usage of another should be reflected in that other section so that
        # when it is reused, it is not re-used for the same things ? maybe it's a non-issue
        def get_sections(distance):
            if not distance_data:
                return [], 0
            index = distance_data["name_to_index"][self.name]
            max_distance = 0
            sections = []
            for name, section in distance_data["sections"].items():
                sub_index = distance_data["name_to_index"][name]
                cur_dist = distance_data["distances"][index][sub_index]
                if distance == cur_dist:
                    sections.append(section)
                if cur_dist > max_distance:
                    max_distance = cur_dist
            return sections, max_distance
        resources = self.compute_state()
        sections, _ = get_sections(1) # max_distance
        for section in sections:
            state = section.compute_state()
            resources = Section.combine_states(resources, state)
        lanes_before, _ = Section.get_lanes(resources)
        recipe = self.solver.recipes[recipe_key]
        # delta = 0
        for resource, quantity in recipe.lanes["+"].items():
            resources.setdefault(resource, 0)
            # TODO commented code is wrong, delete it, do better algo (below)
            # if quantity + resources[resource] > MARGIN:
            #     original_lanes_count = math.ceil(abs(resources[resource]) - MARGIN)
            #     exchange_value = resources[resource] + quantity
            #     current = exchange_value
            #     intermediate_value = 0
            #     for i in range(2, max_distance):
            #         sections, _ = get_sections(i)
            #         for section in sections:
            #             state = section.compute_state()
            #             state_qty = state.get(resource, 0)
            #             if state_qty + MARGIN < 0:
            #                 iter_qty = min(quantity - intermediate_value, abs(state_qty))
            #                 current -= iter_qty
            #                 intermediate_value += iter_qty
            #             if current - MARGIN < resources[resource]:
            #                 break
            #         boosted_lanes_count = math.ceil(abs(current - intermediate_value) - MARGIN)

            resources[resource] += quantity
            # same logic as below, reversed, if there are consumptions at a certain floor
            # add that consumption to resources, and register a penalty depending on the
            # distance
        for resource, quantity in recipe.lanes["-"].items():
            resources.setdefault(resource, 0)
            # TODO commented code is wrong, delete it, do better algo (below)
            # if resources[resource] + MARGIN < quantity:
            #     original_lanes_count = math.ceil(abs(resources[resource]) - MARGIN)
            #     exchange_value = resources[resource] - quantity
            #     current = exchange_value
            #     intermediate_value = 0
            #     # cost of the recipe, is to bring back enough belts
            #     # to recover the resources[resource] state
            #     # taking into acount that existing belts can be filled to the max
            #     for i in range(2, max_distance):
            #         sections, _ = get_sections(i)
            #         for section in sections:
            #             state = section.compute_state()
            #             state_qty = state.get(resource, 0)
            #             if state_qty - MARGIN > 0:
            #                 iter_qty = min(quantity - intermediate_value, state_qty)
            #                 current += iter_qty
            #                 intermediate_value += iter_qty
            #             if current + MARGIN > resources[resource]:
            #                 break
            #         boosted_lanes_count = math.ceil(abs(resources[resource] + intermediate_value) - MARGIN)
            #         # TODO READ THIS
            #         # being able to bring belts from a distance should reduce the impact of
            #         # having to bring these belts without knowing where they are ???
            #         # this will incentivize to use already known ingredients :/
            #         # actually isn't that enough to only consider "sibling" provisions as a priority ?
            #         # when going away from a source, it is interesting to offer the boost
            #         # when going towards it is not.
            #         delta -= (boosted_lanes_count - original_lanes_count) * (1 - 1 / i)
            #         original_lanes_count = boosted_lanes_count
            #         if current + MARGIN > resources[resource]:
            #             break
            resources[resource] -= quantity
            
            
            # better algo:
            #   each prod at each level has multiple assignation slots
            #   state in that section is updated once a prod is consumed for
            #   somewhere (i.e. amount - floor+ -> floor-)
            # assignations are combined to the internal state of a section
            # assignations will deplete a state until it is fully resolved
            # assignations can be combined together on each path to check
            # the belts attribution (assignations of the same item on one path
            # can be combined to minimize amount of belts)
            # ??? TODO

                    
            # here we should check all neighbours in order of distance
            # and compute a correction factor which will represent
            # the distance penalty for choosing that neighbour
            # no neighbour found => no correction penalty 
            # all provided by current section or a direct neighbour
            # => no correction penalty
            # distance 2+: ceil amount of belts rated as a penalty of the distance,
            # every time the amount of belts increase at a further distance, add the
            # new belt with the penalty of that distance
            # lanes_after should be increased by the distance penalty
            # lanes_after can be computed the same as before, once every neighbours
            # only selected resources for the current recipe are shared on the current floor
            # resources are shared on the current floor, and increased by the penalty
            # lanes_before should stay the same 
        lanes_after, _ = Section.get_lanes(resources)
        return lanes_before - lanes_after

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
        max_output_resources = recipe.max_output_resources(self.inventory.resources_sequence_map)
        for resource in recipe.resources["+"]:
            target = self.MINOR_OUT
            if resource in max_output_resources:
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

    # TODO dead code ?
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
            self.output, self.power, self.resources, self.used_recipes, self.paths, self.volumes, self.assignations
        ) = self.read_instructions()
        self.A, self.A_def, self.B, self.B_def, self.X = self.solve()
        self.assign_recipe_results()
        self.working_here()

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
        paths = {}
        volumes = {}
        assignations = {}

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
                
        def register_transport_sizes(belt, pipe):
            self.belt = belt
            self.pipe = pipe

        def register_path(key1, key2):
            paths.setdefault(key1, set())
            paths.setdefault(key2, set())
            paths[key1].add(key2)
            paths[key2].add(key1)

        with open('data/instructions.csv', mode='r') as csv_file:
            def cmd_out(argument):
                nonlocal output
                argument = argument.split('#')
                output[argument[0]] = float(argument[1])

            def cmd_recipe(argument):
                recipe = self.recipes[argument]
                register_recipe(recipe)

            def cmd_transport_sizes(argument):
                argument = argument.split("#")
                register_transport_sizes(int(argument[0]), int(argument[1]))

            def cmd_sections(argument):
                argument = argument.split("#")
                for section in argument[1:]:
                    register_path(argument[0], section)

            def cmd_volumes(argument):
                nonlocal volumes
                argument = argument.split("#")
                volumes[argument[0]] = float(argument[1])

            def cmd_assignations(argument):
                nonlocal assignations
                argument = argument.split("#")
                for assignation in argument[1:]:
                    assignations.setdefault(argument[0], set())
                    assignations[argument[0]].add(assignation)

            cmd = {
                "a": cmd_assignations,
                "out": cmd_out,
                "r": cmd_recipe,
                "s": cmd_sections,
                "t": cmd_transport_sizes,
                "v": cmd_volumes,
            }
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                cmd[row["command"]](row["argument"])
        if len(resources) == 0:
            for recipe in self.recipes.values():
                register_recipe(recipe)

        return output, power, resources, used_recipes, paths, volumes, assignations

    def assign_recipe_results(self):
        for i, recipe_key in enumerate(self.A_def):
            recipe = self.recipes[recipe_key]
            ratio = self.X[0][i]
            metadata = {
                "FLUIDS": FLUIDS,
                "belt": self.belt,
                "pipe": self.pipe,
            }
            recipe.compute_result(ratio, metadata)

    def working_here(self):
        recipes_sequence_map = self.recipes_rank
        resources_sequence_map = self.resources_rank
        def create_sections():
            sections = {}
            for section in self.paths:
                sections[section] = Section(section, self, inventory)
            for recipe in prepare_fluids_pool():
                sections["fluids"].add_recipe(recipe)
            for key, assignation in self.assignations.items():
                for recipe_key in assignation:
                    sections[key].add_recipe(recipe_key)
            for recipe_key in set(inventory.pool):
                if len(self.recipes[recipe_key].resources["-"]) == 0:
                    sections["in"].add_recipe(recipe_key)
            for key, volume in self.volumes.items():
                sections[key].volume = volume
            paths = {}
            for key, links in self.paths.items():
                for section in links:
                    path = Path([key, section])
                    name = str(path)
                    if name in paths:
                        path = paths[name]
                    paths[name] = path
                    sections[key].paths[name] = path
                    sections[section].paths[name] = path
            self.path_objs = paths
            output_keys = list(self.output.keys())
            output_keys.sort(key=lambda val: (resources_sequence_map[val], val))
            for key in output_keys:
                output = self.output[key]
                size = self.pipe if key in FLUIDS else self.belt
                sections["out"].lanes["-"][key] = abs(output) / size
                sections["out"].resources["-"].add(key)
                sections["out"].resources["pool"].add(key)
            construct_base_blocks(sections["fluids"])
            construct_base_blocks(sections["in"])
            return sections

        def prepare_fluids_pool():
            fluid_recipes = set()
            for fluid in FLUIDS:
                if fluid in self.resources:
                    fluid_recipes |= self.resources[fluid]["+"] | self.resources[fluid]["-"]
            return fluid_recipes

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
            for recipe in section.pool:
                if len(self.recipes[recipe].resources["-"]) == 0:
                    for resource in self.recipes[recipe].resources["+"]:
                        inventory.available_resources.add(resource)
                    recipes.append(self.recipes[recipe])
            recipes = sort_recipes(recipes)
            for recipe in recipes:
                section.pool.remove(recipe.key)
                # inventory.pool.remove(recipe.key)
                block = Block(self, inventory)
                block.add_recipe(recipe)
                section.blocks.append(block)

        def find_best_block(section, recipe, reverse = False):
            # associate with the best matching block
            # iterate over blocks
            # check number of matches (consumed vs available_resources in a block)
            # highest number of matches, then highest tiered matches, then order of block (highest tiered block)
            # major matches are considered before minor matches
            result = []
            idx = 0
            for block in section.blocks:
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
            block = section.blocks[result[0]["index"]]
            return block

        # phase 1:
            # take recipes with all available ingredients
            # independent from blocks
            # will be associated with a block later (define criterion)
            # update IN and OUT values according to ingredients used in the new recipe
        def phase1(section, reverse = False):
            batch = set()
            for recipe_key in section.pool:
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
            section.pool.remove(recipe.key)
            # inventory.pool.remove(recipe.key)
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
                for recipe_key in section.pool:
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

        def optimize_fluid_section(section):
            # filter recipes that produce at least one ingredient that is
            # consumed in the section
            batch = set()
            consumed = set(section.lanes["-"].keys())
            for recipe_key in section.inventory.pool:
                recipe = self.recipes[recipe_key]
                for resource in recipe.resources["+"]:
                    if resource in consumed:
                        batch.add(recipe.key)
                        break
            if len(batch) == 0:
                return False
            # iterate over recipes which fully produce what's needed for a resource or less
            enclosed_recipes = set()
            for recipe_key in batch:
                recipe = self.recipes[recipe_key]
                max_output_resources = recipe.max_output_resources(inventory.resources_sequence_map)
                for resource in max_output_resources:
                    if resource not in consumed:
                        continue
                    size = self.pipe if resource in FLUIDS else self.belt
                    output = self.output.get(resource, 0) / size
                    if recipe.lanes["+"][resource] <= section.lanes["-"][resource] + MARGIN + output:
                        enclosed_recipes.add(recipe.key)
            if len(enclosed_recipes) != 0:
                for recipe_key in enclosed_recipes:
                    section.add_recipe(recipe_key)
                # return to get other enclosed_recipes
                return True
            recipes = list(filter(lambda recipe: section.get_recipe_effect(recipe) > 0, batch))
            if len(recipes) != 0:
                for recipe_key in recipes:
                    section.add_recipe(recipe_key)
                return True
            return False

        def optimize_volume_section(section, distance_data):
            batch = list(filter(lambda recipe_key: (
                self.recipes[recipe_key].compute_virtual_volume()
                + section.compute_current_volume()
                <= section.volume
            ), inventory.pool))
            if len(batch) == 0:
                return False
            def key(recipe_key):
                recipe = self.recipes[recipe_key]
                def used_to_create_things(recipe):
                    count = 0
                    for resource in recipe.resources["+"]:
                        count += inventory.T_IN[resource]
                    return count
                def get_tier(recipe):
                    return recipes_sequence_map[recipe.key]
                return (-section.get_recipe_effect(recipe_key, distance_data), used_to_create_things(recipe), -get_tier(recipe), recipe_key)
            batch.sort(key=key)
            recipe_key = batch[0]
            section.add_recipe(recipe_key)
            return True


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

        inventory = Inventory(self, resources_sequence_map)

        sections = create_sections()

        # First phase: grep recipes and minimize path encumbrance for fluids
            # => path encumbrance is already known from the current pool of recipes
            # => should search for "best recipe" with an algo limiting resources on a path
            # think about combining "remain" belts from other sections => should continue until they are fully
            # used
        while optimize_fluid_section(sections["fluids"]):
            continue

        while len(sections["fluids"].pool) > 0:
            if phase1(sections["fluids"]):
                continue
            elif phase2(sections["fluids"]):
                continue
            else:
                raise Exception("Unable to use a recipe in fluids")

        path = list(set(self.volumes.keys()) - set(["in"]))
        path.sort()
        path = ["in"] + path

        section_names = list(self.paths.keys())
        section_names.sort()
        section_names = OrderedSet(section_names)
        section_path_graph = []
        for name1 in section_names:
            distances = []
            for name2 in section_names:
                if name2 in self.paths[name1] and name2 != name1:
                    distances.append(1)
                else:
                    distances.append(0)
            section_path_graph.append(distances)
        name_to_index = {}
        for i, name in enumerate(section_names):
            name_to_index[name] = i
        distances, predecessors = dijkstra(section_path_graph, directed=False, return_predecessors=True)
        distance_data = {
            "distances": distances,
            "predecessors": predecessors,
            "name_to_index": name_to_index,
            "index_to_name": section_names,
            "sections": sections,
        }


        # TODO ABD: consider states of other sections when choosing recipes for
        # one section => weight distance for accessibility
        # having the neighbour providing lanes should be taken into consideration
        # when consuming lanes => compute a neighbour lanes state
        # get_recipe_effect should take into account the "neighbour lanes state"
        # incorporate weights into the formula so that taking a resource from a far
        # neighbour is more expensive, but still better than taking a lane that is not
        # already present at all (scale lanes at lanes/distance ?)
        # provide an array of states to `get_recipe_effect`, all states have a distance
        # metadata to scale them => need dijkstra => will change which recipe is chosen
        # => will fully consider direct neighbour lanes as its own => +++ better results

        # fill sections with recipes
        for section_key in path:
            section = sections[section_key]
            inventory.available_resources -= inventory.external_resources
            inventory.external_resources = set()
            section_resources = set()
            for block in section.blocks:
                section_resources |= set(block.MAJOR_OUT.keys())
            available_resources = list(inventory.available_resources - section_resources - FLUIDS)
            available_resources.sort(key=lambda val: resources_sequence_map[val])
            for resource in available_resources:
                block = Block(self, inventory)
                block.MAJOR_OUT[resource] = 1
                section.blocks.append(block)
            while optimize_volume_section(section, distance_data):
                continue
            while len(section.pool) > 0:
                if phase1(section):
                    continue
                elif phase2(section):
                    continue
                else:
                    raise Exception("Unable to use a recipe in volume section")
            blocks = []
            for block in section.blocks:
                if len(block.containers) > 0:
                    blocks.append(block)
            section.blocks = blocks
        if len(inventory.pool):
            raise Exception("inventory pool is not empty, missing recipes")
        # define ordering of ingredients for each section
        for section in sections.values():
            for block in section.blocks:
                for recipe_key in block.containers:
                    recipe = self.recipes[recipe_key]
                    for sign in ["-", "+"]:
                        for resource in recipe.resources[sign].keys():
                            section.resources["pool"].add(resource)
                            section.resources[sign].add(resource)
        # fill paths with resources
        states = {}
        for name, section in sections.items():
            states[name] = section.compute_state()
        for name, state in states.items():
            index = distance_data["name_to_index"][name]
            for resource, quantity in state.items():
                if quantity == 0:
                    continue
                targets = {}
                for key, target in states.items():
                    if key == name:
                        continue
                    if quantity * target.get(resource, 0) < 0:
                        targets[key] = target
                distances = []
                for key, target in targets.items():
                    sub_index = distance_data["name_to_index"][key]
                    dist = distance_data["distances"][index][sub_index]
                    name_path = [name]
                    path_objs = []
                    current = name
                    while current != key:
                        prev = current
                        idx = distance_data["name_to_index"][current]
                        cur_idx = distance_data["predecessors"][sub_index][idx]
                        current = distance_data["index_to_name"][cur_idx]
                        path = Path([prev, current])
                        path = self.path_objs[str(path)]
                        name_path.append(current)
                        path_objs.append(path)
                    distances.append({
                        "section_name": name,
                        "target_name": key,
                        "distance": dist,
                        "name_path": name_path,
                        "path_objs": path_objs,
                    })
                def sort_dist(val):
                    return (val["distance"], val["target_name"])
                distances.sort(key=sort_dist)
                for dist in distances:
                    val1 = states[dist["section_name"]][resource]
                    val2 = states[dist["target_name"]][resource]
                    transport = min(abs(val1), abs(val2))
                    sign = -1 if val1 < 0 else 1
                    for i, path_obj in enumerate(dist["path_objs"]):
                        subsign = sign
                        if str(path_obj).split("#", maxsplit=1)[0] != dist["name_path"][i]:
                            subsign *= -1
                        path_obj.state.setdefault(resource, 0)
                        path_obj.state[resource] += subsign * transport
                    sign = -1 if val2 < 0 else 1
                    states[dist["target_name"]][resource] = sign * (abs(val2) - transport)
                    if (abs(states[dist["target_name"]][resource]) - MARGIN < 0):
                        states[dist["target_name"]][resource] = 0
                    sign = -1 if val1 < 0 else 1
                    states[dist["section_name"]][resource] = sign * (abs(val1) - transport)
                    if (abs(states[dist["section_name"]][resource]) - MARGIN < 0):
                        states[dist["section_name"]][resource] = 0
                        break
                    # identify transport value (= min abs() of both values)
                    # identify sign (from first name_path to last name_path, *-1 if
                    # first name is negative, *-1 if a path_obj key is not in the
                    # order of name_path, apply resource on each path in path_objs (should be a state)
                    # min value is set to zero, max value is reduced of min value in each state
                    # => each path should be filled with a full state
                    # => can get lanes for each path afterwards
                    # => just need to ordinate them
        # group path resources by layer (a layer contain the resources needed for the sections connected by
        # the path), next layer contains resources needed at a distance away relative to the layer level
        for path_obj in self.path_objs.values():
            path_obj.lanes_count, path_obj.lanes = Section.get_lanes(path_obj.state)
        for path in self.path_objs.values():
            path.layers["1"] = {"+": {}, "-": {}, "resources": {"+": OrderedSet(), "-": OrderedSet()}}
            path.layers["pool"] = {"+": {}, "-": {}}
            section1 = sections[path.sections[0]]
            section2 = sections[path.sections[1]]
            _, lanes1 = section1.get_external_lanes()
            _, lanes2 = section2.get_external_lanes()
            for sign in ["+", "-"]:
                path_resources = set(path.lanes[sign].keys())
                resources1 = path_resources & set(lanes1[sign].keys())
                order1 = section1.resources[sign] & resources1
                resources2 = path_resources & set(lanes2[CONTRARY[sign]].keys())
                order2 = section2.resources[CONTRARY[sign]] & resources2
                # TODO remove exception, was just for debugging
                if order2 != resources2 or order1 != resources1:
                    raise Exception("error in reasoning, order should always be equal to resources (1)")
                orders = {section1.name: order1, section2.name: order2}
                names = section_names & set(orders.keys())
                final_order = OrderedSet()
                for name in names:
                    final_order |= orders[name]
                path.layers["1"]["resources"][sign] = final_order
                resources = resources1 | resources2
                for resource in resources:
                    path.layers["1"][sign][resource] = path.lanes[sign][resource]
                resources = path_resources - resources
                for resource in resources:
                    path.layers["pool"][sign][resource] = path.lanes[sign][resource]
        for path in self.path_objs.values():
            paths = set([path])
            # key of directions is the index of the section in the next path that should
            # be the section registered in the list. if it is not, the path is reversed
            # compared to the main path direction
            directions = {"1": [sections[path.sections[0]]], "0": [sections[path.sections[1]]]}
            layer = 1
            while len(path.layers["pool"]["+"]) > 0 or len(path.layers["pool"]["-"]) > 0:
                layer += 1
                path.layers[str(layer)] = {"+": {}, "-": {}, "resources": {"+": OrderedSet(), "-": OrderedSet()}}
                # in each direction, search the sections for a path that is not yet known
                new_directions = {"1": [], "0": []}
                ordered_resources_by_section_name = {"+": {}, "-": {}}
                for index in ["0", "1"]:
                    for section in directions[index]:
                        for new_path in section.paths.values():
                            if new_path in paths:
                                continue
                            paths.add(new_path)
                            section_name = new_path.sections[int(index)]
                            contrary = section_name != section.name
                            if not contrary:
                                section_name = new_path.sections[int(CONTRARY[index])]
                            new_section = sections[section_name]
                            new_directions[index].append(new_section)
                            for sign in ["+", "-"]:
                                new_sign = CONTRARY[sign] if contrary else sign
                                # can get order from new_path here
                                # must associate section_name with new_path ordered resources for both signs
                                # at the end, for both sign, go through section names in order and aggregates resources
                                resources = set(path.layers["pool"][sign].keys()) & set(new_path.layers["1"][new_sign].keys())
                                order = new_path.layers["1"]["resources"][new_sign] & resources
                                if order != resources:
                                    raise Exception("error in reasoning, order should always be equal to resources (2)")
                                ordered_resources_by_section_name[sign][section_name] = order
                                for resource in resources:
                                    path.layers[str(layer)][sign][resource] = path.layers["pool"][sign][resource]
                                    del path.layers["pool"][sign][resource]
                for sign in ["+", "-"]:
                    names = section_names & set(ordered_resources_by_section_name[sign].keys())
                    final_order = OrderedSet()
                    for name in names:
                        final_order |= ordered_resources_by_section_name[sign][name]
                    path.layers[str(layer)]["resources"][sign] = final_order
                directions = new_directions
            del path.layers["pool"]
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

        self.recipes_rank = recipes
        self.resources_rank = resources

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
