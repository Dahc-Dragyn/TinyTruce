# TinyTruce: Persona Engineering Guide (V1.0)

This guide documents the "Forensic Persona" architecture used to create high-fidelity geopolitical agents and the clinical "Bartender" delivery engine.

---

## 🏗️ The Layer 0 Architecture
Every persona is built on a **Layer 0 Ballast**. This is the foundational grounding that prevents the agent from sounding like a generic chatbot.

### 1. The Core Prompt (mustache)
- **Identity Retention Locks**: A terminal instruction injected at the end of EVERY turn to combat "Context Amnesia".
- **Mustache Variable Integration**: Personas use `{{persona.name}}` and `{{persona.personality.traits}}` to dynamically populate the LLM's system prompt.

### 2. Behavioral Overlays (Fragments)
TinyTruce uses `.fragment.json` files to apply "Mood" or "Stance" overlays (e.g., `Preserver` vs. `Reformer`). These are combined with the base agent in the `AssetManager`.

---

## 🍸 The Bartender Delivery Engine
The "Jaded UN Bartender" recap uses clinical, detached comedic patterns to deliver structural roasts. **Do not refer to the real-world comedian name in the code or prompts—always use "The Bartender".**

| Pattern | Description | Implementation |
| :--- | :--- | :--- |
| **Archetypal Reduction** | Reducing a world leader to a basic, flawed archetype (e.g., "The Entitled Landlord"). | Use in the roast's persona definition. |
| **Grime Anchoring** | Linking high-level diplomatic failures to visceral, "grimy" low-status metaphors. | "Your policy is a 3 AM floor at a bus station." |
| **Tag Escalation** | Taking a simple observation and escalating the stakes until it reveals a terminal diplomatic flaw. | Escalating turn-by-turn critiques. |
| **Compression Governor** | Forces the roast to be clinical and detached. Prevents the AI from becoming "wacky" or over-enthusiastic. | A hard token limit and "detached" temperature setting (0.4). |

---

## 🔒 Identity Retention Locks
To prevent agents from referring to themselves as "Agent 1" or "Agent 2", the engine injects:
> *“CRITICAL IDENTITY LOCK: You are {{agent_name}}. You MUST refer to yourself as {{agent_name}}. DO NOT refer to anyone as 'Agent 1', 'Agent 2', etc. Your turn ONLY consists of 1 or 2 actions.”*

---

## 📝 Best Practices
1.  **Anti-Wonk Vocabulary**: Avoid bureaucratic cliches. Use persona-specific parataxis (short, blunt sentences).
2.  **Redline Definition**: Every agent MUST have explicit `redlines` (e.g., "Will never compromise on territorial integrity") to trigger de-escalation logic.
3.  **Thought Separation**: Encourage the use of `💭 THINKING` actions before `💬 TALK` to allow the LLM to process its forensic grounding ballast.
