import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, ValidationError, ConfigDict, Field

logger = logging.getLogger("tinytroupe")

################################################################################
# PERSONA SCHEMAS
################################################################################

class OccupationSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    title: str
    description: str

class BigFiveSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    openness: str
    conscientiousness: str
    extraversion: str
    agreeableness: str
    neuroticism: str

class PersonalitySchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    traits: Optional[List[str]] = None
    big_five: Optional[BigFiveSchema] = None

class CommunicationSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    style: Optional[str] = None
    patterns: Optional[List[str]] = None
    vocabulary_priority: Optional[List[str]] = None
    tonality: Optional[str] = None

class BehaviorSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    routine: Optional[List[str]] = None
    general: Optional[List[str]] = None
    conflict: Optional[List[str]] = None

class RelationshipSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    name: str
    relation_description: str

class PreferenceSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    likes: Optional[List[str]] = None
    dislikes: Optional[List[str]] = None
    interests: Optional[List[str]] = None

class PersonaDetailsSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    name: Optional[str] = None
    description: Optional[str] = None
    age: Optional[Union[int, str]] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[OccupationSchema] = None
    personality: Optional[PersonalitySchema] = None
    beliefs: Optional[List[str]] = None
    communication: Optional[CommunicationSchema] = None
    full_name: Optional[str] = None
    redlines: Optional[List[str]] = None
    skills: Optional[Union[List[str], Dict[str, Any]]] = None
    behaviors: Optional[Union[BehaviorSchema, Dict[str, Any]]] = None
    relationships: Optional[Union[List[RelationshipSchema], Dict[str, Any]]] = None
    preferences: Optional[Union[PreferenceSchema, Dict[str, Any]]] = None
    routine: Optional[Union[List[str], Dict[str, Any]]] = None
    deep_profile: Optional[str] = None
    filter_proxy_response: Optional[str] = None
    vocabulary_priority: Optional[List[str]] = Field(default_factory=list)
    syntax_constraints: Optional[str] = ""

class PersonaSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    type: Optional[str] = None # "TinyPerson" or "Fragment"
    persona: PersonaDetailsSchema
    filter_proxy_response: Optional[str] = None

################################################################################
# SCENARIO SCHEMAS
################################################################################

class TriggerConditionSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    min_turn: Optional[int] = None
    probability: Optional[float] = None

class DynamicInjectSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    trigger_condition: Optional[TriggerConditionSchema] = None
    broadcast: Optional[str] = None

class ScenarioSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    name: Optional[str] = None
    world_name: Optional[str] = None
    description: Optional[str] = None
    initial_broadcast: Optional[str] = None
    agents: Optional[List[str]] = None
    fragments: Optional[List[str]] = None
    grounding_files: Optional[List[str]] = None
    grounding_payload: Optional[List[str]] = Field(default_factory=list)
    scenario_knowledge: Optional[str] = None
    dynamic_injects: Optional[List[DynamicInjectSchema]] = Field(default_factory=list)
    intervention: Optional[str] = None
    safety_allegories: Optional[Dict[str, str]] = None

################################################################################
# ASSET MANAGER
################################################################################

class AssetManager:
    """
    Handles loading and strict validation of TinyTruce JSON assets.
    Forces an immediate halt if assets are malformed.
    """
    
    @staticmethod
    def load_persona(filepath: str) -> PersonaSchema:
        """Loads and validates an agent persona JSON."""
        path = Path(filepath)
        if not path.exists():
            print(f"\n[FATAL ERROR]: Persona file not found: {filepath}")
            raise SystemExit(1)
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            validated = PersonaSchema.model_validate(data)
            if validated.persona.syntax_constraints:
                logger.debug(f"LOADED syntax_constraints for {filepath}")
            else:
                logger.warning(f"EMPTY syntax_constraints for {filepath}")
            
            return validated
        except ValidationError as e:
            print(f"\n[FATAL VALIDATION ERROR]: Malformed Persona Asset: {filepath}")
            print("-" * 60)
            for error in e.errors():
                loc = " -> ".join([str(x) for x in error['loc']])
                print(f"KEY: {loc}")
                print(f"PROBLEM: {error['msg']}")
                print(f"INPUT: {error.get('input', 'N/A')}")
                print("-" * 60)
            raise SystemExit(1)
        except json.JSONDecodeError as e:
            print(f"\n[FATAL JSON ERROR]: Failed to parse {filepath}")
            print(f"Error: {e}")
            raise SystemExit(1)

    @staticmethod
    def load_scenario(filepath: str) -> ScenarioSchema:
        """Loads and validates a scenario configuration JSON."""
        path = Path(filepath)
        if not path.exists():
            print(f"\n[FATAL ERROR]: Scenario file not found: {filepath}")
            raise SystemExit(1)
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ScenarioSchema.model_validate(data)
        except ValidationError as e:
            print(f"\n[FATAL VALIDATION ERROR]: Malformed Scenario Asset: {filepath}")
            print("-" * 60)
            for error in e.errors():
                loc = " -> ".join([str(x) for x in error['loc']])
                print(f"KEY: {loc}")
                print(f"PROBLEM: {error['msg']}")
                print(f"INPUT: {error.get('input', 'N/A')}")
                print("-" * 60)
            raise SystemExit(1)
        except json.JSONDecodeError as e:
            print(f"\n[FATAL JSON ERROR]: Failed to parse {filepath}")
            print(f"Error: {e}")
            raise SystemExit(1)
