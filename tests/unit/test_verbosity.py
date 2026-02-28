import pytest
from tinytruce_sim import get_verbosity_constraint

def test_dynamic_verbosity_scaling_5_turns():
    total_turns = 5
    # Opening (20% of 5 = 1): Turn 1
    # Core (21% to 80% = Turns 2-4): Detailed
    # Closing (81% to 100% = Turn 5): Lean
    
    assert "75 to 150 words" in get_verbosity_constraint("dynamic", 1, total_turns)
    assert "250 to 350 words" in get_verbosity_constraint("dynamic", 2, total_turns)
    assert "250 to 350 words" in get_verbosity_constraint("dynamic", 3, total_turns)
    assert "250 to 350 words" in get_verbosity_constraint("dynamic", 4, total_turns)
    assert "75 to 150 words" in get_verbosity_constraint("dynamic", 5, total_turns)

def test_dynamic_verbosity_scaling_15_turns():
    total_turns = 15
    # Opening (20% of 15 = 3): Turns 1-3
    # Core (21% to 80% = Turns 4-12): Detailed
    # Closing (81% to 100% = Turns 13-15): Lean
    
    assert "75 to 150 words" in get_verbosity_constraint("dynamic", 1, total_turns)
    assert "75 to 150 words" in get_verbosity_constraint("dynamic", 3, total_turns)
    assert "250 to 350 words" in get_verbosity_constraint("dynamic", 4, total_turns)
    assert "250 to 350 words" in get_verbosity_constraint("dynamic", 12, total_turns)
    assert "75 to 150 words" in get_verbosity_constraint("dynamic", 13, total_turns)
    assert "75 to 150 words" in get_verbosity_constraint("dynamic", 15, total_turns)

def test_dynamic_verbosity_scaling_25_turns():
    total_turns = 25
    # Opening (20% of 25 = 5): Turns 1-5
    # Core (21% to 80% = Turns 6-20): Detailed
    # Closing (81% to 100% = Turns 21-25): Lean
    
    assert "75 to 150 words" in get_verbosity_constraint("dynamic", 1, total_turns)
    assert "75 to 150 words" in get_verbosity_constraint("dynamic", 5, total_turns)
    assert "250 to 350 words" in get_verbosity_constraint("dynamic", 6, total_turns)
    assert "250 to 350 words" in get_verbosity_constraint("dynamic", 20, total_turns)
    assert "75 to 150 words" in get_verbosity_constraint("dynamic", 21, total_turns)
    assert "75 to 150 words" in get_verbosity_constraint("dynamic", 25, total_turns)

def test_static_verbosity():
    assert "75 to 150 words" in get_verbosity_constraint("lean", 1, 15)
    assert "75 to 150 words" in get_verbosity_constraint("lean", 10, 15)
    assert "250 to 350 words" in get_verbosity_constraint("detailed", 1, 15)
    assert "minimum of 500 words" in get_verbosity_constraint("monologue", 1, 15)
