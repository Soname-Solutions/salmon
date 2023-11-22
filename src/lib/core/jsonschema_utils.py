import jsonschema


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
