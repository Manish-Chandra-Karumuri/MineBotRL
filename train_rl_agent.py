from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import CheckpointCallback
from environment import MinecraftEnv  # Updated to match gymnasium API

import os
from datetime import datetime

def train_rl_agent():
    print("📦 Initializing Minecraft environment for RL training...")

    try:
        # Setup logging and checkpointing
        run_name = f"minecraft_rl_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        log_dir = os.path.join("logs", "tensorboard", run_name)
        os.makedirs(log_dir, exist_ok=True)

        checkpoint_callback = CheckpointCallback(
            save_freq=5000,
            save_path=os.path.join(log_dir, "checkpoints"),
            name_prefix="ppo_minecraft"
        )

        # Wrap env properly
        env = DummyVecEnv([lambda: Monitor(MinecraftEnv(), log_dir)])

        print("✅ Environment wrapped and ready.")
        print("🚀 Starting training...")

        model = PPO("MlpPolicy", env, verbose=1, tensorboard_log=log_dir)

        model.learn(
            total_timesteps=100_000,
            callback=checkpoint_callback,
            tb_log_name=run_name
        )

        print("🎉 Training completed successfully.")
        model.save("ppo_minecraft_model")
        print("💾 Model saved to 'ppo_minecraft_model.zip'")

    except Exception as e:
        print(f"❌ Training failed: {e}")
