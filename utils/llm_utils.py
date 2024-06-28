import os
import regex as re
import anthropic
import logging
from typing import List, Dict, Optional, Generator
import config
import json

NARRATIVE_START_PATTERN = f'"{config.NARRATIVE_PARAMETER_NAME}"\\s*:\\s*"'
NARRATIVE_END_PATTERN = r'(?<!\\)("[(,\s*\")(\s*\})])'
NARRATIVE_PATTERN = NARRATIVE_START_PATTERN+r"([.\n]*)"+NARRATIVE_END_PATTERN

def initialize_client() -> anthropic.Anthropic:
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


def create_message_stream(client: anthropic.Anthropic,
                          chat_history: List[Dict[str, str]] = None,
                          system_prompt: str = "You are a helpful assistant.",
                          model: str = "claude-3-5-sonnet-20240620",
                          max_tokens: int = 1000,
                          temperature: float = 0) -> Generator[str, None, Dict]:
    try:
        if chat_history is None:
            chat_history = []
        
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=chat_history,
            tools=config.TOOLS
        ) as stream:
            tool_text = ""
            narrative = ""
            in_narrative = False
            function_call = None

            for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "input_json_delta":
                    text = event.delta.partial_json
                    tool_text += text

                    if not in_narrative:
                        start_match = re.search(NARRATIVE_START_PATTERN, tool_text)
                        if start_match:
                            in_narrative = True
                            narrative_start = start_match.end()
                            tool_text = tool_text[narrative_start:]
                            yield tool_text
                    else:
                        end_match = re.search(NARRATIVE_END_PATTERN, tool_text)
                        if end_match:
                            tool_text = tool_text[:end_match.start()]
                            if text == tool_text[-len(text)-1:]:
                                yield text
                            in_narrative = False
                        else:
                            yield text
            
            message = stream.get_final_message()

            for content in message.content:
                if content.type == 'tool_use':
                    if content.name == 'game_output':
                        yield content.input

        yield None

    except Exception as e:
        logging.error(f"Error creating message: {e}")
        yield None

def update_chat_history(chat_history: List[Dict[str, str]], 
                        role: str, 
                        content: str, 
                        max_history: int = 10) -> List[Dict[str, str]]:
    chat_history.append({"role": role, "content": content})

    chat_history[-max_history:]

    # first message must be from user
    if chat_history[0].get("role") != "user":
        # lazily assuming 1 user 1 assistant back and forth
        chat_history = chat_history[1:]

    return chat_history
