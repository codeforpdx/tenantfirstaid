from flask import jsonify, request

from .shared import SYSTEM_PROMPT, DEFAULT_PROMPT


def get_prompt():
    return jsonify(SYSTEM_PROMPT), 200


def set_prompt():
    if request.args.get("default", "false").lower() == "true":
        SYSTEM_PROMPT["prompt"] = DEFAULT_PROMPT
        return jsonify(SYSTEM_PROMPT), 200

    data = request.get_json(silent=True) or {}
    new_prompt = data.get("prompt")

    if not isinstance(new_prompt, str):
        return jsonify({"error": "'prompt' must be a string"}), 400

    SYSTEM_PROMPT["prompt"] = new_prompt
    return jsonify(SYSTEM_PROMPT), 200
