# /// script
# requires-python = "~=3.11"
# dependencies = [
#     "pandas",
#     "python-dotenv",
# ]
# ///
from time import time
import os
import ast
import argparse
from pathlib import Path
import pandas as pd

from tenantfirstaid.chat import DEFAULT_INSTRUCTIONS, ChatManager

dot_env_path = Path(__file__).parent.parent.parent / ".env"
print(f"Loading environment variables from {dot_env_path}")
if dot_env_path.exists():
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=dot_env_path, override=True)

BOT_INSTRUCTIONS = DEFAULT_INSTRUCTIONS

USER_INSTRUCTIONS_BASE = """You are a user of the Oregon Tenant First Aid chatbot. 
You are seeking legal advice about tenant rights in Oregon. 
You should speak in plain, straightforward language like a real user.
You have a list of facts about your situation that you can reference to respond to the bot.
If the bot asks you a question, you should answer it to the best of your ability, if you do not know the answer you should make something up that is plausible.
Do not try to answer legal questions, let the bot handle those. Only act as a user who is seeking help.
If the bot says something is not possible, do not argue with it, just accept it and move on.
Only ask the questions given in the list of facts, do not come up with new questions.
"""

USER_MODEL = os.getenv("USER_MODEL_NAME", "gemini-2.5-flash")
GEMINI_RAG_CORPUS = os.getenv("GEMINI_RAG_CORPUS")
print("CORPUS: ", GEMINI_RAG_CORPUS)


class ChatView:
    def __init__(self, starting_message, user_facts, city, state):
        self.chat_manager = ChatManager()
        self.city = city
        self.state = state

        self.input_messages = [dict(role="user", content=starting_message)]
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
                reversed_messages.append(dict(role="model", content=message["content"]))
            elif message["role"] == "model":
                reversed_messages.append(dict(role="user", content=message["content"]))
            else:
                reversed_messages.append(message)
        return reversed_messages

    def bot_response(self):
        """Generates a response from the bot using the Gemini API."""
        tries = 0
        while tries < 3:
            # Use the BOT_INSTRUCTIONS for bot responses
            start = time()
            response = self.chat_manager.generate_gemini_chat_response(
                self.input_messages,
                city=self.city,
                state=self.state,
                stream=False,
                model_name="gemini-2.5-pro",
            )
            end = time()
            self.input_messages.append(dict(role="model", content=response.text))
            self.input_messages = self._reverse_message_roles(self.input_messages)
            return response.text, end - start
        # If all attempts fail, return a failure message
        failure_message = "I'm sorry, I am unable to generate a response at this time. Please try again later."
        self.input_messages.append(dict(role="model", content=failure_message))
        return failure_message, None

    def user_response(self):
        """Generates a response from the user using the Gemini API."""
        tries = 0
        while tries < 3:
            try:
                print("\nGenerating user response...")
                # Use the USER_MODEL for user responses
                response = self.chat_manager.generate_gemini_chat_response(
                    self.input_messages,
                    city=self.city,
                    state=self.state,
                    stream=False,
                    instructions=self.USER_INSTRUCTIONS,
                    use_tools=False,
                    model_name="gemini-2.0-flash-lite",
                )
                self.input_messages.append(dict(role="user", content=response.text))
                return response.text
            except Exception as e:
                print(f"Error generating user response: {e}")
                tries += 1
        # If all attempts fail, return a failure message
        failure_message = "I'm sorry, I am unable to generate a user response at this time. Please try again later."
        self.input_messages.append(dict(role="user", content=failure_message))
        return failure_message

    def generate_conversation(self, num_turns=5):
        """Generates a conversation between the bot and the user."""
        chat_history = ""
        print("Starting conversation...")
        print(f"USER: {self.starting_message}")
        times = []
        for _ in range(num_turns):
            print(f"\n--- New Turn ({_ + 1}) ---")
            response, run_time = self.bot_response()
            if run_time is not None:
                times.append(run_time)
            chat_history += f"BOT: {response}\n"
            print(f"\nBOT: {response}")

            user_response = self.user_response()
            chat_history += f"USER: {user_response}\n"
            print(f"USER: {user_response}")
        self.input_messages = [
            self.input_messages[0]
        ]  # Reset input messages to the first message only

        # Catch when times has not populated
        try:
            average = sum(times) / len(times)
            chat_history += f"\nAverage bot response time: {round(average, 2)}s"
        except Exception as e:
            print(e)
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
    else:
        output_file = Path(__file__).parent / output_file

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
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="The file name to save the output CSV to",
    )
    args = parser.parse_args()

    process_csv(
        num_turns=args.num_turns, num_rows=args.num_rows, output_file=args.output_file
    )
# This script generates conversations between a user and a bot using the Gemini API.
