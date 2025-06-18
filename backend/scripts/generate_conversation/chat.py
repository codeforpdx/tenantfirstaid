# /// script
# requires-python = "~=3.11"
# dependencies = [
#     "openai",
#     "pandas",
# ]
# ///
from openai import OpenAI
import os
import ast
import argparse
from pathlib import Path
import pandas as pd
from typing import Self

if Path("../../.env").exists():
    from dotenv import load_dotenv

    load_dotenv(override=True)

from tenantfirstaid.chat import API_KEY, BASE_URL, DEFAULT_INSTRUCTIONS, ChatManager

BOT_INSTRUCTIONS = DEFAULT_INSTRUCTIONS

USER_INSTRUCTIONS_BASE = """You are a user of the Oregon Tenant First Aid chatbot. 
You are seeking legal advice about tenant rights in Oregon. 
You should speak in plain, straightforward language like a real user.
You have a list of facts about your situation that you can reference to respond to the bot.
If the bot asks you a question, you should answer it to the best of your ability, if you do not know the answer you should make something up that is plausible.
"""

USER_MODEL = os.getenv("USER_MODEL_NAME", "gpt-4o-2024-11-20")


class ChatView:
    client: Self

    def __init__(self, starting_message, user_facts, city, state):
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
        )
        self.chat_manager = ChatManager()
        self.city = city
        self.state = state

        self.input_messages = [{"role": "user", "content": starting_message}]
        self.starting_message = starting_message  # Store the starting message

        self.openai_tools = []
        self.USER_INSTRUCTIONS = (
            USER_INSTRUCTIONS_BASE + "\n" + "Facts: " + "\n".join(user_facts)
        )

    # Prompt iteration idea
    # If the user starts off by saying something unclear, start off by asking me \"What are you here for?\"
    def _reverse_message_roles(self, messages):
        """Reverses the roles of the messages in the conversation."""
        reversed_messages = []
        for message in messages:
            if message["role"] == "user":
                reversed_messages.append(
                    {"role": "assistant", "content": message["content"]}
                )
            elif message["role"] == "assistant":
                reversed_messages.append(
                    {"role": "user", "content": message["content"]}
                )
            else:
                reversed_messages.append(message)
        return reversed_messages

    def bot_response(self):
        """Generates a response from the bot using the OpenAI API."""
        tries = 0
        while tries < 3:
            try:
                # Use the BOT_INSTRUCTIONS for bot responses
                response = self.chat_manager.generate_chat_response(
                    self.input_messages,
                    city=self.city,
                    state=self.state,
                    stream=False,
                )
                self.input_messages.append(
                    {"role": "assistant", "content": response.output_text}
                )
                self.input_messages = self._reverse_message_roles(self.input_messages)
                return response.output_text
            except Exception as e:
                print(f"Error generating bot response: {e}")
                tries += 1
        # If all attempts fail, return a failure message
        failure_message = "I'm sorry, I am unable to generate a response at this time. Please try again later."
        self.input_messages.append({"role": "assistant", "content": failure_message})
        return failure_message

    def user_response(self):
        """Generates a response from the user using the OpenAI API."""
        tries = 0
        while tries < 3:
            try:
                # Use the USER_MODEL for user responses
                response = self.client.responses.create(
                    model=USER_MODEL,
                    input=self.input_messages,
                    instructions=self.USER_INSTRUCTIONS,
                    stream=False,
                )
                self.input_messages.append(
                    {"role": "user", "content": response.output_text}
                )
                return response.output_text
            except Exception as e:
                print(f"Error generating user response: {e}")
                tries += 1
        # If all attempts fail, return a failure message
        failure_message = "I'm sorry, I am unable to generate a user response at this time. Please try again later."
        self.input_messages.append({"role": "user", "content": failure_message})
        return failure_message

    def generate_conversation(self, num_turns=5):
        """Generates a conversation between the bot and the user."""
        chat_history = ""
        print("Starting conversation...")
        print(f"USER: {self.starting_message}")
        for _ in range(num_turns):
            response = self.bot_response()
            chat_history += f"BOT: {response}\n"
            print(f"BOT: {response}")

            user_response = self.user_response()
            chat_history += f"USER: {user_response}\n"
            print(f"USER: {user_response}")
        self.input_messages = self.input_messages[
            0
        ]  # Reset input messages to the first message only
        return chat_history


def process_conversation(row, num_turns=5):
    """Process a single row and generate a new conversation."""
    print(f"\nProcessing question: {row['first_question']}")

    # Convert string representation of list to actual list
    facts = ast.literal_eval(row["facts"])
    # if row["city"] is NaN, set it to "null"
    if pd.isna(row["city"]):
        row["city"] = "null"

    # Create chat view with the starting question and facts
    chat = ChatView(row["first_question"], facts, row["city"], row["state"])

    # Generate a new conversation
    return chat.generate_conversation(num_turns)


def process_csv(input_file=None, output_file=None, num_turns=5, num_rows=None):
    """Process input CSV and generate new conversations for each row using pandas."""
    if input_file is None:
        input_file = Path(__file__).parent / "tenant_questions_facts_full.csv"
    if output_file is None:
        output_file = (
            Path(__file__).parent / "tenant_questions_facts_with_new_conversations.csv"
        )

    print(f"\nProcessing conversations from {input_file}")

    # Read CSV using pandas with Windows-1252 encoding
    df = pd.read_csv(input_file, encoding="cp1252")

    # Generate new conversations using map
    print("Generating conversations...")
    if num_rows is not None:
        df = df.head(num_rows)  # Limit to the first num_rows if specified

    # Pass num_turns parameter to process_conversation using lambda
    df["New Conversation"] = df.apply(
        lambda row: process_conversation(row, num_turns=num_turns), axis=1
    )

    # Save the results with the same encoding as input
    print(f"\nWriting results to {output_file}")
    df.to_csv(output_file, index=False, encoding="utf-8")

    print(f"\nAll conversations generated and saved to {output_file}")
    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate conversations between a user and a bot."
    )
    parser.add_argument(
        "--num-turns", type=int, default=5, help="Number of conversation turns"
    )
    parser.add_argument(
        "--num-rows", type=int, default=None, help="Number of rows to process"
    )
    args = parser.parse_args()

    process_csv(num_turns=args.num_turns, num_rows=args.num_rows)
# This script generates conversations between a user and a bot using the OpenAI API.
