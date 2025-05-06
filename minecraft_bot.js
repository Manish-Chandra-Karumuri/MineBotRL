// minecraft_bot.js
const mineflayer = require('mineflayer');
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder');
const { GoalNear } = goals;
const { Vec3 } = require('vec3');
const collectBlock = require('mineflayer-collectblock').plugin;
const mcDataLoader = require('minecraft-data');
const fs = require('fs');
const path = require('path');
const express = require('express');
const { parseShapedRecipe, parseShapelessRecipe } = require('./recipeParser');

const app = express();
const port = 3000;

let bot, mcData;
let craftingInProgress = false;
let lastLogCollection = 0;

function createBot() {
  bot = mineflayer.createBot({
    host: 'localhost',
    port: 25565,
    username: 'RLBot'
  });

  bot.loadPlugin(pathfinder);
  bot.loadPlugin(collectBlock);

  bot.once('spawn', () => {
    mcData = mcDataLoader(bot.version);
    const defaultMove = new Movements(bot, mcData);
    bot.pathfinder.setMovements(defaultMove);
    console.log('[Bot Server] ✅ Bot spawned');
    startPeriodicTasks();
  });

  bot.on('error', err => console.log('[Bot Server] ❗ Bot error:', err));
  bot.on('end', () => {
    console.log('[Bot Server] ❌ Bot disconnected');
    setTimeout(() => {
      console.log('[Bot Server] 🔁 Respawning bot...');
      createBot();
    }, 5000);
  });
}

function startPeriodicTasks() {
  setInterval(async () => {
    const pos = bot.entity.position;
    const inventory = parseInventory(bot.inventory.items());
    console.log('[Bot Status] Position:', pos);
    console.log('[Bot Status] Health:', bot.health);
    console.log('[Bot Status] Hunger:', bot.food);
    console.log('[Bot Status] Inventory:', inventory);
    try {
      await autoCraftTools(inventory);
    } catch (err) {
      console.error('[Bot Logic] ❗ Periodic task error:', err.message);
    }
  }, 12000);
}

function parseInventory(items) {
  const result = {};
  for (const item of items) {
    result[item.name] = (result[item.name] || 0) + item.count;
  }
  return result;
}

async function autoCraftTools(inventory) {
  const now = Date.now();
  const totalLogs = bot.inventory.items()
    .filter(item => item.name.endsWith('_log') && !item.name.includes('stripped'))
    .reduce((sum, item) => sum + item.count, 0);

  if (totalLogs < 6 && now - lastLogCollection > 15000) {
    const logBlock = bot.findBlock({
      matching: block => block.name.endsWith('_log') && !block.name.includes('stripped'),
      maxDistance: 250
    });

    if (logBlock) {
      try {
        console.log('[Bot Collecting] Collecting nearby log:', logBlock.name);
        await bot.collectBlock.collect(logBlock);
        lastLogCollection = Date.now();
        await bot.waitForTicks(20);
        return;
      } catch (err) {
        console.log('[Bot Collecting] ❗ Error:', err.message);
        return;
      }
    } else {
      console.log('[Bot Collecting] ⚠️ No wooden log found nearby');
      return;
    }
  }

  if (!inventory.oak_planks || inventory.oak_planks < 4) {
    await bot.waitForTicks(10);
    await craftItemFromRecipe('oak_planks');
    await bot.waitForTicks(10);
    return;
  }

  if (!inventory.stick || inventory.stick < 2) {
    await bot.waitForTicks(10);
    await craftItemFromRecipe('stick');
    await bot.waitForTicks(10);
    return;
  }

  if (!inventory.crafting_table && inventory.oak_planks >= 4) {
    await bot.waitForTicks(10);
    await craftItemFromRecipe('crafting_table');
    await bot.waitForTicks(10);
    return;
  }

  if (!inventory.wooden_pickaxe && inventory.stick >= 2 && inventory.oak_planks >= 3) {
    await bot.waitForTicks(10);
    await craftItemFromRecipe('wooden_pickaxe');
    await bot.waitForTicks(10);
    return;
  }

  if (inventory.wooden_pickaxe && (!inventory.cobblestone || inventory.cobblestone < 6)) {
    const stoneBlock = bot.findBlock({
      matching: block => ['stone', 'andesite', 'diorite'].includes(block.name),
      maxDistance: 250
    });
    if (stoneBlock) {
      try {
        console.log('[Bot Mining] Mining stone with wooden pickaxe...');
        await bot.equip(bot.inventory.items().find(i => i.name === 'wooden_pickaxe'), 'hand');
        await bot.dig(stoneBlock);
        await bot.waitForTicks(10);
        return;
      } catch (err) {
        console.log('[Bot Mining] ❗ Error:', err.message);
        return;
      }
    } else {
      console.log('[Bot Mining] ⚠️ No stone block nearby');
      return;
    }
  }
}

