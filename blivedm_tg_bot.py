import asyncio
import http.cookies
import os
import logging
import requests
from typing import *
from dotenv import load_dotenv
import aiohttp
import blivedm
import blivedm.models.web as web_models

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 读取配置
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # 默认 Telegram 机器人
ALT_TELEGRAM_BOT_TOKEN = os.getenv('ALT_TELEGRAM_BOT_TOKEN')  # 备用 Telegram 机器人（进房用）
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ROOM_ID = os.getenv('ROOM_ID', '').split(',') if os.getenv('ROOM_ID') else []
SESSDATA = os.getenv('SESSDATA', '')

session: Optional[aiohttp.ClientSession] = None

def init_session():
    cookies = http.cookies.SimpleCookie()
    cookies['SESSDATA'] = SESSDATA
    cookies['SESSDATA']['domain'] = 'bilibili.com'

    global session
    session = aiohttp.ClientSession()
    session.cookie_jar.update_cookies(cookies)

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
            import os
            # 确保logs目录存在
            os.makedirs('logs', exist_ok=True)
            
            filename = self._get_log_filename(prefix)
            with open(filename, 'a', encoding='utf-8') as f:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f'[{timestamp}] {content}\n')
        except Exception as e:
            logger.error(f"写入日志失败: {e}")
            print(f"写入日志失败: {e}")

    def send_to_telegram(self, message: str, use_alt_bot=False):
        """发送消息到 Telegram，use_alt_bot=True 时使用备用 bot"""
        try:
            bot_token = ALT_TELEGRAM_BOT_TOKEN if use_alt_bot else TELEGRAM_BOT_TOKEN
            chat_id = TELEGRAM_CHAT_ID

            if not all([bot_token, chat_id]):
                logger.error("Telegram配置不完整，跳过发送")
                return

            message = str(message).strip()
            if not message:
                logger.warning("消息内容为空，跳过发送")
                return

            url = f"https://api-proxy.me/telegram/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }

            # 添加重试机制
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = requests.post(url, json=data, timeout=10)  # 添加超时设置
                    response.raise_for_status()
                    logger.info("消息发送成功")
                    break
                except requests.exceptions.RequestException as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        logger.error(f"发送消息到 Telegram 失败（已重试{max_retries}次）: {e}")
                    else:
                        logger.warning(f"发送消息失败，正在重试（{retry_count}/{max_retries}）: {e}")
                        import time
                        time.sleep(1)  # 重试前等待1秒

        except Exception as e:
            logger.error(f"发送消息到 Telegram 时发生未知错误: {e}")

    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        """弹幕消息"""
        try:
            if not message.msg or not message.uname:
                return
            # 使用 HTML 格式，将用户名转换为可点击的链接
            user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.uname}</a>'
            content = f'💬 [{client.room_id}] {user_link}: {message.msg}'
            log_content = f'[{client.room_id}] {message.uname}: {message.msg}'  # 日志内容不包含HTML标签
            print(f'💬 {log_content}')  # 控制台输出
            self._write_log('danmaku', log_content)  # 写入日志
            self.send_to_telegram(content)
        except Exception as e:
            logger.error(f"处理弹幕消息时发生错误: {e}")
            print(f"处理弹幕消息时发生错误: {e}")

    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        """礼物消息"""
        if not message.gift_name or not message.uname:
            return
        content = f'🎁 [{client.room_id}] {message.uname} 赠送 {message.gift_name} x{message.num}'
        print(content)
        self.send_to_telegram(content)

    def _on_buy_guard(self, client: blivedm.BLiveClient, message: web_models.GuardBuyMessage):
        """上舰消息"""
        if not message.username:
            return
        content = f'🚢 [{client.room_id}] {message.username} 购买 {message.gift_name}'
        print(content)
        self.send_to_telegram(content)

    def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
        """SC（醒目留言）消息"""
        if not message.uname or not message.message:
            return
        content = f'💎 [{client.room_id}] SC￥{message.price} {message.uname}: {message.message}'
        print(content)
        self.send_to_telegram(content)

    def _on_interact_word(self, client: blivedm.BLiveClient, message: web_models.InteractWordMessage):
        """进房消息（使用备用 bot 发送）"""
        try:
            if message.msg_type == 1:
                user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.username}</a>'
                content = f'🚪 [{client.room_id}] {user_link} 进入房间'
                log_content = f'[{client.room_id}] {message.username} 进入房间'  # 日志内容不包含HTML标签
                print(f'🚪 {log_content}')  # 控制台输出
                self._write_log('enter', log_content)  # 写入日志
                self.send_to_telegram(content, use_alt_bot=True)
        except Exception as e:
            logger.error(f"处理进房消息时发生错误: {e}")
            print(f"处理进房消息时发生错误: {e}")

async def main():
    if not ROOM_ID:
        logger.error("请设置ROOM_ID环境变量")
        return

    try:
        init_session()
        handler = MyHandler()
        clients = [blivedm.BLiveClient(int(room_id), session=session) for room_id in ROOM_ID]

        for client in clients:
            client.set_handler(handler)

        handler.send_to_telegram(f"🎮 开始监控直播间: {', '.join(ROOM_ID)}")

        for client in clients:
            client.start()

        await asyncio.gather(*(client.join() for client in clients))
    except Exception as e:
        logger.error(f"程序运行时发生错误: {e}")
        print(f"程序运行时发生错误: {e}")
    finally:
        if session:
            await session.close()

if __name__ == '__main__':
    asyncio.run(main())
