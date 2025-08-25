# utils/api_translator.py

def to_api_format(data_dict: dict, field_map: dict) -> dict:
    """
    Translates a Python dictionary with English keys to a dictionary
    with Persian keys suitable for the NocoDB API request body.

    Args:
        data_dict: The dictionary with internal English keys.
        field_map: The specific field mapping dictionary from settings.

    Returns:
        A new dictionary with Persian keys.
    """
    api_payload = {}
    for internal_key, value in data_dict.items():
        if internal_key in field_map:
            api_key = field_map[internal_key]
            api_payload[api_key] = value
    return api_payload


def from_api_format(api_object: dict, field_map: dict) -> dict:
    """
    Translates a NocoDB API response object with Persian keys to a
    clean Python dictionary with English keys.

    Args:
        api_object: The dictionary object from the API response.
        field_map: The specific field mapping dictionary from settings.

    Returns:
        A new dictionary with internal English keys.
    """
    # Create an inverted map for efficient lookup (Persian -> English)
    inverted_map = {v: k for k, v in field_map.items()}
    
    internal_data = {}
    for api_key, value in api_object.items():
        if api_key in inverted_map:
            internal_key = inverted_map[api_key]
            internal_data[internal_key] = value
    return internal_data