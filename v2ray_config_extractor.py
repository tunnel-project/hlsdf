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
from telegram.error import RetryAfter, TimedOut
from io import BytesIO
import yaml
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
CHANNEL_NAME = "🍕 @Project_tunnel"

async def get_vless_vmess_configs():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://rentry.co/DailyV2ry/raw') as response:
            if response.status == 200:
                content = await response.text()
                return [line.strip() for line in content.split('\n') if line.strip().startswith(('vmess://', 'vless://'))]
            else:
                logger.error(f"Failed to fetch VLESS/VMESS configs: {response.status}")
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
                    json_config['ps'] = f"Vless|Vmess🍕 @Project_tunnel\n{CHANNEL_NAME}"
                    return f"vmess://{base64.b64encode(json.dumps(json_config).encode()).decode()}"
                except:
                    logger.warning(f"Failed to modify vmess config: {config[:20]}...")
                    return f"{config}\n{CHANNEL_NAME}"
            elif prefix == 'vless://':
                parsed = urllib.parse.urlparse(config)
                parsed = parsed._replace(fragment='')
                modified = parsed._replace(fragment=f"Vless|Vmess🍕 @Project_tunnel\n{CHANNEL_NAME}")
                return urllib.parse.urlunparse(modified)
            else:  # ss
                parsed = urllib.parse.urlparse(config)
                parsed = parsed._replace(fragment='')
                modified = parsed._replace(fragment=f"Shadow🍕 @Project_tunnel\n{CHANNEL_NAME}")
                return urllib.parse.urlunparse(modified)
    return f"{config}\n{CHANNEL_NAME}"

def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

async def send_telegram_message(bot: Bot, chat_id: str, text: str, parse_mode: ParseMode = None, retry_count: int = 0):
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    except RetryAfter as e:
        if retry_count < 5:
            logger.warning(f"Rate limited. Waiting for {e.retry_after} seconds.")
            await asyncio.sleep(e.retry_after)
            return await send_telegram_message(bot, chat_id, text, parse_mode, retry_count + 1)
        else:
            logger.error("Max retries reached. Skipping message.")
    except TimedOut:
        if retry_count < 5:
            logger.warning("Request timed out. Retrying...")
            await asyncio.sleep(3)
            return await send_telegram_message(bot, chat_id, text, parse_mode, retry_count + 1)
        else:
            logger.error("Max retries reached. Skipping message.")
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")


async def send_configs_to_telegram(configs: List[str]):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        logger.error("Telegram bot token or channel ID not set")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    vless_vmess_configs = []
    ss_configs = []

    for i in range(0, len(configs), 6):
        batch = configs[i:i+6]
        message = "🍕 جدیدترین کانفیگها:\n\n"
        message += "```\n"
        for config in batch:
            message += f"{config}\n"
            if config.startswith(('vmess://', 'vless://')):
                vless_vmess_configs.append(config)
            elif config.startswith('ss://'):
                ss_configs.append(config)
        message += "```\n"
        message += f"\n{CHANNEL_NAME}"  # Add channel name outside of the code block

        await send_telegram_message(bot, TELEGRAM_CHANNEL_ID, message, ParseMode.MARKDOWN)
        logger.info(f"Sent batch of {len(batch)} configs to Telegram")

        # Reduced delay to avoid flood control
        await asyncio.sleep(2.5)  # 2.5-second delay between messages

    # Send vless and vmess configs file
    await send_config_file(bot, vless_vmess_configs, "vless_vmess_configs.txt")

    # Send shadowsocks configs file
    await send_config_file(bot, ss_configs, "shadow_socks_configs.txt")

    # Send the final message
    final_message = """سلام رفقا! 🌟

به کانال خودتون خوش اومدید! اینجا هر 12 ساعت کانفیگ‌های جدید و رایگان V2ray رو براتون می‌ذاریم تا همیشه به‌روز باشید. 😎

کانفیگ هارو ربات برای شما جمع میکنه.

همچنین، کانفیگ‌های VLESS/VMESS و Shadowsocks رو در فایل‌های جداگانه براتون آپلود کردیم تا دسترسی بهشون راحت‌تر باشه. 📄

لطفاً روی هر کانفیگ نظر بدید و بگید چطوره تا بتونیم بهترین‌ها رو براتون فراهم کنیم. 📝

✳️ پیشنهاد میکنیم از #فایل استفاده کنید.

✳️ رفقا حتما کانفیگ ها رو به اشتراک بذارید. اینجوری ما دلگرم میشیم و قطعا سرورهای بیشتری رو براتون درست میکنیم.

✳️ همینطور نظرات و پیشنهاداتتون رو با لینک زیر بفرمایید.
https://t.me/HarfinoBot?start=78ea88f6137d0ce

✳️ اعضا به ۲۰۰۰ برسه براتون دامین میگیرم و لینک سابمون رو هم راه میندازیم."""

    final_message += f"\n\n{CHANNEL_NAME}"  # Add channel name at the end of the final message
        
    await asyncio.sleep(3)  # Add a delay before sending the final message
    await send_telegram_message(bot, TELEGRAM_CHANNEL_ID, final_message)
    logger.info("Sent final message to Telegram")

    await bot.close()

async def send_config_file(bot: Bot, configs: List[str], filename: str, retry_count: int = 0):
    config_text = "\n".join([f"{config}\n{CHANNEL_NAME}" for config in configs])
    file_obj = BytesIO(config_text.encode('utf-8'))
    file_obj.name = filename

    try:
        caption = f"Config file: {filename} #فایل\n{CHANNEL_NAME}"
        await bot.send_document(chat_id=TELEGRAM_CHANNEL_ID, document=file_obj, caption=caption)
        logger.info(f"Sent config file {filename} to Telegram with #فایل caption")
        await asyncio.sleep(3)  # Add a delay after sending the file
    except RetryAfter as e:
        if retry_count < 5:
            logger.warning(f"Rate limited. Waiting for {e.retry_after} seconds.")
            await asyncio.sleep(e.retry_after)
            return await send_config_file(bot, configs, filename, retry_count + 1)
        else:
            logger.error("Max retries reached. Skipping file send.")
    except TimedOut:
        if retry_count < 5:
            logger.warning("Request timed out. Retrying...")
            await asyncio.sleep(3)
            return await send_config_file(bot, configs, filename, retry_count + 1)
        else:
            logger.error("Max retries reached. Skipping file send.")
    except Exception as e:
        logger.error(f"Failed to send config file to Telegram: {str(e)}")

async def main():
    logger.info("Starting Config Extractor")
    try:
        # Get VLESS and VMESS configs
        vless_vmess_configs = await get_vless_vmess_configs()
        modified_vless_vmess_configs = [modify_config(config) for config in vless_vmess_configs]

        # Get Shadowsocks configs
        ss_configs = get_shadowsocks_configs()
        modified_ss_configs = [modify_config(config) for config in ss_configs]

        # Combine all configs
        all_configs = modified_vless_vmess_configs + modified_ss_configs

        # Randomly shuffle the combined configs
        random.shuffle(all_configs)

        # Send configs to Telegram
        await send_configs_to_telegram(all_configs)
        
        logger.info(f"Successfully processed and sent {len(all_configs)} configs")
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())