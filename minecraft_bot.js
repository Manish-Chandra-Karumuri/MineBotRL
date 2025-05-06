const mineflayer = require('mineflayer');
const express = require('express');
const bodyParser = require('body-parser');
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder');
const collectBlock = require('mineflayer-collectblock').plugin;
const Vec3 = require('vec3');

const { GoalBlock } = goals;

const app = express();
app.use(bodyParser.json());

let bot;
let mcData;

function createBot() {
  bot = mineflayer.createBot({
    host: 'localhost',
    port: 25565,
    username: 'RLBot'
  });

  bot.loadPlugin(pathfinder);
  bot.loadPlugin(collectBlock);

  bot.once('spawn', () => {
    mcData = require('minecraft-data')(bot.version);
    bot.chat('RL Bot online!');
    console.log('[Bot Server] ✅ Bot spawned');

    setInterval(() => {
      const position = bot.entity.position;
      const health = bot.health;
      const hunger = bot.food;
      const inventory = {};

      bot.inventory.items().forEach(item => {
        inventory[item.name] = (inventory[item.name] || 0) + item.count;
      });

      console.log('[Bot Status] Position:', position);
      console.log('[Bot Status] Health:', health);
      console.log('[Bot Status] Hunger:', hunger);
      console.log('[Bot Status] Inventory:', inventory);

      autoCraftTools(inventory);
    }, 5000);
  });

  bot.on('error', err => {
    console.error(`[Bot Server] ❌ Error: ${err}`);
  });
}

async function autoCraftTools(inventory) {
  try {
    const craftingTableItem = mcData.itemsByName.crafting_table;
    const planksItem = mcData.itemsByName.spruce_planks;
    const stickItem = mcData.itemsByName.stick;

    if (inventory.spruce_log && inventory.spruce_log >= 1 && !inventory.spruce_planks) {
      const logItem = bot.inventory.items().find(item => item.name === 'spruce_log');
      const plankRecipe = bot.recipesFor(planksItem.id, null, 1, logItem)[0];
      if (plankRecipe) {
        await bot.craft(plankRecipe, 1, null);
        console.log('[Bot Crafting] Crafted spruce planks');
      }
    }

    if (inventory.spruce_planks >= 4 && !inventory.crafting_table) {
      const planks = bot.inventory.items().find(item => item.name === 'spruce_planks');
      const recipe = bot.recipesFor(craftingTableItem.id, null, 1, planks)[0];
      if (recipe) {
        await bot.craft(recipe, 1, null);
        console.log('[Bot Crafting] Crafted crafting table');
      }
    }

    const tableNearby = bot.findBlock({ matching: mcData.blocksByName.crafting_table.id, maxDistance: 6 });
    if (!tableNearby && inventory.crafting_table) {
      const tableItem = bot.inventory.items().find(i => i.name === 'crafting_table');
      const offsets = [
        new Vec3(1, -1, 0),
        new Vec3(0, -1, 1),
        new Vec3(-1, -1, 0),
        new Vec3(0, -1, -1)
      ];

      for (let offset of offsets) {
        const pos = bot.entity.position.offset(offset.x, offset.y, offset.z);
        const referenceBlock = bot.blockAt(pos);
        const placePos = new Vec3(0, 1, 0);
        if (referenceBlock && bot.blockAt(referenceBlock.position.offset(...placePos.toArray())).name === 'air') {
          await bot.equip(tableItem, 'hand');
          await bot.placeBlock(referenceBlock, placePos);
          console.log('[Bot Crafting] Placed crafting table');
          break;
        }
      }
    }

    const woodenPickaxe = mcData.itemsByName.wooden_pickaxe;
    const craftingTableBlock = bot.findBlock({ matching: mcData.blocksByName.crafting_table.id, maxDistance: 6 });
    if (inventory.stick >= 2 && inventory.spruce_planks >= 3 && !inventory.wooden_pickaxe && craftingTableBlock) {
      const recipe = bot.recipesFor(woodenPickaxe.id, null, 1, craftingTableBlock)[0];
      if (recipe) {
        await bot.craft(recipe, 1, craftingTableBlock);
        console.log('[Bot Crafting] Crafted wooden pickaxe');
      }
    }

    if (inventory.wooden_pickaxe && !inventory.cobblestone) {
      const stoneBlock = bot.findBlock({ matching: mcData.blocksByName.stone.id, maxDistance: 10 });
      if (stoneBlock) {
        await bot.equip(bot.inventory.items().find(i => i.name === 'wooden_pickaxe'), 'hand');
        await bot.dig(stoneBlock);
        console.log('[Bot Mining] Mined stone for cobblestone');
      }
    }

    const stonePickaxe = mcData.itemsByName.stone_pickaxe;
    if (inventory.cobblestone >= 3 && inventory.stick >= 2 && !inventory.stone_pickaxe && craftingTableBlock) {
      const recipe = bot.recipesFor(stonePickaxe.id, null, 1, craftingTableBlock)[0];
      if (recipe) {
        await bot.craft(recipe, 1, craftingTableBlock);
        console.log('[Bot Crafting] Crafted stone pickaxe');
      }
    }
  } catch (e) {
    console.log('[Bot Crafting] ⚠️ Error during auto crafting:', e.message);
  }
}

