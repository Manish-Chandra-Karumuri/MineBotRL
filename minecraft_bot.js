const mineflayer = require('mineflayer');
const { pathfinder, Movements, goals: { GoalNear } } = require('mineflayer-pathfinder');
const { Vec3 } = require('vec3');
const recipeParser = require('./recipeParser');

function startBot() {
  const bot = mineflayer.createBot({
    host: 'localhost',
    port: 25565,
    username: 'SurvivorBot'
  });

  bot.loadPlugin(pathfinder);

  bot.once('spawn', async () => {
    try {
      console.log("✅ Bot spawned into the world");
      
      // Wait for the world to fully load
      await bot.waitForChunksToLoad();
      console.log("✅ Chunks loaded, starting actions");
      
      // Log inventory
      logInventory(bot);
      
      // Start the survival task sequence
      await performSurvivalTasks(bot);
    } catch (err) {
      console.error("❌ Error during startup:", err.message);
    }
  });

  bot.on('error', err => {
    console.error("❌ Bot error:", err.message);
  });

  bot.on('end', () => {
    console.warn("🔁 Bot disconnected. Restarting...");
    setTimeout(startBot, 3000);
  });
}

function logInventory(bot) {
  const inv = bot.inventory.items();
  console.log("🎒 Inventory:", inv.map(i => `${i.name} x${i.count}`).join(", ") || "Empty");
}

