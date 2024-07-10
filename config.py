import os
from dotenv import load_dotenv

load_dotenv("local.env")

# API Settings
ANTROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"

# LLM Settings
DEFAULT_MODEL = "claude-3-5-sonnet-20240620"
MAX_TOKENS = 1000
TEMPERATURE = 0.7

# Image Generator Settings
IMAGE_GENERATION_MODEL = os.environ.get('IMAGE_GENERATION_MODEL')
SD_KEY = os.environ.get("SD_KEY")
SD_API_HOST = os.getenv('SD_API_HOST', 'https://api.stability.ai')

# Image generation modifiers
POSITIVE_STYLE_MODIFIER = "realistic"
FIRST_PERSON_MODIFIER = "First person, POV, "+POSITIVE_STYLE_MODIFIER+", {visual}, nothing extra"
NEGATIVE_STYLE_MODIFIER = "symmetric, artistic"

# Application Settings
DEBUG_MODE = True
LOG_FILE = "llm_world.log"

NARRATIVE_PARAMETER_NAME = "narrative"
TOOLS = [
    {
        "name": "game_output",
        "description": "Provide only the values necessary for a cohesive game experience based on the player action using well-structured JSON.",
        "input_schema": {
            "type": "object",
            "properties": {
                NARRATIVE_PARAMETER_NAME: {
                    "type": "string",
                    "description": " Make the output always in html format like ```html\n<content>\n```. This narrates what the player experiences as a result of their action. This is to be enjoyable and easily understood by a 1st grader unfamiliar with text based games (guide the story with listed decisions, spoonfeed the adventure)."
                },
                "events": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "The objective events that should be tracked after the player actions"
                },
                "visuals": {
                    "type": "object",
                    "properties": {
                        "first_person_scene": {"type": "string", "description":"Imagine exactly what the player sees in this situation. Use theory of mind to describe exactly and only what the player would be seeing precisely."},
                    },
                    "description": "This generates images. DO NOT USE XML TAGS"
                },
                "map": {
                    "type": "object",
                    "properties": {
                        "scene_description": {"type": "string","description": "The overall visual scene description after the user action and events have taken place. This should be consistent and communicate the highly detailed layout of the scene to the user."},
                        "tile_color": {"type": "string", "description":"The color this location would be on a tiled map (like #FFFFFF)"}
                    },
                    "description": "Use this also when the movement property is used."
                },
                "movement": {
                    "type": "string",
                    "enum": ["N", "S", "E", "W"],
                    "description": "Where the player moves in accordance with the narrative. (if they move to a new scene use this) (N, S, E, W)",
                },
                "rule_updates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rule_name": {"type": "string"},
                            "rule_description": {"type": "string"}
                        }
                    },
                    "description": "Any fundamental mechanics about the world that the player discovers. This should be very rare."
                },
            },
            "required": ["narrative", "visuals", "events"]
        },
    }
]
TOOL_CHOICE = {"type": "tool", "name": "game_output"}