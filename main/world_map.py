import json
import random

class WorldMap:
    def __init__(self):
        self.map = {}
        self.current_position = (0, 0)

    def get_or_create_location(self, x, y):
        position = (x, y)
        if position not in self.map:
            available_directions = random.sample(["N", "S", "E", "W"], k=random.randint(1, 4))
            self.map[position] = {
                "description": "This area hasn't been described yet.",
                "directions": available_directions,
                "color": "#FFFFFF"  # Default color
            }
        return self.map[position]

    def update_location(self, x, y, description, color=None):
        location = self.get_or_create_location(x, y)
        location["description"] = description
        if color:
            location["color"] = color

    def move(self, direction):
        current_location = self.get_or_create_location(*self.current_position)
        if direction not in current_location["directions"]:
            return False, f"You cannot move {direction} from here."
        moves = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}
        self.current_position = (
            self.current_position[0] + moves[direction][0],
            self.current_position[1] + moves[direction][1]
        )
        return True, self.get_current_description()

    def get_current_description(self):
        return self.get_or_create_location(*self.current_position)["description"]

    def get_current_color(self):
        return self.get_or_create_location(*self.current_position)["color"]

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
            self.get_or_create_location(0, 0)
