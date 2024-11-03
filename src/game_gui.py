import tkinter as tk
from tkinter import scrolledtext
from src.game_structure import Game
from utils.llm_utils import initialize_client, update_chat_history
import threading
from PIL import Image, ImageTk
import html
import io
import cairosvg
import codecs
import config

from tkvideo import tkvideo
import os

import imageio
from PIL import Image, ImageTk
import threading
import time
from collections import deque
from moviepy.editor import VideoFileClip, concatenate_videoclips

import shutil

class VideoPlayer:
    def __init__(self, video_path, label, size=(400, 300), loop=True):
        self.video_path = video_path
        self.label = label
        self.size = size
        self.loop = loop
        self.is_playing = False
        self._thread = None
        self.reader = None

    def play(self):
        if self.is_playing:
            self.stop()
        
        try:
            self.reader = imageio.get_reader(self.video_path)
            self.is_playing = True
            self._thread = threading.Thread(target=self._play_video, daemon=True)
            self._thread.start()
        except Exception as e:
            print(f"Failed to open video: {self.video_path} - {e}")

    def _play_video(self):
        try:
            while self.is_playing:
                for frame in self.reader.iter_data():
                    if not self.is_playing:
                        break
                        
                    # Convert frame to PIL Image and resize
                    image = Image.fromarray(frame).resize(self.size)
                    photo = ImageTk.PhotoImage(image=image)
                    
                    # Update label
                    self.label.configure(image=photo)
                    self.label.image = photo
                    
                    # Control frame rate based on video's FPS
                    time.sleep(1/30)  # 30 FPS
                
                if self.loop and self.is_playing:
                    self.reader.set_image_index(0)  # Reset to start
                else:
                    break
                    
        except Exception as e:
            print(f"Error in video playback: {e}")
        finally:
            # Only cleanup resources, don't try to join thread
            if self.reader:
                self.reader.close()
            self.reader = None
            self.label.configure(image='')
            self.label.image = None
            self.is_playing = False

    def stop(self):
        """Stop video playback"""
        self.is_playing = False
        # Don't join thread from within itself
        if threading.current_thread() is not self._thread:
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
        # Cleanup resources
        if self.reader:
            self.reader.close()
        self.reader = None
        self.label.configure(image='')
        self.label.image = None

def unescape_string(s):
    s = s.replace("\\n", "\n")
    return codecs.decode(s, 'unicode_escape')

