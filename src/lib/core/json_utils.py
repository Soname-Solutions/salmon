import json


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

def replace_values_in_json(json_data: json, replacements: dict) -> dict:
    """
    Replaces values in a JSON object based on a dictionary of replacements.

    Args:
        json_data (dict): The JSON object.
        replacements (dict): Dictionary with keys as the values to be replaced and
                            corresponding values as the replacements.

    Returns:
        dict: Updated JSON object.
    """

    def replace_recursive(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = replace_recursive(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                obj[i] = replace_recursive(item)
        elif isinstance(obj, str) and obj in replacements:
            obj = replacements[obj]
        return obj

    return replace_recursive(json_data)