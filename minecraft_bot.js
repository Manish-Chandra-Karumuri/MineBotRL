const mineflayer = require('mineflayer');
const express = require('express');
const bodyParser = require('body-parser');

// Create an Express server to communicate with Python
const app = express();
app.use(bodyParser.json());
const PORT = 3000;

// Bot configuration
let botConfig = {
    host: 'localhost',       // Default Minecraft server host
    port: 25565,             // Default Minecraft server port
    username: 'RLBot',       // Bot username
    version: '1.21.1'        // Minecraft version
};

// Initialize the bot
let bot = null;
let botConnected = false;
let botPosition = { x: 0, y: 0, z: 0 };
let botHealth = 20;
let botHunger = 20;
let botInventory = {};

// Function to connect the bot to the Minecraft server
function connectBot(config) {
    // Create a new bot instance
    bot = mineflayer.createBot(config);
    
    // Event handlers
    bot.on('spawn', () => {
        console.log('Bot spawned in the world');
        botConnected = true;
        updateBotState();
        
        // Send a chat message to indicate the bot is active
        bot.chat("Hello! I am an RL bot learning to play Minecraft!");
        
        // Activate auto-reconnect for better stability
        if (bot.autoReconnect) {
            bot.autoReconnect.enabled = true;
        }
    });
    
    bot.on('error', (err) => {
        console.error('Bot error:', err);
        botConnected = false;
        
        // Try to reconnect after an error
        console.log('Attempting to reconnect in 5 seconds...');
        setTimeout(() => {
            if (!botConnected) {
                connectBot(botConfig);
            }
        }, 5000);
    });
    
    bot.on('end', () => {
        console.log('Bot disconnected');
        botConnected = false;
        
        // Try to reconnect after disconnection
        console.log('Attempting to reconnect in 5 seconds...');
        setTimeout(() => {
            if (!botConnected) {
                connectBot(botConfig);
            }
        }, 5000);
    });
    
    bot.on('health', () => {
        updateBotState();
    });
    
    bot.on('move', () => {
        updateBotState();
    });
    
    bot.on('playerCollect', () => {
        setTimeout(updateBotState, 500); // Update inventory after a short delay
    });
    
    bot.on('diggingCompleted', (block) => {
        console.log(`Finished mining ${block.name}`);
        updateBotState();
        
        // Automatically look for another block to mine
        setTimeout(() => {
            const newBlock = findBlockToMine();
            if (newBlock) {
                bot.lookAt(newBlock.position);
            }
        }, 500);
    });
    
    bot.on('diggingAborted', (block) => {
        console.log(`Mining of ${block.name} was aborted`);
    });
    
    bot.on('blockBreak', (block) => {
        console.log(`Block broken: ${block.name}`);
        updateBotState();
    });
}

// Function to update the bot's state information
function updateBotState() {
    if (!bot || !botConnected) return;
    
    try {
        // Update position
        botPosition = bot.entity.position;
        
        // Update health and hunger
        botHealth = bot.health;
        botHunger = bot.food;
        
        // Update inventory
        botInventory = {};
        bot.inventory.items().forEach(item => {
            const itemName = item.name;
            if (botInventory[itemName]) {
                botInventory[itemName] += item.count;
            } else {
                botInventory[itemName] = item.count;
            }
        });
        
        console.log(`Bot position: (${botPosition.x.toFixed(2)}, ${botPosition.y.toFixed(2)}, ${botPosition.z.toFixed(2)})`);
        console.log(`Health: ${botHealth}, Food: ${botHunger}`);
        console.log('Inventory:', botInventory);
    } catch (err) {
        console.error('Error updating bot state:', err);
    }
}