class GameGUI:
    def __init__(self, master):
        self.master = master
        master.title("LLM World Explorer")

        # Initialize game
        self.game = Game()
        self.game.load_state()  # Ensure game state is loaded before proceeding

        # Setup UI components
        self.setup_ui()

        # Load chat history after state is loaded
        self.load_chat_history()

        # Update display with loaded content
        self.update_display()

        # Start video checking
        self.is_processing = False
        self.video_check_interval = 1000  # Check every second
        self.master.after(self.video_check_interval, self.check_video_update)

        # Video management
        self.video_queue = deque()
        self.current_video_path = None
        self.is_stitching = False
        
        # Create video directories
        os.makedirs("./video_tmp", exist_ok=True)
        os.makedirs("./video_final", exist_ok=True)
        
        # Start video processing thread
        self.video_processor = threading.Thread(target=self._process_video_queue, daemon=True)
        self.video_processor.start()

    def setup_ui(self):
        # Main frame
        self.main_frame = tk.Frame(self.master, width=1200, height=800)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Image display frame
        self.image_frame = tk.Frame(self.main_frame)
        self.image_frame.pack(side=tk.TOP, pady=10)

        # SVG image display
        self.svg_display = tk.Label(self.image_frame)
        self.svg_display.pack(side=tk.LEFT, padx=5)

        # Generated image display
        self.image_display = tk.Label(self.image_frame)
        self.image_display.pack(side=tk.LEFT, padx=5)

        # Video display label
        self.video_label = tk.Label(self.image_frame)
        self.video_label.pack(side=tk.LEFT, padx=5)

        # Minimap
        self.minimap = tk.Canvas(self.main_frame, width=150, height=150)
        self.minimap.place(relx=1.0, rely=0, anchor='ne')

        # Create a frame for the text areas
        text_frame = tk.Frame(self.main_frame)
        text_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Game messages display
        self.message_display = scrolledtext.ScrolledText(text_frame, width=70, height=10)
        self.message_display.pack(side=tk.LEFT, pady=10, padx=5, fill=tk.BOTH, expand=True)
        self.message_display.config(state=tk.DISABLED)
        self.message_display.tag_config("user", foreground="blue")
        self.message_display.tag_config("game", foreground="green")

        # Rules and events display
        self.rules_events_display = scrolledtext.ScrolledText(text_frame, width=40, height=10)
        self.rules_events_display.pack(side=tk.RIGHT, pady=10, padx=5, fill=tk.BOTH, expand=True)
        self.rules_events_display.config(state=tk.DISABLED)

        # Input box
        self.input_box = tk.Entry(self.main_frame, width=70)
        self.input_box.pack(side=tk.BOTTOM, pady=10)
        self.input_box.bind("<Return>", self.process_input)

        # Send button
        self.send_button = tk.Button(self.main_frame, text="Send", command=self.process_input)
        self.send_button.pack(side=tk.BOTTOM)

    def check_video_update(self):
        """Periodically check if new video is available"""
        if self.game.current_video and not self.game.video_processing:
            # Update video display
            self.update_video_display(self.game.current_video)

        # Schedule next check
        self.master.after(self.video_check_interval, self.check_video_update)

        """Check for new videos from game engine"""
        if self.game.current_video and self.game.current_video != self.current_video_path:
            self.video_queue.append(self.game.current_video)
            self.current_video_path = self.game.current_video
            
        self.master.after(self.video_check_interval, self.check_video_update)

    def _process_video_queue(self):
        """Background thread to process incoming videos"""
        while True:
            if self.video_queue and not self.is_stitching:
                self.is_stitching = True
                try:
                    self._stitch_next_video()
                finally:
                    self.is_stitching = False
            time.sleep(0.1)  # Prevent busy waiting

    def _stitch_next_video(self):
        """Stitch next video in queue with current video"""
        new_video_path = self.video_queue.popleft()
        final_path = os.path.join("./video_final", "current.mp4")

        try:
            clips = []
            
            # Add current video if it exists
            if hasattr(self, 'video_player') and os.path.exists(final_path):
                self.video_player.stop()
                clips.append(VideoFileClip(final_path))

            # Add new video
            if os.path.exists(new_video_path):
                clips.append(VideoFileClip(new_video_path))

            if clips:
                # Stitch videos
                final_clip = concatenate_videoclips(clips, method="compose")
                final_clip.write_videofile(
                    final_path + ".tmp",
                    codec="libx264",
                    audio_codec="aac"
                )
                
                # Close clips
                final_clip.close()
                for clip in clips:
                    clip.close()
                    
                # Replace current video with new one
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.rename(final_path + ".tmp", final_path)
                
                # Update video player
                self.master.after(0, lambda: self.play_video(final_path))

        except Exception as e:
            print(f"Error stitching videos: {e}")
            # Fallback to playing just the new video
            if os.path.exists(new_video_path):
                shutil.copy2(new_video_path, final_path)
                self.master.after(0, lambda: self.play_video(final_path))

    def update_video_display(self, video_path):
        # Clear existing video
        if hasattr(self, 'video_player'):
            self.video_player.stop()
        
        # Show video
        try:
            self.video_player = VideoPlayer(video_path, self.video_label, size=(400, 300), loop=True)
            self.video_player.play()
        except Exception as e:
            print(f"Error playing video: {e}")

    def play_video(self, video_path):
        if os.path.exists(video_path):
            try:
                if hasattr(self, 'video_player'):
                    self.video_player.stop()
                self.video_player = VideoPlayer(video_path, self.video_label, size=(400, 300), loop=True)
                self.video_player.play()
            except Exception as e:
                print(f"Error playing video: {e}")
                self.video_label.configure(image='')
                self.video_label.image = None
        else:
            self.video_label.configure(image='')
            self.video_label.image = None

    # Add cleanup method:
    def __del__(self):
        if hasattr(self, 'video_player'):
            self.video_player.stop()

    def load_chat_history(self):
        self.message_display.config(state=tk.NORMAL)
        self.message_display.delete(1.0, tk.END)
        for message in self.game.chat_history:
            role = "User" if message["role"] == "user" else "Game"
            content = message['content']
            
            if role == "Game" and content.startswith("```html"):
                # Parse HTML content
                content = content[7:-3]  # Remove ```html and ```
                content = html.unescape(content)
                self.message_display.insert(tk.END, f"{role}: ", role.lower())
                self.message_display.insert(tk.END, content, (role.lower(), "html"))
                self.message_display.insert(tk.END, "\n\n")
            else:
                self.message_display.insert(tk.END, f"{role}: ", role.lower())
                self.message_display.insert(tk.END, f"{content}\n\n")
        
        self.message_display.see(tk.END)
        self.message_display.config(state=tk.DISABLED)

    def process_input(self, event=None):
        if self.is_processing:
            return

        user_input = self.input_box.get()
        self.input_box.delete(0, tk.END)
        
        self.message_display.config(state=tk.NORMAL)
        self.message_display.insert(tk.END, "User: ", "user")
        self.message_display.insert(tk.END, f"{user_input}\n", "user")

        self.message_display.see(tk.END)
        self.message_display.config(state=tk.DISABLED)

        self.is_processing = True
        threading.Thread(target=self.process_response, args=(user_input,)).start()

    def process_response(self, user_input):
        response_stream = self.game.process_input(user_input)
        
        self.message_display.config(state=tk.NORMAL)
        self.message_display.insert(tk.END, "Game: ", "game")
        
        narrative = ""
        for chunk in response_stream:
            if chunk is None:
                break
            if isinstance(chunk, str):
                # This is a narrative chunk
                try:
                    chunk = unescape_string(chunk)
                except:
                    pass
                
                if chunk.startswith("```html"):
                    # Parse HTML content
                    chunk = chunk[7:-3]  # Remove ```html and ```
                    chunk = html.unescape(chunk)
                
                narrative += chunk
                self.message_display.insert(tk.END, chunk, ("game","html"))
                self.message_display.see(tk.END)
                self.master.update_idletasks()
            elif isinstance(chunk, dict):
                # This is the final game output
                if 'narrative' in chunk:
                    # Update the narrative with the full results
                    self.message_display.delete("end-{}c".format(len(narrative)+1), tk.END)
                    full_narrative = chunk['narrative']
                    
                    if full_narrative.startswith("```html"):
                        # Parse HTML content
                        full_narrative = full_narrative[7:-3]  # Remove ```html and ```
                        full_narrative = html.unescape(full_narrative)
                    
                    self.message_display.insert(tk.END, full_narrative, ("game","html"))

                self.game.update_game_state(chunk)
                break

        self.message_display.insert(tk.END, "\n\n")
        self.message_display.config(state=tk.DISABLED)
        
        self.update_display()
        self.is_processing = False

    def update_display(self):
        # Update SVG display
        first_person_svg = self.game.current_svg
        if first_person_svg:
            svg_image = self.svg_to_image(first_person_svg)
            if svg_image:
                svg_image = svg_image.resize((400, 300), Image.LANCZOS)
                photo = ImageTk.PhotoImage(svg_image)
                self.svg_display.config(image=photo)
                self.svg_display.image = photo
            else:
                self.svg_display.config(image='')
        else:
            self.svg_display.config(image='')

        # Update image display
        if self.game.current_image:
            try:
                # Convert and resize image
                display_width = 400
                image = self.game.current_image.copy()
                width_percent = (display_width / float(image.size[0]))
                height_size = int((float(image.size[1]) * float(width_percent)))
                image = image.resize((display_width, height_size))
                
                # Convert to PhotoImage and display
                photo = ImageTk.PhotoImage(image)
                self.image_display.configure(image=photo)
                self.image_display.image = photo  # Keep a reference
            except Exception as e:
                print(f"Error displaying image: {e}")
                self.image_display.config(image='')
                self.image_display.image = None
        else:
            self.image_display.config(image='')
            self.image_display.image = None

        # Update video display if not already playing
        if self.game.current_video and not hasattr(self, 'video_player'):
            self.play_video(self.game.current_video)

        # Update minimap
        self.update_minimap()

        # Update rules and events display
        self.update_rules_events_display()

    def play_video(self, video_path):
        if os.path.exists(video_path):
            try:
                self.video_player = tkvideo(video_path, self.video_label, loop=1, size=(400, 300))
                self.video_player.play()
            except Exception as e:
                print(f"Error playing video: {e}")
        else:
            self.video_label.configure(image='')
            self.video_label.image = None

    def update_minimap(self):
        self.minimap.delete("all")
        cx, cy = self.game.world_map.current_position
        minimap_size = 150
        tile_size = 10
        visible_range = 7  # Number of tiles visible in each direction

        # Draw the grid
        for x in range(-visible_range, visible_range + 1):
            for y in range(-visible_range, visible_range + 1):
                pos_x, pos_y = cx + x, cy + y
                color = self.game.world_map.get_location_color(pos_x, pos_y)
                
                # Calculate the position on the minimap
                map_x = (x + visible_range) * tile_size
                map_y = (visible_range - y) * tile_size  # Invert y-axis for correct orientation
                
                self.minimap.create_rectangle(
                    map_x, map_y, map_x + tile_size, map_y + tile_size,
                    fill=color, outline=""
                )

        # Highlight current position
        center_x = visible_range * tile_size
        center_y = visible_range * tile_size
        self.minimap.create_rectangle(
            center_x, center_y, center_x + tile_size, center_y + tile_size,
            outline="red", width=2
        )

    def update_rules_events_display(self):
        self.rules_events_display.config(state=tk.NORMAL)
        self.rules_events_display.delete(1.0, tk.END)
        self.rules_events_display.insert(tk.END, "Current Rules:\n")
        for rule_name, rule_description in self.game.world_state.rules.items():
            self.rules_events_display.insert(tk.END, f"- {rule_name}: {rule_description}\n")
        self.rules_events_display.insert(tk.END, "\nRecent Events:\n")
        for event in self.game.world_state.events[-5:]:
            self.rules_events_display.insert(tk.END, f"- {event}\n")
        self.rules_events_display.see(tk.END)
        self.rules_events_display.config(state=tk.DISABLED)

    def svg_to_image(self, svg_string):
        try:
            png_data = cairosvg.svg2png(bytestring=svg_string.encode('utf-8'))
            return Image.open(io.BytesIO(png_data))
        except Exception as e:
            print(f"Error converting SVG to image: {e}")
            return None

    def run(self):
        self.master.mainloop()


def main():
    root = tk.Tk()
    gui = GameGUI(root)
    gui.run()

if __name__ == "__main__":
    main()