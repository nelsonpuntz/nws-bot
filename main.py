import requests
import time
from datetime import datetime
import hashlib
from bs4 import BeautifulSoup
import traceback
import os

class NWSDiscordBot:
    def __init__(self, webhook_url):
        self.url = "https://forecast.weather.gov/product.php?site=BOU&issuedby=BOU&product=AFD&format=ci&version=1&glossary=1"
        self.webhook_url = webhook_url
        self.last_hash = None
        self.error_count = 0
        self.last_success = None
        
    def get_forecast_discussion(self):
        """Fetch and parse the NWS forecast discussion."""
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            # Find the specific section
            discussion = soup.find(class_="glossaryProduct")
            
            if discussion:
                self.error_count = 0  # Reset error count on success
                self.last_success = datetime.now()
                return discussion.get_text().strip()
            else:
                print("Could not find discussion section")
                self.error_count += 1
                return None
            
        except Exception as e:
            print(f"Error fetching forecast: {e}")
            print(traceback.format_exc())
            self.error_count += 1
            return None
    
    def calculate_hash(self, content):
        """Calculate MD5 hash of content to detect changes."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def send_discord_message(self, content):
        """Send message to Discord webhook."""
        # Split content if it exceeds Discord's 2000 character limit
        chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]
        
        for chunk in chunks:
            message = {
                "content": f"```{chunk}```",
                "username": "NWS Denver Forecast Bot"
            }
            
            try:
                response = requests.post(
                    self.webhook_url,
                    json=message,
                    timeout=30
                )
                response.raise_for_status()
                
            except Exception as e:
                print(f"Error sending to Discord: {e}")
                print(traceback.format_exc())
                self.error_count += 1

    def should_restart(self):
        """Check if bot should restart based on errors or time since last success."""
        if self.error_count >= 5:
            return True
        if self.last_success and (datetime.now() - self.last_success).seconds > 3600:  # 1 hour
            return True
        return False
    
    def run(self):
        """Main loop to check for updates."""
        check_interval = 300  # 5 minutes
        
        while True:
            try:
                print("\nStarting NWS Forecast Discussion monitor...")
                self.error_count = 0
                self.last_success = datetime.now()
                
                while not self.should_restart():
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{current_time}] Checking for updates...")
                    
                    content = self.get_forecast_discussion()
                    if content:
                        current_hash = self.calculate_hash(content)
                        
                        if self.last_hash is None:
                            print("Initial forecast loaded")
                            self.last_hash = current_hash
                            self.send_discord_message("Bot started. Current forecast:\n\n" + content)
                        
                        elif current_hash != self.last_hash:
                            print("New forecast detected!")
                            self.last_hash = current_hash
                            self.send_discord_message("New forecast update:\n\n" + content)
                    
                    time.sleep(check_interval)
                
                print("Restarting bot due to errors or timeout...")
                time.sleep(60)  # Wait a minute before restarting
                
            except Exception as e:
                print(f"Critical error in main loop: {e}")
                print(traceback.format_exc())
                time.sleep(60)  # Wait a minute before restarting

if __name__ == "__main__":
    # Get webhook URL from environment variable
    WEBHOOK_URL = "https://discord.com/api/webhooks/1328155097213173811/_Bj1431zkj8qSqZgMuv5Uche2368UhC7oCaB7u-rVPNT_MCwY-gdF7-St5CBPFFnfx9_"
    
    while True:
        try:
            bot = NWSDiscordBot(WEBHOOK_URL)
            bot.run()
        except Exception as e:
            print(f"Bot crashed: {e}")
            print(traceback.format_exc())
            time.sleep(60)  # Wait a minute before restarting
