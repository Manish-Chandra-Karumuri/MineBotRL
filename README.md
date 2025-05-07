# 🧠 Minecraft RL Bot

This project implements a **Reinforcement Learning agent for Minecraft**, where a bot autonomously learns survival tasks like mining, crafting, and exploration using a combination of:

- 🧠 **Stable-Baselines3 (PPO, A2C, DQN)**
- 🕹️ **Custom Gym-compatible environment**
- 🧱 **Mineflayer-based Minecraft bot (Node.js)**
- 📦 **Recipe-based crafting with JSON files**

---

## 📁 Project Structure

```
minecraft-rl-bot/
├── environment.py            # Gym-compatible environment wrapper (Python)
├── main.py                   # Main control script for training/evaluation
├── train_rl_agent.py         # RL training, evaluation, and visualization logic
├── minecraft_bot.js          # Node.js bot logic (movement, crafting, mining)
├── recipeParser.js           # JS utility to parse and validate crafting recipes
├── package.json              # Node.js dependencies and script setup
├── requirements.txt          # Python dependencies
├── recipes/                  # Auto-generated folder of crafting recipes
├── logs/                     # Auto-generated logs during training
```

---

## 🚀 Getting Started

### 1. Requirements

#### 🐍 Python (Recommended: 3.8+)
Install Python dependencies:

```bash
pip install -r requirements.txt
```

#### 🟦 Node.js (Recommended: v16+)
Install JavaScript dependencies:

```bash
npm install
```

---

## 🧪 Run Training

To start training the RL bot:

```bash
python main.py --mode train --algorithm PPO --timesteps 500000
```

Optional flags:

- `--skip-node`: Skip starting the Node.js bot (if already running).
- `--no-curriculum`: Disable curriculum learning logic.
- `--bot-username`: Change bot’s Minecraft name.

---

## 🔍 Evaluation

Evaluate a saved model:

```bash
python main.py --mode evaluate --model-path path/to/final_model.zip
```

---

## 🎥 Visualization

Visualize a trained agent:

```bash
python main.py --mode visualize --model-path path/to/final_model.zip
```

---

## 🧠 RL Environment (environment.py)

- Follows the OpenAI Gym API (`reset`, `step`, `render`)
- Observation space: Bot position, inventory, nearby blocks, health, etc.
- Action space: Move, jump, mine, place, craft, collect, eat
- Reward function encourages resource collection, crafting, and survival

---

## 🤖 Minecraft Bot (minecraft_bot.js)

- Built using [`mineflayer`](https://github.com/PrismarineJS/mineflayer)
- Starts in survival mode, gathers resources, crafts tools, places blocks
- Uses pathfinding and block recognition to perform survival tasks
- Automatically restarts on failure

---

## 📜 Crafting Recipes

All crafting logic is defined in `/recipes/*.json` using official Minecraft formats.

Sample items:

- `crafting_table.json`
- `wooden_pickaxe.json`
- `stick.json`
- `stone_pickaxe.json`

These are parsed by `recipeParser.js` to validate ingredients and simulate crafting.

---

## 📓 Logs & Output

- `logs/`: Contains training metrics, models, and visualizations
- `minecraft_rl.log`: Combined output log for both Python + Node.js

---

## 🧰 Developer Notes

### Start the bot manually (if needed):

```bash
node minecraft_bot.js
```

### Auto-create recipes folder:

The first run of `main.py` will generate a `/recipes/` directory with starter JSONs.

---

## 🧠 Example Workflow

```bash
# Train agent for 1M steps
python main.py --mode train --timesteps 1000000

# Evaluate trained model
python main.py --mode evaluate --model-path logs/minecraft_rl_PPO_*/final_model.zip

# Visualize behavior
python main.py --mode visualize --model-path logs/minecraft_rl_PPO_*/final_model.zip
```

---

## 🛠 Troubleshooting

- Make sure Minecraft server is running and accessible on port `25565`.
- Use [TLauncher](https://tlauncher.org/en/) or a local Minecraft server to host the world.
- If `mineflayer` throws plugin errors, double-check `node_modules` with:

```bash
npm install
```

---

MIT License


---

## 🌐 Emoji Support

All emojis used in this README are supported by [Twemoji](https://twemoji.twitter.com/) and render well on most modern systems. 
For emoji markdown compatibility and usage, refer to: [https://emojipedia.org/](https://emojipedia.org/)
