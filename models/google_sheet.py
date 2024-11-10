from collections import OrderedDict
import csv


class GoogleSheet:
    def __init__(self, solution):
        self.s = solution
        # count the amount of recipes and the amount of resources
        # as soon as an element gets its position, place it on the grid
        # => dimensions of the array are known
        # => create the scaler with formula (self dependent)
        # => create all columns with the display information of the scaler
        self.w = self.s.A.shape[0] + 5  # header - power - [resources] - solution - scaling - building/height
        self.h = 2 * self.s.A.shape[1] + 3  # header - [recipes] - total - contribution - [recipes]
        self.display, self.multiplier = self.generate_display()
        self.write_variable_headers()
        self.scaling = self.generate_data_scaler()
        self.generate_analysis()

        output = []
        for i in range(self.h):
            output.append([])
            for j in range(self.w):
                output[i].append(self.display[self.get_letter(j + 1)][i])
        with open('data/output.csv', mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file,  quoting=csv.QUOTE_ALL)
            for row in output:
                csv_writer.writerow(row)
        print("done")

    def generate_analysis(self):
        # generer "power" separement
        # copier tel quel "A" semble le plus rapide pour les recettes, pas la peine d'aller reformater le reste
        # dans display, recopier uniquement les valeurs non nulles
        # ingred -> [recipes] -> [positions] double dictionnaire par colonne
        # but => generer le calcul par excel pour le bilan et la contribution absolue negative, pas besoin de le faire
        # ici
        # seule la position nous intéresse une fois les données copiées correctement dans display
        for i in range(self.s.A.shape[0]):
            self.display[self.get_letter(i + 3)][self.s.A.shape[1] + 1] = "="
            self.display[self.get_letter(i + 3)][self.s.A.shape[1] + 2] = "=ABS("
            for j in range(self.s.A.shape[1]):
                if self.s.A[i, j]:
                    self.display[self.get_letter(i + 3)][j + 1] = "=" + str(self.s.A[i, j])
                    self.display[self.get_letter(i + 3)][self.s.A.shape[1] + 3 + j] = \
                        "=" + "$" + self.multiplier[0] + str(j + 2) \
                        + "*" \
                        + "$" + self.get_letter(i + 3) + str(j + 2)
                    if self.s.A[i, j] < 0:
                        self.display[self.get_letter(i + 3)][self.s.A.shape[1] + 2] += \
                            "+$" + self.get_letter(i + 3) + "$" + str(self.s.A.shape[1] + 4 + j)
                    self.display[self.get_letter(i + 3)][self.s.A.shape[1] + 1] += \
                        "+$" + self.get_letter(i + 3) + "$" + str(self.s.A.shape[1] + 4 + j)
            self.display[self.get_letter(i + 3)][self.s.A.shape[1] + 2] += ")"
        # power part yeah ok it's ugly but i'm tired
        self.display[self.get_letter(2)][self.s.A.shape[1] + 1] = "="
        self.display[self.get_letter(2)][self.s.A.shape[1] + 2] = "=ABS("
        for j in range(self.s.A.shape[1]):
            if self.s.recipes[self.s.A_def[j]].scaled_power():
                self.display[self.get_letter(2)][j + 1] = "=" + str(self.s.recipes[self.s.A_def[j]].scaled_power())
                self.display[self.get_letter(2)][self.s.A.shape[1] + 3 + j] = \
                    "=" + "$" + self.multiplier[0] + str(j + 2) \
                    + "*" \
                    + "$" + self.get_letter(2) + str(j + 2)
                if self.s.recipes[self.s.A_def[j]].scaled_power() < 0:
                    self.display[self.get_letter(2)][self.s.A.shape[1] + 2] += \
                        "+$" + self.get_letter(2) + "$" + str(self.s.A.shape[1] + 4 + j)
                self.display[self.get_letter(2)][self.s.A.shape[1] + 1] += \
                    "+$" + self.get_letter(2) + "$" + str(self.s.A.shape[1] + 4 + j)
        self.display[self.get_letter(2)][self.s.A.shape[1] + 2] += ")"
        # building part
        for j in range(self.s.A.shape[1]):
            recipe = self.s.recipes[self.s.A_def[j]]
            self.display[self.get_letter(self.s.A.shape[0] + 5)][j + 1] = recipe.building.key
            # surface
            self.display[self.get_letter(self.s.A.shape[0] + 3)][self.s.A.shape[1] + 3 + j] = \
                "=ROUNDUP(" + str(recipe.building.dimensions.visual_width * recipe.building.dimensions.visual_length) \
                + "*ROUNDUP(" \
                + "$" + self.get_letter(self.s.A.shape[0] + 3) + str(j + 2) + \
                ")/64)"
            # scaled surface
            self.display[self.get_letter(self.s.A.shape[0] + 4)][self.s.A.shape[1] + 3 + j] = \
                "=ROUNDUP(" + "$" + self.multiplier[0] + "$" + str(self.multiplier[1]) \
                + "*" + str(recipe.building.dimensions.visual_width * recipe.building.dimensions.visual_length) \
                + "*ROUNDUP(" + "$" + self.get_letter(self.s.A.shape[0] + 3) + str(j + 2) \
                + ")/64)"
            self.display[self.get_letter(self.s.A.shape[0] + 5)][self.s.A.shape[1] + 3 + j] = \
                "=ROUNDUP((" + str(recipe.building.dimensions.visual_height) + "+12)/4)"

    def generate_data_scaler(self):
        solution = OrderedDict()
        scaling = OrderedDict()
        i = 2
        for recipe in self.s.A_def:
            solution[recipe] = [self.get_letter(self.s.A.shape[0] + 3), i]
            scaling[recipe] = [self.get_letter(self.s.A.shape[0] + 4), i]
            self.display[solution[recipe][0]][i - 1] = "=" + str(self.s.X[0][i - 2])  # self.s.X[0][i - 2][0] (lstsq)
            self.display[scaling[recipe][0]][i - 1] = \
                "=" + "$" + self.multiplier[0] + "$" + str(self.multiplier[1]) \
                + "*" \
                + "$" + solution[recipe][0] + str(i)
            i += 1
        return scaling

    def generate_display(self):
        display = OrderedDict()
        for i in range(1, self.w + 1):
            display[self.get_letter(i)] = [""] * self.h
        display["A"][0] = "recipes/resources"
        display["A"][self.s.A.shape[1] + 1] = "total"
        display["A"][self.s.A.shape[1] + 2] = "contribution"
        display[self.get_letter(self.s.A.shape[0] + 3)][0] = "solution"
        display[self.get_letter(self.s.A.shape[0] + 4)][0] = "scaling"
        display[self.get_letter(self.s.A.shape[0] + 5)][0] = "buildings"
        display[self.get_letter(self.s.A.shape[0] + 3)][self.s.A.shape[1] + 1] = "multiplier"
        display[self.get_letter(self.s.A.shape[0] + 4)][self.s.A.shape[1] + 1] = "=1"
        display[self.get_letter(self.s.A.shape[0] + 3)][self.s.A.shape[1] + 2] = "area (blocks)"
        display[self.get_letter(self.s.A.shape[0] + 4)][self.s.A.shape[1] + 2] = "area (scaled)"
        display[self.get_letter(self.s.A.shape[0] + 5)][self.s.A.shape[1] + 2] = "height (blocks)"
        multiplier = [self.get_letter(self.s.A.shape[0] + 4), self.s.A.shape[1] + 2]
        return display, multiplier

    def write_variable_headers(self):
        self.display["B"][0] = "power"
        i = 3
        for resource in self.s.B_def:
            self.display[self.get_letter(i)][0] = resource
            i += 1
        i = 2
        for recipe in self.s.A_def:
            self.display["A"][i - 1] = recipe
            self.display["A"][len(self.s.A_def) + 1 + i] = recipe
            i += 1

    def get_letter(self, index):
        output = ""
        while index:
            index -= 1
            output = str(chr(ord("A") + index % 26)) + output
            index = index // 26
        return output
