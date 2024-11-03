import json
import os
import io
import time
import base64
import shutil
from PIL import Image
from utils.llm_utils import create_message_stream, update_chat_history, initialize_client
from utils.image_utils import ImageManager
from utils.video_utils import VideoManager
from utils.state_manager import StateManager
from src.world_map import WorldMap
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

        self.state_manager = StateManager()
        self.image_manager = ImageManager()
        self.video_manager = VideoManager()

        os.makedirs("./saves", exist_ok=True)
        os.makedirs("./video_tmp", exist_ok=True)

        self.world_map = WorldMap()
        self.world_state = WorldState()
        self.chat_history = []
        self.current_image = None
        self.new_image = None
        self.current_svg = None
        self.current_video = None
        self.video_processing = False

        self.generate_video = config.GENERATE_VIDEO
        self.load_state()
        self.video_manager.cleanup_old_videos()
        self.rate_limited = False

    def load_state(self):
        state = self.state_manager.load_game_state(
            self.world_map, 
            self.world_state, 
            self.video_manager
        )
        if state:
            self.chat_history = state.get('chat_history', [])
            self.current_video = state.get('video_path')
            self.current_image = state.get('current_image')

    def save_state(self):
        self.state_manager.save_game_state(
            self.world_map,
            self.world_state,
            self.chat_history,
            self.current_video,
            self.current_image
        )

    def reset(self):
        """Reset the game to initial state."""
        self.world_map.reset()
        self.world_state = WorldState()
        self.chat_history = []
        self.current_image = None
        self.current_video = None
        self.save_state()

    def start_video_generation(self, image_path, prompt):
        def callback(video_path, last_frame, rate_limited):
            if rate_limited:
                self.rate_limited = True
                self.current_image = self.new_image
                if self.current_image:
                    self.image_manager.save_image(self.current_image, "./current_frame.png")
            else:
                self.current_video = video_path
                if last_frame:
                    self.current_image = last_frame
                    self.image_manager.save_image(self.current_image, "./current_frame.png")
                self.rate_limited = False
            self.video_processing = False
            self.save_state()

        self.video_processing = True
        self.video_manager.start_video_generation(
            image_path=image_path,
            prompt=prompt,
            callback=callback,
            rate_limited_flag=self.rate_limited
        )

    def process_input(self, user_input):
        current_svg = self.world_map.get_current_svg()
        current_description = self.world_map.get_current_description()

        context = (
            f"Current scene SVG: {current_svg}\n"
            f"Current scene description: {current_description}\n"
            f"Available directions: {', '.join(self.world_map.get_available_directions())}\n"
            f"Current world rules: {json.dumps(self.world_state.rules)}\n"
            f"Recent events: {json.dumps(self.world_state.events[-5:])}\n"
            f"Player action: {user_input}\n"
        )
        system_prompt = config.GAME_ENGINE_SYSTEM_PROMPT

        self.chat_history = update_chat_history(self.chat_history, "user", user_input)

        chat_history = update_chat_history(self.chat_history, "assistant", context)
        chat_history = update_chat_history(chat_history, "user", user_input)

        return create_message_stream(
            self.engine_client,
            system_prompt=system_prompt,
            chat_history=chat_history,
            model=config.ENGINE_LLM_PROVIDER,
            tools=config.GAME_TOOLS,
            tools_choice=config.GAME_TOOL_CHOICE
        )
    
    def generate_first_person_visuals(self, user_input, scene_svg, scene_description, narrative):
        user_input_formatted = (
            f"Previous Action: {user_input}\n"
            f"Result: {narrative}\n"
            f"{config.SCENE_SVG_INPUT_NAME}: {scene_svg}\n"
            f"Scene description: {scene_description}\n"
        )
        system_prompt = config.SVG_GENERATION_SYSTEM_PROMPT

        print(user_input_formatted)

        chat_history = [
            {
                "role": "user",
                "content": user_input_formatted
            }
        ]

        visual_stream = create_message_stream(
            self.visual_client,
            chat_history=chat_history,
            system_prompt=system_prompt,
            model=config.VISUAL_LLM_PROVIDER,
            tools=config.VISUAL_TOOLS,
            tools_choice=config.VISUAL_TOOL_CHOICE
        )

        try:
            for chunk in visual_stream:
                if isinstance(chunk, dict):
                    return chunk.get("visuals", {})
        except Exception as e:
            print(e)
            if 'chunk' in locals():
                print(json.dumps(chunk))
        return {}

    def update_game_state(self, game_output):
        if not isinstance(game_output, dict):
            return

        movement = game_output.get('movement')
        narrative = game_output.get('narrative', '')
        scene = game_output.get('scene')
        rule_updates = game_output.get('rule_updates')
        events = game_output.get('events')

        svg = self.world_map.get_current_svg()
        description = self.world_map.get_current_description()
        user_input = self.chat_history[-1]['content'] if self.chat_history else ""

        # Handle movement
        if movement and movement != "NONE":
            success, svg, description = self.world_map.move(movement)

        # Handle scene updates
        if scene:
            new_location = self.world_map.current_position
            tile_color = scene.get('tile_color', '#FFFFFF')
            new_svg = scene.get('new_svg', "")
            new_description = description or scene.get("scene_description", "")
            self.world_map.update_location(*new_location, new_svg, new_description, tile_color)

        print(json.dumps(game_output))

        # Generate visuals
        visual_output = self.generate_first_person_visuals(
            user_input,
            svg,
            description,
            narrative=narrative
        )
        first_person_description = visual_output.get("first_person_description")
        first_person_video = visual_output.get("first_person_video")
        first_person_svg = visual_output.get("first_person_svg")

        print(f"First Person Description:\n{first_person_description}")
        print(f"First Person Video:\n{first_person_video}")

        self.current_svg = first_person_svg  # for dev UI display

        if first_person_description:
            new_image = self.image_manager.generate_new_image(visual_output, config)
            if new_image:
                self.new_image = new_image
                self.image_manager.save_image(self.new_image, "./temp.png")
        
        # Set current_image if none exists
        if self.current_image is None and self.new_image:
            self.current_image = self.new_image

        # Attempt video generation
        if self.new_image and not self.video_processing and config.GENERATE_VIDEO and not self.rate_limited:
            video_prompt = config.VIDEO_FIRST_PERSON_MODIFIER.format(prompt=first_person_video)
            temp_img_path = "./temp.png"
            self.video_manager.start_video_generation(
                image_path=temp_img_path,
                prompt=video_prompt,
                callback=self.handle_video_callback,
                rate_limited_flag=self.rate_limited
            )

        # Handle fallback to new_image if rate limited or video generation fails
        if self.rate_limited or not config.GENERATE_VIDEO:
            self.current_image = self.new_image

        # Update rules and events
        if rule_updates:
            for rule in rule_updates:
                self.world_state.add_rule(rule['rule_name'], rule['rule_description'])

        if events:
            for event in events:
                self.world_state.add_event(event)

        self.chat_history = update_chat_history(self.chat_history, "assistant", narrative)

        self.save_state()

    def handle_video_callback(self, video_path, last_frame, rate_limited):
        if rate_limited:
            self.rate_limited = True
            self.current_image = self.new_image
            if self.current_image:
                self.image_manager.save_image(self.current_image, "./current_frame.png")
        else:
            self.current_video = video_path
            if last_frame:
                self.current_image = last_frame
                self.image_manager.save_image(self.current_image, "./current_frame.png")
            self.rate_limited = False
        self.video_processing = False
        self.save_state()

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

    def compile_videos(self):
        return self.video_manager.compile_videos()