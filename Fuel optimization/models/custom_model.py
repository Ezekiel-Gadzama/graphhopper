import json
import os
from typing import Dict, List
from config.settings import settings
from config.constants import constants

class CustomModel:
    def __init__(self):
        self.model = {constants.PRIORITY_KEY: []}
        self.load_existing_model()

    def load_existing_model(self) -> None:
        if os.path.exists(settings.CUSTOM_MODEL_PATH):
            try:
                with open(settings.CUSTOM_MODEL_PATH, "r") as f:
                    self.model = json.load(f)
                    if constants.PRIORITY_KEY not in self.model:
                        self.model[constants.PRIORITY_KEY] = []
            except json.JSONDecodeError:
                self.model = {constants.PRIORITY_KEY: []}

    def add_priority_rule(self, osm_id: int, multiplier: float) -> None:
        new_rule = {
            constants.IF_CONDITION_KEY: f"osm_id == {osm_id}",
            constants.MULTIPLY_BY_KEY: multiplier
        }
        
        if new_rule not in self.model[constants.PRIORITY_KEY]:
            self.model[constants.PRIORITY_KEY].append(new_rule)

    def save_to_file(self) -> None:
        with open(settings.CUSTOM_MODEL_PATH, "w") as f:
            json.dump(self.model, f, indent=2)