import sys
import os
import json

# FORCE LOCAL IMPORT
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from tinytroupe.agent import TinyPerson
from tinytroupe.environment import TinyWorld

def diag_memory_raw():
    print("\n--- RAW MEMORY DIAGNOSTIC ---")
    agents_dir = os.path.join(project_root, "personas", "agents")
    trump = TinyPerson.load_specification(os.path.join(agents_dir, "donald_trump.agent.json"))
    
    # 1. Give one prompt
    print("Prompting Trump...")
    trump.listen_and_act("Give a short 1-sentence statement about AI.")
    
    # 2. Dump the last 5 messages as raw JSON to a file
    print("\n--- DUMPING TO FILE ---")
    last_msgs = trump.current_messages[-5:]
    with open("diag_memory.json", "w") as f:
        json.dump(last_msgs, f, indent=2)
    print("Done: diag_memory.json")

if __name__ == "__main__":
    diag_memory_raw()
