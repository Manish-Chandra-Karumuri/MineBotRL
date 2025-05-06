import os
import subprocess
import time
from train_rl_agent import train_rl_agent

if __name__ == "__main__":
    print("🚀 Starting Node.js Minecraft bot server...")
    subprocess.Popen(["node", "minecraft_bot.js"], shell=True)

    print("⏳ Waiting 5 seconds for server to initialize...")
    time.sleep(5)

    print("🎮 Connecting bot and launching training...")
    train_rl_agent()