// Helper function to find a block to mine
function findBlockToMine() {
    // Priority blocks to look for
    const targetBlocks = [
        'oak_log', 'spruce_log', 'birch_log', 'jungle_log', 'acacia_log', 'dark_oak_log',
        'stone', 'coal_ore', 'iron_ore', 'gold_ore', 'diamond_ore'
    ];
    
    // Check in a 5x5x5 area around the bot
    const searchDistance = 5;
    
    // Store found blocks and their distances
    const foundBlocks = [];
    
    // Loop through target block types
    for (const blockType of targetBlocks) {
        // Find blocks of this type
        const blocks = bot.findBlocks({
            matching: block => block.name.includes(blockType),
            maxDistance: searchDistance,
            count: 5 // Find up to 5 of each type
        });
        
        // Add found blocks to our list
        blocks.forEach(blockPos => {
            const block = bot.blockAt(blockPos);
            if (block) {
                // Calculate distance from bot
                const distance = Math.sqrt(
                    Math.pow(block.position.x - bot.entity.position.x, 2) +
                    Math.pow(block.position.y - bot.entity.position.y, 2) +
                    Math.pow(block.position.z - bot.entity.position.z, 2)
                );
                
                foundBlocks.push({
                    block: block,
                    distance: distance
                });
            }
        });
    }
    
    // If we found blocks, return the closest one
    if (foundBlocks.length > 0) {
        // Sort by distance
        foundBlocks.sort((a, b) => a.distance - b.distance);
        console.log(`Found ${foundBlocks.length} blocks to mine, closest is ${foundBlocks[0].block.name}`);
        return foundBlocks[0].block;
    }
    
    console.log('No suitable blocks found to mine');
    return null;
}

// Express API endpoints

