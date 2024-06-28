import unittest
from unittest.mock import patch, MagicMock
from utils.llm_utils import initialize_client, create_message, update_chat_history

class TestLLMUtils(unittest.TestCase):

    @patch('os.getenv')
    def test_initialize_client(self, mock_getenv):
        mock_getenv.return_value = 'dummy_api_key'
        client = initialize_client()
        self.assertIsNotNone(client)

    @patch('os.getenv')
    def test_initialize_client_no_api_key(self, mock_getenv):
        mock_getenv.return_value = None
        with self.assertRaises(ValueError):
            initialize_client()

    @patch('anthropic.Anthropic')
    def test_create_message(self, mock_anthropic):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test response")]
        mock_client.messages.create.return_value = mock_response
        
        chat_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        response = create_message(mock_client, "Test prompt", chat_history=chat_history)
        self.assertEqual(response, "Test response")
        
        mock_client.messages.create.assert_called_once_with(
            system="You are a helpful assistant.",
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            temperature=0,
            messages=chat_history
        )

    @patch('anthropic.Anthropic')
    def test_create_message_error(self, mock_anthropic):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        
        with self.assertLogs(level='ERROR') as log:
            response = create_message(mock_client, "Test prompt")
            self.assertIsNone(response)
            self.assertIn("Error creating message: API Error", log.output[0])

    def test_update_chat_history(self):
        history = []
        history = update_chat_history(history, "user", "Hello")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Hello")

        # Test max history
        for i in range(15):
            history = update_chat_history(history, "user", f"Message {i}")
        self.assertEqual(len(history), 10)
        self.assertEqual(history[-1]["content"], "Message 14")

if __name__ == '__main__':
    unittest.main()
