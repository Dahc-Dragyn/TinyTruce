"""
Testing utilities.
"""
import os
import sys
from time import sleep
import json
import re
import datetime
import importlib
import logging

# Standard Path setup for TinyTruce
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
sys.path.insert(0, os.path.join(_ROOT_DIR, "tinytroupe"))
sys.path.insert(0, _ROOT_DIR)

import tinytroupe.openai_utils as openai_utils
from tinytroupe.agent import TinyPerson
from tinytroupe.environment import TinyWorld, TinySocialNetwork
import pytest
import conftest
from dotenv import load_dotenv

# Ensure environment variables are loaded for tests
load_dotenv(os.path.join(_ROOT_DIR, ".env"))

# Project-native Google Generative AI (matching tinytruce_sim.py)
import google.generativeai as genai
from google.generativeai import caching

##################################################
# global constants
##################################################
AGENT_DIR = os.path.join(_ROOT_DIR, "personas", "agents")
ATLAS_PATH = os.path.join(AGENT_DIR, "Forensic_Intelligence_Atlas.md")
PROMPTS_DIR = os.path.join(AGENT_DIR, "archive", "Prompts")
CACHE_FILE_NAME = "tests_cache.pickle"
EXPORT_BASE_FOLDER = os.path.join(_THIS_DIR, "outputs", "exports")

##################################################
# Fixtures
##################################################
@pytest.fixture(scope="function")
def setup():
    # Set the cache according to the command line option
    openai_utils.force_api_cache(conftest.use_cache)
    
    # Clear the global agent registry to avoid name conflicts in parameterized tests
    TinyPerson.all_agents.clear()
    
    yield

############################################################################################################
# Dynamic Agent Discovery & Forensic Extraction
############################################################################################################

def get_available_agents():
    """
    Returns a list of available agent filenames (.agent.json) from the agents directory.
    """
    if not os.path.exists(AGENT_DIR):
        print(f"ERROR: AGENT_DIR not found at {AGENT_DIR}")
        return []
    agents = [f for f in os.listdir(AGENT_DIR) if f.endswith(".agent.json")]
    return sorted(agents)

def extract_expectations(agent_name):
    """
    Extracts forensic expectations/markers for validation from the Atlas or Prompt files.
    """
    # 1. Try to get grounding from Atlas
    grounding = extract_agent_grounding(agent_name)
    
    # 2. Try to supplement or fallback to Prompt files
    base_name = agent_name.replace(".agent.json", "")
    clean_name = base_name.replace(" ", "_").replace("(", "").replace(")", "").split(".")[0]
    
    prompt_candidates = [
        f"{base_name.title().replace(' ', '_')}_Forensic_Prompt.txt",
        f"{base_name.title().replace(' ', '_')}_Forensic_Prompt#.txt",
        f"{base_name.replace('_', ' ').title().replace(' ', '_')}_Forensic_Prompt.txt",
        f"{base_name.replace('_', ' ').title().replace(' ', '_')}_Forensic_Prompt#.txt",
        f"{base_name}_Forensic_Prompt.txt",
        f"{clean_name.title()}_Forensic_Prompt.txt",
        f"{clean_name.title()}_Forensic_Prompt#.txt"
    ]
    
    extra_markers = ""
    for pf in prompt_candidates:
        path = os.path.join(PROMPTS_DIR, pf)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                extra_markers += f.read()
                break
    
    if not grounding and not extra_markers:
        return f"The agent should behave consistently with the persona described in {agent_name}."
    
    return f"GROUNDING:\n{grounding}\n\nFORENSIC MARKERS:\n{extra_markers}"

