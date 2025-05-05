import argparse
import logging
import os
import sys
import time
import numpy as np
import random
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

# Import custom modules
from minecraft_env_js import MinecraftJSEnv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("minecraft_bot.log"),
                              logging.StreamHandler()])
logger = logging.getLogger("MinecraftBot")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Minecraft Reinforcement Learning Bot (JavaScript Bridge)')
    
    parser.add_argument('--username', type=str, default='RLBot',
                        help='Minecraft bot username (default: RLBot)')
    
    parser.add_argument('--js-server', type=str, default='http://localhost:3000',
                        help='JavaScript server URL (default: http://localhost:3000)')
    
    parser.add_argument('--train', action='store_true',
                        help='Train the reinforcement learning model')
    
    parser.add_argument('--load', action='store_true',
                        help='Load a pre-trained reinforcement learning model')
    
    parser.add_argument('--model-path', type=str, default='minecraft_rl_model',
                        help='Path to save/load the model (default: minecraft_rl_model)')
    
    parser.add_argument('--episodes', type=int, default=10,
                        help='Number of episodes to run (default: 10)')
    
    parser.add_argument('--steps', type=int, default=1000,
                        help='Maximum steps per episode (default: 1000)')
    
    parser.add_argument('--test', action='store_true',
                        help='Run a simple connection test only')
                        
    parser.add_argument('--mining-focus', action='store_true',
                        help='Focus training on mining behaviors')
    
    parser.add_argument('--no-start-server', action='store_true',
                        help='Don\'t start the JavaScript server (assume it\'s already running)')
    
    return parser.parse_args()

def test_connection(js_server, username):
    """Test the connection to the Minecraft server"""
    logger.info(f"Testing connection to Minecraft via JavaScript bridge at {js_server}")
    
    try:
        # Create a Minecraft environment
        env = MinecraftJSEnv(js_server_url=js_server, minecraft_username=username, start_js_server=True)
        
        # Reset the environment (this will attempt to connect)
        observation = env.reset()
        
        # Check if we got a valid observation
        if observation is not None and isinstance(observation, np.ndarray):
            logger.info("Connection test successful!")
            
            # Get current state
            status = env._get_status()
            if status and status.get('connected', False):
                logger.info(f"Bot position: {status.get('position')}")
                logger.info(f"Bot health: {status.get('health')}")
                logger.info(f"Bot inventory: {status.get('inventory')}")
                
                # Try a few basic actions
                logger.info("Testing basic actions...")
                
                # Set time to day
                env.step(9)  # Action 9: set time to day
                time.sleep(1)
                
                # Try to mine a block
                env.step(6)  # Action 6: mine block
                time.sleep(1)
                
                # Try to move around
                env.step(0)  # Action 0: move forward
                time.sleep(1)
                
                logger.info("Basic action test completed")
            
            # Clean up
            env.close()
            return True
        else:
            logger.error("Failed to get a valid observation")
            env.close()
            return False
            
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False

def create_mining_callback(env):
    """Create a callback to encourage mining behavior during training"""
    
    class MiningCallback:
        def __init__(self, env):
            self.env = env
            self.blocks_mined = 0
            self.mining_attempts = 0
            self.last_inventory = {}
            self.no_mining_counter = 0
            self.periodic_actions = []
            self.steps_since_last_action = 0
        
        def __call__(self, locals, globals):
            # Track steps
            self.steps_since_last_action += 1
            
            # Every 50 steps, perform a special action to help the bot
            if self.steps_since_last_action >= 50:
                self.steps_since_last_action = 0
                
                # Add some helpful actions to the queue
                if not self.periodic_actions:
                    self.periodic_actions = [
                        9,  # Set time to day
                        0,  # Move forward
                        4,  # Jump
                        6,  # Mine block
                        6   # Mine block again
                    ]
                
                # If we have actions in the queue, use the next one
                if self.periodic_actions:
                    action = self.periodic_actions.pop(0)
                    obs, reward, done, info = self.env.step(action)
                    logger.info(f"Performed periodic action: {action}, Reward: {reward}")
                    
                    # Check if this helps the mining
                    if action == 6:  # Mine action
                        self.mining_attempts += 1
                        new_inventory = info.get('inventory', {})
                        
                        # Check if any inventory items increased (successful mining)
                        for item, count in new_inventory.items():
                            if item in self.last_inventory and count > self.last_inventory[item]:
                                self.blocks_mined += 1
                                logger.info(f"Bot mined a block! Total mined: {self.blocks_mined}")
                                break
                        
                        self.last_inventory = new_inventory
                
                # Check if we're not making progress in mining
                if self.mining_attempts >= 10 and self.blocks_mined == 0:
                    self.no_mining_counter += 1
                    logger.warning(f"Bot hasn't mined any blocks after {self.mining_attempts} attempts")
                    
                    # Every 5 failed attempts, try teleporting to find resources
                    if self.no_mining_counter % 5 == 0:
                        logger.info("Teleporting bot to find resources...")
                        x = random.randint(-50, 50)
                        z = random.randint(-50, 50)
                        self.env.run_command(f"tp @p {x} 70 {z}")
                        time.sleep(1)  # Wait for teleport
                        
                        # Reset counters
                        self.mining_attempts = 0
                        self.blocks_mined = 0
                        self.last_inventory = self.env._get_status().get('inventory', {})
            
            return True
    
    return MiningCallback(env)

