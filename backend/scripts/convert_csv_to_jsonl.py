import csv
import json

with open("scripts/eval.csv", newline="") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # separate the "Text Confirmation" field lines starting with "You:" and "Bot:" into separate list items
        messages = []
        you_messages = row["Text Confirmation"].split("You:")
        for you_message in you_messages:
            if you_message.strip():
                bot_messages = you_message.split("Bot:")
                messages.append({"role": "user", "content": bot_messages[0].strip()})
                if len(bot_messages) > 1:
                    messages.append(
                        {"role": "assistant", "content": bot_messages[1].strip()}
                    )

        # Save the last bot message as the ideal answer
        ideal_answer = messages.pop()["content"]

        # output the messages in JSONL format
        output = {
            "messages": messages,
            "ideal": ideal_answer,
        }
        # print as JSONL
        print(json.dumps(output, ensure_ascii=False))
