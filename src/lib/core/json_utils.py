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
