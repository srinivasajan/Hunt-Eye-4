# Dev 3 - Gymnasium Environment
# AI agent ka "game" - isme drone seekhega

import gymnasium as gym
import numpy as np

class HuntEyeEnv(gym.Env):
    def __init__(self):
        super().__init__()
        
        # AI kya DEKHEGA - 8 numbers
        self.observation_space = gym.spaces.Box(
            low=-1, high=1, shape=(8,), dtype=np.float32
        )
        
        # AI kya KAREGA - 4 numbers
        self.action_space = gym.spaces.Box(
            low=-1, high=1, shape=(4,), dtype=np.float32
        )
        
        # Starting state
        self.target_x = 0.5
        self.target_y = 0.5
        self.drone_vx = 0.0
        self.drone_vy = 0.0
        self.drone_vz = 0.0
        self.altitude = 15.0
        self.target_lost = 0.0
        self.steps = 0
    
    def reset(self, seed=None):
        # Har episode shuru mein reset
        self.target_x = np.random.uniform(-0.5, 0.5)
        self.target_y = np.random.uniform(-0.5, 0.5)
        self.drone_vx = 0.0
        self.drone_vy = 0.0
        self.drone_vz = 0.0
        self.altitude = 15.0
        self.target_lost = 0.0
        self.steps = 0
        
        obs = self._get_obs()
        return obs, {}
    
    def _get_obs(self):
        # AI ko yeh 8 numbers dikhao
        return np.array([
            self.target_x,    # target left/right
            self.target_y,    # target upar/neeche
            0.3,              # bbox size (target kitna paas)
            self.drone_vx,    # drone speed x
            self.drone_vy,    # drone speed y
            self.drone_vz,    # drone speed z
            self.altitude/30, # altitude normalized
            self.target_lost  # target dikh raha hai?
        ], dtype=np.float32)
    
    def step(self, action):
        self.steps += 1
        
        # Action lo - drone ko move karo
        self.drone_vx = float(action[0])
        self.drone_vy = float(action[1])
        self.drone_vz = float(action[2])
        
        # Target thoda move karo (simulate karna)
        self.target_x += np.random.uniform(-0.05, 0.05)
        self.target_y += np.random.uniform(-0.05, 0.05)
        
        # REWARD calculate karo
        cx_err = abs(self.target_x)
        cy_err = abs(self.target_y)
        
        reward = 1.0 - (cx_err + cy_err)  # center mein hai to +1
        reward += 0.5                       # paas hai to +0.5
        
        if self.target_lost:
            reward -= 2.0                   # lost hai to -2 penalty
        
        # Episode kab khatam hoga
        done = self.steps >= 200
        
        obs = self._get_obs()
        return obs, reward, done, False, {}


# TEST
if __name__ == "__main__":
    print("=== Gymnasium Environment Test ===")
    
    env = HuntEyeEnv()
    
    # Reset karo
    obs, _ = env.reset()
    print(f"\nStarting Observation (8 numbers):")
    print(f"Target X: {obs[0]:.3f}")
    print(f"Target Y: {obs[1]:.3f}")
    print(f"Altitude: {obs[6]*30:.1f}m")
    
    # 5 random steps chalo
    print(f"\n5 Steps chalate hain:")
    total_reward = 0
    
    for i in range(5):
        action = env.action_space.sample()  # random action
        obs, reward, done, _, _ = env.step(action)
        total_reward += reward
        print(f"Step {i+1}: Reward={reward:.3f}")
    
    print(f"\nTotal Reward: {total_reward:.3f}")
    print("\nEnvironment bilkul ready hai!")