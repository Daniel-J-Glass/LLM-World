import os
import config

from utils.llm_utils import initialize_client, create_message

def main():
    # Ensure the API key is set
    if 'ANTHROPIC_API_KEY' not in os.environ:
        api_key = input("Please enter your Anthropic API key: ")
        os.environ['ANTHROPIC_API_KEY'] = api_key

    # Initialize the client
    client = initialize_client()

    while True:
        # Get user input
        user_input = input("Enter your prompt (or 'quit' to exit): ")
        
        if user_input.lower() == 'quit':
            break

        # Create a message
        response = create_message(client, user_input)

        if response:
            print("Claude's response:")
            print(response)
        else:
            print("Failed to get a response from Claude.")

if __name__ == "__main__":
    main()