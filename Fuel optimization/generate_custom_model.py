import json
import os

def factor_to_multiplier(jam_factor):
    return 1.0 + (jam_factor / 10.0)  # simple mapping

def write_custom_model(osm_id, multiplier, path="custom_model.json"):
    # Check if the file already exists and has valid JSON
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                custom_model = json.load(f)
        except json.JSONDecodeError:
            custom_model = {"priority": []}
    else:
        custom_model = {"priority": []}

    # Avoid duplicates (optional)
    new_rule = {
        "if": f"osm_id == {osm_id}",
        "multiply_by": multiplier
    }
    if new_rule not in custom_model["priority"]:
        custom_model["priority"].append(new_rule)

    # Write the updated model back to file
    with open(path, "w") as f:
        json.dump(custom_model, f, indent=2)