async function performSurvivalTasks(bot) {
  try {
    console.log("🛠️ Beginning survival task sequence...");
    
    // Ensure survival mode
    await bot.chat("/gamemode survival");
    await bot.waitForTicks(10);
    
    // Convert inventory to recipeParser format
    let inventory = {};
    bot.inventory.items().forEach(item => {
      inventory[item.name] = item.count;
    });
    
    // Step 1: Gather wood if needed (retry up to 5 times)
    let woodAttempts = 0;
    while ((!inventory.oak_log || inventory.oak_log < 4) && woodAttempts < 5) {
      console.log(`🌳 Gathering oak logs (attempt ${woodAttempts + 1}/5)...`);
      await gatherWood(bot);
      // Update inventory
      inventory = {};
      bot.inventory.items().forEach(item => {
        inventory[item.name] = item.count;
      });
      woodAttempts++;
    }
    if (!inventory.oak_log || inventory.oak_log < 4) {
      console.error("❌ Failed to gather enough oak logs");
      setTimeout(startBot, 3000); // Restart on failure
      return;
    }
    
    // Step 2: Craft enough planks (target 12 to cover all needs)
    if (!inventory.oak_planks || inventory.oak_planks < 12) {
      const planksNeeded = 12 - (inventory.oak_planks || 0);
      const logsNeeded = Math.ceil(planksNeeded / 4);
      if (inventory.oak_log < logsNeeded) {
        console.log(`🌳 Gathering additional ${logsNeeded - inventory.oak_log} oak logs for planks...`);
        await gatherWood(bot);
        inventory = {};
        bot.inventory.items().forEach(item => {
          inventory[item.name] = item.count;
        });
      }
      console.log("📏 Crafting oak planks...");
      const logsToUse = Math.min(inventory.oak_log, logsNeeded);
      for (let i = 0; i < logsToUse; i++) {
        const success = await craftItem(bot, 'oak_planks');
        if (!success) {
          console.error("❌ Failed to craft oak planks, aborting sequence");
          setTimeout(startBot, 3000); // Restart on failure
          return;
        }
      }
      // Update inventory
      inventory = {};
      bot.inventory.items().forEach(item => {
        inventory[item.name] = item.count;
      });
    }
    
    // Step 3: Craft sticks if needed
    if (!inventory.stick || inventory.stick < 8) {
      console.log("📍 Crafting sticks...");
      const success = await craftItem(bot, 'stick');
      if (!success) {
        console.error("❌ Failed to craft sticks, aborting sequence");
        setTimeout(startBot, 3000); // Restart on failure
        return;
      }
      // Update inventory
      inventory = {};
      bot.inventory.items().forEach(item => {
        inventory[item.name] = item.count;
      });
    }
    
    // Step 4: Craft crafting table if needed
    if (!inventory.crafting_table) {
      console.log("🔨 Crafting crafting table...");
      const success = await craftItem(bot, 'crafting_table');
      if (!success) {
        console.error("❌ Failed to craft crafting table, aborting sequence");
        setTimeout(startBot, 3000); // Restart on failure
        return;
      }
      // Place crafting table with retry
      let placed = false;
      for (let attempt = 0; attempt < 3; attempt++) {
        if (await placeCraftingTable(bot)) {
          placed = true;
          break;
        }
        console.warn(`⚠️ Retry placing crafting table (attempt ${attempt + 1}/3)`);
        await bot.waitForTicks(20);
      }
      if (!placed) {
        console.error("❌ Failed to place crafting table after retries");
        setTimeout(startBot, 3000); // Restart on failure
        return;
      }
      // Update inventory
      inventory = {};
      bot.inventory.items().forEach(item => {
        inventory[item.name] = item.count;
      });
    }
    
    // Step 5: Craft wooden pickaxe if needed
    if (!inventory.wooden_pickaxe) {
      console.log("⛏️ Crafting wooden pickaxe...");
      const success = await craftItem(bot, 'wooden_pickaxe');
      if (!success) {
        console.error("❌ Failed to craft wooden pickaxe, aborting sequence");
        setTimeout(startBot, 3000); // Restart on failure
        return;
      }
      // Update inventory
      inventory = {};
      bot.inventory.items().forEach(item => {
        inventory[item.name] = item.count;
      });
    }
    
    // Step 6: Craft wooden axe if needed
    if (!inventory.wooden_axe) {
      console.log("🪓 Crafting wooden axe...");
      const success = await craftItem(bot, 'wooden_axe');
      if (!success) {
        console.error("❌ Failed to craft wooden axe, aborting sequence");
        setTimeout(startBot, 3000); // Restart on failure
        return;
      }
      // Update inventory
      inventory = {};
      bot.inventory.items().forEach(item => {
        inventory[item.name] = item.count;
      });
    }
    
    // Step 7: Mine up to 28 blocks
    console.log("⛏️ Mining up to 28 blocks...");
    await mineBlocks(bot, 28);
    // Update inventory
    inventory = {};
    bot.inventory.items().forEach(item => {
      inventory[item.name] = item.count;
    });
    
    // Step 8: Mine cobblestone if needed for stone tools
    if (!inventory.cobblestone || inventory.cobblestone < 12) {
      console.log("⛏️ Mining cobblestone for stone tools...");
      await mineCobblestone(bot, 12 - (inventory.cobblestone || 0));
      // Update inventory
      inventory = {};
      bot.inventory.items().forEach(item => {
        inventory[item.name] = item.count;
      });
    }
    
    // Step 9: Craft stone pickaxe
    if (!inventory.stone_pickaxe) {
      console.log("⛏️ Crafting stone pickaxe...");
      const success = await craftItem(bot, 'stone_pickaxe');
      if (!success) {
        console.error("❌ Failed to craft stone pickaxe");
      }
      // Update inventory
      inventory = {};
      bot.inventory.items().forEach(item => {
        inventory[item.name] = item.count;
      });
    }
    
    // Step 10: Craft stone axe
    if (!inventory.stone_axe) {
      console.log("🪓 Crafting stone axe...");
      const success = await craftItem(bot, 'stone_axe');
      if (!success) {
        console.error("❌ Failed to craft stone axe");
      }
      // Update inventory
      inventory = {};
      bot.inventory.items().forEach(item => {
        inventory[item.name] = item.count;
      });
    }
    
    console.log("🎉 Survival task sequence completed!");
    logInventory(bot);
  } catch (err) {
    console.error("❌ Error in survival tasks:", err.message);
    setTimeout(startBot, 3000); // Restart on failure
  }
}

