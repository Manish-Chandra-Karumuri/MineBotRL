import gymnasium as gym
from gymnasium import spaces
import numpy as np
import time
import requests
import json

class MinecraftEnv(gym.Env):
    def __init__(self):
        super(MinecraftEnv, self).__init__()
        self.base_url = "http://localhost:3000"

        self.observation_space = spaces.Box(low=-1000, high=1000, shape=(6,), dtype=np.float32)
        self.action_space = spaces.Discrete(7)

        self.last_inventory_count = 0
        self.prev_obs = np.zeros(6, dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        print("🔄 Resetting Minecraft environment...")
        try:
            requests.post(f"{self.base_url}/reset", timeout=5)
            time.sleep(3)
        except Exception as e:
            print(f"[Env] Reset error: {e}")
        return self._get_observation(), {}

    def step(self, action):
        reward = 0
        terminated = False
        truncated = False
        info = {}

        try:
            endpoints = ["forward", "backward", "left", "right"]
            if action in range(4):
                requests.post(f"{self.base_url}/move", json={"direction": endpoints[action], "distance": 1}, timeout=3)
            elif action == 4:
                requests.post(f"{self.base_url}/jump", timeout=2)
            elif action == 5:
                requests.post(f"{self.base_url}/mine", timeout=3)
            elif action == 6:
                requests.post(f"{self.base_url}/collect", timeout=3)
            time.sleep(1.2)
        except Exception as e:
            print(f"[Env] Action error: {e}")

        obs = self._get_observation()
        curr_inventory = self._get_inventory_count()
        reward = curr_inventory - self.last_inventory_count
        self.last_inventory_count = curr_inventory

        return obs, reward, terminated, truncated, info

    def render(self):
        pass

    def _get_observation(self):
        try:
            response = requests.get(f"{self.base_url}/status", timeout=2)
            response.raise_for_status()
            data = response.json()
            pos = data.get("position", {})
            health = data.get("health", 0)
            food = data.get("hunger", 0)
            inventory = self._safe_inventory_count(data.get("inventory", {}))

            obs = np.array([
                pos.get("x", 0),
                pos.get("y", 0),
                pos.get("z", 0),
                health,
                food,
                inventory
            ], dtype=np.float32)
            self.prev_obs = obs
            return obs
        except Exception as e:
            print(f"[Env] Observation error: {e}")
            return self.prev_obs

    def _get_inventory_count(self):
        try:
            response = requests.get(f"{self.base_url}/status", timeout=2)
            response.raise_for_status()
            data = response.json()
            inventory = data.get("inventory", {})
            return self._safe_inventory_count(inventory)
        except Exception as e:
            print(f"[Env] Inventory count error: {e}")
            return 0

    def _safe_inventory_count(self, inventory):
        if isinstance(inventory, dict):
            return sum(int(v) for v in inventory.values() if isinstance(v, (int, float)))
        return 0
