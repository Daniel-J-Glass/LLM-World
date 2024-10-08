import json
import random

class WorldMap:
    def __init__(self):
        self.map = {}
        self.current_position = (0, 0)

    def get_or_create_location(self, x, y):
        position = (x, y)
        if position not in self.map:
            available_directions = ["N", "S", "E", "W"]
            self.map[position] = {
                "svg": None,
                "description": None,
                "directions": available_directions,
                "color": "#FFFFFF"  # Default color
            }
        return self.map[position]

    def update_location(self, x, y, svg, description, color=None):
        location = self.get_or_create_location(x, y)
        location["svg"] = svg
        location["description"] = description
        if color:
            location["color"] = color

    def move(self, direction):
        moves = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}
        self.current_position = (
            self.current_position[0] + moves[direction][0],
            self.current_position[1] + moves[direction][1]
        )
        return True, self.get_current_svg(), self.get_current_description()

    def get_current_svg(self):
        return self.get_or_create_location(*self.current_position).get("svg")

    def get_current_description(self):
        return self.get_or_create_location(*self.current_position).get("description")

    def get_location_color(self, x, y):
        return self.get_or_create_location(x, y)["color"]

    def get_available_directions(self):
        return self.get_or_create_location(*self.current_position)["directions"]

    def save_state(self):
        with open('world_map.json', 'w') as f:
            json.dump({"map": {str(k): v for k, v in self.map.items()}, "current_position": self.current_position}, f)

    def load_state(self):
        try:
            with open('world_map.json', 'r') as f:
                state = json.load(f)
            self.map = {eval(k): v for k, v in state["map"].items()}
            self.current_position = tuple(state["current_position"])
        except FileNotFoundError:
            print("Map not found.")
            self.get_or_create_location(0, 0)