async function gatherWood(bot) {
  try {
    console.log("🔍 Looking for oak tree...");
    const tree = bot.findBlock({
      matching: block => block.name === 'oak_log',
      maxDistance: 128
    });
    
    if (tree) {
      console.log(`Found oak log at ${tree.position}`);
      await bot.pathfinder.goto(new GoalNear(tree.position.x, tree.position.y, tree.position.z, 2));
      console.log("✅ Reached tree");
      
      // Dig the initial log
      await bot.dig(tree);
      console.log("🌳 Gathered wood from initial log");
      
      // Look for additional logs in the same tree (vertically)
      let additionalLogs = 0;
      for (let yOffset = 1; yOffset <= 3; yOffset++) {
        const abovePos = tree.position.offset(0, yOffset, 0);
        const blockAbove = bot.blockAt(abovePos);
        if (blockAbove && blockAbove.name === 'oak_log') {
          console.log(`Found additional oak log at ${abovePos}`);
          await bot.dig(blockAbove);
          console.log("🌳 Gathered additional wood");
          additionalLogs++;
        } else {
          break;
        }
      }
      console.log(`Gathered ${additionalLogs} additional logs from the tree`);
      
      // Collect dropped items with improved pickup
      await pickUpNearbyItems(bot);
    } else {
      console.warn("⚠️ No oak trees found nearby");
    }
  } catch (err) {
    console.error("❌ Error gathering wood:", err.message);
  }
}

async function craftItem(bot, itemName) {
  try {
    // Convert inventory to recipeParser format
    const inventory = {};
    bot.inventory.items().forEach(item => {
      inventory[item.name] = item.count;
    });
    
    // Check if recipe exists and is craftable
    const recipePath = `./recipes/${itemName}.json`;
    const shapedRecipe = recipeParser.parseShapedRecipe(recipePath);
    const shapelessRecipe = recipeParser.parseShapelessRecipe(recipePath);
    const recipe = shapedRecipe || shapelessRecipe;
    
    if (!recipe) {
      console.warn(`⚠️ No valid recipe found for ${itemName}`);
      return false;
    }
    
    // Debug: Log the full recipe
    console.log(`Debug: Recipe for ${itemName}:`, JSON.stringify(recipe, null, 2));
    
    if (!recipeParser.hasRequiredIngredients(recipe, inventory)) {
      console.warn(`⚠️ Insufficient ingredients for ${itemName}:`, recipeParser.getRequiredIngredients(recipe));
      return false;
    }
    
    // Handle different result formats
    let itemId;
    let resultCount = 1;
    if (recipe.result && recipe.result.item) {
      itemId = recipe.result.item.replace('minecraft:', '');
      resultCount = recipe.result.count || 1;
    } else if (recipe.result && recipe.result.id) {
      itemId = recipe.result.id.replace('minecraft:', '');
      resultCount = recipe.result.count || 1;
    } else if (typeof recipe.result === 'string') {
      itemId = recipe.result.replace('minecraft:', '');
    } else {
      console.warn(`⚠️ Invalid recipe format for ${itemName}: missing or invalid result`);
      return false;
    }
    
    // Manually craft by consuming ingredients and adding result
    console.log(`🔨 Crafting ${itemName}...`);
    
    // Get required ingredients
    const requiredIngredients = recipeParser.getRequiredIngredients(recipe);
    console.log(`Debug: Required ingredients for ${itemName}:`, requiredIngredients);
    
    // Consume ingredients from inventory
    for (const [item, count] of Object.entries(requiredIngredients)) {
      const itemInInventory = bot.inventory.items().find(i => i.name === item);
      if (!itemInInventory || itemInInventory.count < count) {
        console.warn(`⚠️ Failed to find enough ${item} in inventory`);
        return false;
      }
      await bot.toss(itemInInventory.type, null, count);
      console.log(`Debug: Consumed ${count} ${item}`);
    }
    
    // Add the result to inventory
    await bot.chat(`/give @s ${itemId} ${resultCount}`);
    console.log(`Debug: Added ${resultCount} ${itemId} to inventory`);
    
    // Wait for inventory update
    await bot.waitForTicks(20);
    console.log(`✅ Crafted ${itemName}`);
    return true;
  } catch (err) {
    console.error(`❌ Error crafting ${itemName}:`, err.message);
    return false;
  }
}

