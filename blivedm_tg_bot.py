import asyncio
import http.cookies
import os
import logging
import requests
from typing import Optional
from dotenv import load_dotenv
import aiohttp
import blivedm
import blivedm.models.web as web_models

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 读取配置
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ALT_TELEGRAM_BOT_TOKEN = os.getenv('ALT_TELEGRAM_BOT_TOKEN')  # 备用 Telegram 机器人
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ROOM_ID = os.getenv('ROOM_ID', '').split(',') if os.getenv('ROOM_ID') else []
SESSDATA = os.getenv('SESSDATA', '')

# 提前创建 logs 目录，避免每次写入时检查
os.makedirs('logs', exist_ok=True)


class MyHandler(blivedm.BaseHandler):
    def __init__(self):
        super().__init__()

    def _get_log_filename(self, prefix: str) -> str:
        """获取当天的日志文件名"""
        from datetime import datetime
        return f'logs/{prefix}_{datetime.now().strftime("%Y-%m-%d")}.log'

    def _write_log(self, prefix: str, content: str):
        """写入日志"""
        try:
            filename = self._get_log_filename(prefix)
            # 处理 emoji
            content = content.translate(str.maketrans('', '', '💬🎁🚢💎🚪🎮'))
            with open(filename, 'a', encoding='utf-8') as f:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f'[{timestamp}] {content}\n')
        except Exception as e:
            logger.error(f"写入日志失败: {e}")

    def _handle_message(self, prefix: str, content: str, tg_content: str, use_alt_bot=False):
        """统一处理消息：打印、记录日志、发送到 Telegram"""
        try:
            print(content)
            self._write_log(prefix, content)
            self.send_to_telegram(tg_content, use_alt_bot)
        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}")

    def send_to_telegram(self, message: str, use_alt_bot=False):
        """发送消息到 Telegram"""
        try:
            bot_token = ALT_TELEGRAM_BOT_TOKEN if use_alt_bot else TELEGRAM_BOT_TOKEN
            chat_id = TELEGRAM_CHAT_ID
            if not bot_token or not chat_id:
                return

            api_urls = [
                f"https://tgapi.chenguaself.tk/bot{bot_token}/sendMessage",
                f"https://api-proxy.me/telegram/bot{bot_token}/sendMessage",
                f"https://api.telegram.org/bot{bot_token}/sendMessage"
            ]
            data = {
                "chat_id": chat_id,
                "text": message.strip(),
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }

            for url in api_urls:
                for _ in range(3):
                    try:
                        response = requests.post(url, json=data, timeout=10)
                        response.raise_for_status()
                        return
                    except requests.RequestException:
                        asyncio.sleep(2)
        except Exception as e:
            logger.error(f"发送 Telegram 消息失败: {e}")

    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        """弹幕消息"""
        if not message.msg or not message.uname:
            return
        user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.uname}</a>'
        content = f'💬 [{client.room_id}] {message.uname}: {message.msg}'
        tg_content = f'💬 [{client.room_id}] {user_link}: {message.msg}'
        self._handle_message('danmaku', content, tg_content)

    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        """礼物消息"""
        if not message.gift_name or not message.uname:
            return
        user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.uname}</a>'
        content = f'🎁 [{client.room_id}] {message.uname} 赠送 {message.gift_name} x{message.num}'
        tg_content = f'🎁 [{client.room_id}] {user_link} 赠送 {message.gift_name} x{message.num}'
        self._handle_message('gift', content, tg_content)

    def _on_buy_guard(self, client: blivedm.BLiveClient, message: web_models.GuardBuyMessage):
        """上舰消息"""
        if not message.username:
            return
        user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.username}</a>'
        content = f'🚢 [{client.room_id}] {message.username} 购买 {message.gift_name}'
        tg_content = f'🚢 [{client.room_id}] {user_link} 购买 {message.gift_name}'
        self._handle_message('guard', content, tg_content)

    def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
        """SC（醒目留言）消息"""
        if not message.uname or not message.message:
            return
        user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.uname}</a>'
        content = f'💎 [{client.room_id}] SC￥{message.price} {message.uname}: {message.message}'
        tg_content = f'💎 [{client.room_id}] SC￥{message.price} {user_link}: {message.message}'
        self._handle_message('superchat', content, tg_content)

    def _on_interact_word(self, client: blivedm.BLiveClient, message: web_models.InteractWordMessage):
        """进房消息和互动消息"""
        if not message.username:
            return
            
        user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.username}</a>'
        
        if message.msg_type == 1:
            content = f'🚪 [{client.room_id}] {message.username} 进入房间'
            tg_content = f'🚪 [{client.room_id}] {user_link} 进入房间'
            self._handle_message('enter', content, tg_content, use_alt_bot=True)
        elif message.msg_type == 2:
            content = f'❤️ [{client.room_id}] {message.username} 关注了主播'
            tg_content = f'❤️ [{client.room_id}] {user_link} 关注了主播'
            self._handle_message('follow', content, tg_content, use_alt_bot=True)
        elif message.msg_type == 3:
            content = f'🔄 [{client.room_id}] {message.username} 分享了直播间'
            tg_content = f'🔄 [{client.room_id}] {user_link} 分享了直播间'
            self._handle_message('share', content, tg_content, use_alt_bot=True)
        elif message.msg_type == 4:
            content = f'⭐ [{client.room_id}] {message.username} 特别关注了主播'
            tg_content = f'⭐ [{client.room_id}] {user_link} 特别关注了主播'
            self._handle_message('special_follow', content, tg_content, use_alt_bot=True)
        elif message.msg_type == 5:
            content = f'🔄❤️ [{client.room_id}] {message.username} 与主播互粉了'
            tg_content = f'🔄❤️ [{client.room_id}] {user_link} 与主播互粉了'
            self._handle_message('mutual_follow', content, tg_content, use_alt_bot=True)
        elif message.msg_type == 6:
            content = f'👍 [{client.room_id}] {message.username} 为主播点赞了'
            tg_content = f'👍 [{client.room_id}] {user_link} 为主播点赞了'
            self._handle_message('like', content, tg_content, use_alt_bot=True)


async def main():
    async with aiohttp.ClientSession(cookies={'SESSDATA': SESSDATA}) as session:
        handler = MyHandler()
        clients = [blivedm.BLiveClient(int(room_id), session=session) for room_id in ROOM_ID]

        for client in clients:
            client.set_handler(handler)

        for client in clients:
            client.start()

        await asyncio.gather(*(client.join() for client in clients))


if __name__ == '__main__':
    asyncio.run(main())