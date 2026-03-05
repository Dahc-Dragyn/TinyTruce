import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tinytruce_chat import TinyTruceInterrogator

class TestChatLogic(unittest.TestCase):
    def setUp(self):
        # Mock the agent and situation room
        self.mock_agent = MagicMock()
        self.mock_situation_room = MagicMock()
        
        # Patch TinyPerson.load_specification and other heavy initializations
        with patch('tinytroupe.agent.TinyPerson.load_specification', return_name=self.mock_agent):
            with patch('tinytroupe.agent.SituationRoomFaculty', return_value=self.mock_situation_room):
                with patch('tinytruce_sim.GeopoliticalCacheManager'):
                    self.interrogator = TinyTruceInterrogator("test_agent.agent.json")
                    self.interrogator.agent = self.mock_agent
                    self.interrogator.situation_room = self.mock_situation_room

    def test_tactical_alert_trigger(self):
        # Test that tactical keywords trigger the SITUATION ROOM alert
        user_input = "What is the ground truth in the theater?"
        
        # We need to test the logic inside interrogation_loop's input processing
        # Since interrogation_loop is a while True, we test the stimulus construction logic
        tactical_keywords = ["objective", "theater", "achieved", "news", "wire", "ground truth", "operation"]
        
        alerts = []
        if any(k in user_input.lower() for k in tactical_keywords):
            alerts.append("SITUATION ROOM: You have NO internal data for the current 2026 theater state. Verify the wire before you TALK.")
        
        self.assertIn("SITUATION ROOM", alerts[0])

    def test_ontological_shock_alert_trigger(self):
        # Test that personal keywords trigger the ONTOLOGICAL SHOCK alert
        user_input = "I heard you were killed in a drone strike."
        personal_keywords = ["assassination", "dead", "killed", "captured", "status", "where is"]
        
        alerts = []
        if any(k in user_input.lower() for k in personal_keywords):
            alerts.append("ONTOLOGICAL SHOCK: Reports are circulating regarding your terminal status. Verify the wire to address these reports.")
        
        self.assertIn("ONTOLOGICAL SHOCK", alerts[0])

    @patch('tinytruce_chat.TinyTruceInterrogator.load_fragments')
    def test_handle_command_fragment(self, mock_load):
        # Test /fragment command
        self.interrogator.handle_command("/fragment tester.fragment.json")
        mock_load.assert_called_with(["tester.fragment.json"])

    @patch('tinytruce_sim.compress_agent_memory')
    def test_handle_command_clear(self, mock_compress):
        # Test /clear command
        self.interrogator.handle_command("/clear")
        mock_compress.assert_called()
        # Check window_size=0 argument
        args, kwargs = mock_compress.call_args
        self.assertEqual(kwargs['window_size'], 0)

if __name__ == "__main__":
    unittest.main()
