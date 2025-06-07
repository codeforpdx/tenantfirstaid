import json
import pathlib
from flask import request, jsonify, abort

DATA_PATH = pathlib.Path(__file__).with_name("sections.json")
with DATA_PATH.open(encoding="utf-8") as f:
    SECTIONS = json.load(f)

def get_citation():
    """
    GET /api/citation?section=90.101
    → 200 {"section": "90.101", "text": "..."}
    → 400 if param missing, 404 if unknown
    """
    section = request.args.get("section")
    if not section:
        abort(400, description="missing query param ?section=<number>")

    body = SECTIONS.get(section)
    if body is None:
        abort(404, description=f"section {section} not found")

    return jsonify({"section": section, "text": body})