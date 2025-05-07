const fs = require('fs');

function parseShapedRecipe(recipePath) {
  try {
    const recipeData = JSON.parse(fs.readFileSync(recipePath, 'utf8'));
    if (recipeData.type === 'minecraft:crafting_shaped') {
      return recipeData;
    }
    return null;
  } catch (err) {
    console.error(`Error parsing shaped recipe ${recipePath}:`, err.message);
    return null;
  }
}

function parseShapelessRecipe(recipePath) {
  try {
    const recipeData = JSON.parse(fs.readFileSync(recipePath, 'utf8'));
    if (recipeData.type === 'minecraft:crafting_shapeless') {
      return recipeData;
    }
    return null;
  } catch (err) {
    console.error(`Error parsing shapeless recipe ${recipePath}:`, err.message);
    return null;
  }
}

function hasRequiredIngredients(recipe, inventory) {
  const requiredIngredients = getRequiredIngredients(recipe);
  for (const [item, count] of Object.entries(requiredIngredients)) {
    if (!inventory[item] || inventory[item] < count) {
      return false;
    }
  }
  return true;
}

function getRequiredIngredients(recipe) {
  const ingredients = {};
  
  // Tag mapping for common Minecraft tags
  const tagToItemMap = {
    'minecraft:oak_logs': 'oak_log',
    'minecraft:planks': 'oak_planks',
    'minecraft:logs': 'oak_log',
    'minecraft:stone_tool_materials': 'cobblestone'
  };
  
  if (recipe.type === 'minecraft:crafting_shaped') {
    const pattern = recipe.pattern;
    const key = recipe.key;
    
    for (const row of pattern) {
      for (const symbol of row) {
        if (symbol !== ' ') {
          const ingredient = key[symbol];
          let itemName;
          if (ingredient && ingredient.item) {
            itemName = ingredient.item.replace('minecraft:', '');
            console.log(`Debug: Resolved item ${ingredient.item} to ${itemName}`);
          } else if (ingredient && ingredient.tag) {
            itemName = tagToItemMap[ingredient.tag];
            if (!itemName) {
              console.warn(`Unsupported tag: ${ingredient.tag}`);
              continue;
            }
            console.log(`Debug: Resolved tag ${ingredient.tag} to ${itemName}`);
          } else {
            console.warn(`Invalid ingredient in recipe:`, ingredient);
            continue;
          }
          ingredients[itemName] = (ingredients[itemName] || 0) + 1;
        }
      }
    }
  } else if (recipe.type === 'minecraft:crafting_shapeless') {
    for (const ingredient of recipe.ingredients) {
      let itemName;
      if (ingredient && ingredient.item) {
        itemName = ingredient.item.replace('minecraft:', '');
        console.log(`Debug: Resolved item ${ingredient.item} to ${itemName}`);
      } else if (ingredient && ingredient.tag) {
        itemName = tagToItemMap[ingredient.tag];
        if (!itemName) {
          console.warn(`Unsupported tag: ${ingredient.tag}`);
          continue;
        }
        console.log(`Debug: Resolved tag ${ingredient.tag} to ${itemName}`);
      } else {
        console.warn(`Invalid ingredient in recipe:`, ingredient);
        continue;
      }
      ingredients[itemName] = (ingredients[itemName] || 0) + 1;
    }
  }
  
  console.log(`Debug: Final ingredients for recipe:`, ingredients);
  return ingredients;
}

function findCraftableRecipes(inventory) {
  const craftable = [];
  const recipeFiles = fs.readdirSync('./recipes').filter(file => file.endsWith('.json'));
  
  for (const file of recipeFiles) {
    const recipePath = `./recipes/${file}`;
    const shapedRecipe = parseShapedRecipe(recipePath);
    const shapelessRecipe = parseShapelessRecipe(recipePath);
    const recipe = shapedRecipe || shapelessRecipe;
    
    if (recipe && hasRequiredIngredients(recipe, inventory)) {
      const itemName = file.replace('.json', '');
      craftable.push(itemName);
    }
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