async function findFlatArea(bot) {
  const startPos = bot.entity.position.floored();
  const maxDistance = 64;
  
  for (let dx = -maxDistance; dx <= maxDistance; dx += 3) {
    for (let dz = -maxDistance; dz <= maxDistance; dz += 3) {
      const centerPos = startPos.offset(dx, 0, dz);
      
      // Check a 3x3 area around centerPos
      let isFlat = true;
      let referenceHeight = null;
      let referenceBlock = null;
      
      for (let x = -1; x <= 1; x++) {
        for (let z = -1; z <= 1; z++) {
          const pos = centerPos.offset(x, -1, z);
          const block = bot.blockAt(pos);
          
          // Check if the block is solid (e.g., grass_block, dirt, stone, sand)
          if (!block || !['grass_block', 'dirt', 'stone', 'sand'].includes(block.name)) {
            isFlat = false;
            break;
          }
          
          // Check if the block above is air (nothing obstructing)
          const blockAbove = bot.blockAt(pos.offset(0, 1, 0));
          if (!blockAbove || blockAbove.name !== 'air') {
            isFlat = false;
            break;
          }
          
          // Check if all blocks are at the same height
          if (referenceHeight === null) {
            referenceHeight = pos.y;
            referenceBlock = block.name;
          } else if (pos.y !== referenceHeight || block.name !== referenceBlock) {
            isFlat = false;
            break;
          }
        }
        if (!isFlat) break;
      }
      
      if (isFlat) {
        console.log(`Found flat 3x3 area at ${centerPos} (height ${referenceHeight})`);
        return centerPos;
      }
    }
  }
  
  console.warn("⚠️ No flat 3x3 area found within range");
  return null;
}

async function placeCraftingTable(bot) {
  try {
    const craftingTable = bot.inventory.items().find(item => item.name === 'crafting_table');
    if (!craftingTable) {
      console.warn("⚠️ No crafting table in inventory");
      return false;
    }
    
    // Find a flat 3x3 area
    const flatAreaPos = await findFlatArea(bot);
    if (!flatAreaPos) {
      console.error("❌ Cannot place crafting table: no flat area found");
      return false;
    }
    
    // Move to the center of the flat area
    await bot.pathfinder.goto(new GoalNear(flatAreaPos.x, flatAreaPos.y, flatAreaPos.z, 1));
    console.log(`✅ Moved to flat area at ${flatAreaPos}`);
    
    await bot.equip(craftingTable, 'hand');
    console.log("✅ Equipped crafting table");
    
    const groundPos = flatAreaPos.offset(0, -1, 0);
    const groundBlock = bot.blockAt(groundPos);
    
    if (groundBlock && groundBlock.name !== 'air') {
      console.log(`🧱 Placing crafting table at ${groundPos}...`);
      await bot.placeBlock(groundBlock, new Vec3(0, 1, 0));
      // Wait for block update
      const blockUpdate = await new Promise(resolve => {
        bot.once('blockUpdate', (oldBlock, newBlock) => {
          if (newBlock.position.equals(groundPos.offset(0, 1, 0)) && newBlock.name === 'crafting_table') {
            resolve(true);
          }
        });
        setTimeout(() => resolve(false), 10000); // Increased to 10-second timeout
      });
      if (blockUpdate) {
        console.log("✅ Placed crafting table");
        return true;
      }
      console.warn(`⚠️ Block update timeout at ${groundPos.offset(0, 1, 0)}`);
    }
    
    console.warn("⚠️ No suitable ground found to place crafting table");
    return false;
  } catch (err) {
    console.error("❌ Error placing crafting table:", err.message);
    return false;
  }
}

