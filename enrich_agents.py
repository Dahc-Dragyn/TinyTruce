import os
import json

agent_dir = "personas/agents"
profile_dir = "data/profiles"

# Mapping of a few that might need manual name cleanup if name field was just a slug
# But checking some files showed they are already formal.

for filename in os.listdir(agent_dir):
    if filename.endswith(".agent.json"):
        if filename.endswith(".bak"): continue
        
        slug = filename[:-11] # Remove .agent.json
        filepath = os.path.join(agent_dir, filename)
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            persona = data.get("persona", {})
            
            # Add full_name if not present
            if "full_name" not in persona:
                # Use name as base for full_name
                persona["full_name"] = persona.get("name", slug.replace("_", " ").title())
            
            # Check for deep profile
            profile_path = os.path.join(profile_dir, f"{slug}.txt")
            if os.path.exists(profile_path):
                persona["deep_profile"] = f"data/profiles/{slug}.txt"
            
            data["persona"] = persona
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Updated {filename}")
        except Exception as e:
            print(f"Error updating {filename}: {e}")
