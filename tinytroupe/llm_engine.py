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
                          agent_name: str = None,
                          max_output_tokens: int = None) -> Any:
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
        [DEPRECATED] Identity lock injection is now handled via proper system instruction 
        passing to avoid prompt/schema clashes in native LLM engines.
        """
        pass

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
                          agent_name: str = None,
                          max_output_tokens: int = None) -> Any:
        
        self._inject_identity_lock(messages, agent_name)
        
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        if max_output_tokens:
            params["max_tokens"] = max_output_tokens
        
        if response_format:
            # We must manually validate/parse the JSON since proxy doesn't support .parse()
            try:
                import json
                
                # Standard call
                response = self.client.chat.completions.create(**params)
                
                # Capture usage metadata
                if hasattr(response, 'usage') and response.usage:
                    details = getattr(response.usage, 'prompt_tokens_details', None)
                    cached = getattr(details, 'cached_tokens', 0) if details else 0
                    cost_manager.add_usage(
                        model_name=self.model,
                        input_tokens=response.usage.prompt_tokens or 0,
                        output_tokens=response.usage.completion_tokens or 0,
                        cached_tokens=cached, 
                        agent_name=agent_name
                    )

                raw_text = response.choices[0].message.content
                if not raw_text:
                    return None

                # Clean markdown blocks if present
                clean_text = raw_text.strip()
                if clean_text.startswith("```json"): clean_text = clean_text[7:]
                elif clean_text.startswith("```"): clean_text = clean_text[3:]
                clean_text = clean_text.strip()
                if clean_text.endswith("```"): clean_text = clean_text[:-3]
                clean_text = clean_text.strip()

                parsed_dict = None
                try:
                    parsed_dict = json.loads(clean_text)
                    return response_format.model_validate(parsed_dict)
                except Exception as eval_e:
                    logger.debug(f"OpenAIEngine initial validation failed: {eval_e}. Attempting repair...")
                    try:
                        import re
                        # Hardened Extraction: Find the character-balanced outermost braces.
                        start_idx = clean_text.find('{')
                        if start_idx != -1:
                            stack = 0
                            final_idx = -1
                            for i in range(start_idx, len(clean_text)):
                                if clean_text[i] == '{': stack += 1
                                elif clean_text[i] == '}': 
                                    stack -= 1
                                    if stack == 0:
                                        final_idx = i
                                        break
                            
                            if final_idx != -1:
                                potential_json = clean_text[start_idx:final_idx+1]
                                parsed_dict = json.loads(potential_json)
                                
                                # Inject defaults if missing
                                if 'action' in parsed_dict and isinstance(parsed_dict['action'], str):
                                    parsed_dict['action'] = {"type": "TALK", "content": parsed_dict['action'], "target": "everyone"}
                                if 'cognitive_state' not in parsed_dict:
                                    parsed_dict['cognitive_state'] = {"goals": "Continue.", "attention": "Active.", "emotions": "Neutral", "emotional_intensity": 0.5}
                                
                                return response_format.model_validate(parsed_dict)
                    except Exception as repair_e:
                        logger.warning(f"OpenAIEngine JSON repair failed: {repair_e}")

                # Final Fallback: Raw Text Recovery
                if clean_text and len(clean_text) > 5:
                    logger.warning(f"OpenAIEngine recovering raw text as TALK action for {agent_name or 'System'}.")
                    reconstructed = {
                        "action": {"type": "TALK", "content": clean_text, "target": "everyone"},
                        "cognitive_state": {"goals": "Continue.", "attention": "Active.", "emotions": "Neutral", "emotional_intensity": 0.5}
                    }
                    try:
                        return response_format.model_validate(reconstructed)
                    except:
                        pass

                return None
            except Exception as e:
                logger.error(f"Failed to parse structured output with OpenAI Engine: {e}")
                return None

                
        # Standard generation
        response = self.client.chat.completions.create(**params)
        
        # Capture usage metadata
        if hasattr(response, 'usage') and response.usage:
            details = getattr(response.usage, 'prompt_tokens_details', None)
            cached = getattr(details, 'cached_tokens', 0) if details else 0
            cost_manager.add_usage(
                model_name=self.model,
                input_tokens=response.usage.prompt_tokens or 0,
                output_tokens=response.usage.completion_tokens or 0,
                cached_tokens=cached,
                agent_name=agent_name
            )
            
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
        from tinytroupe import utils
        import os
        
        config = utils.read_config_file()
        self.model = config["OpenAI"].get("MODEL", "gemini-2.5-flash-lite")
        self.max_attempts = 10 # Hardened for Production High-Intensity Runs
        self.waiting_time = 3.0 # Increased for better Vertex AI quota compliance
        self.backoff_factor = float(config["OpenAI"].get("EXPONENTIAL_BACKOFF_FACTOR", "2.0"))
        
        # Determine if we should use Vertex AI mode
        gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
        gcp_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        if gcp_project:
            logger.info(f"NativeGeminiEngine initializing in Vertex AI mode for project {gcp_project}")
            self.client = genai.Client(
                vertexai=True,
                project=gcp_project,
                location=gcp_location
            )
        else:
            logger.info("NativeGeminiEngine initializing in AI Studio mode")
            self.client = genai.Client()
            
        # Strip 'models/' prefix for consistency across engines if present
        if self.model.startswith("models/"):
            self.model = self.model.replace("models/", "")
            
        logger.info(f"NativeGeminiEngine initialized with model: {self.model}")
        
    def generate_response(self, 
                          messages: List[Dict[str, str]], 
                          temperature: float = 0.2, 
                          response_format: Any = None, 
                          agent_name: str = None,
                          max_output_tokens: int = None) -> Any:
        
        from google.genai import types
        
        # Inject the identity lock first
        self._inject_identity_lock(messages, agent_name)
        
        cache_id = os.getenv("TINYTRUCE_CURRENT_CACHE")
        valid_cache = cache_id and ("/cachedContents/" in cache_id)
        if valid_cache:
             # Ensure we use the relative path 'cachedContents/{id}' regardless of full resource name
             cache_id = "cachedContents/" + cache_id.split("/cachedContents/")[-1]
        
        system_instruction = None
        gemini_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if msg.get("role") == "system":
                if not valid_cache:
                    system_instruction = content
                else:
                    # If caching is active, we cannot provide system_instruction separately.
                    # We wrap it sparingly without the 'Identity Lock' garbage.
                    gemini_messages.append(
                        types.Content(role="user", parts=[types.Part.from_text(text=f"Instructions:\n{content}")])
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
        if max_output_tokens:
            config_kwargs["max_output_tokens"] = max_output_tokens
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        
        if valid_cache:
            config_kwargs["cached_content"] = cache_id
            
        if response_format:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_format
            
        import time
        import random
        max_retries = self.max_attempts
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=gemini_messages,
                    config=types.GenerateContentConfig(**config_kwargs)
                )
                break 
            except Exception as e:
                # If it's a 429 Resource Exhausted, backoff and retry
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    # Jittered Exponential Backoff
                    jitter = random.uniform(0.8, 1.2)
                    wait = self.waiting_time * (self.backoff_factor ** attempt) * jitter
                    logger.warning(f"429 Resource Exhausted for {agent_name or 'System'}. Backing off for {wait:.2f}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    if attempt == max_retries - 1:
                        raise e # Give up on last attempt
                    continue
                raise e # Re-raise other errors
        
        # Capture usage metadata for cost analysis
        try:
            usage = response.usage_metadata
            input_tokens = (usage.prompt_token_count or 0) - (usage.cached_content_token_count or 0)
            output_tokens = usage.candidates_token_count or 0
            cached_tokens = usage.cached_content_token_count or 0
            
            cost_manager.add_usage(
                model_name=self.model,
                input_tokens=max(0, input_tokens), # Ensure non-negative
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
                logger.debug(f"\\n[DEBUG] NativeGeminiEngine Raw Response for {agent_name}:\\n{raw_text}\\n")
                return response_format.model_validate_json(raw_text)
            except Exception as e:
                logger.debug(f"[DEBUG] Selection failure for {agent_name}: {e}")
                logger.debug(f"Initial Pydantic validation failed for {agent_name}: {e}. Attempting manual extraction/repair...")
                try:
                    import re
                    import json
                    
                    # Hardened Extraction: Find the character-balanced outermost braces.
                    start_idx = raw_text.find('{')
                    if start_idx != -1:
                        stack = 0
                        final_idx = -1
                        for i in range(start_idx, len(raw_text)):
                            if raw_text[i] == '{': stack += 1
                            elif raw_text[i] == '}': 
                                stack -= 1
                                if stack == 0:
                                    final_idx = i
                                    break # We found the primary object
                        
                        if final_idx != -1:
                            potential_json = raw_text[start_idx:final_idx+1]
                            try:
                                parsed_dict = json.loads(potential_json)
                                
                                # REPAIR LOGIC:
                                # 0. Handle 'actions' (plural) if model glitched into batch mode outside eco-mode
                                if 'actions' in parsed_dict and isinstance(parsed_dict['actions'], list) and len(parsed_dict['actions']) > 0:
                                    if 'action' not in parsed_dict or not parsed_dict['action']:
                                        parsed_dict['action'] = parsed_dict['actions'][0]
                                        logger.debug(f"[REPAIR] Extracted primary action from glitched 'actions' batch for {agent_name}.")

                                # 1. Clean [SYSTEM INSTRUCTION] and other noise from all string fields
                                def recursive_clean(d):
                                    if isinstance(d, dict):
                                        for k, v in d.items():
                                            if isinstance(v, str):
                                                if "[SYSTEM INSTRUCTION]" in v:
                                                    v = v.split("[SYSTEM INSTRUCTION]")[0].strip()
                                                # Remove thinking tags if leaked inside fields
                                                v = re.sub(r'<(?:THINK|RECALL|CONSULT).*?>', '', v).strip()
                                                d[k] = v
                                            else:
                                                recursive_clean(v)
                                    elif isinstance(d, list):
                                        for i in range(len(d)):
                                            if isinstance(d[i], str):
                                                if "[SYSTEM INSTRUCTION]" in d[i]:
                                                    d[i] = d[i].split("[SYSTEM INSTRUCTION]")[0].strip()
                                                d[i] = re.sub(r'<(?:THINK|RECALL|CONSULT).*?>', '', d[i]).strip()
                                            else:
                                                recursive_clean(d[i])
                                
                                recursive_clean(parsed_dict)
                                
                                # 2. Handle 'action' as string if model glitched
                                if 'action' in parsed_dict and isinstance(parsed_dict['action'], str):
                                    parsed_dict['action'] = {"type": "TALK", "content": parsed_dict['action'], "target": "everyone"}
                                
                                # 3. Handle missing fields by providing minimal defaults to satisfy Pydantic
                                if 'cognitive_state' not in parsed_dict:
                                    parsed_dict['cognitive_state'] = {"goals": "Continue.", "attention": "Active.", "emotions": "Neutral", "emotional_intensity": 0.5}

                                # 4. [TINYTRUCE] Silence Prevention Logic:
                                # If 'action' is null but 'thought' or 'actions' exists, or if turn leaked purely into 'thought' field.
                                raw_action = parsed_dict.get('action')
                                if not raw_action or (isinstance(raw_action, dict) and raw_action.get('type') == 'TALK' and not raw_action.get('content')):
                                    thought_content = parsed_dict.get('thought', raw_text)
                                    if thought_content and len(thought_content.strip()) > 5:
                                        # Convert the internal thought/yield into a visible TALK action so the turn isn't skipped.
                                        # We use a 'Forensic Pause' marker if the thought is purely logic-focused.
                                        is_logic = any(x in thought_content.upper() for x in ["SYSTEMIC", "COHERENCE", "VARIABLE", "CALCULAT", "ECONOM", "FISCAL"])
                                        
                                        # Special markers for explosive agents
                                        if "MILEI" in agent_name.upper():
                                            prefix = "[¡AFUERA! Milei ruptures the silence with a fiscal chainsaw...]"
                                        elif is_logic:
                                            prefix = f"[{agent_name} pauses to calculate systemic variables...]"
                                        else:
                                            prefix = f"[{agent_name} remains silent, weighing the moral cost...]"
                                        
                                        parsed_dict['action'] = {
                                            "type": "TALK", 
                                            "content": f"{prefix}\n\n{thought_content[:400]}...", 
                                            "target": "everyone"
                                        }
                                        logger.info(f"[REPAIR] Converted null/empty action into Forensic Pause for {agent_name} to prevent silent turn.")

                                return response_format.model_validate(parsed_dict)
                            except Exception as parse_e:
                                logger.warning(f"Manual extraction failed for {agent_name}: {parse_e}")
                    
                    # Final Fallback: If JSON failed entirely but we have text, wrap it into a TALK action.
                    # This prevents the simulation from crashing or defaulting to an emergency DONE.
                    if raw_text and len(raw_text.strip()) > 5:
                        # Truncate to prevent massive context/file bloat (e.g., 600KB glitches)
                        safe_content = raw_text.strip()
                        if len(safe_content) > 10000:
                            safe_content = safe_content[:10000] + "... [TRUNCATED DUE TO EXCESSIVE LENGTH]"
                        
                        logger.warning(f"JSON repair failed for {agent_name or 'System'}. Recovering content as TALK action (Truncated if necessary).")
                        
                        # We return a list of actions to satisfy both single and until_done loops, 
                        # enforcing a DONE to prevent infinite recovery cycles.
                        reconstructed = {
                            "action": {
                                "type": "TALK",
                                "content": safe_content,
                                "target": "everyone"
                            },
                            "cognitive_state": {
                                "goals": "Emergency turn termination due to LLM glitch.",
                                "attention": "System stability.",
                                "emotions": "Functional",
                                "emotional_intensity": 1.0
                            }
                        }
                        
                        # Note: If TinyPerson.act is called with until_done=True, 
                        # it will only stop if it sees a DONE action in the sequence.
                        # However, since we return a single action here, the caller 
                        # will execute it and then call us again. 
                        # A better way is to provide the content and then let the next call fail 
                        # or provide a way to inject DONE. 
                        # For now, truncation is the most critical safety valve.
                        try:
                            return response_format.model_validate(reconstructed)
                        except Exception as final_e:
                            logger.error(f"Failed to wrap raw text into action for {agent_name or 'System'}: {final_e}")
                    
                    # Log the malformed text for debugging
                    logger.warning(f"CRITICAL: {agent_name or 'System'} generated unrecoverable response. Raw response follows:\n{raw_text[:1000]}")
                except Exception as inner_e:
                    logger.error(f"Internal error during JSON repair for {agent_name}: {inner_e}")
                
                return None
                
        return raw_text
