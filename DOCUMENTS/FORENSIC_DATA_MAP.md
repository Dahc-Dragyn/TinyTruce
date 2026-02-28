# TinyTruce: Forensic Data Map (V1.0)

This document serves as the project's canonical index for **Forensic Grounding**. It tracks the provenance, thematic focus, and scenario-mapping for all factual data used to anchor AI agent behavior.

---

## 📂 Data Directory Structure
The grounding ballast is organized into six functional silos:

1.  **`data/economics/`**: IMF reports, labor automation indices, and debt/deficit projections.
2.  **`data/finance/`**: Treasury reserve status and sovereign debt forgiveness protocols.
3.  **`data/legal/`**: Legislative acts (EU AI Act), judicial precedents, and compliance standards.
4.  **`data/security/`**: Deployment logs, maritime forensics, and kinetic weather event tracking.
5.  **`data/tech/`**: Technical whitepapers, BCI latency logs, and compute-credit indices.
6.  **`data/theology/`**: Vatican encyclicals, theological schism logs, and digital baptism whitepapers.
7.  **`data/treaties/`**: Bilateral agreements and maritime accords (e.g., Jakarta Accord).

---

## 🗺️ Canonical Mapping (Scenario -> Ballast)

| Scenario | Primary Grounding Files | Context Weight |
| :--- | :--- | :--- |
| **Wilderness** | `security/extreme-weather-deployment-log.2026.txt` | High (Forensic) |
| **Pacific Deep Sea Cable Cut** | `security/malacca-straits-cable-forensics.2026.txt`, `security/subsea_cable_resilience.2026.txt`, `treaties/jakarta-maritime-accord-DRAFT.txt` | Critical |
| **Strait Quarantine** | `facts/strait-quarantine.2026.txt`, `security/subsea_cable_resilience.2026.txt`, `treaties/jakarta-maritime-accord-DRAFT.txt` | High |
| **Petrodollar Pivot** | `trade/petrodollar_pivot.txt`, `finance/us-treasury-reserve-status-2026.txt` | Kinetic |
| **Middle East Reset** | `economics/sira-gold-peg.2026.txt`, `economics/imf-world-outlook-jan2026.txt` | Structural |
| **Sovereign AI Debt** | `economics/cbo-obbba-deficit-projection-2026.txt`, `economics/global-labor-automation-report.2026.txt` | Financial |
| **Vatican Cyber-Schism** | `theology/antiqua-et-nova-vatican-2025.txt`, `theology/theological_schism_2026.txt` | Ideological |
| **Silicon Siege** | `tech/bci-latency-and-influence.2026.txt`, `tech/trillium-compute-credit-index.2025.txt` | Technical |
| **Amazon Debt Swap** | `economics/imf-world-outlook-jan2026.txt`, `economics/potosi-protocol-2026.txt` | Ecological |
| **EU Fiscal Lockdown** | `facts/eu-fiscal-lockdown.2026.txt`, `security/subsea_cable_resilience.2026.txt` | Strategic |
| **Thermostat Hegemony** | `tech/smart-home-resilience-protocol.2025.txt`, `tech/biometric-consensus-standards.2026.txt` | Interior |

---

## 🛠️ Data Maintenance Protocol
1.  **Avoid Monoliths**: Never add data to a global "world facts" file. Use scenario-specific `grounding_payload` entries.
2.  **Naming Convention**: `[category]/[descriptive-name].[year].[extension]` (e.g., `tech/5g-spectrum.2025.txt`).
3.  **Scenario Sync**: When adding a new file to `data/`, search `scenarios/` for any thematic matches and update their JSON `grounding_payload`.

---

*“Data without context is just noise; context without data is just fiction.”*
