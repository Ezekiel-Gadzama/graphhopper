import json
import os
from typing import Dict
from config.settings import settings
from config.constants import constants

class CustomModel:
    def __init__(self):
        self.rule_map: Dict[str, float] = {}  # acts like a set for uniqueness
        self.load_existing_model()

    def load_existing_model(self) -> None:
        if os.path.exists(settings.CUSTOM_MODEL_PATH):
            try:
                with open(settings.CUSTOM_MODEL_PATH, "r") as f:
                    model = json.load(f)
                    priority_list = model.get(constants.PRIORITY_KEY, [])
                    for rule in priority_list:
                        condition = rule.get(constants.IF_CONDITION_KEY)
                        multiplier = rule.get(constants.MULTIPLY_BY_KEY, 1.0)
                        if condition:
                            self.rule_map[condition] = multiplier
            except json.JSONDecodeError:
                self.rule_map = {}

    def add_priority_rule(self, osm_id: int, multiplier: float) -> None:
        condition_str = f"osm_id == {osm_id}"
        self.rule_map[condition_str] = multiplier  # this ensures update or add (no duplicates)

    def save_to_file(self) -> None:
        priority_list = [
            {
                constants.IF_CONDITION_KEY: condition,
                constants.MULTIPLY_BY_KEY: multiplier
            }
            for condition, multiplier in self.rule_map.items()
        ]

        model = {constants.PRIORITY_KEY: priority_list}

        with open(settings.CUSTOM_MODEL_PATH, "w") as f:
            json.dump(model, f, indent=2)
