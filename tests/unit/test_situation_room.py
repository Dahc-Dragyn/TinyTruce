import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tinytroupe.agent.mental_faculty import SituationRoomFaculty

class TestSituationRoom(unittest.TestCase):
    def setUp(self):
        # Mock environment variables
        self.patcher = patch.dict(os.environ, {
            "BASE_URL": "http://mock-api",
            "WAR_API_SECRET": "test-secret"
        })
        self.patcher.start()
        self.faculty = SituationRoomFaculty()
        self.mock_agent = MagicMock()
        self.mock_agent.name = "TestAgent"

    def tearDown(self):
        self.patcher.stop()

    def test_quota_enforcement(self):
        # First query should pass
        action = {"type": "GET_ALERTS"}
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {"alerts": []}
            mock_get.return_value.status_code = 200
            
            result = self.faculty.process_action(self.mock_agent, action)
            self.assertTrue(result)
            self.assertEqual(self.faculty.turn_news_queries, 1)

            # Second query should be blocked by quota
            result = self.faculty.process_action(self.mock_agent, action)
            self.assertTrue(result) # Still returns True because it "processed" the block
            self.assertEqual(self.faculty.turn_news_queries, 1) # Quota should still be 1
            
            # Check that agent was told about the quota
            self.mock_agent.think.assert_called()
            args, _ = self.mock_agent.think.call_args
            self.assertIn("QUOTA EXCEEDED", args[0])

    def test_search_news_formatting(self):
        # Test that SEARCH_NEWS includes the query in the API call
        action = {"type": "SEARCH_NEWS", "content": "test theater"}
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {"results": []}
            mock_get.return_value.status_code = 200
            
            self.faculty.process_action(self.mock_agent, action)
            
            # Verify the call parameters
            args, kwargs = mock_get.call_args
            self.assertEqual(kwargs['params']['q'], "test theater")
            self.assertIn("http://mock-api", args[0])

    def test_api_error_handling(self):
        # Test that API errors are handled gracefully
        action = {"type": "GET_ALERTS"}
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection Failed")
            
            self.faculty.process_action(self.mock_agent, action)
            
            # Agent should be told about the failure
            self.mock_agent.think.assert_called()
            args, _ = self.mock_agent.think.call_args
            self.assertIn("connection failed", args[0])

if __name__ == "__main__":
    unittest.main()
