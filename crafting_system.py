def craft_item(self, item_name):
    """Craft a specific item"""
    # Check if we have the resources to craft the item
    if not self.can_craft_item(item_name):
        logger.warning(f"Cannot craft {item_name}: Missing required resources")
        return False
    
    # Different crafting methods depending on the item
    if item_name == "crafting_table":
        if self.inventory.get("wooden_log", 0) >= 4:
            # Convert logs to planks first
            self.execute_command("recipe give @p minecraft:crafting_table")
            self.execute_command("replaceitem entity @p weapon.mainhand 4 minecraft:oak_planks")
            
            # Craft the item
            result = self.execute_command("execute as @p run loot spawn ~ ~ ~ loot minecraft:blocks/crafting_table")
            
            # Update inventory
            self.update_player_state()
            
            return "Result: 1 crafting_table" in result
    
    elif item_name == "wooden_pickaxe":
        if self.inventory.get("wooden_log", 0) >= 3 and self.inventory.get("stick", 0) >= 2:
            # Need a crafting table
            if not self.has_item_in_inventory("crafting_table"):
                if not self.craft_item("crafting_table"):
                    return False
            
            # Place the crafting table
            self.place_crafting_table()
            
            # Craft the wooden pickaxe
            self.execute_command("recipe give @p minecraft:wooden_pickaxe")
            
            # Simulate placing items in the crafting grid
            # This is a placeholder. In a real implementation, you would need to
            # interact with the crafting table GUI.
            
            # Update inventory
            self.update_player_state()
            
            return self.has_item_in_inventory("wooden_pickaxe")
    
    # Add more crafting recipes as needed
    
    logger.warning(f"Crafting recipe not implemented for {item_name}")
    return False

def can_craft_item(self, item_name):
    """Check if the player has the resources to craft a specific item"""
    if item_name == "crafting_table":
        return self.inventory.get("wooden_log", 0) >= 4
    
    elif item_name == "wooden_pickaxe":
        return (self.inventory.get("wooden_log", 0) >= 3 and 
                self.inventory.get("stick", 0) >= 2)
    
    elif item_name == "stone_pickaxe":
        return (self.inventory.get("cobblestone", 0) >= 3 and 
                self.inventory.get("stick", 0) >= 2)
    
    elif item_name == "iron_pickaxe":
        return (self.inventory.get("iron_ingot", 0) >= 3 and 
                self.inventory.get("stick", 0) >= 2)
    
    # Add more crafting recipes as needed
    
    return False

def place_crafting_table(self):
    """Place a crafting table near the player"""
    x, y, z = self.position
    command = f"setblock {x} {y} {z+1} minecraft:crafting_table"
    self.execute_command(command)
    return True

def smelt_item(self, input_item, output_item):
    """Smelt an item using a furnace"""
    # Check if we have the resources
    if self.inventory.get(input_item, 0) == 0:
        logger.warning(f"Cannot smelt {input_item}: Missing required resources")
        return False
    
    # Check if we have a furnace, or craft one
    if not self.has_item_in_inventory("furnace"):
        if self.inventory.get("cobblestone", 0) >= 8:
            if not self.craft_item("furnace"):
                return False
        else:
            logger.warning("Cannot craft furnace: Not enough cobblestone")
            return False
    
    # Place the furnace
    x, y, z = self.position
    furnace_pos = (x, y, z+1)
    command = f"setblock {furnace_pos[0]} {furnace_pos[1]} {furnace_pos[2]} minecraft:furnace"
    self.execute_command(command)
    
    # Add the item to smelt
    # This is a placeholder. In a real implementation, you would need to
    # interact with the furnace GUI.
    
    # Add fuel (assume we have some coal or wood)
    fuel = "coal" if self.inventory.get("coal", 0) > 0 else "wooden_log"
    if self.inventory.get(fuel, 0) == 0:
        logger.warning("Cannot smelt: No fuel available")
        return False
    
    # Simulate the smelting process
    # In a real implementation, you would need to wait for the smelting to complete
    logger.info(f"Smelting {input_item} into {output_item}...")
    time.sleep(5)  # Simulate waiting for the smelting to complete
    
    # Update inventory
    self.update_player_state()
    
    return self.has_item_in_inventory(output_item)

def manage_inventory(self):
    """Manage the player's inventory - craft tools when needed"""
    # Check if we need to craft basic tools
    if not self.has_item_in_inventory("wooden_pickaxe") and self.can_craft_item("wooden_pickaxe"):
        logger.info("Crafting wooden pickaxe")
        self.craft_item("wooden_pickaxe")
    
    if (not self.has_item_in_inventory("stone_pickaxe") and 
            self.inventory.get("cobblestone", 0) >= 3 and
            self.can_craft_item("stone_pickaxe")):
        logger.info("Crafting stone pickaxe")
        self.craft_item("stone_pickaxe")
    
    if (not self.has_item_in_inventory("iron_pickaxe") and 
            self.inventory.get("iron_ingot", 0) >= 3 and
            self.can_craft_item("iron_pickaxe")):
        logger.info("Crafting iron pickaxe")
        self.craft_item("iron_pickaxe")
    
    # Craft weapons
    if not self.has_item_in_inventory("wooden_sword") and self.can_craft_item("wooden_sword"):
        logger.info("Crafting wooden sword")
        self.craft_item("wooden_sword")
    
    # Craft food-related items if needed
    if self.inventory.get("raw_beef", 0) > 0 and not self.has_item_in_inventory("cooked_beef"):
        logger.info("Smelting raw beef into cooked beef")
        self.smelt_item("raw_beef", "cooked_beef")
    
    # Other inventory management tasks...