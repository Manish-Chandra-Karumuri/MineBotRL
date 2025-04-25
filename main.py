import time
from bot import MinecraftBot

def main():
    print("Minecraft Bot Setup")
    print("1. Make sure Minecraft is running and visible")
    print("2. Be in a world where you can move around")
    print("3. The bot will control your character using keyboard and mouse")
    print("4. To stop the bot, press Ctrl+C or move your mouse to any corner of the screen")
    print("\nStarting in 5 seconds... Switch to Minecraft window now!")
    
    for i in range(5, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    bot = MinecraftBot()
    
    try:
        bot.setup_environment()
        print("Starting training...")
        bot.train(total_timesteps=10000)
        bot.save_model()
        print("Running an episode with the trained model...")
        bot.run_episode()
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting steps:")
        print("1. Make sure Minecraft is running and visible")
        print("2. Check that you're in a world and can move around")
        print("3. Try restarting both Minecraft and this script")
        print("4. Make sure no other program is interfering with keyboard/mouse input")

if __name__ == "__main__":
    main() 