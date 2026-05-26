# Dev 3 - PPO Agent
# Trained AI ko load karta hai aur decisions leta hai

from stable_baselines3 import PPO
from ai.gym_env import HuntEyeEnv
import os

class HuntEyeAgent:
    def __init__(self):
        self.env = HuntEyeEnv()
        self.model = None
    
    def train(self, total_steps=100000):
        print("=== PPO Training Shuru ===")
        print(f"Total Steps: {total_steps}")
        print("TensorBoard: tensorboard --logdir ./logs/")
        print("Ruko... time lagega!\n")
        
        # Models folder banao
        os.makedirs("models", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        self.model = PPO(
            "MlpPolicy", 
            self.env, 
            verbose=1,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            gamma=0.99,
            tensorboard_log="./logs/"
        )
        
        self.model.learn(total_timesteps=total_steps)
        self.model.save("models/ppo_hunt_eye")
        print("\n✅ Training complete! Model saved!")
    
    def load(self):
        if os.path.exists("models/ppo_hunt_eye.zip"):
            self.model = PPO.load("models/ppo_hunt_eye", env=self.env)
            print("✅ Model load ho gaya!")
            return True
        else:
            print("❌ Model nahi mila - pehle train karo!")
            return False
    
    def predict(self, observation):
        if self.model is None:
            print("Model load nahi hai!")
            return None
        action, _ = self.model.predict(observation)
        return action


# TEST
if __name__ == "__main__":
    print("=== Agent Test ===")
    
    agent = HuntEyeAgent()
    
    # Pehle thoda train karo - sirf 10000 steps test ke liye
    print("\nTest training (10000 steps)...")
    agent.train(total_steps=10000)
    
    # Load karo
    print("\nModel load karte hain...")
    agent.load()
    
    # Ek prediction karo
    print("\nEk action predict karte hain...")
    obs, _ = agent.env.reset()
    action = agent.predict(obs)
    print(f"Action: {action}")
    print(f"\nvx={action[0]:.3f}, vy={action[1]:.3f}, vz={action[2]:.3f}, yaw={action[3]:.3f}")
    
    print("\n✅ Agent bilkul ready hai!")