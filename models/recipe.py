import math

MARGIN = 1 / 120000
class Recipe:
    def __init__(self, data):
        '''
        self.resources["+"|"-"][resource_key] = ratio/min for the recipe
        self.power = overwritten consumption or building power
        self.efficiency = percentage of recipe ratio
        '''
        self.resources = data["resources"]
        self.building = data["building"]
        self.power = float(data["power"]) if data["power"] else self.building.power
        self.efficiency = 100
        self.key = data["key"]
        self.coefficient = 1.321928
        self.lanes = {"+": {}, "-": {}}  # amount of belts for each resource for this recipe
        self.ratio = 0
        self.virtual_height = 7 * 4

    def compute_result(self, ratio, metadata):
        self.ratio = ratio
        self.lanes = {"+": {}, "-": {}}
        for sign in ["+", "-"]:
            for resource in self.resources[sign]:
                size = metadata["pipe"] if resource in metadata["FLUIDS"] else metadata["belt"]
                self.lanes[sign][resource] = ratio * abs(self.resources[sign][resource]) / size

    def compute_virtual_volume(self):
        return (
            int(round(self.building.dimensions.visual_width))
            * int(round(self.building.dimensions.visual_length))
            * int(math.ceil(self.ratio - MARGIN))
            * int(round(self.virtual_height))
        )

    def scaled_power(self):
        if not self.building or not self.power:
            return 0
        if (self.power >= 0):
            return self.power * (self.efficiency / 100)
        else:
            return self.power * (self.efficiency / 100) ** (1 / self.coefficient)

    def consumption_ratio(self):
        if not self.building or self.power <= 0:
            return self.efficiency / 100

    def max_output_resources(self, resources_sequence_map):
        max_resource_sequence = 0
        for resource in self.resources["+"]:
            sequence = resources_sequence_map[resource]
            if sequence > max_resource_sequence:
                max_resource_sequence = sequence
        resources = set()
        for resource in self.resources["+"]:
            if resources_sequence_map[resource] == max_resource_sequence:
                resources.add(resource)
        return resources
