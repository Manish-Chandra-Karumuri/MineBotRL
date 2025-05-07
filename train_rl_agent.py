# train_rl_agent.py
import os
import time
import numpy as np
import gymnasium as gym
from datetime import datetime
from stable_baselines3 import PPO, A2C, DQN
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.logger import configure
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import seaborn as sns
import logging
import glob
import torch
import argparse

# Import our environment
from environment import EnhancedMinecraftEnv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MinecraftTrainer")

from stable_baselines3.common.callbacks import BaseCallback

class CurriculumLearningCallback(BaseCallback):
    """
    Custom callback for curriculum learning. Increases difficulty or adjusts environment parameters
    based on the number of timesteps trained.
    """

    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.curriculum_level = 0

    def _on_training_start(self) -> None:
        if self.verbose:
            print(f"[Curriculum] Training started at level {self.curriculum_level}")

    def _on_rollout_start(self) -> None:
        if self.verbose:
            print(f"[Curriculum] Rollout started at level {self.curriculum_level}")

    def _on_step(self) -> bool:
        # You can customize this logic to update difficulty
        if self.num_timesteps > 300000:
            self.curriculum_level = 3
        elif self.num_timesteps > 200000:
            self.curriculum_level = 2
        elif self.num_timesteps > 100000:
            self.curriculum_level = 1
        else:
            self.curriculum_level = 0

        # Optional: log curriculum level
        if self.verbose:
            print(f"[Curriculum] Current step: {self.num_timesteps}, level: {self.curriculum_level}")

        return True  # Continue training

    def _on_rollout_end(self) -> None:
        if self.verbose:
            print(f"[Curriculum] Rollout ended at level {self.curriculum_level}")

    def _on_training_end(self) -> None:
        if self.verbose:
            print(f"[Curriculum] Training completed at level {self.curriculum_level}")

class MetricLogger:
    """Logger for training metrics with visualization capabilities."""
    
    def __init__(self, log_dir):
        self.log_dir = log_dir
        self.metrics = {
            "episode_rewards": [],
            "episode_lengths": [],
            "inventory_counts": {},
            "craft_counts": {},
            "exploration_distance": []
        }
        self.log_file = os.path.join(log_dir, "training_metrics.csv")
        
        # Create directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize log file with header
        with open(self.log_file, "w") as f:
            f.write("Episode,Reward,Length,Wood,Stone,CraftingTable,Pickaxe,Exploration\n")
    
    def log_episode(self, episode_num, reward, length, inventory, exploration_distance):
        """Log metrics for a completed episode."""
        # Store metrics
        self.metrics["episode_rewards"].append(reward)
        self.metrics["episode_lengths"].append(length)
        self.metrics["exploration_distance"].append(exploration_distance)
        
        # Store inventory counts
        for item, count in inventory.items():
            if item not in self.metrics["inventory_counts"]:
                self.metrics["inventory_counts"][item] = []
            
            # Pad with zeros if needed
            while len(self.metrics["inventory_counts"][item]) < episode_num - 1:
                self.metrics["inventory_counts"][item].append(0)
                
            self.metrics["inventory_counts"][item].append(count)
        
        # Write to log file
        with open(self.log_file, "a") as f:
            wood = inventory.get("oak_log", 0)
            stone = inventory.get("stone", 0) + inventory.get("cobblestone", 0)
            table = inventory.get("crafting_table", 0)
            pickaxe = inventory.get("wooden_pickaxe", 0) + inventory.get("stone_pickaxe", 0)
            
            f.write(f"{episode_num},{reward},{length},{wood},{stone},{table},{pickaxe},{exploration_distance}\n")
    
    def plot_metrics(self, save=True, show=False):
        """Generate plots of the logged metrics."""
        sns.set(style="darkgrid")
        
        # Create a figure with multiple subplots
        fig, axs = plt.subplots(3, 1, figsize=(12, 18))
        
        # Plot 1: Episode Rewards
        axs[0].plot(self.metrics["episode_rewards"], linewidth=2)
        axs[0].set_title("Episode Rewards", fontsize=16)
        axs[0].set_xlabel("Episode", fontsize=14)
        axs[0].set_ylabel("Reward", fontsize=14)
        axs[0].xaxis.set_major_locator(MaxNLocator(integer=True))
        
        # Plot 2: Episode Lengths
        axs[1].plot(self.metrics["episode_lengths"], linewidth=2)
        axs[1].set_title("Episode Lengths", fontsize=16)
        axs[1].set_xlabel("Episode", fontsize=14)
        axs[1].set_ylabel("Steps", fontsize=14)
        axs[1].xaxis.set_major_locator(MaxNLocator(integer=True))
        
        # Plot 3: Key Items Collected
        key_items = ["oak_log", "cobblestone", "wooden_pickaxe", "stone_pickaxe", "crafting_table"]
        for item in key_items:
            if item in self.metrics["inventory_counts"]:
                axs[2].plot(self.metrics["inventory_counts"][item], label=item)
        
        axs[2].set_title("Items Collected", fontsize=16)
        axs[2].set_xlabel("Episode", fontsize=14)
        axs[2].set_ylabel("Count", fontsize=14)
        axs[2].legend(fontsize=12)
        axs[2].xaxis.set_major_locator(MaxNLocator(integer=True))
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.log_dir, "training_metrics.png"))
            logger.info(f"Saved metrics plot to {os.path.join(self.log_dir, 'training_metrics.png')}")
        
        if show:
            plt.show()
        else:
            plt.close()

