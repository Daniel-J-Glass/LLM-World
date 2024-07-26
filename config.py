import os
from dotenv import load_dotenv

load_dotenv("local.env")

# LLM Provider Settings
LLM_PROVIDER = "anthropic"  # or "openai"
ENGINE_LLM_PROVIDER = "anthropic"
VISUAL_LLM_PROVIDER = "anthropic"

# OpenAI Settings
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
OPENAI_DEFAULT_MODEL = "gpt-3.5-turbo"  # or "gpt-4" if you have access

# API Settings
ANTROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"

# LLM Settings
DEFAULT_MODEL = "claude-3-5-sonnet-20240620"
MAX_TOKENS = 1000
TEMPERATURE = 0.7

# Image Generator Settings
IMAGE_GENERATION_MODEL = os.environ.get('IMAGE_GENERATION_MODEL')
IMAGE_GENERATION_SEED = 1

SD_KEY = os.environ.get("SD_KEY")
SD_API_HOST = os.getenv('SD_API_HOST', 'https://api.stability.ai')

# Image generation modifiers
POSITIVE_STYLE_MODIFIER = "realistic"
FIRST_PERSON_MODIFIER = "First person, POV, " + POSITIVE_STYLE_MODIFIER + ", {visual}, nothing extra"
NEGATIVE_STYLE_MODIFIER = "symmetric, artistic"

# 1 is more 0 is less
SVG_IMAGE_CONTROL_STRENGTH = .3

# Application Settings
DEBUG_MODE = True
LOG_FILE = "llm_world.log"

NARRATIVE_PARAMETER_NAME = "narrative" #used for streaming
SCENE_SVG_INPUT_NAME = "Scene Visual"

GAME_ENGINE_SYSTEM_PROMPT = "You are the game master for providing a narrative based experience. Interpret the player's action."

GAME_TOOLS = [
    {
        "name": "game_output",
        "description": "Provide only the values necessary for a cohesive game experience based on the player action using well-structured JSON.",
        "input_schema": {
            "type": "object",
            "properties": {
                NARRATIVE_PARAMETER_NAME: {
                    "type": "string",
                    "description": " Make the output always in html format like ```html\n<content>\n```. This narrates what the player experiences as a result of their action."
                },
                "events": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "The objective events that should be tracked after the player actions"
                },
                "scene": {
                    "type": "object",
                    "properties": {
                        "scene_description": {"type": "string","description": "A lossless visual description of the scene. Incorporate all objects description and layout in the scene."},
                        "scene_svg": {"type": "string","description": "A highly detailed panorama picture of the scene (in SVG code). It should be in 4 vertical sections for all cardinal directions and their visual details. From the players POV."},
                        "tile_color": {"type": "string", "description": "The color this location would be on a tiled map (like #FFFFFF)"}
                    },
                    "description": "Use this when the movement property is used. Should be used to reflect any changes resulting from the player action."
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
            "required": ["narrative", "events"]
        },
    }
]
GAME_TOOL_CHOICE = {"type": "tool", "name": "game_output"}

VISUAL_TOOLS = [
    {
        "name": "visual_output",
        "description": "Provide the relevant visuals during the player action using well-structured JSON.",
        "input_schema": {
            "type": "object",
            "properties": {
                "visuals": {
                    "type": "object",
                    "properties": {
                        "first_person_description": {"type": "string", "description": "Visual description of exactly what the player sees in this situation. Use theory of mind to describe exactly and only what the player would be seeing precisely."},
                        "first_person_svg": {"type": "string", "description": f"An accurate SVG visualization of the player's POV (like the player can see their hands, tools, etc.). Accurately capture composition, forms, and colors rather than complex details. This should be based on the {SCENE_SVG_INPUT_NAME} field and the description."}
                    },
                    "description": "These properties are used to generate visuals."
                },
            },
            "required": ["visuals"]
        },
    }
]
VISUAL_TOOL_CHOICE = {"type": "tool", "name": "visual_output"}