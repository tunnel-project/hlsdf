import os
import requests
import base64
import json
import logging
from typing import List
import time
import re
import urllib.parse
import asyncio
import aiohttp
from telegram import Bot
from telegram.constants import ParseMode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
CHANNEL_NAME = "🍕 @Project_tunnel"

async def get_premium_configs():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://rentry.co/DailyV2ry/raw') as response:
            if response.status == 200:
                content = await response.text()
                return [line.strip() for line in content.split('\n') if line.strip().startswith(('vmess://', 'vless://', 'trojan://'))]
            else:
                logger.error(f"Failed to fetch premium configs: {response.status}")
                return []

def get_files_from_github(repo_url: str) -> List[str]:
    logger.info(f"Fetching files from GitHub repository: {repo_url}")
    api_url = f"https://api.github.com/repos/{repo_url}/contents"
    response = requests.get(api_url)
    if response.status_code == 200:
        contents = response.json()
        file_urls = [item['download_url'] for item in contents if item['name'].endswith('.txt')]
        logger.info(f"Found {len(file_urls)} txt files in the repository")
        return file_urls
    else:
        logger.error(f"Failed to fetch repository contents: {response.status}")
        return []

def extract_configs(file_urls: List[str]) -> List[str]:
    configs = []
    for url in file_urls:
        logger.info(f"Processing file: {url}")
        response = requests.get(url)
        if response.status_code == 200:
            content = response.text
            lines = content.split('\n')
            for line in lines:
                if line.startswith(('vmess://', 'vless://', 'trojan://')):
                    configs.append(line.strip())
    logger.info(f"Extracted a total of {len(configs)} configs")
    return configs

def modify_config(config: str) -> str:
    for prefix in ('vmess://', 'vless://', 'trojan://'):
        if config.startswith(prefix):
            if prefix == 'vmess://':
                try:
                    decoded = base64.b64decode(config[8:]).decode('utf-8')
                    json_config = json.loads(decoded)
                    json_config['ps'] = re.sub(r' - @\w+$', '', json_config.get('ps', ''))
                    json_config['ps'] = f"{json_config['ps']} - {CHANNEL_NAME}".strip()
                    return f"vmess://{base64.b64encode(json.dumps(json_config).encode()).decode()}"
                except:
                    logger.warning(f"Failed to modify vmess config: {config[:20]}...")
                    return config
            else:  # vless or trojan
                parsed = urllib.parse.urlparse(config)
                parsed = parsed._replace(fragment='')
                modified = parsed._replace(fragment=f"{CHANNEL_NAME}")
                return urllib.parse.urlunparse(modified)
    return config

async def send_configs_to_telegram(configs: List[str]):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        logger.error("Telegram bot token or channel ID not set")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    for i in range(0, len(configs), 6):
        batch = configs[i:i+6]
        message = "Latest Configs:\n\n"
        for config in batch:
            message += f"`{config}`\n\n"

        try:
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Sent batch of {len(batch)} configs to Telegram")
            await asyncio.sleep(2)  # 2-second delay between messages
        except Exception as e:
            logger.error(f"Failed to send configs to Telegram: {str(e)}")

    await bot.close()

async def main():
    repo_url = "Epodonios/v2ray-configs"

    logger.info("Starting Config Extractor")
    try:
        # Get premium configs first
        premium_configs = await get_premium_configs()
        modified_premium_configs = [modify_config(config) for config in premium_configs]

        # Get configs from GitHub repository
        file_urls = get_files_from_github(repo_url)
        configs = extract_configs(file_urls)
        modified_configs = [modify_config(config) for config in configs]

        # Combine configs, prioritizing premium ones
        all_configs = modified_premium_configs + modified_configs[:100]  # All premium configs + first 100 regular configs

        # Send configs to Telegram
        await send_configs_to_telegram(all_configs)
        
        logger.info(f"Successfully processed and sent {len(all_configs)} configs")
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())