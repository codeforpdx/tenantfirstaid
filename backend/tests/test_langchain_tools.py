"""
Test location sanitization and other methods
"""
from typing import Dict
from tenantfirstaid.location import UsaState, OregonCity
from tenantfirstaid.langchain_tools import _StateLawInputSchema, _CityLawInputSchema

def test_usastate_json_serialization():
    beaver_state = UsaState("or")
    schema = _StateLawInputSchema(query="", state=beaver_state)
    d: Dict[str, str] = schema.model_dump(mode="json")
    assert d['state'] == "or"

def test_oregoncity_json_serialization():
    rose_city = OregonCity("portland")
    beaver_state = UsaState("or")
    schema = _CityLawInputSchema(query="", city=rose_city, state=beaver_state)
    d: Dict[str, str] = schema.model_dump(mode="json")
    assert d['state'] == "or"

# TODO: negative tests for input validation

# TODO: test _filter_builder