def extract_agent_grounding(agent_name, atlas_path=ATLAS_PATH):
    """
    Extracts the forensic grounding for a specific agent from the Forensic Atlas.
    """
    if not os.path.exists(atlas_path):
        return None
    
    search_term = agent_name.lower().replace(".agent.json", "").replace(" vladimirovich", "").replace(" gertrude", "").split("(")[0].strip()
    
    with open(atlas_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = content.split("\n")
    found_section = []
    capture = False
    
    for line in lines:
        if line.startswith("###") and search_term in line.lower():
            capture = True
            found_section.append(line)
            continue
        elif capture and (line.startswith("###") or line.startswith("---") or line.startswith("## ")):
            break
        elif capture:
            found_section.append(line)
            
    if found_section:
        return "\n".join(found_section).strip()
    return None

class GeopoliticalCacheManager:
    """Manages Gemini Explicit Context Caching for Layer 0 profiles (matching tinytruce_sim.py)."""
    def __init__(self, profiles_text, model="models/gemini-2.5-flash-lite-preview-09-2025"):
        self.profiles_text = profiles_text
        self.model = model
        self.cache = None
        self.last_renewed = None
        self.min_chars = 4000 

    def create_cache(self):
        if len(self.profiles_text) < self.min_chars:
            return None
        try:
            self.cache = caching.CachedContent.create(
                model=self.model,
                display_name="tinytruce_test_validation",
                contents=[self.profiles_text],
                ttl=datetime.timedelta(minutes=15),
            )
            self.last_renewed = datetime.datetime.now()
            return self.cache.name
        except Exception as e:
            print(f"Gemini Cache Creation Failed: {e}")
            return None

    def renew_if_needed(self):
        if not self.cache:
            return
        elapsed = datetime.datetime.now() - self.last_renewed
        if elapsed > datetime.timedelta(minutes=10):
            self.cache.update(ttl=datetime.timedelta(minutes=15))
            self.last_renewed = datetime.datetime.now()

############################################################################################################
# Original Testing Utilities (preserved)
############################################################################################################

def remove_file_if_exists(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)

def get_fresh_working_copy(file_path, working_dir="temp_working_copies"):
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)
    file_name = os.path.basename(file_path)
    working_copy_path = os.path.join(working_dir, file_name)
    import shutil
    shutil.copyfile(file_path, working_copy_path)
    return working_copy_path

def agents_configs_are_equal(agent_1, agent_2):
    return agent_1._configuration == agent_2._configuration

def contains_action_type(actions, action_type):
    return any(action['action']['type'] == action_type for action in actions)

def contains_action_content(actions, action_content):
    return any(action_content in action['action']['content'] for action in actions)

def contains_stimulus_type(stimuli, stimulus_type):
    return any(stimulus['type'] == stimulus_type for stimuli in stimuli)

def contains_stimulus_content(stimuli, stimulus_content):
    return any(stimulus_content in stimulus['content'] for stimulus in stimuli)

def proposition_holds(proposition: str) -> bool:
    system_prompt = "Check whether the following proposition is true or false. If it is true, write 'true', otherwise write 'false'. Don't write anything else!"
    user_prompt = f"Proposition: {proposition}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    next_message = openai_utils.client().send_message(messages)
    cleaned_message = ''.join(c for c in next_message["content"] if c.isalnum())
    if cleaned_message.lower().startswith("true"):
        return True
    elif cleaned_message.lower().startswith("false"):
        return False
    else:
        raise Exception(f"LLM returned unexpected result: {cleaned_message}")

def only_alphanumeric(string: str):
    return ''.join(c for c in string if c.isalnum())

def create_and_save_person(name, age, nationality, occupation, file_path):
    person = TinyPerson(name)
    person.define("age", age)
    person.define("nationality", nationality)
    person.define("occupation", occupation)
    person.save_specification(file_path)
    return person

def create_oscar_the_architect():
    return TinyPerson.load_specification(os.path.join(AGENT_DIR, "oscar_the_architect.agent.json"))

def create_lisa_the_data_scientist():
    return TinyPerson.load_specification(os.path.join(AGENT_DIR, "lisa_the_data_scientist.agent.json"))

def create_kim_the_designer():
    return TinyPerson.load_specification(os.path.join(AGENT_DIR, "kim_the_designer.agent.json"))

def create_town_hall_world():
    world = TinyWorld("Town Hall", [create_oscar_the_architect(), create_lisa_the_data_scientist()])
    return world

def get_agent_name(agent):
    return agent.name.split()[0]
