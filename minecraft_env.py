import gym
import numpy as np
import requests
import time
from gym import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env

class MinecraftEnv(gym.Env):
    def __init__(self):
        super(MinecraftEnv, self).__init__()
        
        # Define actions: forward, backward, left, right, jump, mine, attack, collect, explore
        self.action_space = spaces.Discrete(9)  
        
        # Define observations: position (x,y,z), health, hunger, inventory counts for key items, 
        # environment state flags (mining, collecting, exploring)
        self.observation_space = spaces.Box(low=-100, high=100, shape=(15,), dtype=np.float32)
        self.base_url = "http://localhost:3000"
        self.previous_position = None
        self.previous_inventory = {}
        self.step_count = 0
        self.last_reward = 0
        self.last_action = None
        
        # Rewarded items and their values
        self.valuable_items = {
            'diamond': 10.0,
            'iron_ingot': 5.0,
            'gold_ingot': 4.0,
            'coal': 2.0,
            'oak_log': 1.0,
            'stone': 0.5,
            'dirt': 0.1
        }

    def reset(self):
        try:
            requests.post(f"{self.base_url}/connect", json={
                "host": "localhost",
                "port": 25565,
                "username": "TeriMakiKamKar",
                "version": "1.21.1"
            })
            time.sleep(5)  # Give bot time to spawn
        except Exception as e:
            print(f"Warning: Could not connect bot: {e}")
        
        self.step_count = 0
        self.last_reward = 0
        self.last_action = None
        obs = self._get_obs()
        self.previous_position = obs[0:3]  # Save x,y,z
        self.previous_inventory = self._get_inventory()
        return obs

    def _get_obs(self):
        try:
            status = requests.get(f"{self.base_url}/status").json()
        except:
            return np.zeros(15, dtype=np.float32)

        # Extract position
        pos = status.get("position", {})
        x = pos.get("x", 0)
        y = pos.get("y", 0)
        z = pos.get("z", 0)
        
        # Extract inventory
        inv = status.get("inventory", {})
        
        # Create observation vector
        obs = [
            x, y, z,  # Position
            status.get("health", 0),  # Health
            status.get("hunger", 0),  # Hunger
            inv.get("diamond", 0),  # Key items
            inv.get("iron_ingot", 0),
            inv.get("gold_ingot", 0),
            inv.get("coal", 0),
            inv.get("oak_log", 0),
            inv.get("stone", 0),
            inv.get("dirt", 0),
            int(status.get("isMining", False)),  # State flags
            int(status.get("isCollecting", False)),
            status.get("itemsCollected", 0)  # Total collected items
        ]
        
        return np.array(obs, dtype=np.float32)

    def _get_inventory(self):
        try:
            status = requests.get(f"{self.base_url}/status").json()
            return status.get("inventory", {})
        except:
            return {}

    def _calculate_reward(self, current_obs):
        reward = 0
        
        # Position changed reward - exploration
        if self.previous_position is not None:
            pos_diff = np.linalg.norm(current_obs[0:3] - self.previous_position)
            # Small reward for movement if not too small (not just jittering in place)
            if 0.5 < pos_diff < 10:  
                reward += 0.05 * pos_diff
            # Penalty for no movement
            elif pos_diff < 0.1 and self.last_action in [0, 1, 2, 3]:  # Movement actions
                reward -= 0.1
        
        # Item collection rewards
        current_inventory = self._get_inventory()
        if self.previous_inventory:
            for item, value in self.valuable_items.items():
                prev_count = self.previous_inventory.get(item, 0)
                curr_count = current_inventory.get(item, 0)
                if curr_count > prev_count:
                    reward += (curr_count - prev_count) * value
        
        # Mining activity reward
        if current_obs[13] > 0:  # if mining
            reward += 0.2
        
        # Collecting activity reward
        if current_obs[14] > 0:  # if collecting
            reward += 0.3
        
        # Small penalty for taking too many steps without reward
        if self.last_reward == 0:
            reward -= 0.01
        
        self.last_reward = reward
        return reward

    def step(self, action):
        self.step_count += 1
        self.last_action = action
        
        # Execute action based on index
        try:
            if action == 0:  # Forward
                requests.post(f"{self.base_url}/move", json={"direction": "forward", "distance": 1})
            elif action == 1:  # Backward
                requests.post(f"{self.base_url}/move", json={"direction": "backward", "distance": 1})
            elif action == 2:  # Left
                requests.post(f"{self.base_url}/move", json={"direction": "left", "distance": 1})
            elif action == 3:  # Right
                requests.post(f"{self.base_url}/move", json={"direction": "right", "distance": 1})
            elif action == 4:  # Jump
                requests.post(f"{self.base_url}/jump")
            elif action == 5:  # Mine
                requests.post(f"{self.base_url}/mine")
            elif action == 6:  # Attack
                requests.post(f"{self.base_url}/attack")
            elif action == 7:  # Collect
                requests.post(f"{self.base_url}/collect")
            elif action == 8:  # Explore (handled by bot's internal logic)
                pass
            
            # Add a short delay to let actions complete
            time.sleep(0.5)
        except Exception as e:
            print(f"Error executing action: {e}")
        
        # Get updated state
        current_obs = self._get_obs()
        
        # Calculate reward
        reward = self._calculate_reward(current_obs)
        
        # Check if episode is done
        done = current_obs[3] <= 0 or self.step_count >= 500  # Done if health <= 0 or max steps reached
        
        # Update previous state
        self.previous_position = current_obs[0:3]
        self.previous_inventory = self._get_inventory()
        
        return current_obs, reward, done, {}

    def render(self, mode="human"):
        # Render is not implemented but could display status information
        print(f"Step: {self.step_count}, Last Action: {self.last_action}, Last Reward: {self.last_reward}")
        try:
            status = requests.get(f"{self.base_url}/status").json()
            print(f"Position: {status.get('position')}")
            print(f"Health: {status.get('health')}, Hunger: {status.get('hunger')}")
            print(f"Inventory: {status.get('inventory')}")
            print(f"Mining: {status.get('isMining')}, Collecting: {status.get('isCollecting')}")
        except:
            print("Could not get status")

    def close(self):
        pass
        
# Test the environment if run directly
if __name__ == "__main__":
    env = MinecraftEnv()
    # Validate environment
    check_env(env, warn=True)
    
    # Test environment with random actions
    obs = env.reset()
    done = False
    total_reward = 0
    
    while not done:
        action = env.action_space.sample()  # Random action
        obs, reward, done, _ = env.step(action)
        total_reward += reward
        env.render()
        
        if done:
            print(f"Episode done. Total reward: {total_reward}")
            break