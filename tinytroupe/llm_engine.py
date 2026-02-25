import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json
from tinytroupe.cost_manager import cost_manager

logger = logging.getLogger("tinytroupe")

class LLMEngine(ABC):
    """
    Abstract base class for Large Language Model engines.
    Provides a standardized interface to decouple specific provider SDKs
    from the core TinyTroupe simulation logic.
    """
    
    @abstractmethod
    def generate_response(self, 
                          messages: List[Dict[str, str]], 
                          temperature: float = 0.2, 
                          response_format: Any = None, 
                          agent_name: str = None) -> Any:
        """
        Generates a response from the LLM based on the provided messages.
        
        Args:
            messages: A list of message dictionaries (e.g., [{"role": "user", "content": "..."}]).
            temperature: The sampling temperature.
            response_format: A Pydantic model class to enforce structured JSON output.
            agent_name: Optional name of the agent calling the model, used for identity locking.
            
        Returns:
            The raw text response from the model, or a parsed Pydantic object if response_format was provided.
        """
        pass
    
    def _inject_identity_lock(self, messages: List[Dict[str, str]], agent_name: str):
        """
        Injects a critical identity lock right before inference to combat
        Context Caching amnesia and strict JSON schema name stripping.
        Modifies the messages list in-place.
        """
        if agent_name:
            lock_text = f"\n\n[SYSTEM INSTRUCTION]: CRITICAL IDENTITY LOCK: You are {agent_name}. You MUST refer to yourself as {agent_name}. DO NOT refer to anyone as 'Agent 1', 'Agent 2', etc. Your turn ONLY consists of 1 or 2 actions. If you just used a 'TALK' or 'THINK' action, you MUST immediately output a 'DONE' action next to yield your turn. Output your response as a strict JSON."
            
            # Append the lock to the last user message to avoid 'poking' the LLM
            # with a brand new turn, which causes infinite action loops.
            for msg in reversed(messages):
                if msg.get("role") == "user" or msg.get("role") == "system":
                    msg["content"] += lock_text
                    return
            
            # Fallback if no user/system messages exist (should not happen in TinyTroupe)
            messages.append({
                "role": "user",
                "content": lock_text.strip()
            })

class OpenAIEngine(LLMEngine):
    """
    Implementation for generating responses using the standard OpenAI client.
    """
    def __init__(self, client, default_model: str):
        self.client = client
        self.model = default_model
        
    def generate_response(self, 
                          messages: List[Dict[str, str]], 
                          temperature: float = 0.2, 
                          response_format: Any = None, 
                          agent_name: str = None) -> Any:
        
        self._inject_identity_lock(messages, agent_name)
        
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if response_format:
            # Enforce structured output parsing via beta.chat.completions.parse
            # (Requires newer OpenAI SDK)
            try:
                response = self.client.beta.chat.completions.parse(
                    **params,
                    response_format=response_format
                )
                return response.choices[0].message.parsed
            except Exception as e:
                logger.error(f"Failed to parse structured output with OpenAI Engine: {e}")
                
        # Fallback or standard generation
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content


