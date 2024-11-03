import json
import os
import io
import base64
import time
import shutil

from PIL import Image

from moviepy.editor import VideoFileClip


class StateManager:
    def save_game_state(self, world_map, world_state, chat_history, current_video, current_image, saves_dir="./saves"):
        try:
            os.makedirs(saves_dir, exist_ok=True)
            
            # Save world and event state
            world_map.save_state()
            world_state.save_state()
            
            state = {
                'chat_history': chat_history,
                'video_path': None,
                'current_image': None
            }
            
            # Save current video with unique name
            if current_video and os.path.exists(current_video):
                video_filename = f"video_state_{int(time.time())}.mp4"
                video_save_path = os.path.join(saves_dir, video_filename)
                shutil.copy2(current_video, video_save_path)
                state['video_path'] = video_save_path
                print(f"Saved video state to: {video_save_path}")
            
            # Save current image
            if current_image:
                image_filename = f"image_state_{int(time.time())}.png"
                image_save_path = os.path.join(saves_dir, image_filename)
                current_image.save(image_save_path)
                state['current_image'] = self.encode_image_to_base64(current_image)
                print(f"Saved image state to: {image_save_path}")
            
            # Save state file
            state_path = os.path.abspath("./game_state.json")
            with open(state_path, 'w') as f:
                json.dump(state, f)
            print(f"Saved game state to: {state_path}")
            
        except Exception as e:
            print(f"Error saving game state: {e}")

    def load_game_state(self, world_map, world_state, video_manager, load_path="game_state.json"):
        try:
            world_map.load_state()
            world_state.load_state()
            
            if not os.path.exists(load_path):
                print("No game state file found")
                return False
                
            with open(load_path, 'r') as f:
                state = json.load(f)
            
            chat_history = state.get('chat_history', [])
            video_path = state.get('video_path')
            current_image = None

            # Load video
            if video_path and os.path.exists(video_path):
                try:
                    with VideoFileClip(video_path) as clip:
                        duration = clip.duration
                    print(f"Loaded video: {video_path} (duration: {duration}s)")
                    # Optionally, add to video_manager if needed
                except Exception as e:
                    print(f"Error validating video file: {e}")
            
            # Load image
            if state.get('current_image'):
                try:
                    image_data = base64.b64decode(state['current_image'])
                    current_image = Image.open(io.BytesIO(image_data))
                    print("Loaded current image")
                except Exception as e:
                    print(f"Error loading image: {e}")
            
            return {
                'chat_history': chat_history,
                'video_path': video_path,
                'current_image': current_image
            }
                
        except Exception as e:
            print(f"Error loading game state: {e}")
            return False

    def encode_image_to_base64(self, image):
        try:
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            return img_str
        except Exception as e:
            print(f"Error encoding image: {e}")
            return None
