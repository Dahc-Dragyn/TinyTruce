import pytest
import os
import json
from tinytroupe.cost_manager import CostManager

def test_revenue_shield_math():
    """
    Mathematically verifies that the CostManager calculates costs correctly
    down to the sixth decimal point.
    """
    # 1. Setup a clean manager (ignoring external files for this test)
    manager = CostManager()
    manager.reset()
    
    # 2. Add a specific usage turn
    # Model: gemini-2.0-flash-lite-001
    # Input: 100,000 tokens ($0.075 per 1M -> $0.0075)
    # Output: 50,000 tokens ($0.30 per 1M -> $0.0150)
    # Cached: 1,000,000 tokens ($0.01875 per 1M -> $0.01875)
    # Total Expected: 0.0075 + 0.015 + 0.01875 = 0.04125
    
    model = "gemini-2.0-flash-lite-001"
    cost = manager.add_usage(
        model_name=model,
        input_tokens=100_000,
        output_tokens=50_000,
        cached_tokens=1_000_000
    )
    
    expected_cost = 0.04125
    
    # Verify single call cost
    assert round(cost, 6) == round(expected_cost, 6)
    
    # Verify running totals
    summary = manager.get_summary()
    assert summary["total_input_tokens"] == 100_000
    assert summary["total_output_tokens"] == 50_000
    assert summary["total_cached_tokens"] == 1_000_000
    assert summary["total_cost"] == round(expected_cost, 6)
    
    print(f"\n[SUCCESS] Revenue Shield: Math verified. Expected: {expected_cost}, Calculated: {summary['total_cost']}")

def test_revenue_shield_model_fallback():
    """
    Verifies that the manager falls back to a default rate if a model is unknown.
    """
    manager = CostManager()
    manager.reset()
    
    # This model doesn't exist in DEFAULT_PRICING
    # It should fallback to gemini-2.5-flash-lite
    # Rates: Input 0.10, Output 0.40 (per 1M)
    cost = manager.add_usage(
        model_name="unseen-hyper-model-x",
        input_tokens=1_000_000,
        output_tokens=1_000_000
    )
    
    # Expected: 0.10 + 0.40 = 0.50
    assert cost == 0.50
    print(f"[SUCCESS] Revenue Shield: Fallback logic verified.")

if __name__ == "__main__":
    pytest.main([__file__])
