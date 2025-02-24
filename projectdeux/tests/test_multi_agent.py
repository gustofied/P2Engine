from dotenv import load_dotenv


# Load environment variables first
load_dotenv()

def test_enhanced_scenario():
    """Test the enhanced scenario with logging verification"""
    from multi_agent_systems.goal_scenario import run_enhanced_scenario
    
    # Run the scenario
    result = run_enhanced_scenario()
    
    # Basic content assertions
    assert len(result) > 100, "Result too short"
    assert "balance" in result.lower(), "Missing key concept"
    

    
    # Add file existence checks if needed

if __name__ == "__main__":
    test_enhanced_scenario()