import gym
import numpy as np
import requests
import time
import logging
import subprocess
import os
import json
import atexit
import random

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("minecraft_bot.log"),
                              logging.StreamHandler()])
logger = logging.getLogger("MinecraftEnvJS")

class MinecraftJSEnv(gym.Env):
    """
    Minecraft environment for Reinforcement Learning using a JavaScript bridge
    """
    def __init__(self, js_server_url='http://localhost:3000', start_js_server=True, minecraft_username='RLBot'):
        super(MinecraftJSEnv, self).__init__()
        
        # JS Server configuration
        self.js_server_url = js_server_url
        self.js_server_process = None
        self.start_js_server = start_js_server
        self.minecraft_username = minecraft_username
        
        # Environment parameters
        self.max_steps = 10000
        self.current_step = 0
        self.health = 20
        self.hunger = 20
        self.inventory = {}
        self.position = {'x': 0, 'y': 0, 'z': 0}
        self.time_of_day = 0
        
        # Action and observation space
        # Define actions:
        # 0: Move forward
        # 1: Move backward
        # 2: Move left
        # 3: Move right
        # 4: Jump
        # 5: Attack
        # 6: Mine block
        # 7: Place block (dirt)
        # 8: Place block (stone)
        # 9: Run command (/time set day)
        # 10: Run command (/weather clear)
        self.action_space = gym.spaces.Discrete(11)
        
        # Observation space
        self.observation_space = gym.spaces.Box(
            low=0, high=1, shape=(20,), dtype=np.float32
        )
        
        # Start the JS server if requested
        if self.start_js_server:
            self._start_js_server()
        
        # Connect to the Minecraft server
        self.connect()
        
        # Register the cleanup function
        atexit.register(self.close)
    
    def _start_js_server(self):
        """Start the JavaScript server"""
        try:
            # Assumes the js file is in the same directory
            js_file_path = os.path.join(os.path.dirname(__file__), 'minecraft_bot.js')
            
            if not os.path.exists(js_file_path):
                logger.error(f"JavaScript file not found at {js_file_path}")
                return False
            
            logger.info("Starting JavaScript server...")
            self.js_server_process = subprocess.Popen(['node', js_file_path], 
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE)
            
            # Give the server time to start
            time.sleep(2)
            
            # Check if the server started successfully
            if self.js_server_process.poll() is not None:
                stdout, stderr = self.js_server_process.communicate()
                logger.error(f"Failed to start JavaScript server. Stdout: {stdout.decode()}, Stderr: {stderr.decode()}")
                return False
            
            logger.info("JavaScript server started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting JavaScript server: {e}")
            return False
    
    def connect(self):
        """Connect to the Minecraft server via the JavaScript bridge"""
        try:
            # Send connection request to the JS server
            response = requests.post(
                f"{self.js_server_url}/connect", 
                json={"username": self.minecraft_username}
            )
            
            # Check response
            if response.status_code == 200:
                logger.info("Connection request sent to JavaScript server")
                
                # Wait for the bot to connect (timeout after 20 seconds)
                max_attempts = 40
                for attempt in range(max_attempts):
                    status = self._get_status()
                    if status and status.get('connected', False):
                        logger.info("Connected to Minecraft server")
                        
                        # Give the bot some time to stabilize in the game
                        logger.info("Waiting for bot to stabilize in the game...")
                        time.sleep(3)
                        
                        return True
                    
                    logger.info(f"Waiting for connection... ({attempt+1}/{max_attempts})")
                    time.sleep(0.5)
                
                logger.error("Timed out waiting for connection")
                return False
            else:
                logger.error(f"Failed to send connection request: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to JavaScript server: {e}")
            return False
    
    def _get_status(self):
        """Get the current status from the JavaScript server"""
        try:
            response = requests.get(f"{self.js_server_url}/status")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get status: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting status: {e}")
            return None
    
    def update_state(self):
        """Update the environment state from the JavaScript server"""
        status = self._get_status()
        if status:
            self.health = status.get('health', 20)
            self.hunger = status.get('hunger', 20)
            self.position = status.get('position', {'x': 0, 'y': 0, 'z': 0})
            self.inventory = status.get('inventory', {})
    
    def reset(self):
        """Reset the environment to its initial state"""
        self.current_step = 0
        self.health = 20
        self.hunger = 20
        
        # Update the state from the JavaScript server
        self.update_state()
        
        return self._get_observation()
    
    def _get_observation(self):
        """Convert the current state into an observation vector"""
        observation = np.zeros(20, dtype=np.float32)
        
        # Basic observations
        observation[0] = self.health / 20.0  # Normalize health to [0, 1]
        observation[1] = self.hunger / 20.0  # Normalize hunger to [0, 1]
        
        # Position information (normalized somewhat arbitrarily)
        max_coord = 100.0  # Assume world isn't bigger than this for normalization
        observation[2] = (self.position.get('x', 0) + max_coord) / (2 * max_coord)
        observation[3] = self.position.get('y', 0) / 256.0  # Y is 0-256 in Minecraft
        observation[4] = (self.position.get('z', 0) + max_coord) / (2 * max_coord)
        
        # Inventory information
        observation[5] = min(self.inventory.get("oak_log", 0) / 64.0, 1.0)
        observation[6] = min(self.inventory.get("cobblestone", 0) / 64.0, 1.0)
        observation[7] = min(self.inventory.get("iron_ore", 0) / 64.0, 1.0)
        observation[8] = min(self.inventory.get("cooked_beef", 0) / 64.0, 1.0)
        
        # Tool possession as binary features
        observation[9] = 1.0 if self.inventory.get("wooden_pickaxe", 0) > 0 else 0.0
        observation[10] = 1.0 if self.inventory.get("stone_pickaxe", 0) > 0 else 0.0
        observation[11] = 1.0 if self.inventory.get("iron_pickaxe", 0) > 0 else 0.0
        observation[12] = 1.0 if self.inventory.get("wooden_sword", 0) > 0 else 0.0
        observation[13] = 1.0 if self.inventory.get("stone_sword", 0) > 0 else 0.0
        observation[14] = 1.0 if self.inventory.get("iron_sword", 0) > 0 else 0.0
        
        # The remaining elements could be used for nearby block information,
        # nearby entities, etc. For now, we'll just leave them as zeros.
        
        return observation
    
    def step(self, action):
        """Execute one action in the environment"""
        self.current_step += 1
        done = False
        
        # Execute the selected action
        reward = self._execute_action(action)
        
        # Update the environment state
        self.update_state()
        
        # Check if the episode is done
        if self.current_step >= self.max_steps or self.health <= 0:
            done = True
        
        # Return the observation, reward, done flag, and additional info
        observation = self._get_observation()
        info = {
            "health": self.health,
            "hunger": self.hunger,
            "inventory": self.inventory,
            "position": self.position
        }
        
        return observation, reward, done, info
    
    def _execute_action(self, action):
        """Execute the selected action in Minecraft via JavaScript bridge with enhanced mining focus"""
        reward = 0
        
        try:
            if action == 0:  # Move forward
                response = requests.post(
                    f"{self.js_server_url}/move", 
                    json={"direction": "forward", "distance": 1}
                )
                reward = 0.05  # Lower reward for movement
            
            elif action == 1:  # Move backward
                response = requests.post(
                    f"{self.js_server_url}/move", 
                    json={"direction": "backward", "distance": 1}
                )
                reward = 0.05  # Lower reward for movement
            
            elif action == 2:  # Move left
                response = requests.post(
                    f"{self.js_server_url}/move", 
                    json={"direction": "left", "distance": 1}
                )
                reward = 0.05  # Lower reward for movement
            
            elif action == 3:  # Move right
                response = requests.post(
                    f"{self.js_server_url}/move", 
                    json={"direction": "right", "distance": 1}
                )
                reward = 0.05  # Lower reward for movement
            
            elif action == 4:  # Jump
                response = requests.post(f"{self.js_server_url}/jump")
                reward = 0.05  # Lower reward for jumping
            
            elif action == 5:  # Attack
                response = requests.post(f"{self.js_server_url}/attack")
                result = response.json() if response.status_code == 200 else {}
                # Reward for successful attack
                if result.get('status') == 'attacked':
                    reward = 0.2
                else:
                    reward = 0.05
            
            elif action == 6:  # Mine block
                response = requests.post(f"{self.js_server_url}/mine")
                result = response.json() if response.status_code == 200 else {}
                
                # MUCH higher reward for successful mining
                if result.get('status') == 'mined':
                    block_type = result.get('block', '')
                    if 'log' in block_type:
                        reward = 2.0  # Highest reward for mining wood
                    elif 'stone' in block_type or 'ore' in block_type:
                        reward = 1.5  # High reward for mining stone/ore
                    else:
                        reward = 1.0  # Good reward for mining anything
                    
                    # Log successful mining
                    logger.info(f"Bot successfully mined a {block_type} block! Reward: {reward}")
                else:
                    # Small reward just for trying to mine
                    reward = 0.2
                    
                    # Try to look for a block that can be mined
                    self._look_for_minable_block()
            
            elif action == 7:  # Place dirt block
                response = requests.post(
                    f"{self.js_server_url}/place", 
                    json={"itemName": "dirt"}
                )
                result = response.json() if response.status_code == 200 else {}
                # Reward for successful placement
                if result.get('status') == 'placed':
                    reward = 0.3
                else:
                    reward = 0.05
            
            elif action == 8:  # Place stone block
                response = requests.post(
                    f"{self.js_server_url}/place", 
                    json={"itemName": "stone"}
                )
                result = response.json() if response.status_code == 200 else {}
                # Reward for successful placement
                if result.get('status') == 'placed':
                    reward = 0.3
                else:
                    reward = 0.05
            
            elif action == 9:  # Run command: set time to day
                response = requests.post(
                    f"{self.js_server_url}/command", 
                    json={"command": "time set day"}
                )
                reward = 0.1
            
            elif action == 10:  # Run command: weather clear
                response = requests.post(
                    f"{self.js_server_url}/command", 
                    json={"command": "weather clear"}
                )
                reward = 0.1
            
            else:
                logger.warning(f"Unknown action: {action}")
                reward = -0.1
                
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            reward = -0.1
        
        return reward
    
    def _look_for_minable_block(self):
        """Helper function to make the bot look for blocks it can mine"""
        try:
            # Get blocks around the bot
            blocks = self.get_blocks_around(radius=5)
            
            # Filter for preferred blocks (logs, stone)
            preferred_blocks = {}
            for block_type, block_positions in blocks.items():
                if 'log' in block_type or 'stone' in block_type or 'ore' in block_type:
                    preferred_blocks[block_type] = block_positions
            
            # If no preferred blocks, use any blocks
            if not preferred_blocks:
                preferred_blocks = blocks
            
            # Find a random block to look at
            if preferred_blocks:
                block_type = random.choice(list(preferred_blocks.keys()))
                if preferred_blocks[block_type]:
                    block_pos = random.choice(preferred_blocks[block_type])
                    
                    # Move closer to the block
                    self.move_to_block(block_pos)
                    logger.info(f"Bot is now looking at a {block_type} block")
                    return True
        
        except Exception as e:
            logger.error(f"Error looking for minable block: {e}")
        
        return False
    
    def get_blocks_around(self, radius=3):
        """Get blocks in a radius around the player"""
        try:
            response = requests.get(
                f"{self.js_server_url}/blocks", 
                params={"radius": radius}
            )
            
            if response.status_code == 200:
                return response.json().get('blocks', {})
            else:
                logger.error(f"Failed to get blocks: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting blocks: {e}")
            return {}
    
    def find_nearest_resource(self, resource_type):
        """Find the nearest block of a specific resource type"""
        blocks = self.get_blocks_around(radius=10)
        
        if resource_type in blocks and blocks[resource_type]:
            # Find the closest block of this type
            pos = self.position
            closest_block = min(
                blocks[resource_type],
                key=lambda b: ((b['x'] - pos['x'])**2 + (b['y'] - pos['y'])**2 + (b['z'] - pos['z'])**2)
            )
            return closest_block
        
        return None
    
    def move_to_block(self, block_pos):
        """Move the bot to a specific block position"""
        if not block_pos:
            return False
            
        # Convert block position format if needed
        if isinstance(block_pos, dict):
            x, y, z = block_pos.get('x', 0), block_pos.get('y', 0), block_pos.get('z', 0)
        else:
            x, y, z = block_pos
            
        try:
            # Use the teleport command to move to the block
            response = requests.post(
                f"{self.js_server_url}/command",
                json={"command": f"tp @e[name={self.minecraft_username}] {x} {y} {z}"}
            )
            
            # Update the bot's position
            self.position = {'x': x, 'y': y, 'z': z}
            
            # Give the bot time to stabilize after teleporting
            time.sleep(0.5)
            
            return True
        except Exception as e:
            logger.error(f"Error moving to block: {e}")
            return False
    
    def craft_item(self, item_name):
        """Craft an item (placeholder - would need to be implemented in the JS server)"""
        logger.info(f"Attempting to craft {item_name}")
        
        # This would need a proper implementation in the JavaScript server
        # For now, we'll just use a command to give the item to simulate crafting
        try:
            # Give the player the item
            response = requests.post(
                f"{self.js_server_url}/command",
                json={"command": f"give {self.minecraft_username} minecraft:{item_name} 1"}
            )
            
            # Update the inventory
            self.update_state()
            
            return item_name in self.inventory
        except Exception as e:
            logger.error(f"Error crafting item: {e}")
            return False
    
    def get_entity_nearby(self, entity_type, distance=10):
        """Check if there's an entity of the specified type nearby"""
        try:
            # This would need to be implemented in the JavaScript server
            # For now, we'll use a command to detect entities
            response = requests.post(
                f"{self.js_server_url}/command",
                json={"command": f"execute if entity @e[type={entity_type},distance=..{distance}]"}
            )
            
            # Parse the response to determine if an entity was found
            # This is just a placeholder - the actual implementation would depend
            # on the JavaScript server's capabilities
            result = response.text if response else ""
            
            return "Found entity" in result
        except Exception as e:
            logger.error(f"Error checking for nearby entities: {e}")
            return False
    
    def eat_food(self, food_item="cooked_beef"):
        """Eat food to restore hunger"""
        logger.info(f"Attempting to eat {food_item}")
        
        # This would need a proper implementation in the JavaScript server
        # For now, we'll just use a command to simulate eating
        try:
            # First make sure the player has the food item
            if food_item not in self.inventory or self.inventory[food_item] <= 0:
                # Give the player the food item
                response = requests.post(
                    f"{self.js_server_url}/command",
                    json={"command": f"give {self.minecraft_username} minecraft:{food_item} 1"}
                )
            
            # Simulate eating (would need proper implementation)
            # For now, just restore hunger directly
            self.hunger = min(20, self.hunger + 4)
            
            # Update the state
            self.update_state()
            
            return True
        except Exception as e:
            logger.error(f"Error eating food: {e}")
            return False
    
    def run_command(self, command):
        """Run a Minecraft command"""
        try:
            response = requests.post(
                f"{self.js_server_url}/command", 
                json={"command": command}
            )
            
            if response.status_code == 200:
                logger.info(f"Command executed: {command}")
                return True
            else:
                logger.error(f"Failed to execute command: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return False
    
    def teleport_to_resources(self):
        """Teleport the bot to an area with resources"""
        try:
            # First, check if there are resources nearby
            blocks = self.get_blocks_around(radius=10)
            has_resources = False
            
            for block_type, positions in blocks.items():
                if ('log' in block_type or 'stone' in block_type or 'ore' in block_type) and positions:
                    has_resources = True
                    break
            
            # If no resources nearby, teleport to a new location
            if not has_resources:
                logger.info("No resources found nearby. Teleporting to find resources...")
                
                # Get current position
                x, y, z = self.position.get('x', 0), self.position.get('y', 0), self.position.get('z', 0)
                
                # Generate a random offset (30-50 blocks away)
                dx = random.randint(30, 50) * (1 if random.random() > 0.5 else -1)
                dz = random.randint(30, 50) * (1 if random.random() > 0.5 else -1)
                
                # Teleport to new location
                new_x, new_z = x + dx, z + dz
                
                # Find a good Y level (start high and let the bot fall)
                self.run_command(f"execute in minecraft:overworld run tp {self.minecraft_username} {new_x} 150 {new_z}")
                time.sleep(1)  # Wait for the teleport to complete
                
                # Update our state
                self.update_state()
                
                # Announce teleport
                self.run_command("say Searching for resources in a new area!")
                
                return True
        except Exception as e:
            logger.error(f"Error teleporting to resources: {e}")
        
        return False
    
    def close(self):
        """Clean up resources"""
        try:
            if self.js_server_process and self.js_server_process.poll() is None:
                logger.info("Shutting down JavaScript server...")
                self.js_server_process.terminate()
                self.js_server_process.wait(timeout=5)
                logger.info("JavaScript server shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down JavaScript server: {e}")


# Example usage
if __name__ == "__main__":
    # Create a Minecraft environment
    env = MinecraftJSEnv()
    
    # Reset the environment
    observation = env.reset()
    
    # Run a few actions
    for i in range(10):
        # Take a random action
        action = env.action_space.sample()
        observation, reward, done, info = env.step(action)
        
        print(f"Step {i+1}")
        print(f"Action: {action}")
        print(f"Reward: {reward}")
        print(f"Observation: {observation}")
        print(f"Info: {info}")
        
        if done:
            break
    
    # Clean up
    env.close()