createBot();

app.post('/reset', (req, res) => {
  bot.chat('Resetting environment...');
  res.sendStatus(200);
});

app.post('/move', (req, res) => {
  const { direction, distance } = req.body;
  const movement = new Movements(bot, mcData);
  bot.pathfinder.setMovements(movement);

  const pos = bot.entity.position;
  let goal;
  switch (direction) {
    case 'forward':
      goal = new GoalBlock(pos.x + distance, pos.y, pos.z);
      break;
    case 'backward':
      goal = new GoalBlock(pos.x - distance, pos.y, pos.z);
      break;
    case 'left':
      goal = new GoalBlock(pos.x, pos.y, pos.z + distance);
      break;
    case 'right':
      goal = new GoalBlock(pos.x, pos.y, pos.z - distance);
      break;
    default:
      return res.status(400).send('Invalid direction');
  }

  try {
    bot.pathfinder.setGoal(goal, true);
    res.sendStatus(200);
  } catch (err) {
    console.error('[Bot Server] ❗ Error during move:', err);
    res.status(500).send('Movement error');
  }
});

app.post('/jump', (req, res) => {
  bot.setControlState('jump', true);
  setTimeout(() => bot.setControlState('jump', false), 500);
  res.sendStatus(200);
});

app.post('/mine', async (req, res) => {
  try {
    const block = bot.findBlock({ matching: mcData.blocksByName.spruce_log.id, maxDistance: 5 });
    if (block) {
      bot.pathfinder.setGoal(null);
      await bot.waitForTicks(2);
      await bot.dig(block);
      res.sendStatus(200);
    } else {
      res.status(404).send('No block found');
    }
  } catch (err) {
    console.error('[Bot Server] ❗ Error during mining:', err);
    res.status(500).send('Mining error');
  }
});

app.post('/collect', async (req, res) => {
  try {
    const block = bot.findBlock({ matching: mcData.blocksByName.spruce_log.id, maxDistance: 6 });
    if (block) {
      bot.pathfinder.setGoal(null);
      await bot.waitForTicks(2);
      await bot.collectBlock.collect(block, { ignoreGoalConflict: true });
      res.sendStatus(200);
    } else {
      res.status(404).send('No block to collect');
    }
  } catch (err) {
    console.error('[Bot Server] ❗ Error during collect:', err);
    res.status(500).send('Collect error');
  }
});

app.get('/status', (req, res) => {
  if (!bot || !bot.entity) {
    return res.status(500).send('Bot not ready');
  }

  const position = bot.entity.position;
  const health = bot.health;
  const hunger = bot.food;
  const inventory = {};

  bot.inventory.items().forEach(item => {
    inventory[item.name] = (inventory[item.name] || 0) + item.count;
  });

  res.json({
    position: { x: position.x, y: position.y, z: position.z },
    health,
    hunger,
    inventory
  });
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`🚀 Bot server running on http://localhost:${PORT}`);
});
