import time
import requests
import logging
import argparse
import os
import subprocess
import signal
import sys
import atexit
import random

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger("MiningBot")

class MiningBot:
    """A specialized bot focused on mining resources in Minecraft"""
    
    def __init__(self, js_server_url='http://localhost:3000', start_js_server=True, minecraft_username='MiningBot'):
        self.js_server_url = js_server_url
        self.js_server_process = None
        self.start_js_server = start_js_server
        self.minecraft_username = minecraft_username
        self.connected = False
        self.inventory = {}
        self.position = {'x': 0, 'y': 0, 'z': 0}
        self.blocks_mined = 0
        
        # Start the JS server if requested
        if self.start_js_server:
            self._start_js_server()
        
        # Register cleanup handler
        atexit.register(self.cleanup)
        
        # Connect to the Minecraft server
        self.connect()
    
    def _start_js_server(self):
        """Start the JavaScript server"""
        try:
            # Assumes the js file is in the same directory
            js_file_path = os.path.join(os.path.dirname(__file__), 'minecraft_bot.js')
            
            if not os.path.exists(js_file_path):
                logger.error(f"JavaScript file not found at {js_file_path}")
                return False
            
            logger.info("Starting JavaScript server...")
            self.js_server_process = subprocess.Popen(['node', js_file_path], 
                                                     stdout=subprocess.PIPE,
                                                     stderr=subprocess.PIPE)
            
            # Give the server time to start
            time.sleep(2)
            
            # Check if the server started successfully
            if self.js_server_process.poll() is not None:
                stdout, stderr = self.js_server_process.communicate()
                logger.error(f"Failed to start JavaScript server. Stdout: {stdout.decode()}, Stderr: {stderr.decode()}")
                return False
            
            logger.info("JavaScript server started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting JavaScript server: {e}")
            return False
    
    def connect(self):
        """Connect to the Minecraft server via the JavaScript bridge"""
        try:
            # Send connection request to the JS server
            response = requests.post(
                f"{self.js_server_url}/connect", 
                json={"username": self.minecraft_username}
            )
            
            # Check response
            if response.status_code == 200:
                logger.info("Connection request sent to JavaScript server")
                
                # Wait for the bot to connect (timeout after 20 seconds)
                max_attempts = 40
                for attempt in range(max_attempts):
                    status = self._get_status()
                    if status and status.get('connected', False):
                        logger.info("Connected to Minecraft server")
                        self.connected = True
                        self.inventory = status.get('inventory', {})
                        self.position = status.get('position', {'x': 0, 'y': 0, 'z': 0})
                        
                        # Give the bot some time to stabilize in the game
                        logger.info("Waiting for bot to stabilize in the game...")
                        time.sleep(3)
                        
                        # Let the world know we're here to mine!
                        self.run_command("say I'm a mining bot! Watch me work!")
                        
                        # Clear weather and set daytime for better visibility
                        self.run_command("weather clear")
                        self.run_command("time set day")
                        
                        return True
                    
                    logger.info(f"Waiting for connection... ({attempt+1}/{max_attempts})")
                    time.sleep(0.5)
                
                logger.error("Timed out waiting for connection")
                return False
            else:
                logger.error(f"Failed to send connection request: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to JavaScript server: {e}")
            return False
    
    def _get_status(self):
        """Get the current status from the JavaScript server"""
        try:
            response = requests.get(f"{self.js_server_url}/status")
            if response.status_code == 200:
                result = response.json()
                # Update our local state
                if result.get('connected', False):
                    self.inventory = result.get('inventory', {})
                    self.position = result.get('position', {'x': 0, 'y': 0, 'z': 0})
                return result
            else:
                logger.error(f"Failed to get status: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting status: {e}")
            return None
    
    def run_command(self, command):
        """Run a Minecraft command"""
        try:
            response = requests.post(
                f"{self.js_server_url}/command", 
                json={"command": command}
            )
            
            if response.status_code == 200:
                logger.info(f"Command executed: {command}")
                return True
            else:
                logger.error(f"Failed to execute command: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error executing command: {e}")
            return False
    
    def mine_block(self):
        """Mine a block"""
        try:
            response = requests.post(f"{self.js_server_url}/mine")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'mined':
                    block_type = result.get('block', 'unknown')
                    logger.info(f"Successfully mined {block_type}")
                    self.blocks_mined += 1
                    
                    # Announce every 5 blocks mined
                    if self.blocks_mined % 5 == 0:
                        self.run_command(f"say I've mined {self.blocks_mined} blocks so far!")
                    
                    # Update our inventory
                    self._get_status()
                    return True
                else:
                    logger.info("No suitable block found to mine")
                    return False
            else:
                logger.error(f"Failed to mine block: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error mining block: {e}")
            return False
    
    def move(self, direction, distance=1):
        """Move the bot in a specific direction"""
        try:
            response = requests.post(
                f"{self.js_server_url}/move", 
                json={"direction": direction, "distance": distance}
            )
            
            if response.status_code == 200:
                logger.info(f"Moved {direction} by {distance}")
                # Update our position
                self._get_status()
                return True
            else:
                logger.error(f"Failed to move: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error moving: {e}")
            return False
    
    def jump(self):
        """Make the bot jump"""
        try:
            response = requests.post(f"{self.js_server_url}/jump")
            
            if response.status_code == 200:
                logger.info("Jumped")
                return True
            else:
                logger.error(f"Failed to jump: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error jumping: {e}")
            return False
    
    def get_blocks_around(self, radius=3):
        """Get blocks in a radius around the player"""
        try:
            response = requests.get(
                f"{self.js_server_url}/blocks", 
                params={"radius": radius}
            )
            
            if response.status_code == 200:
                return response.json().get('blocks', {})
            else:
                logger.error(f"Failed to get blocks: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting blocks: {e}")
            return {}
    
    def teleport_to_resources(self):
        """Teleport the bot to an area with resources"""
        try:
            # First, check if there are resources nearby
            blocks = self.get_blocks_around(radius=10)
            has_resources = False
            
            for block_type, positions in blocks.items():
                if ('log' in block_type or 'stone' in block_type or 'ore' in block_type) and positions:
                    has_resources = True
                    break
            
            # If no resources nearby, teleport to a new location
            if not has_resources:
                logger.info("No resources found nearby. Teleporting to find resources...")
                
                # Get current position
                x, y, z = self.position.get('x', 0), self.position.get('y', 0), self.position.get('z', 0)
                
                # Generate a random offset (30-50 blocks away)
                dx = random.randint(30, 50) * (1 if random.random() > 0.5 else -1)
                dz = random.randint(30, 50) * (1 if random.random() > 0.5 else -1)
                
                # Teleport to new location
                new_x, new_z = x + dx, z + dz
                
                # Find a good Y level (look for highest block at the new XZ)
                self.run_command(f"execute in minecraft:overworld run tp {self.minecraft_username} {new_x} 150 {new_z}")
                time.sleep(1)  # Wait for the teleport to complete
                
                # Update our state
                self._get_status()
                
                # Announce teleport
                self.run_command("say Searching for resources in a new area!")
                
                return True
        except Exception as e:
            logger.error(f"Error teleporting to resources: {e}")
        
        return False
    
    def mine_continuously(self, duration_seconds=300):
        """Mine continuously for a specified duration"""
        logger.info(f"Starting continuous mining for {duration_seconds} seconds")
        
        if not self.connected:
            logger.error("Not connected to Minecraft server")
            return False
        
        start_time = time.time()
        actions_taken = 0
        self.blocks_mined = 0
        no_blocks_count = 0
        
        try:
            while time.time() - start_time < duration_seconds:
                # Try to mine a block
                if self.mine_block():
                    no_blocks_count = 0  # Reset the counter when successful
                else:
                    no_blocks_count += 1
                
                # If we couldn't find blocks to mine for several attempts,
                # try moving around or teleporting
                if no_blocks_count >= 5:
                    logger.info("Having trouble finding blocks to mine. Trying to move around...")
                    
                    # Try moving in random directions
                    for _ in range(3):
                        direction = ["forward", "backward", "left", "right"][random.randint(0, 3)]
                        self.move(direction)
                        self.jump()
                        time.sleep(0.5)
                    
                    # If still no luck after several attempts, teleport to a new area
                    if no_blocks_count >= 10:
                        self.teleport_to_resources()
                        no_blocks_count = 0
                
                # Move in a random direction occasionally
                if actions_taken % 5 == 0:
                    direction = ["forward", "backward", "left", "right"][random.randint(0, 3)]
                    self.move(direction)
                
                # Jump occasionally to get unstuck
                if actions_taken % 7 == 0:
                    self.jump()
                
                actions_taken += 1
                
                # Small delay between actions
                time.sleep(0.5)
                
                # Log progress
                if actions_taken % 20 == 0:
                    elapsed = time.time() - start_time
                    logger.info(f"Mining progress: {self.blocks_mined} blocks mined in {elapsed:.1f} seconds")
                    
        except KeyboardInterrupt:
            logger.info("Mining interrupted by user")
        except Exception as e:
            logger.error(f"Error during continuous mining: {e}")
        
        # Final stats
        total_time = time.time() - start_time
        logger.info(f"Mining completed: {self.blocks_mined} blocks mined in {total_time:.1f} seconds")
        
        if self.blocks_mined > 0:
            mining_rate = self.blocks_mined / total_time
            logger.info(f"Mining rate: {mining_rate:.2f} blocks per second")
            
            # Announce completion
            self.run_command(f"say Mining session complete! Mined {self.blocks_mined} blocks!")
        else:
            logger.info("No blocks were mined during this session")
            
            # Announce completion
            self.run_command("say Mining session complete, but I didn't find any blocks to mine!")
        
        return self.blocks_mined
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.connected:
                # Say goodbye
                self.run_command("say Mining bot signing off!")
                
            if self.js_server_process and self.js_server_process.poll() is None:
                logger.info("Shutting down JavaScript server...")
                self.js_server_process.terminate()
                self.js_server_process.wait(timeout=5)
                logger.info("JavaScript server shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down JavaScript server: {e}")


def main():
    parser = argparse.ArgumentParser(description='Minecraft Mining Bot')
    parser.add_argument('--username', type=str, default='MiningBot', help='Minecraft bot username')
    parser.add_argument('--duration', type=int, default=300, help='Mining duration in seconds')
    parser.add_argument('--server', type=str, default='http://localhost:3000', help='JavaScript server URL')
    parser.add_argument('--no-start-server', action='store_true', help='Don\'t start the JavaScript server (assume it\'s already running)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Minecraft Mining Bot")
    print("=" * 80)
    print(f"Bot will mine continuously for {args.duration} seconds")
    print("Press Ctrl+C to stop mining early")
    print("=" * 80)
    
    # Create and run the mining bot
    bot = MiningBot(
        js_server_url=args.server, 
        minecraft_username=args.username,
        start_js_server=not args.no_start_server
    )
    
    bot.mine_continuously(duration_seconds=args.duration)


if __name__ == "__main__":
    main()