import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json
import re
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
                          agent_name: str = None,
                          max_output_tokens: int = None) -> Any:
        """
        Generates a response from the LLM based on the provided messages.
        """
        pass
    
    def _inject_identity_lock(self, messages: List[Dict[str, str]], agent_name: str):
        pass

class OpenAIEngine(LLMEngine):
    def __init__(self, client, default_model: str):
        self.client = client
        self.model = default_model
        
    def generate_response(self, 
                          messages: List[Dict[str, str]], 
                          temperature: float = 0.2, 
                          response_format: Any = None, 
                          agent_name: str = None,
                          max_output_tokens: int = None) -> Any:
        self._inject_identity_lock(messages, agent_name)
        params = {"model": self.model, "messages": messages, "temperature": temperature}
        if max_output_tokens: params["max_tokens"] = max_output_tokens
        
        if response_format:
            try:
                response = self.client.chat.completions.create(**params)
                if hasattr(response, 'usage') and response.usage:
                    details = getattr(response.usage, 'prompt_tokens_details', None)
                    cached = getattr(details, 'cached_tokens', 0) if details else 0
                    cost_manager.add_usage(model_name=self.model, input_tokens=response.usage.prompt_tokens or 0, output_tokens=response.usage.completion_tokens or 0, cached_tokens=cached, agent_name=agent_name)
                raw_text = response.choices[0].message.content
                if not raw_text: return None
                clean_text = raw_text.strip()
                if clean_text.startswith("```json"): clean_text = clean_text[7:]
                elif clean_text.startswith("```"): clean_text = clean_text[3:]
                clean_text = clean_text.strip()
                if clean_text.endswith("```"): clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                try:
                    parsed_dict = json.loads(clean_text)
                    return response_format.model_validate(parsed_dict)
                except:
                    # Generic repair logic for OpenAI
                    start_idx = clean_text.find('{')
                    final_idx = clean_text.rfind('}')
                    if start_idx != -1 and final_idx != -1:
                        parsed_dict = json.loads(clean_text[start_idx:final_idx+1])
                        return response_format.model_validate(parsed_dict)
                return None
            except Exception as e:
                logger.error(f"OpenAIEngine failure: {e}")
                return None
        
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content

