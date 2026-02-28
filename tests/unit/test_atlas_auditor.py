import pytest
import os
from tinytruce_sim import extract_agent_grounding

def test_atlas_auditor_header_resilience(tmp_path):
    """
    Verifies that the grounding extractor can handle messy headers,
    capitalization mismatches, and aliases.
    """
    # 1. Create a "Messy" Atlas file in a temp directory
    atlas_content = """
# Forensic Intelligence Atlas (Testing)

---
## Section: Leaders

### DJT
Core: MAGA energy.

 ### Vladimir Putin
Core: Strategic patience (Note the LEADING space).

### Xi Jinping(Senior)
Core: Long-term focus.

### The Hungarian
Core: Special grounding for Orban.

### Melania Trump
Core: Fashion and Diplomacy.

---
"""
    atlas_file = tmp_path / "mock_atlas.md"
    atlas_file.write_text(atlas_content, encoding="utf-8")
    
    # 2. Test Cases
    
    # Case A: Alias match (Donald Trump matches the DJT header via AGENT_ALIAS_MAP)
    grounding_a = extract_agent_grounding("Donald Trump", atlas_path=str(atlas_file))
    assert grounding_a is not None
    assert "MAGA energy" in grounding_a
    
    # Case B: Leading space resilience (Vladimir Putin header has a leading space)
    grounding_b = extract_agent_grounding("Vladimir Putin", atlas_path=str(atlas_file))
    assert grounding_b is not None
    assert "Strategic patience" in grounding_b
    
    # Case C: Name with noise (parentheses)
    grounding_c = extract_agent_grounding("Xi Jinping", atlas_path=str(atlas_file))
    assert grounding_c is not None
    assert "Long-term focus" in grounding_c

    # Case D: Exact Substring match
    grounding_d = extract_agent_grounding("Melania Trump", atlas_path=str(atlas_file))
    assert grounding_d is not None
    assert "Fashion" in grounding_d

    # Case F: Explicit Alias match (Viktor Orban matches 'The Hungarian' via AGENT_ALIAS_MAP)
    grounding_f = extract_agent_grounding("Viktor Orban", atlas_path=str(atlas_file))
    assert grounding_f is not None
    assert "Special grounding for Orban" in grounding_f

    print(f"\n[SUCCESS] Atlas Auditor: Verified resilience against casing, spaces, substrings, and Aliases.")

def test_atlas_auditor_missing_file():
    """Verifies graceful failure if Atlas is missing."""
    result = extract_agent_grounding("Anyone", atlas_path="non_existent_file.md")
    assert result is None

if __name__ == "__main__":
    pytest.main([__file__])
