#!/usr/bin/env python3
import json
import jsonlines
import os
import sys
from pathlib import Path

# Import the model from app.py
from .chat import MODEL
from .shared import SYSTEM_PROMPT

# Define file paths (relative to the script location)
SCRIPT_DIR = Path(__file__).parent.parent  # Go up one level to backend directory
DATA_FILE = SCRIPT_DIR / "chatlog.jsonl"
OUTPUT_FILE = SCRIPT_DIR / f"combined_training_{MODEL.replace('.', '_')}.jsonl"


def prepare_training_data():
    """
    Process training data from chatlog.jsonl to create a clean combined_training.jsonl 
    file suitable for model training.

    This script fixes several issues with the data format:
    1. Removes the 'metadata' field from each entry (causing API errors)
    2. Ensures each conversation includes the system prompt
    3. Organizes messages by session to create proper conversation flows
    4. Uses a sliding window approach to create multiple training examples from each conversation
       at different points, which helps the model learn to respond appropriately at various stages

    The approach:
    - For conversations: [system, assistant, user, assistant, user, assistant, ...]
      - Creates the full conversation example
      - Plus intermediate examples ending with assistant responses:
        1. [system, assistant, user, assistant]
        2. [system, assistant, user, assistant, user, assistant]
        3. And so on
    - This helps the model learn to respond appropriately at different
      points in a conversation

    Returns:
        Path: The path to the generated training file
    """
    print(f"Preparing training data...")
    print(f"- Data file: {DATA_FILE}")
    print(f"- Output file: {OUTPUT_FILE}")

    # List to collect all processed training examples
    processed_examples = []

    # Track sessions to build complete conversations
    sessions = {}

    # Process regular conversation data
    if os.path.exists(DATA_FILE):
        print(f"Reading conversation data from {DATA_FILE}")
        with jsonlines.open(DATA_FILE, mode="r") as inf:
            for item in inf:
                if (
                    "messages" in item
                    and "metadata" in item
                    and "session_id" in item["metadata"]
                ):
                    session_id = item["metadata"]["session_id"]

                    # Initialize session with system prompt if needed
                    if session_id not in sessions:
                        sessions[session_id] = [
                            {"role": "system", "content": SYSTEM_PROMPT}
                        ]

                    # Add the user and assistant messages
                    for msg in item["messages"]:
                        sessions[session_id].append(msg)
    else:
        print(f"Warning: {DATA_FILE} not found")


    # Convert sessions to training examples using sliding window approach
    for session_id, messages in sessions.items():

        # Only use examples with at least one exchange
        if len(messages) >= 3:  # system + user + assistant
            # Track whether we've added the full conversation already
            added_full = False

            # Include sliding window examples
            for i in range(3, len(messages), 2):  # Start with minimum context
                # Only include if this slice ends with an assistant message
                if i < len(messages) and messages[i - 1]["role"] == "assistant":
                    conversation_window = messages[:i]

                    # If we're at the last window (full conversation),
                    # only add it if we haven't already
                    if i >= len(messages) - 1:
                        if not added_full:
                            processed_examples.append({"messages": conversation_window})
                            added_full = True
                    else:
                        # For intermediate windows, always add
                        processed_examples.append({"messages": conversation_window})

            # Make sure we add the full conversation if we didn't already
            if not added_full:
                processed_examples.append({"messages": messages})


    # Write the processed data to the output file
    print(f"Writing {len(processed_examples)} examples to {OUTPUT_FILE}")
    with jsonlines.open(OUTPUT_FILE, mode="w") as outf:
        for item in processed_examples:
            outf.write(item)

    print(f"Training data preparation complete. Output file: {OUTPUT_FILE}")
    return OUTPUT_FILE


if __name__ == "__main__":
    output_file = prepare_training_data()
    print(f"\nSuccess! Your training file is ready at:\n{output_file}")
    print("\nTo use this file for training, run:")
    print(
        f"openai fine-tuning create -t {output_file} -m {MODEL} --suffix law_chat"
    )
