import gym
import numpy as np
import logging
import time
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("minecraft_bot.log"),
                              logging.StreamHandler()])
logger = logging.getLogger("TaskManager")

class MinecraftTaskManager:
    """
    Manages high-level tasks for the Minecraft bot
    Each task has its own reinforcement learning policy and reward structure
    """
    def __init__(self, env):
        self.env = env
        self.current_task = None
        self.task_models = {}
        self.task_complete = False
        
        # Define task-specific observation and action spaces
        self.task_spaces = {
            'gather_wood': {
                'observation_space': gym.spaces.Box(low=0, high=1, shape=(10,), dtype=np.float32),
                'action_space': gym.spaces.Discrete(5)  # Simplified action space for this task
            },
            'mine_stone': {
                'observation_space': gym.spaces.Box(low=0, high=1, shape=(10,), dtype=np.float32),
                'action_space': gym.spaces.Discrete(5)
            },
            'mine_iron': {
                'observation_space': gym.spaces.Box(low=0, high=1, shape=(12,), dtype=np.float32),
                'action_space': gym.spaces.Discrete(5)
            },
            'gather_food': {
                'observation_space': gym.spaces.Box(low=0, high=1, shape=(15,), dtype=np.float32),
                'action_space': gym.spaces.Discrete(7)
            },
            'combat': {
                'observation_space': gym.spaces.Box(low=0, high=1, shape=(20,), dtype=np.float32),
                'action_space': gym.spaces.Discrete(8)
            }
        }
    
    def initialize_models(self):
        """Initialize reinforcement learning models for each task"""
        for task_name in self.task_spaces.keys():
            # Create a custom environment wrapper for this task
            task_env = TaskEnvironment(
                self.env, 
                self.task_spaces[task_name]['observation_space'],
                self.task_spaces[task_name]['action_space'],
                task_name
            )
            
            # Create a vectorized environment
            vec_env = DummyVecEnv([lambda task_name=task_name: TaskEnvironment(
                self.env,
                self.task_spaces[task_name]['observation_space'],
                self.task_spaces[task_name]['action_space'],
                task_name
            )])
            
            # Initialize the PPO model for this task
            model = PPO("MlpPolicy", vec_env, verbose=1)
            
            self.task_models[task_name] = {
                'model': model,
                'env': task_env
            }
            
            logger.info(f"Initialized model for task: {task_name}")
    
    def train_task(self, task_name, total_timesteps=10000):
        """Train the model for a specific task"""
        if task_name not in self.task_models:
            logger.error(f"Task {task_name} not found")
            return False
        
        logger.info(f"Training model for task: {task_name}")
        
        # Train the model
        self.task_models[task_name]['model'].learn(total_timesteps=total_timesteps)
        
        # Save the trained model
        self.task_models[task_name]['model'].save(f"minecraft_rl_bot_{task_name}")
        
        logger.info(f"Model training completed for task: {task_name}")
        return True
    
    def load_task_model(self, task_name, path=None):
        """Load a pre-trained model for a specific task"""
        if task_name not in self.task_models:
            logger.error(f"Task {task_name} not found")
            return False
        
        if path is None:
            path = f"minecraft_rl_bot_{task_name}"
        
        try:
            # Create a custom environment wrapper for this task
            task_env = TaskEnvironment(
                self.env, 
                self.task_spaces[task_name]['observation_space'],
                self.task_spaces[task_name]['action_space'],
                task_name
            )
            
            # Create a vectorized environment
            vec_env = DummyVecEnv([lambda: task_env])
            
            # Load the model
            model = PPO.load(path, env=vec_env)
            
            self.task_models[task_name] = {
                'model': model,
                'env': task_env
            }
            
            logger.info(f"Model loaded for task: {task_name}")
            return True
        except Exception as e:
            logger.error(f"Error loading model for task {task_name}: {e}")
            return False
    
    def set_current_task(self, task_name):
        """Set the current task for the bot"""
        if task_name not in self.task_models:
            logger.error(f"Task {task_name} not found")
            return False
        
        self.current_task = task_name
        self.task_complete = False
        
        logger.info(f"Current task set to: {task_name}")
        return True
    
    def execute_current_task(self, max_steps=1000):
        """Execute the current task using the trained model"""
        if self.current_task is None:
            logger.error("No current task set")
            return False
        
        if self.current_task not in self.task_models:
            logger.error(f"Task {self.current_task} not found")
            return False
        
        logger.info(f"Executing task: {self.current_task}")
        
        task_env = self.task_models[self.current_task]['env']
        model = self.task_models[self.current_task]['model']
        
        # Reset the task environment
        obs = task_env.reset()
        
        for step in range(max_steps):
            # Get the action from the model
            action, _ = model.predict(obs, deterministic=True)
            
            # Execute the action
            obs, reward, done, info = task_env.step(action)
            
            # Check if the task is complete
            if done:
                self.task_complete = True
                logger.info(f"Task {self.current_task} completed in {step+1} steps")
                return True
        
        logger.info(f"Task {self.current_task} not completed after {max_steps} steps")
        return False
    
    def is_task_complete(self):
        """Check if the current task is complete"""
        return self.task_complete
    
    def prioritize_tasks(self):
        """Determine which task to execute next based on current state"""
        # This is a simple heuristic-based task prioritization
        # In a more advanced implementation, you could use another RL model
        # to learn the optimal task prioritization
        
        # Check inventory and state
        inventory = self.env.inventory
        health = self.env.health
        hunger = self.env.hunger
        time_of_day = self.env.time_of_day
        
        # If health is low and we have food, eat
        if health < 10 and inventory.get("cooked_beef", 0) > 0:
            return "eat_food"
        
        # If hunger is low, prioritize gathering food
        if hunger < 10:
            return "gather_food"
        
        # If it's night time, prioritize combat/defense
        if time_of_day > 12000 and time_of_day < 24000:
            return "combat"
        
        # If we don't have wooden tools, prioritize gathering wood
        if not any(item in inventory and inventory[item] > 0 
                   for item in ["wooden_pickaxe", "wooden_axe", "wooden_sword"]):
            return "gather_wood"
        
        # If we have wooden tools but no stone tools, prioritize mining stone
        if (inventory.get("wooden_pickaxe", 0) > 0 and 
            not any(item in inventory and inventory[item] > 0 
                   for item in ["stone_pickaxe", "stone_axe", "stone_sword"])):
            return "mine_stone"
        
        # If we have stone tools but no iron tools, prioritize mining iron
        if (inventory.get("stone_pickaxe", 0) > 0 and 
            not any(item in inventory and inventory[item] > 0 
                   for item in ["iron_pickaxe", "iron_axe", "iron_sword"])):
            return "mine_iron"
        
        # Default to gathering wood as a fallback
        return "gather_wood"


