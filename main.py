# main.py
import os
import subprocess
import time
import argparse
import logging
import signal
import sys
from train_rl_agent import train_rl_agent, evaluate_trained_agent, visualize_agent_behavior

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("minecraft_rl.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MinecraftRL")

# Global variable to track running processes
nodejs_process = None

def signal_handler(sig, frame):
    """Handle Ctrl+C by shutting down all processes gracefully"""
    logger.info("Received shutdown signal, cleaning up...")
    if nodejs_process:
        logger.info("Terminating Node.js bot server...")
        nodejs_process.terminate()
    logger.info("Shutdown complete")
    sys.exit(0)

def start_bot_server():
    """Start the Node.js Minecraft bot server"""
    global nodejs_process
    
    logger.info("Starting Node.js Minecraft bot server...")
    
    # Use shell=False for better process management
    nodejs_process = subprocess.Popen(
        ["node", "minecraft_bot.js"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
        encoding='utf-8',
    )
    
    # Start a thread to log NodeJS output
    def log_output():
        for line in nodejs_process.stdout:
            logger.info(f"[NodeJS] {line.strip()}")
        for line in nodejs_process.stderr:
            logger.error(f"[NodeJS Error] {line.strip()}")
    
    from threading import Thread
    log_thread = Thread(target=log_output, daemon=True)
    log_thread.start()
    
    # Wait for server to start up
    logger.info("Waiting for bot server to initialize...")
    time.sleep(5)
    
    return nodejs_process

def setup_recipes_directory():
    """Set up the recipes directory if it doesn't exist"""
    recipes_dir = os.path.join(os.getcwd(), 'recipes')
    if not os.path.exists(recipes_dir):
        logger.info("Creating recipes directory...")
        os.makedirs(recipes_dir)
        
        # Create sample recipe files
        create_sample_recipes(recipes_dir)
        
    return recipes_dir

def create_sample_recipes(recipes_dir):
    """Create sample recipe files for basic items"""
    recipes = {
        "crafting_table.json": """{
  "type": "minecraft:crafting_shaped",
  "pattern": [
    "##",
    "##"
  ],
  "key": {
    "#": {
      "item": "minecraft:oak_planks"
    }
  },
  "result": {
    "item": "minecraft:crafting_table",
    "count": 1
  }
}""",
        "wooden_pickaxe.json": """{
  "type": "minecraft:crafting_shaped",
  "pattern": [
    "###",
    " | ",
    " | "
  ],
  "key": {
    "#": {
      "item": "minecraft:oak_planks"
    },
    "|": {
      "item": "minecraft:stick"
    }
  },
  "result": {
    "item": "minecraft:wooden_pickaxe",
    "count": 1
  }
}""",
        "stick.json": """{
  "type": "minecraft:crafting_shaped",
  "pattern": [
    "#",
    "#"
  ],
  "key": {
    "#": {
      "item": "minecraft:oak_planks"
    }
  },
  "result": {
    "item": "minecraft:stick",
    "count": 4
  }
}""",
        "stone_pickaxe.json": """{
  "type": "minecraft:crafting_shaped",
  "pattern": [
    "###",
    " | ",
    " | "
  ],
  "key": {
    "#": {
      "item": "minecraft:cobblestone"
    },
    "|": {
      "item": "minecraft:stick"
    }
  },
  "result": {
    "item": "minecraft:stone_pickaxe",
    "count": 1
  }
}""",
        "oak_planks.json": """{
  "type": "minecraft:crafting_shapeless",
  "ingredients": [
    {
      "item": "minecraft:oak_log"
    }
  ],
  "result": {
    "item": "minecraft:oak_planks",
    "count": 4
  }
}""",
        "furnace.json": """{
  "type": "minecraft:crafting_shaped",
  "pattern": [
    "###",
    "# #",
    "###"
  ],
  "key": {
    "#": {
      "item": "minecraft:cobblestone"
    }
  },
  "result": {
    "item": "minecraft:furnace",
    "count": 1
  }
}"""
    }
    
    for filename, content in recipes.items():
        filepath = os.path.join(recipes_dir, filename)
        with open(filepath, 'w') as f:
            f.write(content)
            
    logger.info(f"Created {len(recipes)} sample recipe files")

def create_logs_directory():
    """Create logs directory if it doesn't exist"""
    logs_dir = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(logs_dir):
        logger.info("Creating logs directory...")
        os.makedirs(logs_dir)
    return logs_dir

def main():
    parser = argparse.ArgumentParser(description="Minecraft RL Bot Training System")
    parser.add_argument("--mode", type=str, choices=["train", "evaluate", "visualize"], default="train",
                        help="Mode to run in: train, evaluate, or visualize")
    parser.add_argument("--algorithm", type=str, choices=["PPO", "A2C", "DQN"], default="PPO",
                        help="RL algorithm to use for training")
    parser.add_argument("--timesteps", type=int, default=500000,
                        help="Number of timesteps to train for")
    parser.add_argument("--no-curriculum", action="store_true",
                        help="Disable curriculum learning")
    parser.add_argument("--model-path", type=str,
                        help="Path to trained model for evaluation or visualization")
    parser.add_argument("--episodes", type=int, default=10,
                        help="Number of episodes for evaluation")
    parser.add_argument("--visualization-time", type=int, default=60,
                        help="Duration for visualization in seconds")
    parser.add_argument("--skip-node", action="store_true",
                        help="Skip starting the Node.js server (if it's already running)")
    parser.add_argument("--server-host", type=str, default="localhost",
                        help="Minecraft server host")
    parser.add_argument("--server-port", type=int, default=25565,
                        help="Minecraft server port")
    parser.add_argument("--bot-username", type=str, default="RLBot",
                        help="Username for the Minecraft bot")
    
    args = parser.parse_args()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set up directories
    setup_recipes_directory()
    create_logs_directory()
    
    try:
        # Start Node.js bot server if needed
        if not args.skip_node:
            nodejs_proc = start_bot_server()
        
        # Run the specified mode
        if args.mode == "train":
            logger.info(f"Starting training with {args.algorithm} for {args.timesteps} timesteps")
            model, log_dir = train_rl_agent(
                algorithm=args.algorithm,
                total_timesteps=args.timesteps,
                use_curriculum=not args.no_curriculum
            )
            logger.info(f"Training completed. Model saved to {log_dir}")
            
        elif args.mode == "evaluate":
            if not args.model_path:
                logger.error("Error: --model-path is required for evaluation mode")
                return 1
                
            logger.info(f"Evaluating model from {args.model_path} for {args.episodes} episodes")
            results = evaluate_trained_agent(args.model_path, args.episodes)
            
            logger.info(f"Evaluation results:")
            logger.info(f"Average reward: {results['avg_reward']:.2f}")
            logger.info(f"Average episode length: {results['avg_length']:.1f} steps")
            logger.info("Inventory statistics:")
            for item, stats in results['inventory_stats'].items():
                avg = sum(stats) / len(stats)
                max_val = max(stats)
                logger.info(f"  {item}: avg={avg:.1f}, max={max_val}")
            
        elif args.mode == "visualize":
            if not args.model_path:
                logger.error("Error: --model-path is required for visualization mode")
                return 1
                
            logger.info(f"Visualizing agent behavior from {args.model_path} for {args.visualization_time} seconds")
            visualize_agent_behavior(args.model_path, args.visualization_time)
        
        logger.info("Process completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error in main process: {e}", exc_info=True)
        return 1
    finally:
        # Clean up resources
        if nodejs_process and not args.skip_node:
            logger.info("Terminating Node.js bot server...")
            nodejs_process.terminate()
            nodejs_process.wait()
            logger.info("Node.js bot server terminated")

if __name__ == "__main__":
    sys.exit(main())