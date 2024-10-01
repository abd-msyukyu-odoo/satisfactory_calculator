

class Recipe:
    def __init__(self, data):
        '''
        self.resources[resource_key] = ratio/min for the recipe
        self.power = overwritten consumption or building power
        self.efficiency = percentage of recipe ratio
        '''
        self.resources = data["resources"]
        self.building = data["building"]
        self.power = float(data["power"]) if data["power"] else self.building.power
        self.efficiency = 100
        self.key = data["key"]
        self.coefficient = 1.321928

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