class TaskEnvironment(gym.Env):
    """
    A wrapper environment for task-specific reinforcement learning
    """
    def __init__(self, base_env, observation_space, action_space, task_name):
        self.base_env = base_env
        self.observation_space = observation_space
        self.action_space = action_space
        self.task_name = task_name
        
        # Task-specific variables
        self.task_steps = 0
        self.task_max_steps = 1000
        self.task_reward = 0
        self.task_goal_achieved = False
        
        # Task-specific goals
        self.task_goals = {
            'gather_wood': {'wooden_log': 10},
            'mine_stone': {'cobblestone': 20},
            'mine_iron': {'iron_ore': 10},
            'gather_food': {'cooked_beef': 5},
            'combat': {'successful_kills': 5}
        }
        
        # Additional task-specific state
        self.task_state = {
            'gather_wood': {'trees_found': 0, 'distance_to_nearest_tree': 0},
            'mine_stone': {'stone_found': 0, 'distance_to_nearest_stone': 0},
            'mine_iron': {'iron_found': 0, 'distance_to_nearest_iron': 0},
            'gather_food': {'animals_found': 0, 'distance_to_nearest_animal': 0},
            'combat': {'mobs_nearby': 0, 'distance_to_nearest_mob': 0, 'weapon_equipped': False}
        }
        
    def reset(self):
        """Reset the task environment"""
        # Reset the base environment
        self.base_env.reset()
        
        # Reset task-specific variables
        self.task_steps = 0
        self.task_reward = 0
        self.task_goal_achieved = False
        
        # Initialize task-specific state
        self._update_task_state()
        
        return self._get_task_observation()
    
    def step(self, action):
        """Execute a task-specific action"""
        # Map the task-specific action to a base environment action
        base_action = self._map_action(action)
        
        # Execute the action in the base environment
        _, base_reward, base_done, info = self.base_env.step(base_action)
        
        # Update task-specific state
        self._update_task_state()
        
        # Calculate task-specific reward
        reward = self._calculate_reward(base_reward, action)
        self.task_reward += reward
        
        # Increment step counter
        self.task_steps += 1
        
        # Check if the task is complete
        done = self._is_task_complete() or base_done or self.task_steps >= self.task_max_steps
        
        # Get task-specific observation
        observation = self._get_task_observation()
        
        # Add task-specific info
        info.update({
            'task_reward': self.task_reward,
            'task_steps': self.task_steps,
            'task_goal_achieved': self.task_goal_achieved
        })
        
        return observation, reward, done, info
    
    def _update_task_state(self):
        """Update task-specific state based on the base environment"""
        if self.task_name == 'gather_wood':
            # Find the nearest tree
            nearest_tree = self.base_env.find_nearest_resource('oak_log')
            if nearest_tree:
                x, y, z = self.base_env.position
                tree_x, tree_y, tree_z = nearest_tree
                distance = ((tree_x - x)**2 + (tree_y - y)**2 + (tree_z - z)**2)**0.5
                
                self.task_state['gather_wood']['trees_found'] = 1
                self.task_state['gather_wood']['distance_to_nearest_tree'] = distance
            else:
                self.task_state['gather_wood']['trees_found'] = 0
                self.task_state['gather_wood']['distance_to_nearest_tree'] = 100  # Large default value
        
        elif self.task_name == 'mine_stone':
            # Find the nearest stone
            nearest_stone = self.base_env.find_nearest_resource('stone')
            if nearest_stone:
                x, y, z = self.base_env.position
                stone_x, stone_y, stone_z = nearest_stone
                distance = ((stone_x - x)**2 + (stone_y - y)**2 + (stone_z - z)**2)**0.5
                
                self.task_state['mine_stone']['stone_found'] = 1
                self.task_state['mine_stone']['distance_to_nearest_stone'] = distance
            else:
                self.task_state['mine_stone']['stone_found'] = 0
                self.task_state['mine_stone']['distance_to_nearest_stone'] = 100
        
        # Update task states for other tasks similarly...
        
    def _get_task_observation(self):
        """Get a task-specific observation vector"""
        # Get basic observations from the base environment
        base_obs = self.base_env._get_observation()
        
        # Create a task-specific observation vector
        if self.task_name == 'gather_wood':
            obs = np.zeros(10, dtype=np.float32)
            
            # Include base observations
            obs[0] = base_obs[0]  # health
            obs[1] = base_obs[1]  # hunger
            
            # Include inventory information
            obs[2] = min(self.base_env.inventory.get("wooden_log", 0) / 10.0, 1.0)
            obs[3] = 1.0 if self.base_env.inventory.get("wooden_axe", 0) > 0 else 0.0
            
            # Include task-specific state
            obs[4] = self.task_state['gather_wood']['trees_found']
            obs[5] = min(self.task_state['gather_wood']['distance_to_nearest_tree'] / 100.0, 1.0)
            
            # Progress towards goal
            goal_amount = self.task_goals['gather_wood']['wooden_log']
            current_amount = self.base_env.inventory.get("wooden_log", 0)
            obs[6] = min(current_amount / goal_amount, 1.0)
            
            # The remaining elements could be used for nearby block information
        
        elif self.task_name == 'mine_stone':
            obs = np.zeros(10, dtype=np.float32)
            
            # Similar to above, fill the observation vector with relevant information
            # for the stone mining task
            
            # Include base observations
            obs[0] = base_obs[0]  # health
            obs[1] = base_obs[1]  # hunger
            
            # Include inventory information
            obs[2] = min(self.base_env.inventory.get("cobblestone", 0) / 20.0, 1.0)
            obs[3] = 1.0 if self.base_env.inventory.get("wooden_pickaxe", 0) > 0 else 0.0
            
            # Include task-specific state
            obs[4] = self.task_state['mine_stone']['stone_found']
            obs[5] = min(self.task_state['mine_stone']['distance_to_nearest_stone'] / 100.0, 1.0)
            
            # Progress towards goal
            goal_amount = self.task_goals['mine_stone']['cobblestone']
            current_amount = self.base_env.inventory.get("cobblestone", 0)
            obs[6] = min(current_amount / goal_amount, 1.0)
        
        # Similar patterns for other tasks...
        
        # If the task isn't recognized, return a default observation
        else:
            obs = np.zeros(self.observation_space.shape[0], dtype=np.float32)
        
        return obs
    
    def _map_action(self, action):
        """Map a task-specific action to a base environment action"""
        if self.task_name == 'gather_wood':
            # Task-specific actions:
            # 0: Find nearest tree
            # 1: Move towards nearest tree
            # 2: Mine wood
            # 3: Craft axe
            # 4: Return to base
            
            if action == 0:  # Find nearest tree
                nearest_tree = self.base_env.find_nearest_resource('oak_log')
                if nearest_tree:
                    self.task_state['gather_wood']['trees_found'] = 1
                    self.task_state['gather_wood']['distance_to_nearest_tree'] = \
                        ((nearest_tree[0] - self.base_env.position[0])**2 + 
                         (nearest_tree[1] - self.base_env.position[1])**2 + 
                         (nearest_tree[2] - self.base_env.position[2])**2)**0.5
                return 0  # No-op in the base environment
            
            elif action == 1:  # Move towards nearest tree
                if self.task_state['gather_wood']['trees_found'] > 0:
                    nearest_tree = self.base_env.find_nearest_resource('oak_log')
                    if nearest_tree:
                        # In a real implementation, you would need to break this down into
                        # multiple steps to navigate to the tree
                        self.base_env.move_to_position(nearest_tree)
                
                # Default to moving forward in the base environment
                return 0  # Move forward
            
            elif action == 2:  # Mine wood
                if self.task_state['gather_wood']['trees_found'] > 0 and \
                   self.task_state['gather_wood']['distance_to_nearest_tree'] < 3:
                    nearest_tree = self.base_env.find_nearest_resource('oak_log')
                    if nearest_tree:
                        self.base_env.mine_block(nearest_tree)
                
                return 7  # Mine block in the base environment
            
            elif action == 3:  # Craft axe
                if self.base_env.inventory.get("wooden_log", 0) >= 3 and \
                   self.base_env.inventory.get("stick", 0) >= 2:
                    self.base_env.craft_item("wooden_axe")
                
                return 9  # Craft item in the base environment
            
            elif action == 4:  # Return to base
                # In a real implementation, you would need to navigate back to a base location
                return 1  # Move backward in the base environment
        
        # Similar mappings for other tasks...
        
        # Default to the same action in the base environment
        return action if action < self.base_env.action_space.n else 0
    
    def _calculate_reward(self, base_reward, action):
        """Calculate a task-specific reward"""
        reward = base_reward  # Start with the base reward
        
        if self.task_name == 'gather_wood':
            # Check inventory before and after the action
            wooden_logs_before = self.base_env.inventory.get("wooden_log", 0) - (1 if action == 2 else 0)
            wooden_logs_after = self.base_env.inventory.get("wooden_log", 0)
            
            # Reward for collecting wood
            if wooden_logs_after > wooden_logs_before:
                reward += 1.0
            
            # Reward for crafting an axe
            if action == 3 and self.base_env.inventory.get("wooden_axe", 0) > 0:
                reward += 5.0
            
            # Reward for getting closer to a tree
            distance_before = self.task_state['gather_wood']['distance_to_nearest_tree']
            nearest_tree = self.base_env.find_nearest_resource('oak_log')
            if nearest_tree:
                x, y, z = self.base_env.position
                tree_x, tree_y, tree_z = nearest_tree
                distance_after = ((tree_x - x)**2 + (tree_y - y)**2 + (tree_z - z)**2)**0.5
                
                if distance_after < distance_before:
                    reward += 0.1
                elif distance_after > distance_before:
                    reward -= 0.1
            
            # Check progress towards goal
            goal_amount = self.task_goals['gather_wood']['wooden_log']
            current_amount = self.base_env.inventory.get("wooden_log", 0)
            
            if current_amount >= goal_amount:
                reward += 10.0
                self.task_goal_achieved = True
        
        # Similar reward calculations for other tasks...
        
        return reward
    
    def _is_task_complete(self):
        """Check if the task is complete"""
        if self.task_name == 'gather_wood':
            goal_amount = self.task_goals['gather_wood']['wooden_log']
            current_amount = self.base_env.inventory.get("wooden_log", 0)
            return current_amount >= goal_amount
        
        elif self.task_name == 'mine_stone':
            goal_amount = self.task_goals['mine_stone']['cobblestone']
            current_amount = self.base_env.inventory.get("cobblestone", 0)
            return current_amount >= goal_amount
        
        # Similar checks for other tasks...
        
        return False


def run_hierarchical_agent(task_manager, episodes=10, steps_per_episode=1000):
    """
    Run the hierarchical agent
    """
    for episode in range(episodes):
        logger.info(f"Running episode {episode+1}/{episodes}")
        
        # Reset the environment
        task_manager.env.reset()
        
        for step in range(steps_per_episode):
            # Determine which task to execute next
            next_task = task_manager.prioritize_tasks()
            
            # Set the current task
            task_manager.set_current_task(next_task)
            
            # Execute the task
            task_completed = task_manager.execute_current_task(max_steps=100)
            
            # If the task is complete, re-prioritize
            if task_completed:
                logger.info(f"Task {next_task} completed. Re-prioritizing...")
            
            # Check if we should end the episode
            if task_manager.env.health <= 0:
                logger.info("Agent died. Ending episode.")
                break
        
        logger.info(f"Episode {episode+1} completed after {step+1} steps")
    
    logger.info("Hierarchical agent run completed")