// Connect the bot
app.post('/connect', (req, res) => {
    const config = req.body;
    try {
        // Update config with values from request
        botConfig = { ...botConfig, ...config };
        
        // Disconnect existing bot if necessary
        if (bot && botConnected) {
            bot.quit();
            botConnected = false;
        }
        
        // Connect new bot
        connectBot(botConfig);
        res.json({ status: 'connecting', config: botConfig });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Get bot status
app.get('/status', (req, res) => {
    res.json({
        connected: botConnected,
        position: botPosition,
        health: botHealth,
        hunger: botHunger,
        inventory: botInventory
    });
});

// Move the bot
app.post('/move', (req, res) => {
    const { direction, distance } = req.body;
    
    if (!bot || !botConnected) {
        return res.status(400).json({ error: 'Bot not connected' });
    }
    
    try {
        switch (direction) {
            case 'forward':
                bot.setControlState('forward', true);
                setTimeout(() => {
                    bot.setControlState('forward', false);
                    res.json({ status: 'moved', direction });
                }, distance * 250);
                break;
            case 'backward':
                bot.setControlState('back', true);
                setTimeout(() => {
                    bot.setControlState('back', false);
                    res.json({ status: 'moved', direction });
                }, distance * 250);
                break;
            case 'left':
                bot.setControlState('left', true);
                setTimeout(() => {
                    bot.setControlState('left', false);
                    res.json({ status: 'moved', direction });
                }, distance * 250);
                break;
            case 'right':
                bot.setControlState('right', true);
                setTimeout(() => {
                    bot.setControlState('right', false);
                    res.json({ status: 'moved', direction });
                }, distance * 250);
                break;
            default:
                res.status(400).json({ error: 'Invalid direction' });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Jump
app.post('/jump', (req, res) => {
    if (!bot || !botConnected) {
        return res.status(400).json({ error: 'Bot not connected' });
    }
    
    try {
        bot.setControlState('jump', true);
        setTimeout(() => {
            bot.setControlState('jump', false);
            res.json({ status: 'jumped' });
        }, 500);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Attack (entity in front of the bot)
app.post('/attack', (req, res) => {
    if (!bot || !botConnected) {
        return res.status(400).json({ error: 'Bot not connected' });
    }
    
    try {
        const entity = bot.nearestEntity(e => e.type === 'mob');
        if (entity) {
            bot.attack(entity);
            res.json({ status: 'attacked', entity: entity.name });
        } else {
            res.json({ status: 'no target' });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Mine block (in front of the bot)
app.post('/mine', (req, res) => {
    if (!bot || !botConnected) {
        return res.status(400).json({ error: 'Bot not connected' });
    }
    
    try {
        // Look for blocks to mine within 4 blocks distance
        const block = bot.blockAtCursor(4); 
        
        // If no block is found, try looking for one
        if (!block || block.name === 'air') {
            // Try to find a better block to mine
            const targetBlock = findBlockToMine();
            
            if (targetBlock) {
                // Look at the block first
                bot.lookAt(targetBlock.position);
                
                // Dig the block
                bot.dig(targetBlock, (err) => {
                    if (err) {
                        console.error('Error mining block:', err);
                        res.status(500).json({ error: err.message });
                    } else {
                        console.log(`Successfully mined ${targetBlock.name}`);
                        res.json({ status: 'mined', block: targetBlock.name });
                    }
                });
                return;
            } else {
                // No blocks found to mine
                res.json({ status: 'no block' });
                return;
            }
        }
        
        // If we found a block, mine it
        console.log(`Mining block: ${block.name}`);
        bot.dig(block, (err) => {
            if (err) {
                console.error('Error mining block:', err);
                res.status(500).json({ error: err.message });
            } else {
                console.log(`Successfully mined ${block.name}`);
                res.json({ status: 'mined', block: block.name });
            }
        });
    } catch (err) {
        console.error('Error in /mine endpoint:', err);
        res.status(500).json({ error: err.message });
    }
});

// Place block
app.post('/place', (req, res) => {
    const { itemName } = req.body;
    
    if (!bot || !botConnected) {
        return res.status(400).json({ error: 'Bot not connected' });
    }
    
    try {
        const block = bot.blockAtCursor(4); // Look at block within 4 blocks distance
        if (block) {
            // Find the item in inventory
            const item = bot.inventory.items().find(item => item.name === itemName);
            if (item) {
                bot.equip(item, 'hand', err => {
                    if (err) {
                        res.status(500).json({ error: err.message });
                    } else {
                        bot.placeBlock(block, bot.entity.position.offset(0, 0, 1), err => {
                            if (err) {
                                res.status(500).json({ error: err.message });
                            } else {
                                res.json({ status: 'placed', block: itemName });
                            }
                        });
                    }
                });
            } else {
                res.json({ status: 'no item', itemName });
            }
        } else {
            res.json({ status: 'no block' });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Get blocks around bot
app.get('/blocks', (req, res) => {
    const { radius } = req.query;
    const blockRadius = parseInt(radius) || 3;
    
    if (!bot || !botConnected) {
        return res.status(400).json({ error: 'Bot not connected' });
    }
    
    try {
        const blocks = {};
        const pos = bot.entity.position;
        
        for (let x = -blockRadius; x <= blockRadius; x++) {
            for (let y = -blockRadius; y <= blockRadius; y++) {
                for (let z = -blockRadius; z <= blockRadius; z++) {
                    const block = bot.blockAt(pos.offset(x, y, z));
                    if (block && block.name !== 'air') {
                        if (!blocks[block.name]) {
                            blocks[block.name] = [];
                        }
                        blocks[block.name].push({
                            x: block.position.x,
                            y: block.position.y,
                            z: block.position.z
                        });
                    }
                }
            }
        }
        
        res.json({ blocks });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Run a raw Minecraft command
app.post('/command', (req, res) => {
    const { command } = req.body;
    
    if (!bot || !botConnected) {
        return res.status(400).json({ error: 'Bot not connected' });
    }
    
    try {
        bot.chat(`/${command}`);
        res.json({ status: 'command sent', command });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Start the server
app.listen(PORT, () => {
    console.log(`Minecraft Bot API running on http://localhost:${PORT}`);
    console.log('Use /connect to connect the bot to your Minecraft server');
});