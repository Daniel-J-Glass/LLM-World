import os
import regex as re
import anthropic
import openai
import logging
from typing import List, Dict, Optional, Generator
import config
import json

NARRATIVE_START_PATTERN = f'"{config.NARRATIVE_PARAMETER_NAME}"\\s*:\\s*"'
NARRATIVE_END_PATTERN = r'(?<!\\)("[(,\s*\")(\s*\})])'
NARRATIVE_PATTERN = NARRATIVE_START_PATTERN+r"([.\n]*)"+NARRATIVE_END_PATTERN

def initialize_client(provider):
    if provider == "anthropic":
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        return anthropic.Anthropic(api_key=api_key)
    elif provider == "openai":
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        return openai.Client(api_key=api_key)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

def create_message_stream(client,
                          chat_history: List[Dict[str, str]] = None,
                          system_prompt: str = "You are a helpful assistant.",
                          tools: List[Dict] = None,
                          tools_choice: Dict = None,
                          model:str = None,
                          max_tokens: int = config.MAX_TOKENS,
                          temperature: float = 0) -> Generator[str, None, Dict]:
    print(json.dumps(chat_history,indent=4))
    
    if config.LLM_PROVIDER == "anthropic":
        return create_anthropic_message_stream(client, chat_history, system_prompt, tools, tools_choice, config.ANTHROPIC_DEFAULT_MODEL, max_tokens, temperature)
    elif config.LLM_PROVIDER == "openai":
        return create_openai_message_stream(client, chat_history, system_prompt, tools, tools_choice, config.OPENAI_DEFAULT_MODEL, max_tokens, temperature)
    else:
        raise ValueError(f"Unsupported LLM provider: {config.LLM_PROVIDER}")

def create_anthropic_message_stream(client: anthropic.Anthropic,
                                    chat_history: List[Dict[str, str]] = None,
                                    system_prompt: str = "You are a helpful assistant.",
                                    tools: List[Dict] = None,
                                    tools_choice: Dict = None,
                                    model: str = config.ANTHROPIC_DEFAULT_MODEL,
                                    max_tokens: int = 1500,
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
            tools=tools,
            tool_choice=tools_choice
        ) as stream:
            tool_text = ""
            in_narrative = False

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
                    yield content.input

        yield None

    except Exception as e:
        logging.error(f"Error creating message: {e}")
        yield None

def create_openai_message_stream(client: openai.Client,
                                 chat_history: List[Dict[str, str]] = None,
                                 system_prompt: str = "You are a helpful assistant.",
                                 tools: List[Dict] = None,
                                 tools_choice: Dict = None,
                                 model: str = config.OPENAI_DEFAULT_MODEL,
                                 max_tokens: int = 1500,
                                 temperature: float = 0) -> Generator[str, None, Dict]:
    try:
        if chat_history is None:
            chat_history = []

        messages = [{"role": "system", "content": system_prompt}] + chat_history

        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            tool_choice=tools_choice,
            stream=True
        )

        tool_text = ""
        total_text = ""
        in_narrative = False
        
        for chunk in stream:
            if chunk.choices[0].delta.tool_calls:
                tool_call = chunk.choices[0].delta.tool_calls[0]
                if tool_call.function.arguments:
                    text = tool_call.function.arguments
                    tool_text += text
                    total_text +=text

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

        yield json.loads(total_text)

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
