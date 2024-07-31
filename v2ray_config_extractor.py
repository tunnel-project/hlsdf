import os
import requests
import base64
import json
import logging
from typing import List
import asyncio
import aiohttp
from telegram import Bot
import urllib.parse
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TimedOut
from io import BytesIO
import yaml
import random
import jdatetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
CHANNEL_NAME = "🚀 @Project_tunnel"

async def get_configs(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.text()
                return [line.strip() for line in content.split('\n') if line.strip().startswith(('vmess://', 'vless://', 'ss://'))]
            else:
                logger.error(f"Failed to fetch configs from {url}: {response.status}")
                return []

def get_shadowsocks_configs():
    response = requests.get('https://raw.githubusercontent.com/AzadNetCH/Clash/main/AzadNet_META_IRAN-Direct.yml')
    if response.status_code == 200:
        try:
            yaml_content = yaml.safe_load(response.text)
            proxies = yaml_content.get('proxies', [])
            ss_configs = []
            for proxy in proxies:
                if proxy['type'] == 'ss':
                    cipher = proxy['cipher']
                    password = proxy['password']
                    server = proxy['server']
                    port = proxy['port']
                    name = proxy['name']
                    
                    user_info = base64.b64encode(f"{cipher}:{password}".encode()).decode()
                    ss_url = f"ss://{user_info}@{server}:{port}#{urllib.parse.quote(name)}"
                    ss_configs.append(ss_url)
            return ss_configs
        except Exception as e:
            logger.error(f"Failed to parse Shadowsocks configs: {str(e)}")
            return []
    else:
        logger.error(f"Failed to fetch Shadowsocks configs: {response.status_code}")
        return []

def modify_config(config: str) -> str:
    for prefix in ('vmess://', 'vless://', 'ss://'):
        if config.startswith(prefix):
            if prefix == 'vmess://':
                try:
                    decoded = base64.b64decode(config[8:]).decode('utf-8')
                    json_config = json.loads(decoded)
                    json_config['ps'] = CHANNEL_NAME
                    return f"vmess://{base64.b64encode(json.dumps(json_config).encode()).decode()}"
                except:
                    logger.warning(f"Failed to modify vmess config: {config[:20]}...")
                    return config
            else:  # vless or ss
                parsed = urllib.parse.urlparse(config)
                parsed = parsed._replace(fragment='')
                modified = parsed._replace(fragment=CHANNEL_NAME)
                return urllib.parse.urlunparse(modified)
    return config

async def send_config_file(bot: Bot, configs: List[str], filename: str, config_type: str):
    config_text = "\n".join(configs)
    file_obj = BytesIO(config_text.encode('utf-8'))
    file_obj.name = filename

    try:
        jalali_date = jdatetime.datetime.now().strftime("%Y/%m/%d")
        caption = f"{filename} \n 🌀 {config_type} \n 🌀 Date: {jalali_date}\n\n"
        caption += "آموزش اتصال: فایل کانفیگ را باز کنید و سپس کل محتوا را کپی کنید. "
        caption += "سپس وارد hiddify next یا اپ مربوط در ios شوید و import from clipboard را بزنید.\n\n"
        caption += "#vpn #v2ray \n 🍪 @Project_Tunnel"

        await bot.send_document(chat_id=TELEGRAM_CHANNEL_ID, document=file_obj, caption=caption)
        logger.info(f"Sent config file {filename} to Telegram")
        await asyncio.sleep(3)  # Add a delay after sending the file
    except Exception as e:
        logger.error(f"Failed to send config file to Telegram: {str(e)}")

async def main():
    logger.info("Starting Config Extractor")
    try:
        all_configs = []
        SUBSCRIPTION_LINKS = [
            'https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/V2RAY_SUB.txt',
            'https://rentry.co/DailyV2ry/raw',
            "https://raw.githubusercontent.com/Falconchi/falconchi4/main/argo_vpnn4"
        ]
        for sub in SUBSCRIPTION_LINKS:
            all_configs += await get_configs(sub)
        # Combine and modify all configs
        ss_configs = get_shadowsocks_configs()

        # Combine and modify all configs
        all_configs += ss_configs
        modified_configs = [modify_config(config) for config in all_configs]

        # Separate configs by type
        vless_configs = [c for c in modified_configs if c.startswith('vless://')]
        vmess_configs = [c for c in modified_configs if c.startswith('vmess://')]
        ss_configs = [c for c in modified_configs if c.startswith('ss://')]

        # Randomly shuffle each config type
        random.shuffle(vless_configs)
        random.shuffle(vmess_configs)
        random.shuffle(ss_configs)

        # Initialize bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN)

        # Send config files
        await send_config_file(bot, vless_configs, "butterflies.txt", "VLESS")
        await send_config_file(bot, vmess_configs, "and.txt", "VMESS")
        await send_config_file(bot, ss_configs, "hurricanes.txt", "Shadowsocks")

        await bot.close()
        
        logger.info(f"Successfully processed and sent {len(all_configs)} configs")
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())