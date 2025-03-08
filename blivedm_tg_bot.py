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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8'  # 添加编码设置
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
        """写入日志，带重试机制"""
        max_retries = 3
        retry_delay = 1  # 初始重试延迟（秒）
        
        for attempt in range(max_retries):
            try:
                import os
                # 确保logs目录存在
                os.makedirs('logs', exist_ok=True)
                
                filename = self._get_log_filename(prefix)
                # 处理 emoji 和特殊字符
                content = content.encode('utf-8', errors='replace').decode('utf-8')
                
                with open(filename, 'a', encoding='utf-8', errors='replace') as f:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f'[{timestamp}] {content}\n')
                    f.flush()  # 立即刷新缓冲区
                    os.fsync(f.fileno())  # 确保写入磁盘
                return True  # 写入成功
            except Exception as e:
                if attempt == max_retries - 1:  # 最后一次尝试
                    logger.error(f"写入日志失败（已重试{max_retries}次）: {e}")
                    print(f"写入日志失败（已重试{max_retries}次）: {e}")
                else:
                    logger.warning(f"写入日志失败，正在重试（{attempt + 1}/{max_retries}）: {e}")
                    import time
                    time.sleep(retry_delay)
        return False  # 写入失败

    def _handle_message(self, prefix: str, content: str, tg_content: str, use_alt_bot=False):
        """统一处理消息：打印、记录日志、发送到Telegram"""
        try:
            # 1. 打印到控制台（确保使用正确的编码）
            print(content.encode('utf-8', errors='replace').decode('utf-8'))
            
            # 2. 写入日志（移除 emoji）
            log_content = content
            # 移除常见的 emoji
            emojis = ['💬', '🎁', '🚢', '💎', '🚪', '🎮']
            for emoji in emojis:
                log_content = log_content.replace(emoji, '')
            log_success = self._write_log(prefix, log_content.strip())
            if not log_success:
                logger.error(f"无法写入{prefix}日志")
            
            # 3. 发送到Telegram（保留 emoji）
            self.send_to_telegram(tg_content, use_alt_bot)
            
        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}")
            print(f"处理消息时发生错误: {e}")

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

            # 使用多个API地址，如果一个失败就尝试下一个
            api_urls = [
                f"https://tgapi.chenguaself.tk/bot{bot_token}/sendMessage",  # 你的 Cloudflare Workers 反代
                f"https://api-proxy.me/telegram/bot{bot_token}/sendMessage",
                f"https://api.telegram.org/bot{bot_token}/sendMessage"  # 官方 API（备用）
            ]

            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }

            # 添加增强的重试机制
            max_retries = 3
            retry_delay = 2  # 初始重试延迟（秒）

            for url in api_urls:
                retry_count = 0
                current_delay = retry_delay

                while retry_count < max_retries:
                    try:
                        response = requests.post(
                            url,
                            json=data,
                            timeout=10,  # 增加超时时间到30秒
                            headers={
                                'Connection': 'close',  # 避免连接复用问题
                                'User-Agent': 'BiliTgBot/1.0'  # 添加 User-Agent
                            }
                        )
                        response.raise_for_status()
                        logger.info(f"消息发送成功 (使用 {url})")
                        return  # 成功发送后直接返回
                    except requests.exceptions.RequestException as e:
                        retry_count += 1
                        if retry_count == max_retries:
                            logger.warning(f"使用 {url} 发送失败（已重试{max_retries}次）: {e}")
                            break  # 尝试下一个 URL
                        else:
                            logger.warning(f"发送消息失败，正在重试（{retry_count}/{max_retries}）: {e}")
                            import time
                            time.sleep(current_delay)
                            current_delay *= 2  # 指数退避

            # 如果所有 URL 都失败了
            logger.error("所有 Telegram API 地址均发送失败")

        except Exception as e:
            logger.error(f"发送消息到 Telegram 时发生未知错误: {e}")
            print(f"发送消息到 Telegram 时发生未知错误: {e}")

    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        """弹幕消息"""
        try:
            if not message.msg or not message.uname:
                return
            # 使用 HTML 格式，将用户名转换为可点击的链接
            user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.uname}</a>'
            # 确保消息内容使用正确的编码
            message_content = message.msg.encode('utf-8', errors='replace').decode('utf-8')
            tg_content = f'💬 [{client.room_id}] {user_link}: {message_content}'
            log_content = f'[{client.room_id}] {message.uname}: {message_content}'
            self._handle_message('danmaku', f'💬 {log_content}', tg_content)
        except Exception as e:
            logger.error(f"处理弹幕消息时发生错误: {e}")
            print(f"处理弹幕消息时发生错误: {e}")

    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        """礼物消息"""
        try:
            if not message.gift_name or not message.uname:
                return
            user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.uname}</a>'
            content = f'🎁 [{client.room_id}] {message.uname} 赠送 {message.gift_name} x{message.num}'
            tg_content = f'🎁 [{client.room_id}] {user_link} 赠送 {message.gift_name} x{message.num}'
            self._handle_message('gift', content, tg_content)
        except Exception as e:
            logger.error(f"处理礼物消息时发生错误: {e}")
            print(f"处理礼物消息时发生错误: {e}")

    def _on_buy_guard(self, client: blivedm.BLiveClient, message: web_models.GuardBuyMessage):
        """上舰消息"""
        try:
            if not message.username:
                return
            user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.username}</a>'
            content = f'🚢 [{client.room_id}] {message.username} 购买 {message.gift_name}'
            tg_content = f'🚢 [{client.room_id}] {user_link} 购买 {message.gift_name}'
            self._handle_message('guard', content, tg_content)
        except Exception as e:
            logger.error(f"处理上舰消息时发生错误: {e}")
            print(f"处理上舰消息时发生错误: {e}")

    def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
        """SC（醒目留言）消息"""
        try:
            if not message.uname or not message.message:
                return
            user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.uname}</a>'
            content = f'💎 [{client.room_id}] SC￥{message.price} {message.uname}: {message.message}'
            tg_content = f'💎 [{client.room_id}] SC￥{message.price} {user_link}: {message.message}'
            self._handle_message('superchat', content, tg_content)
        except Exception as e:
            logger.error(f"处理SC消息时发生错误: {e}")
            print(f"处理SC消息时发生错误: {e}")

    def _on_interact_word(self, client: blivedm.BLiveClient, message: web_models.InteractWordMessage):
        """进房消息（使用备用 bot 发送）"""
        try:
            if message.msg_type == 1:
                user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.username}</a>'
                content = f'🚪 [{client.room_id}] {message.username} 进入房间'
                tg_content = f'🚪 [{client.room_id}] {user_link} 进入房间'
                self._handle_message('enter', content, tg_content, use_alt_bot=True)
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
