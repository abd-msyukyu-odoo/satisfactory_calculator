from base import dimensions


class Building:
    def __init__(self, data):
        self.dimensions = dimensions.Dimensions(
            float(data["w"]), float(data["l"]), float(data["h"]), float(data["vh"])
        )
        self.power = float(data["power"])
        self.key = data["key"]
