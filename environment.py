import gymnasium as gym
from gymnasium import spaces
import numpy as np
import time
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MinecraftEnv")

class EnhancedMinecraftEnv(gym.Env):
    """
    Enhanced Minecraft environment with improved observation space and reward structure
    """
    def __init__(self, server_url="http://localhost:3000"):
        super(EnhancedMinecraftEnv, self).__init__()
        self.base_url = server_url
        
        # Configuration
        self.max_episode_steps = 500
        self.step_count = 0
        
        # Define action space with more actions
        # 0-3: Movement (forward, backward, left, right)
        # 4: Jump
        # 5: Mine block
        # 6: Place block
        # 7: Craft item
        # 8: Collect item
        # 9: Eat food
        self.action_space = spaces.Discrete(10)
        
        # Enhanced observation space
        # [0-2]: Position (x, y, z)
        # [3]: Health
        # [4]: Food
        # [5-9]: Inventory counts (wood, stone, crafting_table, pickaxe, food)
        # [10-12]: Block types in view (in front, below, above)
        # [13]: Biome type (encoded)
        # [14]: Time of day
        # [15]: Threat level (enemies nearby)
        self.observation_space = spaces.Box(
            low=-1000, high=1000, shape=(16,), dtype=np.float32
        )
        
        # Track previous values for reward calculation
        self.last_inventory = {}
        self.prev_obs = np.zeros(16, dtype=np.float32)
        self.last_position = np.zeros(3, dtype=np.float32)
        
        # Item values for reward calculation
        self.item_values = {
            "oak_log": 1.0,
            "oak_planks": 0.5,
            "stick": 0.3,
            "crafting_table": 2.0,
            "wooden_pickaxe": 3.0,
            "stone": 0.5,
            "cobblestone": 0.7,
            "stone_pickaxe": 5.0,
            "iron_ore": 7.0,
            "iron_ingot": 10.0,
            "cooked_beef": 2.0,
            "apple": 1.5
        }
        
        # Connect to the Minecraft server to ensure it's ready
        self._check_server_connection()
    
    def _check_server_connection(self):
        """Check if the server is running and ready"""
        try:
            response = requests.get(f"{self.base_url}/status", timeout=5)
            if response.status_code == 200:
                logger.info("Successfully connected to Minecraft server")
            else:
                logger.warning(f"Server responded with status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to connect to Minecraft server: {e}")
            logger.info("Make sure the Minecraft bot server is running")
    
    def reset(self, seed=None, options=None):
        """Reset the environment to start a new episode"""
        super().reset(seed=seed)
        logger.info("Resetting Minecraft environment...")
        
        try:
            requests.post(f"{self.base_url}/reset", timeout=5)
            time.sleep(3)  # Wait for server to reset
            
            # Get initial observation
            obs = self._get_observation()
            self.prev_obs = obs
            self.last_position = obs[0:3]
            self.last_inventory = self._get_inventory()
            self.step_count = 0
            
            return obs, {}
        except Exception as e:
            logger.error(f"Reset error: {e}")
            # Return zero observation if reset fails
            return self.prev_obs, {}
    
    def step(self, action):
        """Take a step in the environment with the given action"""
        self.step_count += 1
        reward = 0
        terminated = False
        truncated = False
        info = {}
        
        try:
            # Process different actions
            if action in range(4):
                # Movement actions
                directions = ["forward", "backward", "left", "right"]
                requests.post(f"{self.base_url}/move", json={"direction": directions[action], "distance": 1}, timeout=3)
            elif action == 4:
                # Jump
                requests.post(f"{self.base_url}/jump", timeout=2)
            elif action == 5:
                # Mine block
                requests.post(f"{self.base_url}/mine", timeout=3)
            elif action == 6:
                # Place block (if available in inventory)
                requests.post(f"{self.base_url}/place", timeout=3)
            elif action == 7:
                # Craft item (if possible)
                requests.post(f"{self.base_url}/craft", timeout=3)
            elif action == 8:
                # Collect item
                requests.post(f"{self.base_url}/collect", timeout=3)
            elif action == 9:
                # Eat food (if available)
                requests.post(f"{self.base_url}/eat", timeout=3)
            
            # Wait for action to complete
            time.sleep(1.0)
            
            # Get new observation
            obs = self._get_observation()
            current_inventory = self._get_inventory()
            
            # Calculate reward components
            reward = self._calculate_reward(obs, current_inventory, action)
            
            # Update tracking variables for next step
            self.prev_obs = obs
            self.last_inventory = current_inventory
            self.last_position = obs[0:3]
            
            # Check if episode should end
            if obs[3] <= 0:  # Health <= 0
                terminated = True
                reward -= 10  # Penalty for dying
            
            if self.step_count >= self.max_episode_steps:
                truncated = True
            
            # Add relevant info for debugging and tracking
            info = {
                "inventory": current_inventory,
                "health": obs[3],
                "food": obs[4],
                "step_count": self.step_count,
                "position": obs[0:3].tolist()
            }
            
            return obs, reward, terminated, truncated, info
            
        except Exception as e:
            logger.error(f"Step error: {e}")
            return self.prev_obs, -0.1, terminated, truncated, info
    
    def _calculate_reward(self, obs, current_inventory, action):
        """Calculate the reward based on changes in the environment and agent's state"""
        reward = 0
        
        # 1. Reward for collecting valuable items
        for item, value in self.item_values.items():
            prev_count = self.last_inventory.get(item, 0)
            curr_count = current_inventory.get(item, 0)
            if curr_count > prev_count:
                reward += (curr_count - prev_count) * value
                logger.debug(f"Reward for collecting {item}: +{(curr_count - prev_count) * value}")
        
        # 2. Reward for crafting
        if action == 7 and any(curr_count > prev_count for item, curr_count in current_inventory.items() 
                              if item in ["wooden_pickaxe", "stone_pickaxe", "crafting_table", "stick", "oak_planks"]):
            reward += 2.0
            logger.debug("Reward for successful crafting: +2.0")
        
        # 3. Reward for exploration (based on movement)
        if action in range(4):
            # Calculate distance moved
            position_delta = np.linalg.norm(obs[0:3] - self.last_position)
            if position_delta > 0.5:  # Only reward significant movement
                reward += 0.05 * position_delta
                logger.debug(f"Reward for exploration: +{0.05 * position_delta}")
        
        # 4. Penalty for repeating the same action in the same location
        if action in range(4) and np.linalg.norm(obs[0:3] - self.last_position) < 0.1:
            reward -= 0.1
            logger.debug("Penalty for not moving: -0.1")
        
        # 5. Small reward for maintaining health and food
        if obs[3] > self.prev_obs[3]:  # Health increased
            reward += 0.5
            logger.debug("Reward for health increase: +0.5")
        
        if obs[4] > self.prev_obs[4]:  # Food increased
            reward += 0.3
            logger.debug("Reward for food increase: +0.3")
        
        # 6. Bonus for achieving specific goals
        if "wooden_pickaxe" in current_inventory and self.last_inventory.get("wooden_pickaxe", 0) == 0:
            reward += 5.0
            logger.debug("Major milestone: Crafted first wooden pickaxe! +5.0")
        
        if "stone_pickaxe" in current_inventory and self.last_inventory.get("stone_pickaxe", 0) == 0:
            reward += 10.0
            logger.debug("Major milestone: Crafted first stone pickaxe! +10.0")
        
        return reward
    
    def _get_observation(self):
        """Get the current observation from the environment"""
        try:
            response = requests.get(f"{self.base_url}/status", timeout=3)
            response.raise_for_status()
            data = response.json()
            
            # Extract position
            pos = data.get("position", {})
            
            # Extract inventory counts for tracked items
            inventory = data.get("inventory", {})
            
            # Extract block information
            blocks = data.get("blocks", {})
            block_in_front = self._encode_block_type(blocks.get("front", "air"))
            block_below = self._encode_block_type(blocks.get("below", "air"))
            block_above = self._encode_block_type(blocks.get("above", "air"))
            
            # Other environmental information
            biome = self._encode_biome(data.get("biome", "plains"))
            time_of_day = data.get("timeOfDay", 0) / 24000.0  # Normalize to 0-1
            threat_level = data.get("threatLevel", 0)
            
            # Construct observation vector
            obs = np.array([
                pos.get("x", 0),
                pos.get("y", 0),
                pos.get("z", 0),
                data.get("health", 0),
                data.get("hunger", 0),
                inventory.get("oak_log", 0),
                inventory.get("cobblestone", 0),
                inventory.get("crafting_table", 0),
                inventory.get("wooden_pickaxe", 0) + inventory.get("stone_pickaxe", 0),
                inventory.get("cooked_beef", 0) + inventory.get("apple", 0),
                block_in_front,
                block_below,
                block_above,
                biome,
                time_of_day,
                threat_level
            ], dtype=np.float32)
            
            return obs
        except Exception as e:
            logger.error(f"Error getting observation: {e}")
            return self.prev_obs
    
    def _get_inventory(self):
        """Get the current inventory state"""
        try:
            response = requests.get(f"{self.base_url}/status", timeout=3)
            response.raise_for_status()
            data = response.json()
            return data.get("inventory", {})
        except Exception as e:
            logger.error(f"Error getting inventory: {e}")
            return self.last_inventory
    
    def _encode_block_type(self, block_type):
        """Encode block type as a numeric value"""
        block_values = {
            "air": 0,
            "dirt": 1,
            "grass_block": 2,
            "stone": 3,
            "oak_log": 4,
            "oak_leaves": 5,
            "crafting_table": 6,
            "coal_ore": 7,
            "iron_ore": 8,
            "water": 9,
            "lava": 10
        }
        return block_values.get(block_type, 0)
    
    def _encode_biome(self, biome):
        """Encode biome as a numeric value"""
        biome_values = {
            "plains": 0,
            "forest": 1,
            "desert": 2,
            "mountains": 3,
            "swamp": 4,
            "ocean": 5,
            "river": 6,
            "beach": 7,
            "jungle": 8,
            "taiga": 9
        }
        return biome_values.get(biome, 0)
    
    def render(self):
        """Render the environment (prints current status to console)"""
        try:
            status = requests.get(f"{self.base_url}/status", timeout=3).json()
            logger.info(f"Position: {status.get('position')}")
            logger.info(f"Health: {status.get('health')}, Food: {status.get('hunger')}")
            logger.info(f"Inventory: {status.get('inventory')}")
        except Exception as e:
            logger.error(f"Error rendering: {e}")
    
    def close(self):
        """Clean up resources"""
        try:
            requests.post(f"{self.base_url}/disconnect", timeout=3)
            logger.info("Environment closed and bot disconnected")
        except Exception as e:
            logger.error(f"Error closing environment: {e}")