# Minecraft RL Bot

A reinforcement learning bot that controls Minecraft using PyAutoGUI. The bot uses the PPO (Proximal Policy Optimization) algorithm to learn basic movement and navigation in Minecraft.

## Project Structure

The project is organized into multiple files:

- `controller.py`: Handles direct interaction with Minecraft (keyboard/mouse control)
- `environment.py`: Defines the reinforcement learning environment
- `bot.py`: Manages the training and execution of the bot
- `main.py`: Entry point of the program

## Requirements

- Python 3.8 or higher
- Minecraft (any version)
- Required Python packages (install using `pip install -r requirements.txt`):
  - numpy
  - gymnasium
  - stable-baselines3
  - pyautogui
  - keyboard
  - pywin32

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Make sure Minecraft is installed and running on your system.

## Usage

1. Start Minecraft and enter a world where you can move around.

2. Run the bot:
```bash
python main.py
```

3. The bot will:
   - Show a 5-second countdown
   - Find and focus the Minecraft window
   - Train for 10,000 timesteps
   - Save the trained model
   - Run an episode to demonstrate learned behavior

4. To stop the bot:
   - Press Ctrl+C
   - Or move your mouse to any corner of the screen (PyAutoGUI failsafe)

## How It Works

The bot uses reinforcement learning to control Minecraft through simulated keyboard and mouse inputs:

1. **Action Space**:
   - Movement (forward/backward, left/right)
   - Jumping
   - Looking around (yaw and pitch)

2. **Observation Space**:
   - Position (x, y, z)
   - Rotation (yaw, pitch)
   - Block information

3. **Reward Function**:
   - Small negative reward (-0.1) for each step
   - Positive reward (+0.5) for jumping
   - Small positive reward (+0.1) for moving

## Troubleshooting

If you encounter issues:

1. Make sure Minecraft is running and visible
2. Check that you're in a world and can move around
3. Try restarting both Minecraft and the script
4. Ensure no other program is interfering with keyboard/mouse input
5. Verify all required packages are installed correctly

## Notes

- The bot currently uses simulated state information since we can't directly read the game state
- The rewards are simple and might not lead to complex behaviors
- The bot controls your actual Minecraft character through keyboard and mouse simulation 