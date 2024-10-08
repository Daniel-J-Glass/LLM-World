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

def unescape_string(s):
    s = s.replace("\\n", "\n")
    return codecs.decode(s, 'unicode_escape')

class GameGUI:
    def __init__(self, master):
        self.master = master
        master.title("LLM World Explorer")

        # Initialize game
        self.game = Game()

        # Main frame
        self.main_frame = tk.Frame(master, width=1200, height=800)
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

        self.update_display()
        self.load_chat_history()

        self.is_processing = False

    def load_chat_history(self):
        self.message_display.config(state=tk.NORMAL)
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

    def process_input(self, event):
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

        # Update generated image display
        image = self.game.get_current_image()
        if image:
            image = image.resize((400, 300), Image.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            self.image_display.config(image=photo)
            self.image_display.image = photo
        else:
            self.image_display.config(image='')

        # Update minimap
        self.update_minimap()

        # Update rules and events display
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
                map_y = minimap_size - (y + visible_range + 1) * tile_size
                
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