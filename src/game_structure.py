import json
from utils.llm_utils import create_message_stream, update_chat_history, initialize_client
from utils.visual_utils import generate_svg_image
from src.world_map import WorldMap
import io
from PIL import Image
import base64

import config

import logging

class WorldState:
    def __init__(self):
        self.rules = {}
        self.events = []
        self.load_state()

    def load_state(self):
        try:
            with open('world_state.json', 'r') as f:
                data = json.load(f)
                self.rules = data.get('rules', {})
                self.events = data.get('events', [])
        except FileNotFoundError:
            pass  # Start with empty state if file doesn't exist

    def save_state(self):
        with open('world_state.json', 'w') as f:
            json.dump({'rules': self.rules, 'events': self.events}, f)

    def add_rule(self, rule_name, rule_description):
        self.rules[rule_name] = rule_description
        self.save_state()

    def add_event(self, event_description):
        self.events.append(event_description)
        self.save_state()

class Game:
    def __init__(self):
        self.engine_client = initialize_client(config.ENGINE_LLM_PROVIDER)
        self.visual_client = initialize_client(config.VISUAL_LLM_PROVIDER)
        self.world_map = WorldMap()
        self.world_state = WorldState()
        self.chat_history = []
        self.current_image = None
        self.current_svg = None
        self.load_state()

    def process_input(self, user_input):
        current_svg = self.world_map.get_current_svg()
        current_description = self.world_map.get_current_description()

        context = f"Current location SVG: {current_svg}\n"
        context += f"Current location description: {current_description}\n"
        context += f"Available directions: {', '.join(self.world_map.get_available_directions())}\n"
        context += f"Current world rules: {json.dumps(self.world_state.rules)}\n"
        context += f"Recent events: {json.dumps(self.world_state.events[-5:])}\n"
        context += f"Player action: {user_input}\n"
        context += config.GAME_ENGINE_SYSTEM_PROMPT

        self.chat_history = update_chat_history(self.chat_history, "user", user_input)
        
        print(self.chat_history)

        return create_message_stream(self.engine_client, system_prompt=context, chat_history=self.chat_history, tools=config.GAME_TOOLS, tools_choice=config.GAME_TOOL_CHOICE)
    
    def generate_first_person_visuals(self, user_input, scene_svg, scene_description):
        user_input = f"User input: {user_input}\n{config.SCENE_SVG_INPUT_NAME}: {scene_svg}\nScene description: {scene_description}\n"
        system_prompt = "Generate first-person visuals based on the user input, scene SVG, and scene description."

        chat_history = [
            {
                "role": "user",
                "content": user_input
            }
        ]
        print(user_input)
        visual_stream = create_message_stream(self.visual_client, chat_history=chat_history, system_prompt=system_prompt, tools=config.VISUAL_TOOLS, tools_choice=config.VISUAL_TOOL_CHOICE)

        try:
            for chunk in visual_stream:
                print(chunk)
                if isinstance(chunk, dict):
                    return chunk["visuals"]
        except Exception as e:
            print(e)
            print(json.dumps(chunk))

    def update_game_state(self, game_output):
        if not isinstance(game_output, dict):
            return

        movement = game_output.get('movement')
        narrative = game_output.get('narrative', '')
        print(game_output)

        svg = None
        description = None
        if movement and movement != "NONE":
            success, svg, description = self.world_map.move(movement)

        if 'scene' in game_output and not (svg and description):
            new_location = self.world_map.current_position
            tile_color = game_output['scene'].get('tile_color', '#FFFFFF')
            new_svg = game_output['scene'].get('scene_svg')
            new_description = game_output['scene'].get('scene_description')
            self.world_map.update_location(*new_location, new_svg, new_description, tile_color)

        svg = self.world_map.get_current_svg()
        description = self.world_map.get_current_description()
        user_input = self.chat_history[-1]['content'] if self.chat_history else ""

        visual_output = self.generate_first_person_visuals(user_input, svg, description)
        first_person_description = visual_output.get("first_person_description")
        first_person_svg = visual_output.get("first_person_svg")

        self.current_svg = first_person_svg # for dev ui display

        if first_person_description and first_person_svg:
            first_person_visual = config.FIRST_PERSON_MODIFIER.format(visual=first_person_description)
            try:
                image_bytes = generate_svg_image(positive_prompt=first_person_visual, svg=first_person_svg, negative_prompt=config.NEGATIVE_STYLE_MODIFIER, control_strength=config.SVG_IMAGE_CONTROL_STRENGTH)
                self.current_image = Image.open(io.BytesIO(image_bytes)) if image_bytes else None
            except Exception as e:
                print(f"Failed to generate image: {str(e)}")
                logging.error(f"Failed to generate image: {str(e)}")
                self.current_image = None

        for rule in game_output.get('rule_updates', []):
            self.world_state.add_rule(rule['rule_name'], rule['rule_description'])

        if 'events' in game_output:
            for event in game_output['events']:
                self.world_state.add_event(event)

        self.chat_history = update_chat_history(self.chat_history, "assistant", narrative)

        self.save_state()

    def save_state(self):
        self.world_map.save_state()
        self.world_state.save_state()
        
        # Save chat history and current image
        state = {
            'chat_history': self.chat_history
        }
        
        if self.current_image:
            buffered = io.BytesIO()
            self.current_image.save(buffered, format="PNG")
            state['current_image'] = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        with open('game_state.json', 'w') as f:
            json.dump(state, f)

    def load_state(self):
        self.world_map.load_state()
        self.world_state.load_state()
        
        try:
            with open('game_state.json', 'r') as f:
                state = json.load(f)
                self.chat_history = state.get('chat_history', [])
                
                if 'current_image' in state:
                    image_data = base64.b64decode(state['current_image'])
                    self.current_image = Image.open(io.BytesIO(image_data))
                else:
                    self.current_image = None
        except FileNotFoundError:
            print("File not found")
            # If the file doesn't exist, start with empty chat history and no image
            self.chat_history = []
            self.current_image = None

    def get_current_image(self):
        return self.current_image

    def get_minimap_data(self):
        minimap_data = []
        visited_positions = set()

        def dfs(x, y, distance):
            if distance <= 0:
                return

            visited_positions.add((x, y))
            minimap_data.append({
                'x': x,
                'y': y,
                'color': self.world_map.get_location_color(x, y)
            })

            for direction in self.world_map.get_available_directions():
                dx, dy = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}[direction]
                new_x, new_y = x + dx, y + dy
                if (new_x, new_y) not in visited_positions:
                    dfs(new_x, new_y, distance - 1)

        start_x, start_y = self.world_map.current_position
        dfs(start_x, start_y, 5)  # Explore up to a distance of 5 from the current position

        return {
            'minimap': minimap_data,
            'current_position': {'x': start_x, 'y': start_y}
        }