def train_model(env, total_timesteps=100000, model_path='minecraft_rl_model', mining_focus=False):
    """Train a reinforcement learning model"""
    logger.info(f"Training model with {total_timesteps} timesteps")
    
    # Create a vectorized environment
    vec_env = DummyVecEnv([lambda: env])
    
    # Initialize the agent with parameters optimized for mining if requested
    if mining_focus:
        logger.info("Using mining-optimized parameters")
        model = PPO(
            "MlpPolicy", 
            vec_env, 
            verbose=1,
            learning_rate=0.0001,  # Lower learning rate for more stability
            n_steps=512,           # More steps per update
            batch_size=64,         # Smaller batch size
            n_epochs=10,           # More epochs per update
            gamma=0.99,            # Discount factor
            gae_lambda=0.95,       # GAE parameter
            clip_range=0.2,        # PPO clip parameter
            tensorboard_log="./minecraft_tensorboard/",  # Add tensorboard logging
            policy_kwargs=dict(
                net_arch=[dict(pi=[128, 128], vf=[128, 128])]  # Larger network
            )
        )
        
        # Create a mining-focused callback
        callback = create_mining_callback(env)
    else:
        model = PPO(
            "MlpPolicy", 
            vec_env, 
            verbose=1,
            tensorboard_log="./minecraft_tensorboard/"
        )
        callback = None
    
    try:
        # Train the agent with periodic saving
        checkpoint_interval = max(1, total_timesteps // 5)  # Save 5 checkpoints
        
        for i in range(5):
            current_step = i * checkpoint_interval
            remaining_steps = min(checkpoint_interval, total_timesteps - current_step)
            
            if remaining_steps <= 0:
                break
                
            logger.info(f"Training iteration {i+1}/5, steps {current_step} to {current_step + remaining_steps}")
            model.learn(total_timesteps=remaining_steps, reset_num_timesteps=False, callback=callback)
            
            # Save intermediate checkpoint
            checkpoint_path = f"{model_path}_checkpoint_{i+1}"
            model.save(checkpoint_path)
            logger.info(f"Saved checkpoint to {checkpoint_path}")
            
            # Small pause between training sessions to let the connection stabilize
            logger.info("Taking a short break to stabilize connection...")
            time.sleep(3)
        
        # Save the final model
        model.save(model_path)
        logger.info(f"Model training completed and saved to {model_path}")
        
        return model
    except Exception as e:
        logger.error(f"Error during training: {e}")
        # Try to save the model even if training was interrupted
        try:
            model.save(f"{model_path}_interrupted")
            logger.info(f"Partially trained model saved to {model_path}_interrupted")
        except:
            pass
        return model

def load_model(env, model_path='minecraft_rl_model'):
    """Load a pre-trained reinforcement learning model"""
    logger.info(f"Loading model from {model_path}")
    
    try:
        # Create a vectorized environment
        vec_env = DummyVecEnv([lambda: env])
        
        # Load the model
        model = PPO.load(model_path, env=vec_env)
        logger.info("Model loaded successfully")
        
        return model
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return None

def run_model(model, env, episodes=10, steps_per_episode=1000, mining_focus=False):
    """Run the trained model"""
    logger.info(f"Running model for {episodes} episodes with {steps_per_episode} steps per episode")
    
    # Set time to day for better visibility
    env.step(9)  # Action 9: set time to day
    
    total_blocks_mined = 0
    
    for episode in range(episodes):
        # Reset the environment
        obs = env.reset()
        done = False
        total_reward = 0
        step = 0
        episode_blocks_mined = 0
        last_inventory = env._get_status().get('inventory', {})
        
        logger.info(f"Starting episode {episode+1}/{episodes}")
        
        # If mining focused, teleport to a random location to find resources
        if mining_focus and episode > 0:
            x = random.randint(-100, 100)
            z = random.randint(-100, 100)
            env.run_command(f"tp @p {x} 70 {z}")
            time.sleep(1)  # Wait for teleport
            obs = env.reset()  # Reset after teleport
        
        while not done and step < steps_per_episode:
            # Every 20 steps, encourage mining directly
            if mining_focus and step % 20 == 0:
                action = 6  # Mine action
                logger.info("Forcing mining action")
            else:
                # Get the action from the model
                action, _states = model.predict(obs, deterministic=True)
            
            # Execute the action
            obs, reward, done, info = env.step(action)
            total_reward += reward
            step += 1
            
            # Check if a block was mined (inventory changed)
            current_inventory = info.get('inventory', {})
            block_mined = False
            
            for item, count in current_inventory.items():
                if item in last_inventory and count > last_inventory[item]:
                    block_mined = True
                    episode_blocks_mined += 1
                    total_blocks_mined += 1
                    logger.info(f"Block mined! Type: {item}, Count: {count}")
                    break
            
            last_inventory = current_inventory.copy()
            
            # Log information periodically
            if step % 10 == 0 or block_mined:
                logger.info(f"Episode {episode+1}, Step {step}: Action={action}, Reward={reward}, Total Reward={total_reward}")
                logger.info(f"Blocks mined this episode: {episode_blocks_mined}")
                logger.info(f"Position: {info['position']}, Inventory: {info['inventory']}")
            
            # Every 50 steps, set time to day for better visibility
            if step % 50 == 0:
                env.step(9)  # Action 9: set time to day
        
        logger.info(f"Episode {episode+1} completed after {step} steps with total reward {total_reward}")
        logger.info(f"Blocks mined this episode: {episode_blocks_mined}")
        
        # Set time to day for next episode
        env.step(9)  # Action 9: set time to day
    
    logger.info(f"Model run completed. Total blocks mined across all episodes: {total_blocks_mined}")

def main():
    """Main function"""
    # Parse command line arguments
    args = parse_args()
    
    # Print banner
    print("=" * 80)
    print("Minecraft Reinforcement Learning Bot (JavaScript Bridge)")
    print("=" * 80)
    
    # Print instructions for the user
    print("\nInstructions:")
    print("1. Make sure Minecraft is running and you're in a world")
    print("2. Ensure cheats are enabled ('Open to LAN' with 'Allow Cheats: ON')")
    print("3. The bot will join with username '" + args.username + "'")
    print("4. Keep Minecraft running in the foreground while the bot operates")
    print("5. Press Ctrl+C in this terminal to stop the bot at any time\n")
    
    # Display mining focus info if enabled
    if args.mining_focus:
        print("Mining focus is enabled - the bot will prioritize mining blocks!")
        print("It will receive higher rewards for mining and will be encouraged to find resources.\n")
    
    # Allow the user to get ready
    input("Press Enter when you're ready to start...")
    
    # Test connection if requested
    if args.test:
        print("Testing connection to Minecraft...")
        success = test_connection(args.js_server, args.username)
        if success:
            print("\n✅ Connection test successful!")
            print("The bot is able to connect to your Minecraft world.")
            print("You can now try training or running a model with --train or --load")
        else:
            print("\n❌ Connection test failed.")
            print("Please check your Minecraft server and connection settings.")
            print("Make sure Minecraft is running and open to LAN with cheats enabled.")
        return 0 if success else 1
    
    # Create the Minecraft environment
    logger.info(f"Creating Minecraft environment with JavaScript bridge at {args.js_server}")
    env = MinecraftJSEnv(
        js_server_url=args.js_server, 
        minecraft_username=args.username,
        start_js_server=not args.no_start_server
    )
    
    # Initialize the model
    model = None
    
    try:
        # Train the model if requested
        if args.train:
            print("\n🔄 Training a new reinforcement learning model...")
            print(f"This will run for approximately {args.episodes} episodes with {args.steps} steps per episode")
            print("The bot will learn from its interactions with the Minecraft world")
            print("You should see the bot moving around and performing actions\n")
            
            # Use smaller timesteps for stability
            timesteps = args.episodes * args.steps
            model = train_model(env, total_timesteps=timesteps, model_path=args.model_path, mining_focus=args.mining_focus)
            
            print("\n✅ Training completed!")
            print(f"The model has been saved to {args.model_path}")
        
        # Load a pre-trained model if requested
        if args.load:
            print("\n📂 Loading pre-trained model...")
            model = load_model(env, model_path=args.model_path)
            if model:
                print(f"✅ Model loaded successfully from {args.model_path}")
            else:
                print(f"❌ Failed to load model from {args.model_path}")
                return 1
        
        # If we have a model, run it
        if model:
            print("\n▶️ Running the reinforcement learning model...")
            print(f"The bot will run for {args.episodes} episodes with up to {args.steps} steps per episode")
            print("Watch the bot as it explores and interacts with the Minecraft world\n")
            
            run_model(model, env, episodes=args.episodes, steps_per_episode=args.steps, mining_focus=args.mining_focus)
            print("\n✅ Model run completed!")
        else:
            logger.error("No model available. Please use --train or --load to get a model.")
            print("\n❌ No model available.")
            print("Please use --train to train a new model or --load to use an existing one.")
            return 1
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation interrupted by user")
        print("Cleaning up and shutting down...")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        # Clean up
        print("\nShutting down the Minecraft bot...")
        env.close()
        
        print("\n✅ Done. The bot has been disconnected from Minecraft.")
        if model:
            print(f"Any trained model has been saved to {args.model_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())