class NativeGeminiEngine(LLMEngine):
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None: cls._instance = cls()
        return cls._instance

    def __init__(self):
        logging.getLogger("google_genai._api_client").setLevel(logging.ERROR)
        logging.getLogger("google_genai.models").setLevel(logging.ERROR)
        from google import genai
        from tinytroupe import utils
        import os
        config = utils.read_config_file()
        self.model = config["OpenAI"].get("MODEL", "gemini-2.5-flash-lite")
        self.max_attempts = 10
        self.waiting_time = 3.0
        self.backoff_factor = 2.0
        gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
        gcp_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        if gcp_project:
            self.client = genai.Client(vertexai=True, project=gcp_project, location=gcp_location)
        else:
            self.client = genai.Client()
        if self.model.startswith("models/"): self.model = self.model.replace("models/", "")
        logger.info(f"NativeGeminiEngine initialized: {self.model}")

    def generate_response(self, 
                          messages: List[Dict[str, str]], 
                          temperature: float = None, 
                          response_format: Any = None, 
                          agent_name: str = None,
                          max_output_tokens: int = None,
                          frequency_penalty: float = None,
                          presence_penalty: float = None) -> Any:
        from google.genai import types
        self._inject_identity_lock(messages, agent_name)
        cache_id = os.getenv("TINYTRUCE_CURRENT_CACHE")
        valid_cache = cache_id and ("/cachedContents/" in cache_id)
        if valid_cache: cache_id = "cachedContents/" + cache_id.split("/cachedContents/")[-1]
        
        system_instructions = []
        gemini_messages = []
        current_role = None
        current_parts = []
        
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role")
            
            # [TINYTRUCE] System role is strictly for instruction parameter, NOT contents.
            if role == "system":
                system_instructions.append(content)
                continue
            
            # Map roles correctly
            if role == "assistant": role = "model"
            elif role == "user": role = "user"
            else: role = "user" # Default safest
            
            speaker = msg.get("name")
            if speaker and speaker != agent_name: content = f"[{speaker}]: {content}"
            
            if role == current_role:
                current_parts.append(types.Part.from_text(text=f"\n\n{content}"))
            else:
                if current_role: gemini_messages.append(types.Content(role=current_role, parts=current_parts))
                current_role = role
                current_parts = [types.Part.from_text(text=content)]
        
        if current_role: gemini_messages.append(types.Content(role=current_role, parts=current_parts))
        
        # Consolidate instructions
        system_instruction = "\n\n".join(system_instructions) if system_instructions else None
        
        # [TINYTRUCE] Gemini API Policy Guard:
        # "Tool config, tools and system instruction should not be set in the request when using cached content."
        # If we have a cache ID, we must merge the system instruction into the prompt contents.
        if valid_cache and system_instruction:
            logger.debug(f"[CACHE-SAFETY] Merging System Instruction into prompt for {agent_name} to avoid API collision.")
            if gemini_messages and len(gemini_messages) > 0:
                # Prepend to the first part of the first message
                instruction_header = f"### AGENT IDENTITY & PROTOCOL ###\n{system_instruction}\n\n"
                gemini_messages[0].parts[0].text = instruction_header + gemini_messages[0].parts[0].text
            else:
                # Add a new user message if no messages exist yet
                gemini_messages.append(types.Content(role="user", parts=[types.Part.from_text(text=f"### AGENT IDENTITY & PROTOCOL ###\n{system_instruction}")]))
            system_instruction = None # Clear it so it won't be set in config_kwargs

        config_kwargs = {}
        if max_output_tokens: config_kwargs["max_output_tokens"] = max_output_tokens
        if system_instruction: config_kwargs["system_instruction"] = system_instruction
        if valid_cache: config_kwargs["cached_content"] = cache_id
        if response_format:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_format

        # --- [TINYTRUCE] ACTION ITEM 4: SOFT REDLINE FALLBACK RETRY LOOP ---
        max_soft_retries = 2
        last_failure_reason = "Initial logic error"
        base_messages = [m for m in gemini_messages]
        
        for soft_attempt in range(max_soft_retries + 1):
            import random
            import time
            
            # [TINYTRUCE] ACTION ITEM 3/6: Stochastic Pivot & Deterministic Temp
            # If temp is passed (Pivot Mode), use it. Otherwise default to narrow stability (0.4/0.3).
            pivot_temp = temperature if temperature is not None else (0.4 if soft_attempt == 0 else 0.3)
            config_kwargs["temperature"] = pivot_temp
            
            # [TINYTRUCE] Phase 6: Frequency & Presence Penalties for Repetition Breaks
            if frequency_penalty is not None: config_kwargs["frequency_penalty"] = frequency_penalty
            if presence_penalty is not None: config_kwargs["presence_penalty"] = presence_penalty

            # [TINYTRUCE] Phase 6: Semantic Drift Guardrail
            # If entropy is high, inject a hidden anchor to maintain core persona.
            current_messages = [m for m in base_messages]
            if pivot_temp > 1.0:
                anchor_diag = "### [SYSTEM ANCHOR] ###\nMaintain core persona constraints strictly while exploring new vocabulary and rhetorical paths. Do not drift into generic AI or unrelated archetypes."
                if current_messages[-1].role == "user":
                    current_messages[-1].parts[0].text += f"\n\n{anchor_diag}"
                else:
                    current_messages.append(types.Content(role="user", parts=[types.Part.from_text(text=anchor_diag)]))

            if soft_attempt > 0:
                diag = f"[SYSTEM DIAGNOSTIC]: Your previous output failed constraints ({last_failure_reason}). Provide a standard, safe diplomatic response addressing the last point. Avoid '[No action]'."
                if current_messages[-1].role == "user":
                    current_messages[-1].parts[0].text += f"\n\n{diag}"
                else:
                    current_messages.append(types.Content(role="user", parts=[types.Part.from_text(text=diag)]))
                logger.warning(f"Soft Redline Loop: Attempt {soft_attempt+1} for {agent_name}. Reason: {last_failure_reason}")

            # Transient Error Loop
            response = None
            for attempt in range(self.max_attempts):
                try:
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=current_messages,
                        config=types.GenerateContentConfig(**config_kwargs)
                    )
                    break 
                except Exception as e:
                    # [TINYTRUCE] CACHE RESILIENCY FALLBACK
                    # If the cache is in an invalid state (e.g. still being flushed/created in background),
                    # we do NOT want to crash the whole sim. We drop the cache for this request and retry once.
                    if "Invalid resource state for cache content" in str(e) or "cached_content" in str(e).lower():
                        logger.warning(f"Gemini Cache Error: {e}. Dropping cache from request and retrying for {agent_name}...")
                        if "cached_content" in config_kwargs:
                            del config_kwargs["cached_content"]
                        # Retry immediately without the cache
                        continue

                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        wait = self.waiting_time * (self.backoff_factor ** attempt) * random.uniform(0.8, 1.2)
                        logger.warning(f"429 for {agent_name}. Backing off {wait:.2f}s...")
                        time.sleep(wait)
                        if attempt == self.max_attempts - 1: raise e
                        continue
                    raise e
            
            if not response or not response.text:
                last_failure_reason = "Empty response"
                continue

            try:
                u = response.usage_metadata
                cost_manager.add_usage(model_name=self.model, input_tokens=max(0, (u.prompt_token_count or 0) - (u.cached_content_token_count or 0)), output_tokens=u.candidates_token_count or 0, cached_tokens=u.cached_content_token_count or 0, agent_name=agent_name)
            except: pass
            
            raw = response.text.strip()
            if raw.startswith("```json"): raw = raw[7:]
            elif raw.startswith("```"): raw = raw[3:]
            raw = raw.strip()
            if raw.endswith("```"): raw = raw[:-3]
            raw = raw.strip()
            
            # Redline Detection
            if len(raw) < 5:
                last_failure_reason = "Empty content"
                continue
            if "[No action]" in raw or "[No Action]" in raw:
                last_failure_reason = "Redline paralysis ([No action])"
                continue

            if response_format:
                try:
                    result = response_format.model_validate_json(raw)
                    # Check both singular 'action' and plural 'actions' list
                    has_action = result.action and (result.action.type != "TALK" or result.action.content)
                    has_actions = result.actions and len(result.actions) > 0 and any(a.content for a in result.actions)
                    
                    if has_action or has_actions:
                        return result
                    last_failure_reason = "Action content empty"
                except Exception as e:
                    # Repair: Attempt to find and validate the largest possible JSON object
                    try:
                        import json
                        start = raw.find('{')
                        end = raw.rfind('}')
                        
                        # [REPAIR] JSON Autoclose: If it looks truncated (missing closing brace), try to heal it.
                        if raw.count('{') > raw.count('}'):
                            raw += '}' * (raw.count('{') - raw.count('}'))
                            end = len(raw) - 1
                            # If it's still missing quotes for a value, this is harder, 
                            # but usually adding braces helps json.loads if the truncation is at a boundary.

                        if start != -1 and end != -1:
                            d = json.loads(raw[start:end+1])
                            # If they gave 'actions' but not 'action', populate 'action' for compatibility
                            if 'actions' in d and (not d.get('action')):
                                if isinstance(d['actions'], list) and len(d['actions']) > 0:
                                    d['action'] = d['actions'][0]
                            
                            if 'cognitive_state' not in d:
                                d['cognitive_state'] = {"attention": "Active", "emotions": "Neutral"}
                            
                            result = response_format.model_validate(d)
                            has_action = result.action and (result.action.type != "TALK" or result.action.content)
                            has_actions = result.actions and len(result.actions) > 0 and any(a.content for a in result.actions)
                            
                            if has_action or has_actions:
                                return result
                    except: 
                        # FINAL DUMB EXTRACTION: If JSON is broken, try to harvest anything in 'content' fields using regex.
                        logger.warning(f"JSON repair failed for {agent_name}. Harvesting raw content via regex.")
                        import re
                        contents = re.findall(r'"content":\s*"([^"]*)"', raw)
                        if contents:
                            # Join all harvested content into a single TALK action
                            display_text = " ".join(contents).strip()
                            if len(display_text) > 10:
                                try:
                                    emergency_action = {"type": "TALK", "content": display_text[:1000], "target": "everyone"}
                                    emergency_state = {"goals": "Tactical recovery.", "attention": "Active", "emotions": "Neutral"}
                                    return response_format.model_validate({"action": emergency_action, "cognitive_state": emergency_state, "thought": "Harvested raw content from malformed JSON to preserve dialogue."})
                                except: pass

                    last_failure_reason = f"JSON Error: {str(e)[:40]}"
                    
                    # [TINYTRUCE] SILENCE PREVENTION: Only wrap if it DOESN'T look like JSON.
                    # If it starts with '{', we NEVER want to print it as cleartext.
                    if len(raw) > 10 and not raw.strip().startswith("{"):
                        try:
                            logger.info(f"Soft Redline: Wrapping malformed output as TALK for {agent_name}")
                            # Strip common markers if they exist in the raw text
                            display_text = raw.replace("```json", "").replace("```", "").strip()
                            emergency_action = {"type": "TALK", "content": display_text[:1000], "target": "everyone"}
                            emergency_state = {"goals": "Maintain posture.", "attention": "Active", "emotions": "Neutral"}
                            return response_format.model_validate({"action": emergency_action, "cognitive_state": emergency_state, "thought": "Auto-wrapped non-JSON response to prevent simulation silence."})
                        except: pass
                continue
            else:
                return raw
                
        logger.error(f"CRITICAL: {agent_name} failed all retries. Last: {last_failure_reason}")
        
        # [TINYTRUCE] EMERGENCY FALLBACK: Never return None to avoid simulation hangs.
        if response_format:
            try:
                emergency_action = {"type": "TALK", "content": "[SYSTEM ADVISORY]: Direct engagement protocol temporarily suspended. Maintaining strategic posture.", "target": "everyone"}
                emergency_state = {"goals": "Maintain continuity.", "attention": "Internalized", "emotions": "Neutral"}
                return response_format.model_validate({
                    "action": emergency_action,
                    "cognitive_state": emergency_state,
                    "thought": f"Emergency recovery triggered due to persistent validation failure: {last_failure_reason}"
                })
            except:
                # Even if pydantic fails, return the simplest possible valid-looking object
                return None # Last resort but should be unreachable with valid model_validate
        
        return "[SYSTEM ERROR]: Persistent failure. Consult logs."
