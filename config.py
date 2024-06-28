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
FIRST_PERSON_MODIFIER = "First person, POV, {visual}"

# Application Settings
DEBUG_MODE = True
LOG_FILE = "llm_world.log"

NARRATIVE_PARAMETER_NAME = "narrative"
TOOLS = [
    {
        "name": "game_output",
        "description": "Provide values necessary for a cohesive game experience based on the player action",
        "input_schema": {
            "type": "object",
            "properties": {
                NARRATIVE_PARAMETER_NAME: {
                    "type": "string",
                    "description": "This narrates what the player experiences as a result of their action."
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
                        "first_person_scene": {"type": "string", "description":"What the player sees, first person POV"},
                    }
                },
                "map": {
                    "type": "object",
                    "properties": {
                        "scene_description": {"type": "string","description": "The overall visual scene description after the user action and events have taken place"},
                        "tile_color": {"type": "string", "description":"The color this location would be on a tiled map (like #FFFFFF)"}
                    }
                },
                "movement": {
                    "type": "string",
                    "enum": ["N", "S", "E", "W"],
                    "description": "Where the player wants to move (N, S, E, W)",
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
                    "description": "Any new rules or updates to existing rules"
                },
            },
            "required": ["narrative", "events"]
        }
    }
]