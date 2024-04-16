import json
import os


class Config:

    def __init__(self):
        self.path = os.path.join(os.getcwd(), "opkvs.json")
        if not os.path.isfile(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({}, f)
        self.data = {}

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def set(self, key, value, save=True):
        self.data[key] = value
        if save:
            self.save()
        return self

    def get(self, key, default=None):
        return self.data.get(key, default)
