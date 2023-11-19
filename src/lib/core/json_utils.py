import json
import jsonschema


def parse_json(json_data: str) -> dict:
    """Parses the input JSON data into a Python dictionary.

    Args:
        json_data (str): The JSON data.

    Returns:
        dict: Parsed JSON data as a dictionary.

    Raises:
        json.JSONDecodeError: If there's an error parsing the JSON data.

    """
    try:
        parsed_data = json.loads(json_data)
        return parsed_data
    except json.decoder.JSONDecodeError as e:
        raise json.decoder.JSONDecodeError(
            f"Error parsing JSON data '{json_data[:100]}...'", e.doc, e.pos
        )


def validate_json_schema(json_data: dict, json_schema: dict):
    """Validates a JSON data against the schema.

    Args:
        json_data (dict): The JSON data.
        json_schema (dict): The JSON schema to be used for validation.

    Raises:
        jsonschema.exceptions.ValidationError: If the JSON file does not match the schema.
    """
    try:
        jsonschema.validate(json_data, json_schema)
    except jsonschema.exceptions.ValidationError as e:
        raise jsonschema.exceptions.ValidationError(
            f"JSON schema validation failed for '{str(json_data)[:100]}...': {e}"
        )
