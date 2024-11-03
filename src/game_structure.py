import json
from utils.llm_utils import create_message_stream, update_chat_history, initialize_client
from utils.visual_utils import generate_svg_image, generate_image, upload_image_to_imgur, image_to_video

from src.world_map import WorldMap
import io
from PIL import Image
import base64
import shutil
import time
import os

import config

import logging

import asyncio
import threading
import tempfile  # Added for temporary file handling

from moviepy.editor import VideoFileClip, concatenate_videoclips

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

        os.makedirs("./saves", exist_ok=True)
        os.makedirs("./video_tmp", exist_ok=True)

        self.final_path = os.path.abspath("./current_video.mp4")
    
        self.world_map = WorldMap()
        self.world_state = WorldState()
        self.chat_history = []
        self.current_image = None
        self.current_svg = None
        self.current_video = None
        self.video_path = None  # Store path to video file
        self.video_processing = False
        self.videos_generated = 0  # Track number of videos generated
        self.load_state()
        self.cleanup_old_videos()

    def start_video_generation(self, image_path, prompt):
        def video_gen_thread():
            try:
                # Upload image to imgur
                image_url = upload_image_to_imgur(image_path)
                
                # Generate unique video name
                video_name = f"video_{self.videos_generated}.mp4"
                temp_video_path = os.path.join("./video_tmp", video_name)
                
                # Generate video
                image_to_video(prompt, image_url, temp_video_path)
                
                # Extract last frame from generated video
                try:
                    with VideoFileClip(temp_video_path) as clip:
                        # Get last frame using iter_frames
                        frames = [frame for i, frame in enumerate(clip.iter_frames()) 
                                if i >= clip.reader.nframes - 1]
                        if frames:
                            last_frame = frames[-1]
                            self.current_image = Image.fromarray(last_frame)
                            # Save immediately to ensure persistence
                            self.current_image.save("./current_frame.png")
                            print(f"Extracted last frame successfully")
                except Exception as e:
                    print(f"Error extracting last frame: {e}")
                
                # Update state
                self.current_video = temp_video_path
                self.videos_generated += 1

            except Exception as e:
                print(f"Video generation failed: {str(e)}")
            finally:
                self.video_processing = False

        self.video_processing = True
        thread = threading.Thread(target=video_gen_thread, daemon=True)
        thread.start()

    def save_state(self):
        """Save game state with improved video/image handling."""
        try:
            self.world_map.save_state()
            self.world_state.save_state()
            
            self.current_video = self.final_path if self.current_video else None

            state = {
                'chat_history': self.chat_history,
                'video_path': None,
                'current_image': None
            }
            
            # Save current video with unique name
            if self.current_video and os.path.exists(self.current_video):
                saves_dir = os.path.abspath("./saves")
                os.makedirs(saves_dir, exist_ok=True)
                
                video_filename = f"video_state_{int(time.time())}.mp4"
                video_save_path = os.path.join(saves_dir, video_filename)
                
                # Copy video to saves directory
                shutil.copy2(self.current_video, video_save_path)
                state['video_path'] = video_save_path
                print(f"Saved video state to: {video_save_path}")
            
            # Save current image
            if self.current_image:
                # Save as PNG file
                image_save_path = os.path.join("./saves", f"image_state_{int(time.time())}.png")
                self.current_image.save(image_save_path)
                
                # Also save as base64 in state
                buffered = io.BytesIO()
                self.current_image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                state['current_image'] = img_str
                print(f"Saved image state to: {image_save_path}")
            
            # Save state file
            state_path = os.path.abspath("./game_state.json")
            with open(state_path, 'w') as f:
                json.dump(state, f)
            print(f"Saved game state to: {state_path}")
            
        except Exception as e:
            print(f"Error saving game state: {e}")

    def load_state(self):
        """Load game state with improved validation."""
        try:
            self.world_map.load_state()
            self.world_state.load_state()
            
            if not os.path.exists("game_state.json"):
                print("No game state file found")
                return False
                
            with open("game_state.json", 'r') as f:
                state = json.load(f)
            
            self.chat_history = state.get('chat_history', [])
            
            # Load video
            video_path = state.get('video_path')
            if video_path and os.path.exists(video_path):
                # Validate video file
                try:
                    with VideoFileClip(video_path) as clip:
                        duration = clip.duration
                    print(f"Loaded video: {video_path} (duration: {duration}s)")
                    self.current_video = video_path
                except Exception as e:
                    print(f"Error validating video file: {e}")
                    self.current_video = None
            
            # Load image
            if state.get('current_image'):
                try:
                    image_data = base64.b64decode(state['current_image'])
                    self.current_image = Image.open(io.BytesIO(image_data))
                    self.current_image.save("./current_frame.png")  # Save for verification
                    print("Loaded current image")
                except Exception as e:
                    print(f"Error loading image: {e}")
                    self.current_image = None
                    
            return True
            
        except Exception as e:
            print(f"Error loading game state: {e}")
            return False

    def process_input(self, user_input):
        current_svg = self.world_map.get_current_svg()
        current_description = self.world_map.get_current_description()

        context = f"Current scene SVG: {current_svg}\n"
        context += f"Current scene description: {current_description}\n"
        context += f"Available directions: {', '.join(self.world_map.get_available_directions())}\n"
        context += f"Current world rules: {json.dumps(self.world_state.rules)}\n"
        context += f"Recent events: {json.dumps(self.world_state.events[-5:])}\n"
        context += f"Player action: {user_input}\n"
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
        user_input = (
            f"Previous Action: {user_input}\n"
            f"Result: {narrative}\n"
            f"{config.SCENE_SVG_INPUT_NAME}: {scene_svg}\n"
            f"Scene description: {scene_description}\n"
        )
        system_prompt = config.SVG_GENERATION_SYSTEM_PROMPT

        print(user_input)

        chat_history = [
            {
                "role": "user",
                "content": user_input
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
                    return chunk["visuals"]
        except Exception as e:
            print(e)
            print(json.dumps(chunk))

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
            new_svg = ""
            new_description = description
            self.world_map.update_location(*new_location, new_svg, new_description, tile_color)

        if not description and scene:
            description = scene.get("scene_description")

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

        if first_person_description and not config.CONTINUOUS_VIDEO or self.current_image is None:
            first_person_visual = config.FIRST_PERSON_MODIFIER.format(visual=first_person_description)
            try:
                if config.GENERATE_SVG and first_person_svg:
                    image_bytes = generate_svg_image(
                        positive_prompt=first_person_visual,
                        svg=first_person_svg,
                        negative_prompt=config.NEGATIVE_STYLE_MODIFIER,
                        kwargs=config.SVG_IMAGE_ARGS
                    )
                else:
                    image_bytes = generate_image(
                        positive_prompt=first_person_visual,
                        negative_prompt=config.NEGATIVE_STYLE_MODIFIER
                    )

                self.current_image = Image.open(io.BytesIO(image_bytes)) if image_bytes else None
                self.current_image.save("./temp.png")

            except Exception as e:
                print(f"Failed to generate image: {str(e)}")
                logging.error(f"Failed to generate image: {str(e)}")
                self.current_image = None
        
        # After image generation:
        if self.current_image and not self.video_processing:
            # Save temp image for video generation
            temp_img_path = "./temp.png"
            self.current_image.save(temp_img_path)

            video_prompt = config.VIDEO_FIRST_PERSON_MODIFIER.format(prompt=first_person_video)
    
            if first_person_video:
                # Start async video generation using the LLM-provided video description
                self.start_video_generation(
                    image_path=temp_img_path,
                    prompt=video_prompt
                )

        if rule_updates:
            for rule in rule_updates:
                self.world_state.add_rule(rule['rule_name'], rule['rule_description'])

        if events:
            for event in events:
                self.world_state.add_event(event)

        self.chat_history = update_chat_history(self.chat_history, "assistant", narrative)

        self.save_state()

    def compile_videos(self):
        """Compile all videos in video_tmp into a single video."""
        try:
            video_files = sorted(
                [f for f in os.listdir("./video_tmp") if f.startswith("video_")],
                key=lambda x: int(x.split("_")[1].split(".")[0])
            )
            
            if not video_files:
                return None, "No videos found to compile"

            clips = []
            for video_file in video_files:
                video_path = os.path.join("./video_tmp", video_file)
                try:
                    clip = VideoFileClip(video_path)
                    clips.append(clip)
                except Exception as e:
                    print(f"Error loading video {video_file}: {e}")
                    continue

            if not clips:
                return None, "No valid video clips found"

            compilation_path = os.path.join("./video_tmp", "compilation.mp4")
            
            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip.write_videofile(compilation_path)
            
            for clip in clips:
                clip.close()
            final_clip.close()

            return compilation_path, "Success"
            
        except Exception as e:
            return None, f"Compilation failed: {str(e)}"

    def cleanup_old_videos(self):
        """Remove old video files to prevent disk space issues"""
        saves_dir = "saves"
        if not os.path.exists(saves_dir):
            return
        for file in os.listdir(saves_dir):
            if file.startswith("save_video_"):
                file_path = os.path.join(saves_dir, file)
                # Keep only videos from last 24 hours
                if time.time() - os.path.getctime(file_path) > 86400:
                    try:
                        os.remove(file_path)
                        print(f"Removed old video: {file_path}")
                    except Exception as e:
                        print(f"Error removing old video {file_path}: {e}")

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