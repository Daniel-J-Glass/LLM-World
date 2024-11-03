import os
from dotenv import load_dotenv

load_dotenv("local.env")

# LLM Provider Settings
LLM_PROVIDER = "openai"  # or "openai"
ENGINE_LLM_PROVIDER = "openai"
VISUAL_LLM_PROVIDER = "openai"

# OpenAI Settings
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
OPENAI_DEFAULT_MODEL = "gpt-4o"  # or "gpt-4" if you have access

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

IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")
IMGUR_CLIENT_SECRET = os.getenv("IMGUR_CLIENT_SECRET")

VIDEO_GENERATION_MODEL = os.getenv("VIDEO_GENERATION_MODEL")
VIDEO_FIRST_PERSON_MODIFIER = "{prompt}"
VIDEO_GENERATION_KEY = os.getenv("RUNWAY_API_KEY")
CONTINUOUS_VIDEO = True

# Image generation modifiers
POSITIVE_STYLE_MODIFIER = "realism, POV, first person perspective"
FIRST_PERSON_MODIFIER = POSITIVE_STYLE_MODIFIER + ", {visual}"
NEGATIVE_STYLE_MODIFIER = "symmetric, artistic, unrealistic, painting", 

# 1 is more 0 is less
SVG_IMAGE_ARGS = {
    "control_strength": .3
}
SVG_IMAGE_ENDPOINT = "/v2beta/stable-image/control/sketch"
GENERATE_SVG = False

# Application Settings
DEBUG_MODE = True
LOG_FILE = "llm_world.log"

NARRATIVE_PARAMETER_NAME = "narrative" #used for streaming
SCENE_SVG_INPUT_NAME = "Scene SVG"
SVG_GENERATION_SYSTEM_PROMPT = "Generate first-person visuals based on the user's previous action, scene SVG, and scene description. Be highly descriptive and don't miss any details."

GAME_ENGINE_SYSTEM_PROMPT = "You are the game master for providing a narrative based experience for a fantasy world. Act as a game engine by interpretting the player's action and update the game accordingly."
VISUAL_ENGINE_SYSTEM_PROMPT = "Use the tools to AI generate an image. Use the Scene Description and Previous action to inform what image is generated."

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
                        "description": "Use this when the surroundings have changed. If it's a change to the existing scene, modify the old Scene Description. If it's a change to an entirely new location, create an entirely new scene_description.",
                        "properties": {
                            "scene_description": {"type": "string","description": "A highly descriptive and factual description of the player's surroundings. Include terrain, focal points, objects, entities, layout, colors, shapes, sounds, etc. Between 100-150 words"},
                            "tile_color": {"type": "string", "description": "The color representation of these surroundings on a minimap (like #FFFFFF)"}
                        },
                        "required":["scene_description", "tile_color"],
                        "additionalProperties": False,
                    },
                    "movement": {
                        "type": ["string", "null"],
                        "description": "Use this only if the player has moved more than 50 feet from their original location. Where the player moves in accordance with the narrative. (N, S, E, W)",
                        "enum": ["N", "S", "E", "W", "NONE"],
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
                "required": ["narrative", "events", "scene", "movement", "rule_updates"],
                "additionalProperties": False,
            },
        }
    }
]

CLAUDE_GAME_TOOLS = {
    "name": "game_output",
    "description": "Provide only the values necessary for a cohesive game experience based on the player action. Maintain consistency is key.",
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
                "description": "Use this when the surroundings have changed. If it's a change to the existing scene, modify the old Scene Description. If it's a change to an entirely new location, create an entirely new scene_description.",
                "properties": {
                    "scene_description": {"type": "string","description": "A highly descriptive and factual description of the player's surroundings. Include terrain, focal points, objects, entities, layout, colors, shapes, sounds, etc. Between 100-150 words"},
                    "tile_color": {"type": "string", "description": "The color representation of these surroundings on a minimap (like #FFFFFF)"}
                },
                "required":["scene_description", "tile_color"],
                "additionalProperties": False,
            },
            "movement": {
                "type": ["string", "null"],
                "description": "Use this only if the player has moved more than 50 feet from their original location. Where the player moves in accordance with the narrative. (N, S, E, W)",
                "enum": ["N", "S", "E", "W", "NONE"],
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
        "required": ["narrative", "events", "scene", "movement", "rule_updates"],
        "additionalProperties": False,
    }
}

GAME_TOOL_CHOICE = {"type": "function", "function": {"name": "game_output"}}

VISUAL_TOOLS = [
    {
        "type":"function",
        "function": {
            "name": "visual_output",
            "description": "Provide the visuals that result from the player action.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "visuals": {
                        "type": "object",
                        "description": "These properties are used to generate visuals with Stable Diffusion ControlNet and RunwayML. Consistency between them is key. Describe the visuals in a way that is easy to understand and generate.",
                        "properties": {
                            "first_person_description": {"type": "string", "description": "This is a detailed Stable Diffusion prompt. Do not miss any details. Highly detailed description of what the player sees in this situation (first person visuals). Use theory of mind to describe exactly and only what the player would be seeing."},
                            # "first_person_svg": {"type": "string", "description": f"This is used for ControlNet. First person POV. An accurate SVG picture of what the player sees (to match the above description). Accurately capture composition. If the player doesn't change scenes, base this on the {SCENE_SVG_INPUT_NAME} field and the description. If the user does change scenes, this should be completely different. This should not be a diagram."},
                            "first_person_video": {"type": "string", "description": "Use less than 400 characters. This is used for RunwayML video generation prompt. First person POV. An visual description of what the plaer sees based on their previous action and result in the next 5 seconds. Make the video start with the Previous Action and end on the Result. Describe camera movement that mirrors the player movement. If the player doesn't move, the camera shouldn't move."}
                        },
                        "required": ["first_person_description", "first_person_video"],
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
