// recipeParser.js
const fs = require('fs');
const path = require('path');

/**
 * Parse a Minecraft shaped crafting recipe from a JSON file
 * @param {string} filePath - Path to the recipe JSON file
 * @returns {object|null} - Parsed recipe object or null if invalid
 */
function parseShapedRecipe(filePath) {
  try {
    const raw = fs.readFileSync(filePath);
    const data = JSON.parse(raw);
    if (data.type === 'minecraft:crafting_shaped') {
      return data;
    }
  } catch (err) {
    console.warn(`[Recipe Parser] ❌ Error parsing shaped recipe at ${filePath}: ${err.message}`);
  }
  return null;
}

/**
 * Parse a Minecraft shapeless crafting recipe from a JSON file
 * @param {string} filePath - Path to the recipe JSON file
 * @returns {object|null} - Parsed recipe object or null if invalid
 */
function parseShapelessRecipe(filePath) {
  try {
    const raw = fs.readFileSync(filePath);
    const data = JSON.parse(raw);
    if (data.type === 'minecraft:crafting_shapeless') {
      return data;
    }
  } catch (err) {
    console.warn(`[Recipe Parser] ❌ Error parsing shapeless recipe at ${filePath}: ${err.message}`);
  }
  return null;
}

/**
 * Check if all required ingredients for a recipe are present in the inventory
 * @param {object} recipe - Recipe object
 * @param {object} inventory - Inventory object with item counts
 * @returns {boolean} - True if all ingredients are available
 */
function hasRequiredIngredients(recipe, inventory) {
  // For shaped recipes
  if (recipe.type === 'minecraft:crafting_shaped') {
    const pattern = recipe.pattern;
    const key = recipe.key;
    
    // Count required items
    const required = {};
    for (const row of pattern) {
      for (const char of row) {
        if (char !== ' ') {
          const item = key[char];
          if (item && item.item) {
            const itemName = item.item.replace('minecraft:', '');
            required[itemName] = (required[itemName] || 0) + 1;
          }
        }
      }
    }
    
    // Check if all required items are in inventory
    for (const [itemName, count] of Object.entries(required)) {
      if (!inventory[itemName] || inventory[itemName] < count) {
        return false;
      }
    }
    return true;
  }
  
  // For shapeless recipes
  if (recipe.type === 'minecraft:crafting_shapeless') {
    const ingredients = recipe.ingredients;
    
    // Count required items
    const required = {};
    for (const ingredient of ingredients) {
      if (ingredient && ingredient.item) {
        const itemName = ingredient.item.replace('minecraft:', '');
        required[itemName] = (required[itemName] || 0) + 1;
      }
    }
    
    // Check if all required items are in inventory
    for (const [itemName, count] of Object.entries(required)) {
      if (!inventory[itemName] || inventory[itemName] < count) {
        return false;
      }
    }
    return true;
  }
  
  return false;
}

/**
 * Get a list of required ingredients for a recipe
 * @param {object} recipe - Recipe object
 * @returns {object} - Object with ingredient names and counts
 */
function getRequiredIngredients(recipe) {
  const required = {};
  
  // For shaped recipes
  if (recipe.type === 'minecraft:crafting_shaped') {
    const pattern = recipe.pattern;
    const key = recipe.key;
    
    for (const row of pattern) {
      for (const char of row) {
        if (char !== ' ') {
          const item = key[char];
          if (item && item.item) {
            const itemName = item.item.replace('minecraft:', '');
            required[itemName] = (required[itemName] || 0) + 1;
          }
        }
      }
    }
  }
  
  // For shapeless recipes
  if (recipe.type === 'minecraft:crafting_shapeless') {
    const ingredients = recipe.ingredients;
    
    for (const ingredient of ingredients) {
      if (ingredient && ingredient.item) {
        const itemName = ingredient.item.replace('minecraft:', '');
        required[itemName] = (required[itemName] || 0) + 1;
      }
    }
  }
  
  return required;
}

/**
 * Find all craftable recipes based on current inventory
 * @param {object} inventory - Inventory object with item counts
 * @param {string} recipesDir - Directory containing recipe JSON files
 * @returns {array} - Array of craftable recipe names
 */
function findCraftableRecipes(inventory, recipesDir = path.join(__dirname, 'recipes')) {
  const craftable = [];
  
  try {
    const files = fs.readdirSync(recipesDir);
    
    for (const file of files) {
      if (file.endsWith('.json')) {
        const filePath = path.join(recipesDir, file);
        const recipeName = file.replace('.json', '');
        
        // Try both shaped and shapeless
        const shaped = parseShapedRecipe(filePath);
        if (shaped && hasRequiredIngredients(shaped, inventory)) {
          craftable.push(recipeName);
          continue;
        }
        
        const shapeless = parseShapelessRecipe(filePath);
        if (shapeless && hasRequiredIngredients(shapeless, inventory)) {
          craftable.push(recipeName);
        }
      }
    }
  } catch (err) {
    console.warn(`[Recipe Parser] ❌ Error finding craftable recipes: ${err.message}`);
  }
  
  return craftable;
}

module.exports = {
  parseShapedRecipe,
  parseShapelessRecipe,
  hasRequiredIngredients,
  getRequiredIngredients,
  findCraftableRecipes
};