def train_rl_agent(algorithm="PPO", 
                   total_timesteps=1_000_000, 
                   log_dir=None, 
                   use_curriculum=True,
                   show_progress=True,
                   server_host="localhost",
                   server_port=25565,
                   bot_username="RLBot"):
    """
    Train a reinforcement learning agent in the Minecraft environment.
    
    Args:
        algorithm (str): The RL algorithm to use (PPO, A2C, or DQN)
        total_timesteps (int): Total number of timesteps to train for
        log_dir (str): Directory to save logs and models
        use_curriculum (bool): Whether to use curriculum learning
        show_progress (bool): Whether to show progress bar during training
        server_host (str): Minecraft server host
        server_port (int): Minecraft server port
        bot_username (str): Username for the Minecraft bot
    """
    # Set up logging directory
    if log_dir is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_dir = os.path.join("logs", f"minecraft_rl_{algorithm}_{timestamp}")
    
    # Ensure the directory exists
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(os.path.join(log_dir, "models"), exist_ok=True)
    
    # Configure logger
    logger.info(f"Starting training with {algorithm} for {total_timesteps} timesteps")
    logger.info(f"Logs will be saved to {log_dir}")
    
    try:
        # Create the Minecraft environment with server details
        env = EnhancedMinecraftEnv(server_url=f"http://{server_host}:3000")
        
        # Create the vectorized environment
        env = Monitor(env, os.path.join(log_dir, "monitor"))
        env = DummyVecEnv([lambda: env])
        env = VecMonitor(env, os.path.join(log_dir, "vec_monitor"))
        
        # Create an evaluation environment
        eval_env = EnhancedMinecraftEnv(server_url=f"http://{server_host}:3000")
        eval_env = Monitor(eval_env, os.path.join(log_dir, "eval_monitor"))
        eval_env = DummyVecEnv([lambda: eval_env])
        
        # Initialize metric logger
        metric_logger = MetricLogger(log_dir)
        
        # Set up callbacks
        checkpoint_callback = CheckpointCallback(
            save_freq=10000,
            save_path=os.path.join(log_dir, "models"),
            name_prefix=f"{algorithm}_minecraft",
            save_replay_buffer=True,
            save_vecnormalize=True
        )
        
        eval_callback = EvalCallback(
            eval_env,
            best_model_save_path=os.path.join(log_dir, "best_model"),
            log_path=os.path.join(log_dir, "eval_logs"),
            eval_freq=25000,
            deterministic=True,
            render=False
        )
        
        callbacks = [checkpoint_callback, eval_callback]
        
        # Add curriculum learning if enabled
        if use_curriculum:
            curriculum_callback = CurriculumLearningCallback(eval_env)
            callbacks.append(curriculum_callback)
        
        # Create the model based on the selected algorithm
        if algorithm == "PPO":
            model = PPO(
                "MlpPolicy", 
                env, 
                verbose=1, 
                tensorboard_log=os.path.join(log_dir, "tensorboard"),
                learning_rate=3e-4,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                policy_kwargs=dict(
                    net_arch=[dict(pi=[128, 128], vf=[128, 128])]
                )
            )
        elif algorithm == "A2C":
            model = A2C(
                "MlpPolicy", 
                env, 
                verbose=1, 
                tensorboard_log=os.path.join(log_dir, "tensorboard"),
                learning_rate=7e-4,
                n_steps=5,
                gamma=0.99,
                policy_kwargs=dict(
                    net_arch=[dict(pi=[128, 128], vf=[128, 128])]
                )
            )
        elif algorithm == "DQN":
            model = DQN(
                "MlpPolicy", 
                env, 
                verbose=1, 
                tensorboard_log=os.path.join(log_dir, "tensorboard"),
                learning_rate=1e-4,
                buffer_size=100000,
                learning_starts=1000,
                batch_size=64,
                gamma=0.99,
                exploration_fraction=0.2,
                exploration_final_eps=0.05,
                policy_kwargs=dict(
                    net_arch=[128, 128]
                )
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        # Train the model
        logger.info(f"Training {algorithm} model...")
        model.learn(
            total_timesteps=total_timesteps,
            callback=callbacks,
            tb_log_name=algorithm,
            progress_bar=show_progress
        )
        
        # Save the final model
        final_model_path = os.path.join(log_dir, "final_model")
        model.save(final_model_path)
        logger.info(f"Saved final model to {final_model_path}")
        
        # Plot training metrics
        metric_logger.plot_metrics(save=True, show=False)
        
        return model, log_dir
        
    except Exception as e:
        logger.error(f"Error during training: {e}")
        raise e

def evaluate_trained_agent(model_path, num_episodes=10):
    """
    Evaluate a trained agent on the Minecraft environment.
    
    Args:
        model_path (str): Path to the trained model file
        num_episodes (int): Number of episodes to evaluate
    """
    logger.info(f"Evaluating model from {model_path} for {num_episodes} episodes")
    
    # Load model
    model_filename = os.path.basename(model_path)
    if "PPO" in model_filename:
        model = PPO.load(model_path)
    elif "A2C" in model_filename:
        model = A2C.load(model_path)
    elif "DQN" in model_filename:
        model = DQN.load(model_path)
    else:
        raise ValueError(f"Unknown model type: {model_filename}")
    
    # Create environment
    env = EnhancedMinecraftEnv()
    
    # Run evaluation episodes
    total_reward = 0
    episode_lengths = []
    inventory_stats = {}
    
    for episode in range(num_episodes):
        logger.info(f"Starting evaluation episode {episode + 1}/{num_episodes}")
        obs, _ = env.reset()
        done = False
        truncated = False
        episode_reward = 0
        step_count = 0
        
        while not (done or truncated):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, truncated, info = env.step(action)
            episode_reward += reward
            step_count += 1
            
            if step_count % 100 == 0:
                logger.info(f"Episode {episode + 1}, Step {step_count}, Reward so far: {episode_reward:.2f}")
        
        # Log episode results
        logger.info(f"Episode {episode + 1} finished with reward: {episode_reward:.2f} in {step_count} steps")
        logger.info(f"Inventory at end of episode: {info.get('inventory', {})}")
        
        # Update statistics
        total_reward += episode_reward
        episode_lengths.append(step_count)
        
        # Update inventory statistics
        for item, count in info.get('inventory', {}).items():
            if item not in inventory_stats:
                inventory_stats[item] = []
            inventory_stats[item].append(count)
    
    # Calculate and display summary statistics
    avg_reward = total_reward / num_episodes
    avg_length = sum(episode_lengths) / num_episodes
    
    logger.info(f"\n=== Evaluation Results ===")
    logger.info(f"Average reward: {avg_reward:.2f}")
    logger.info(f"Average episode length: {avg_length:.1f} steps")
    logger.info(f"Inventory statistics:")
    
    for item, counts in inventory_stats.items():
        avg_count = sum(counts) / len(counts)
        max_count = max(counts)
        logger.info(f"  {item}: avg={avg_count:.1f}, max={max_count}")
    
    env.close()
    
    return {
        "avg_reward": avg_reward,
        "avg_length": avg_length,
        "inventory_stats": inventory_stats
    }

def visualize_agent_behavior(model_path, duration=60):
    """
    Visualize the behavior of a trained agent by running it and logging detailed information.
    
    Args:
        model_path (str): Path to the trained model file
        duration (int): Duration in seconds to run the visualization
    """
    logger.info(f"Visualizing agent behavior from model {model_path} for {duration} seconds")
    
    # Load model
    model_filename = os.path.basename(model_path)
    if "PPO" in model_filename:
        model = PPO.load(model_path)
    elif "A2C" in model_filename:
        model = A2C.load(model_path)
    elif "DQN" in model_filename:
        model = DQN.load(model_path)
    else:
        raise ValueError(f"Unknown model type: {model_filename}")
    
    # Create environment
    env = EnhancedMinecraftEnv()
    
    # Run visualization
    obs, _ = env.reset()
    done = False
    truncated = False
    step_count = 0
    start_time = time.time()
    action_counts = {i: 0 for i in range(env.action_space.n)}
    
    while time.time() - start_time < duration and not (done or truncated):
        action, _ = model.predict(obs, deterministic=True)
        action_counts[action] += 1
        
        obs, reward, done, truncated, info = env.step(action)
        step_count += 1
        
        # Log detailed information periodically
        if step_count % 10 == 0:
            # Render current state
            env.render()
            
            # Log action distribution
            total_actions = sum(action_counts.values())
            action_distribution = {
                action_name: count / total_actions * 100
                for action_name, count in zip(
                    ["forward", "backward", "left", "right", "jump", "mine", "place", "craft", "collect", "eat"],
                    action_counts.values()
                )
            }
            
            # Log current position and inventory
            logger.info(f"Step {step_count}, Position: {info.get('position')}")
            logger.info(f"Action distribution (%):")
            for action_name, percentage in action_distribution.items():
                logger.info(f"  {action_name}: {percentage:.1f}%")
            
            # Log current inventory
            logger.info(f"Current inventory:")
            for item, count in info.get('inventory', {}).items():
                logger.info(f"  {item}: {count}")
    
    if done:
        logger.info("Episode finished because the agent died or completed the task")
    elif truncated:
        logger.info("Episode truncated due to reaching max steps")
    else:
        logger.info(f"Visualization completed after {step_count} steps")
    
    env.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a reinforcement learning agent for Minecraft")
    parser.add_argument("--algorithm", type=str, default="PPO", choices=["PPO", "A2C", "DQN"],
                        help="RL algorithm to use")
    parser.add_argument("--timesteps", type=int, default=500000,
                        help="Total timesteps to train for")
    parser.add_argument("--no-curriculum", action="store_true",
                        help="Disable curriculum learning")
    parser.add_argument("--eval", action="store_true",
                        help="Evaluate a trained model instead of training")
    parser.add_argument("--visualize", action="store_true",
                        help="Visualize agent behavior from a trained model")
    parser.add_argument("--model-path", type=str,
                        help="Path to a trained model for evaluation or visualization")
    
    args = parser.parse_args()
    
    if args.eval:
        if not args.model_path:
            parser.error("--eval requires --model-path")
        evaluate_trained_agent(args.model_path)
    elif args.visualize:
        if not args.model_path:
            parser.error("--visualize requires --model-path")
        visualize_agent_behavior(args.model_path)
    else:
        train_rl_agent(
            algorithm=args.algorithm,
            total_timesteps=args.timesteps,
            use_curriculum=not args.no_curriculum
        )