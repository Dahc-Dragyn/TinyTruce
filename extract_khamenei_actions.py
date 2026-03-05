import re

log_path = r"c:\Antigravity projects\TinyTruce\tinytruce_simulation.log"
agent_name = "Seyyed Ali Hosseini Khamenei"

try:
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
except UnicodeDecodeError:
    with open(log_path, "r", encoding="latin-1") as f:
        lines = f.readlines()

actions = []
recording = False
current_action = []

for line in lines:
    if agent_name in line and "'action':" in line:
        recording = True
        current_action = [line.strip()]
    elif recording:
        current_action.append(line.strip())
        if "}" in line:
            actions.append("\n".join(current_action))
            recording = False

print(f"Extracted {len(actions)} total actions for {agent_name}.\n")
# Print the last turn actions (from the latest loop guard warning)
for i, action in enumerate(actions[-20:]):
    print(f"--- Action {i+1} ---")
    print(action)
