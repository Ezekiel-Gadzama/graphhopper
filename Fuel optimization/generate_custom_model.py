

def jam_factor_to_multiplier(jam_factor):
    return 1.0 + (jam_factor / 10.0)  # simple mapping

def write_custom_model(road_id, multiplier, path="custom_model.json"):
    custom_model = {
        "priority": [
            {
                "if": f"road_id == '{road_id}'",
                "multiply_by": multiplier
            }
        ]
    }

    import json
    with open(path, "w") as f:
        json.dump(custom_model, f, indent=2)

# Example usage:
jam_factor = 5.5
multiplier = jam_factor_to_multiplier(jam_factor)
write_custom_model("road_001", multiplier)
