# TinyTruce: Persona Engineering Guide (V2.0 - Forensic Architecture)

This guide documents the **Forensic Persona Architecture** used to achieve high-fidelity linguistic realism and structural simulation integrity in TinyTruce.

---

## 🏗️ The Layered DNA Model
TinyTruce agents are not monolithic prompts. They are 3-layer behavioral stacks:

### Layer 0: Baseline Identity (`.agent.json`)
The fundamental "soul" of the agent. Includes name, age, core traits, and permanent `redlines`. 
- **Linguistic Baseline**: Defines the frequency of specific metaphors and tonal descriptors.
- **Lexical Priority**: Categories of words the agent should favor (e.g., *social_navigation*, *professional_craft*).

### Layer 1: Forensic Grounding (`Atlas / Deep Profile`)
Factual anchors derived from the `Forensic_Intelligence_Atlas.md` and agent-specific deep profiles.
- **Deep Profile Injection**: The `deep_profile` key in the JSON maps to a text file containing the agent's historical and tactical DNA.
- **Atlas Mapping**: Dynamic extraction of situational "Theater Grounding" based on the scenario.

### Layer 2: Behavioral Fragments (`.fragment.json`)
Situational overlays (e.g., `savior`, `reformer`, `preserver`) that modify Layer 0 behavior without erasing it.
- **Behavioral Stacking**: TinyTruce supports chaining multiple fragments (e.g., `Base + Reformer + Savior`).
- **Redline Aggregation**: Banned behaviors from all fragments are combined and enforced as negative constraints.

---

## 🔒 Forensic Linguistic Locks
To prevent "LLM Leak" (sounding like a helpful chatbot), TinyTruce employs forensic locks:

| Lock Type | Description | Targeted Outcome |
| :--- | :--- | :--- |
| **Parataxis** | Short, blunt, fragmented sentences. Abandoning thoughts mid-stream. | High-fidelity realism (e.g., Trump V4). |
| **The Weave** | Mirroring user vocabulary and immediately redirecting to a persona-specific vector. | Prevents agents from "agreeing" too easily. |
| **Quotative Inversion** | Using "I was like" (internal logic) and "And he goes" (external absurdity). | The "Sam Morril" narrative bridge (Bartender V2). |
| **Anti-Wonk** | Systematic removal of bureaucratic cliches in favor of "Grime Anchors." | Maintains "Street Cred" and grounding. |

---

## 🍸 The Bartender Forensic Engine (V2)
The "Jaded UN Bartender" recap is a clinical delivery engine for forensic roasts.

| Pattern | Description |
| :--- | :--- |
| **Athletic Mapping** | Critiquing geopolitical failures as "iso dribbling" or a player not "pulling their weight." |
| **City Hick Tension** | Contrasting urban street-smarts with a complete lack of basic "freedom" skills (e.g., driving). |
| **Systemic Grievance** | Using bureaucratic finality ("The door is shut") as a motif for declining human logic. |
| **Pathological Anchor** | Using clinical triggers (Adderall, scale of one to ten, street cred diagnoses) for self-deprecation. |

---

## 🔒 Identity Retention Locks
To combat "Context Amnesia" and identity collapse in long turns, the engine injects a terminal lock:
> *“CRITICAL IDENTITY LOCK: You are {{agent_name}}. You MUST refer to yourself as {{agent_name}}. DO NOT refer to anyone as 'Agent 1', 'Agent 2', etc. Your turn ONLY consists of 1 or 2 actions.”*

---

## 📝 Best Practices for Forensic Tuning
1.  **Redline Enforcement**: Always define what an agent **CANNOT** do. Negative constraints are more powerful than positive ones for maintaining tension.
2.  **Paratactic Pruning**: If an agent sounds too organized, prune their vocabulary and force them to abandon sentences.
3.  **Grime Anchoring**: Every high-level diplomatic point must be tethered to a minor physical annoyance (e.g., a sticky bar floor, a broken 5G antenna).
4.  **Operational Logic**: In unscripted modes, agents should value "The Move" or "The Deal" over the "Statement."
