import json
from utils.llm_utils import create_message_stream, update_chat_history
from utils.visual_utils import generate_image
from main.world_map import WorldMap
import io
from PIL import Image
import base64

import config

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
    def __init__(self, client):
        self.client = client
        self.world_map = WorldMap()
        self.world_state = WorldState()
        self.chat_history = []
        self.current_image = None
        self.load_state()

    def process_input(self, user_input):
        current_description = self.world_map.get_current_description()

        context = f"Current location: {current_description}\n"
        context += f"Available directions: {', '.join(self.world_map.get_available_directions())}\n"
        context += f"Current world rules: {json.dumps(self.world_state.rules)}\n"
        context += f"Recent events: {json.dumps(self.world_state.events[-5:])}\n"
        context += f"Player action: {user_input}\n"
        context += "Interpret the player's action, including any movement. If the player is trying to move, determine the direction (N, S, E, W) and include it in your response. If the action doesn't involve movement, set the movement to NONE. Then, describe the result of the player's action and the new surroundings if movement occurred. If this is a new or undescribed location, provide a scene description. Descriptions should be brief, but can be longer if the user looks around more. If any new rules are discovered or significant events occur, include them in your response. Make sure to include a first_person_scene description in the visuals for image generation."

        # Update chat history with user input
        self.chat_history = update_chat_history(self.chat_history, "user", user_input)
        
        return create_message_stream(self.client, system_prompt=context, chat_history=self.chat_history)

    def update_game_state(self, game_output):
        if not isinstance(game_output, dict):
            return  # Skip processing if game_output is not a dictionary

        movement = game_output.get('movement', 'NONE')
        visuals = game_output.get('visuals', {})
        narrative = game_output.get('narrative', '')
        print(game_output)

        # Generate first-person image
        first_person_scene = visuals.get('first_person_scene', '')
        if first_person_scene:
            visual = config.FIRST_PERSON_MODIFIER.format(visual=first_person_scene)
            image_bytes = generate_image(visual)
            self.current_image = Image.open(io.BytesIO(image_bytes)) if image_bytes else None

        if movement != 'NONE':
            success, _ = self.world_map.move(movement)
            if success and 'map' in game_output:
                new_location = self.world_map.current_position
                self.world_map.update_location(*new_location, game_output['map'].get('scene_description', ''))

        # Process any new rules
        for rule in game_output.get('rule_updates', []):
            self.world_state.add_rule(rule['rule_name'], rule['rule_description'])

        # Process any new events
        if 'events' in game_output:
            for event in game_output['events']:
                self.world_state.add_event(event)

        # Update chat history with AI response
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
            # If the file doesn't exist, start with empty chat history and no image
            self.chat_history = []
            self.current_image = None

    def get_current_image(self):
        return self.current_image
