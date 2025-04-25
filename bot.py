from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from environment import MinecraftEnv

class MinecraftBot:
    def __init__(self):
        self.env = None
        self.model = None

    def setup_environment(self):
        self.env = MinecraftEnv()
        self.env = DummyVecEnv([lambda: self.env])

    def train(self, total_timesteps=10000):
        self.model = PPO("MlpPolicy", self.env, verbose=1)
        self.model.learn(total_timesteps=total_timesteps)
        print("Training completed!")

    def save_model(self, path="minecraft_bot_model"):
        if self.model:
            self.model.save(path)
            print(f"Model saved to {path}")

    def load_model(self, path="minecraft_bot_model"):
        self.model = PPO.load(path)
        print(f"Model loaded from {path}")

    def run_episode(self, render=True):
        if not self.model:
            raise ValueError("No model loaded")

        obs = self.env.reset()
        done = False
        total_reward = 0
        step = 0

        while not done:
            action, _ = self.model.predict(obs)
            obs, reward, done, info = self.env.step(action)
            total_reward += reward[0]
            step += 1

            if render:
                print(f"Step {step}: Reward: {reward[0]}")

            if done.any():
                done = True

        print(f"Episode finished with total reward: {total_reward}") 