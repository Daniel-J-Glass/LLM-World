import os
from dotenv import load_dotenv

load_dotenv("local.env")

# LLM Provider Settings
LLM_PROVIDER = "openai"  # or "openai"
ENGINE_LLM_PROVIDER = "openai"
VISUAL_LLM_PROVIDER = "openai"

# OpenAI Settings
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
OPENAI_DEFAULT_MODEL = "gpt-4o-2024-08-06"  # or "gpt-4" if you have access

# API Settings
ANTROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"

# LLM Settings
ANTHROPIC_DEFAULT_MODEL = "claude-3-5-sonnet-20240620"
MAX_TOKENS = 3000
TEMPERATURE = 0.7

# Image Generator Settings
IMAGE_GENERATION_MODEL = os.environ.get('IMAGE_GENERATION_MODEL')
IMAGE_GENERATION_SEED = 1

SD_KEY = os.environ.get("SD_KEY")
SD_API_HOST = os.getenv('SD_API_HOST', 'https://api.stability.ai')

# Image generation modifiers
POSITIVE_STYLE_MODIFIER = "realistic"
FIRST_PERSON_MODIFIER = "First person, point-of-view, " + POSITIVE_STYLE_MODIFIER + ", {visual}, nothing extra"
NEGATIVE_STYLE_MODIFIER = "symmetric, artistic"

# 1 is more 0 is less
SVG_IMAGE_ARGS = {
    "control_strength": .3
}
SVG_IMAGE_ENDPOINT = "/v2beta/stable-image/control/sketch"


# Application Settings
DEBUG_MODE = True
LOG_FILE = "llm_world.log"

NARRATIVE_PARAMETER_NAME = "narrative" #used for streaming
SCENE_SVG_INPUT_NAME = "Scene Visual"
SVG_GENERATION_SYSTEM_PROMPT = "Generate first-person visuals based on the user's previous action, scene SVG, and scene description."

GAME_ENGINE_SYSTEM_PROMPT = "You are the game master for providing a narrative based experience for a fantasy world. Act as a game engine by interpretting the player's action and update the game accordingly."

GAME_TOOLS = [
    {
        "type":"function",
        "function":{
            "name": "game_output",
            "description": "Provide only the values necessary for a cohesive game experience based on the player action. Maintain consistency is key.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    NARRATIVE_PARAMETER_NAME: {
                        "type": "string",
                        "description": " Make the output always in html format like ```html\n<content>\n```. This narrates what the player experiences as a result of their action. Keep it less than 100 words"
                    },
                    "events": {
                        "type": "array",
                        "description": "The objective events that should be tracked after the player actions",
                        "items": {
                            "type": "string",
                        },
                    },
                    "scene": {
                        "type": ["object", "null"],
                        "description": "Use this when the player changes the scene or moves to a new scene. If it's a change to the existing scene, modify the scene SVG. If it's a change to an entirely new location, create an entirely new scene.",
                        "properties": {
                            "scene_description": {"type": "string","description": "A lossless visual description of the scene."},
                            "scene_svg": {"type": "string","description": "A highly detailed picture of the scene (in SVG code). From the players POV."},
                            "tile_color": {"type": "string", "description": "The color this location would be on a tiled map (like #FFFFFF)"}
                        },
                        "required":["scene_description", "scene_svg", "tile_color"],
                        "additionalProperties": False,
                    },
                    "visuals": {
                        "type": "object",
                        "description": "These should be highly detailed visuals for the first person perspective of the player like go pro footage (like if the player holds their hands in front of them, they can see their hands) based on the scene they're in.",
                        "properties": {
                            "image_generation_prompt": {"type": "string", "description": "Description of what the player sees. Use theory of mind to describe exactly and only what the player would be seeing. This description is used for an AI image generator."},
                            "first_person_sees_svg": {"type": "string", "description": f"An detailed SVG picture of what the player sees (like the player can see their hands, tools, objects in the scene, etc.). This should not be a diagram. No artistic liberties. This should be at least 30 lines of SVG code."}
                        },
                        "required": ["image_generation_prompt","first_person_sees_svg"],
                        "additionalProperties": False,
                    },
                    "movement": {
                        "type": ["string", "null"],
                        "description": "Where the player moves in accordance with the narrative. (if they move to a new scene use this) (N, S, E, W)",
                        "enum": ["N", "S", "E", "W"],
                    },
                    "rule_updates": {
                        "type": ["array", "null"],
                        "description": "Any fundamental mechanics about the world that the player discovers. This should be on the same level as the discovery of electromagnetism, cells, etc.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rule_name": {"type": "string"},
                                "rule_description": {"type": "string"}
                            },
                            "required":["rule_name","rule_description"],
                            "additionalProperties": False
                        },
                    },
                },
                "required": ["narrative", "events", "scene", "movement", "rule_updates", "visuals"],
                "additionalProperties": False,
            },
        }
    }
]
GAME_TOOL_CHOICE = {"type": "function", "function": {"name": "game_output"}}

VISUAL_TOOLS = [
    {
        "type":"function",
        "function": {
            "name": "visual_output",
            "description": "Provide the realistic visuals during the player action using well-structured JSON.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "visuals": {
                        "type": "object",
                        "description": "These properties are used to generate visuals.",
                        "properties": {
                            "first_person_description": {"type": "string", "description": "First person POV. Description of what the player sees in this situation. Use theory of mind to describe exactly and only what the player would be seeing. This description is used to create an image."},
                            "first_person_svg": {"type": "string", "description": f"First person POV. An accurate SVG picture of what the player sees (like the player can see their hands, tools, etc.). Accurately capture composition, and colors rather than complex details. This should be based on the {SCENE_SVG_INPUT_NAME} field and the description. This should not be a diagram."}
                        },
                        "required": ["first_person_description","first_person_svg"],
                        "additionalProperties": False,
                    },
                },
                "required": ["visuals"],
                "additionalProperties": False
            },
        }
    }
]
VISUAL_TOOL_CHOICE = {"type": "function", "function": {"name": "visual_output"}}