class NativeGeminiEngine(LLMEngine):
    """
    Implementation for generating responses using the native google-genai SDK.
    Designed to tightly control Explicit Context Caching and structured output matching.
    """
    def __init__(self):
        # Suppress noisy SDK warnings
        logging.getLogger("google_genai._api_client").setLevel(logging.ERROR)
        logging.getLogger("google_genai.models").setLevel(logging.ERROR)
        
        from google import genai
        self.client = genai.Client()
        # Locked per architectural requirements
        self.model = "gemini-2.5-flash-lite-preview-09-2025"
        
    def generate_response(self, 
                          messages: List[Dict[str, str]], 
                          temperature: float = 0.2, 
                          response_format: Any = None, 
                          agent_name: str = None) -> Any:
        
        from google.genai import types
        
        # Inject the identity lock first
        self._inject_identity_lock(messages, agent_name)
        
        cache_id = os.getenv("TINYTRUCE_CURRENT_CACHE")
        
        gemini_messages = []
        for msg in messages:
            # The Context Cache handles Layer 0 grounding, but the system msg here contains 
            # the core TinyTroupe instructions (tiny_person.mustache) dictating the loop/DONE mechanics.
            # We MUST not drop it. Since explicit caching forbids the `system_instruction` config,
            # we simply wrap the system instruction as the very first user message.
            if msg.get("role") == "system":
                sys_content = msg.get("content", "")
                if sys_content:
                    gemini_messages.append(
                        types.Content(role="user", parts=[types.Part.from_text(text=f"System Instruction:\n{sys_content}")])
                    )
                continue
                
            role = "model" if msg.get("role") == "assistant" else "user"
            content = msg.get("content", "")
            
            # TinyTroupe uses 'name', we prefix it on the string since Gemini Content drops it
            speaker = msg.get("name")
            if speaker and speaker != agent_name:
                 content = f"[{speaker}]: {content}"
                 
            gemini_messages.append(
                types.Content(role=role, parts=[types.Part.from_text(text=content)])
            )
            
        config_kwargs = {
            "temperature": temperature
        }
        
        if cache_id:
            config_kwargs["cached_content"] = cache_id
            
        if response_format:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_format
            
        response = self.client.models.generate_content(
            model=self.model,
            contents=gemini_messages,
            config=types.GenerateContentConfig(**config_kwargs)
        )
        
        # Capture usage metadata for cost analysis
        try:
            usage = response.usage_metadata
            input_tokens = usage.prompt_token_count or 0
            output_tokens = usage.candidates_token_count or 0
            cached_tokens = usage.cached_content_token_count or 0
            
            cost_manager.add_usage(
                model_name=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
                agent_name=agent_name
            )
            
            logger.debug(f"Cost recorded for {agent_name or 'System'}: {input_tokens} in, {output_tokens} out, {cached_tokens} cached.")
        except Exception as e:
            logger.warning(f"Failed to record cost metadata: {e}")
        
        raw_text = response.text
        if raw_text:
            raw_text = raw_text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
                
            raw_text = raw_text.strip()
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
        raw_text = raw_text.strip()
        
        if response_format:
            try:
                return response_format.model_validate_json(raw_text)
            except Exception as e:
                try:
                    import re
                    import json
                    
                    # Non-greedy search for top-level objects
                    json_matches = re.finditer(r'\{.*?\}', raw_text, re.DOTALL)
                    for match in json_matches:
                        potential_json = match.group(0)
                        try:
                            parsed_dict = json.loads(potential_json)
                            # We MUST have an action to proceed with the simulation.
                            if isinstance(parsed_dict, dict) and 'action' in parsed_dict:
                                return response_format.model_validate(parsed_dict)
                        except (json.JSONDecodeError, Exception):
                            # If a simple match fails, it might be due to nested braces.
                            # We try to find the matching closing brace for the first {
                            start_idx = raw_text.find('{')
                            if start_idx != -1:
                                stack = 0
                                end_idx = -1
                                for i in range(start_idx, len(raw_text)):
                                    if raw_text[i] == '{': stack += 1
                                    elif raw_text[i] == '}': 
                                        stack -= 1
                                        if stack == 0:
                                            end_idx = i
                                            break
                                if end_idx != -1:
                                    try:
                                        potential_json = raw_text[start_idx:end_idx+1]
                                        parsed_dict = json.loads(potential_json)
                                        if isinstance(parsed_dict, dict) and 'action' in parsed_dict:
                                            return response_format.model_validate(parsed_dict)
                                    except:
                                        pass
                except Exception as inner_e:
                    logger.error(f"Failed to extract native JSON via Regex: {inner_e}")
                
                return None
                
        return raw_text