async function pickUpNearbyItems(bot) {
  console.log("🔄 Looking for nearby items to pick up...");
  
  return new Promise(resolve => {
    const collectHandler = (collector, collected) => {
      if (collector.username === bot.username) {
        console.log(`Collected ${collected.name} x${collected.count || 1}`);
      }
    };
    
    bot.on('playerCollect', collectHandler);
    
    // Wait for items to spawn
    setTimeout(() => {
      // Move in a wider pattern to collect items
      bot.setControlState('forward', true);
      setTimeout(() => {
        bot.setControlState('forward', false);
        bot.setControlState('left', true);
        setTimeout(() => {
          bot.setControlState('left', false);
          bot.setControlState('right', true);
          setTimeout(() => {
            bot.setControlState('right', false);
            bot.setControlState('back', true);
            setTimeout(() => {
              bot.setControlState('back', false);
              bot.removeListener('playerCollect', collectHandler);
              logInventory(bot);
              resolve();
            }, 1500);
          }, 1500);
        }, 1500);
      }, 1500);
    }, 500);
  });
}

async function mineBlocks(bot, maxBlocks) {
  try {
    console.log(`⛏️ Attempting to mine up to ${maxBlocks} blocks...`);
    
    // Equip pickaxe
    const pickaxe = bot.inventory.items().find(item => item.name === 'wooden_pickaxe' || item.name === 'stone_pickaxe');
    if (pickaxe) {
      await bot.equip(pickaxe, 'hand');
      console.log(`✅ Equipped ${pickaxe.name}`);
    } else {
      console.warn("⚠️ No pickaxe found to equip");
      return;
    }
    
    let blocksMined = 0;
    while (blocksMined < maxBlocks) {
      // Look for mineable blocks
      const block = bot.findBlock({
        matching: block => ['stone', 'cobblestone', 'dirt', 'grass_block'].includes(block.name),
        maxDistance: 32
      });
      
      if (!block) {
        console.log("⚠️ No mineable blocks found nearby");
        break;
      }
      
      console.log(`Found ${block.name} at ${block.position}`);
      await bot.pathfinder.goto(new GoalNear(block.position.x, block.position.y, block.position.z, 2));
      console.log("✅ Reached block");
      
      await bot.dig(block);
      console.log(`⛏️ Mined ${block.name}`);
      blocksMined++;
      
      // Collect dropped items
      await pickUpNearbyItems(bot);
      
      // Update inventory
      const inventory = {};
      bot.inventory.items().forEach(item => {
        inventory[item.name] = item.count;
      });
      logInventory(bot);
    }
    
    console.log(`✅ Mined ${blocksMined} blocks`);
  } catch (err) {
    console.error("❌ Error during block mining:", err.message);
  }
}

async function mineCobblestone(bot, amountNeeded) {
  try {
    console.log(`⛏️ Attempting to mine ${amountNeeded} cobblestone...`);
    
    // Equip pickaxe
    const pickaxe = bot.inventory.items().find(item => item.name === 'wooden_pickaxe' || item.name === 'stone_pickaxe');
    if (pickaxe) {
      await bot.equip(pickaxe, 'hand');
      console.log(`✅ Equipped ${pickaxe.name}`);
    } else {
      console.warn("⚠️ No pickaxe found to equip");
      return;
    }
    
    let cobblestoneMined = 0;
    while (cobblestoneMined < amountNeeded) {
      // Look for stone (which drops cobblestone when mined)
      const block = bot.findBlock({
        matching: block => block.name === 'stone',
        maxDistance: 32
      });
      
      if (!block) {
        console.log("⚠️ No stone found nearby");
        break;
      }
      
      console.log(`Found stone at ${block.position}`);
      await bot.pathfinder.goto(new GoalNear(block.position.x, block.position.y, block.position.z, 2));
      console.log("✅ Reached stone");
      
      await bot.dig(block);
      console.log("⛏️ Mined stone (drops cobblestone)");
      cobblestoneMined++;
      
      // Collect dropped items
      await pickUpNearbyItems(bot);
      
      // Update inventory
      const inventory = {};
      bot.inventory.items().forEach(item => {
        inventory[item.name] = item.count;
      });
      logInventory(bot);
    }
    
    console.log(`✅ Mined ${cobblestoneMined} cobblestone`);
  } catch (err) {
    console.error("❌ Error during cobblestone mining:", err.message);
  }
}

startBot();