async function craftItemFromRecipe(recipeName) {
  if (craftingInProgress) return;
  craftingInProgress = true;

  try {
    const recipePath = path.join(__dirname, 'recipes', `${recipeName}.json`);
    const shaped = parseShapedRecipe(recipePath);
    const shapeless = parseShapelessRecipe(recipePath);
    const parsed = shaped || shapeless;

    if (!parsed) {
      console.log(`[Bot Crafting] ❌ Failed to load recipe: ${recipeName}`);
      return;
    }

    const { result } = parsed;
    console.log(`[Bot Crafting] 🔧 Crafting ${result.id}...`);

    let craftingTableBlock = bot.findBlock({
      matching: block => block.name === 'crafting_table',
      maxDistance: 250
    });

    if (!craftingTableBlock && shaped && recipeName !== 'crafting_table') {
      const tableInInventory = bot.inventory.items().find(item => item.name === 'crafting_table');
      if (tableInInventory) {
        const targetPos = bot.entity.position.offset(1, 0, 0).floored();
        const refBlock = bot.blockAt(targetPos.offset(0, -1, 0));
        if (refBlock && bot.canPlaceBlock(refBlock)) {
          await bot.equip(tableInInventory, 'hand');
          await bot.placeBlock(refBlock, new Vec3(0, 1, 0));
          await bot.waitForTicks(10);
          craftingTableBlock = bot.blockAt(targetPos);
        }
      } else {
        await craftItemFromRecipe('crafting_table');
        await bot.waitForTicks(10);
        craftingTableBlock = bot.findBlock({
          matching: block => block.name === 'crafting_table',
          maxDistance: 250
        });
      }
    }

    const itemName = result.id.replace('minecraft:', '');
    const itemInfo = mcData.itemsByName[itemName];

    if (!itemInfo) {
      console.log(`[Bot Crafting] ❌ Invalid item name: ${itemName}`);
      return;
    }

    const tableToUse = shaped ? craftingTableBlock : null;
    const allRecipes = bot.recipesFor(itemInfo.id, null, 1, tableToUse);

    if (!allRecipes || allRecipes.length === 0) {
      console.log(`[Bot Crafting] ❌ No matching recipe found for ${itemName}`);
      return;
    }

    const recipe = allRecipes[0];
    await bot.craft(recipe, result.count || 1, tableToUse);
    console.log(`[Bot Crafting] ✅ Crafted ${result.id}`);
    await bot.waitForTicks(20);
  } catch (err) {
    console.log(`[Bot Crafting] ❌ Crafting failed: ${err.message}`);
  } finally {
    craftingInProgress = false;
  }
}

createBot();

app.use(express.json());

app.post('/reset', async (req, res) => {
  try {
    await bot.waitForTicks(5);
    res.sendStatus(200);
  } catch (err) {
    console.error('[Bot Server] ❌ Reset error:', err.message);
    res.status(500).send('Reset failed');
  }
});

app.post('/act', async (req, res) => {
  try {
    await bot.waitForTicks(1);
    res.sendStatus(200);
  } catch (err) {
    console.error('[Bot Server] ❌ Act error:', err.message);
    res.status(500).send('Action failed');
  }
});

app.get('/status', (req, res) => {
  try {
    const pos = bot.entity.position;
    const inventory = parseInventory(bot.inventory.items());
    res.json({
      health: bot.health,
      hunger: bot.food,
      position: pos,
      inventory: inventory
    });
  } catch (err) {
    console.error('[Bot Server] ❌ Status error:', err.message);
    res.status(500).send('Status unavailable');
  }
});

app.get('/ping', (_, res) => res.sendStatus(200));

app.listen(port, () => {
  console.log(`🚀 Bot server running on http://localhost:${port}`);
});
