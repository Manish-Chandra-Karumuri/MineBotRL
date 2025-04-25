import numpy as np
import gymnasium as gym
from stable_baselines3.common.vec_env import DummyVecEnv
from controller import MinecraftController

class MinecraftEnv(gym.Env):
    def __init__(self):
        super(MinecraftEnv, self).__init__()
        self.controller = MinecraftController()
        
        self.action_space = gym.spaces.Box(
            low=np.array([-1, -1, 0, -180, -90], dtype=np.float32),
            high=np.array([1, 1, 1, 180, 90], dtype=np.float32),
            dtype=np.float32
        )
        
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(7,),
            dtype=np.float32
        )
        
        self.state = None
        self.reset()

    def reset(self, seed=None):
        super().reset(seed=seed)
        if not self.controller.focus_minecraft():
            raise Exception("Could not find Minecraft window")
        
        self.controller.reset_controls()
        self.state = np.array([0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        return self.state, {}

    def step(self, action):
        try:
            action = action.astype(np.float32)
            move_x, move_z, jump, look_yaw, look_pitch = action
            
            if not self.controller.focus_minecraft():
                raise Exception("Lost focus of Minecraft window")
            
            self.controller.handle_movement(move_x, move_z)
            self.controller.handle_jump(jump)
            self.controller.handle_looking(look_yaw, look_pitch)
            
            self.state = np.array([
                self.state[0] + move_x,
                self.state[1],
                self.state[2] + move_z,
                look_yaw, look_pitch,
                0, 0
            ], dtype=np.float32)
            
            reward = float(-0.1)
            if jump > 0.5:
                reward += float(0.5)
            if abs(move_x) > 0.5 or abs(move_z) > 0.5:
                reward += float(0.1)
            
            print(f"Action: move_x={move_x:.2f}, move_z={move_z:.2f}, jump={jump:.2f}, "
                  f"look_yaw={look_yaw:.1f}, look_pitch={look_pitch:.1f}, Reward: {reward}")
            
            return self.state, reward, False, False, {}
        except Exception as e:
            print(f"Error in step: {e}")
            raise 