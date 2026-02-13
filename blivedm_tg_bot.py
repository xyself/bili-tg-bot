import asyncio
import time
import os
import logging
from typing import Optional
from dotenv import load_dotenv
import aiohttp
import blivedm
import blivedm.models.web as web_models

# ================= 配置日志 =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# ================= 加载环境变量 =================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ALT_TELEGRAM_BOT_TOKEN = os.getenv('ALT_TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ROOM_ID = os.getenv('ROOM_ID', '').split(',') if os.getenv('ROOM_ID') else []
SESSDATA = os.getenv('SESSDATA', '')

os.makedirs('logs', exist_ok=True)

# ================= 异步 Telegram =================
async def send_telegram(session: aiohttp.ClientSession, message: str, use_alt_bot=False):
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
                async with session.post(url, json=data, timeout=10) as resp:
                    if resp.status == 200:
                        return
            except Exception:
                await asyncio.sleep(2)

# ================= 消息处理 =================
class MyHandler(blivedm.BaseHandler):

    def __init__(self, session: aiohttp.ClientSession):
        super().__init__()
        self.session = session

    # ---------------- 日志 ----------------
    def _get_log_filename(self, prefix: str) -> str:
        from datetime import datetime
        return f'logs/{prefix}_{datetime.now().strftime("%Y-%m-%d")}.log'

    def _write_log(self, prefix: str, content: str):
        try:
            filename = self._get_log_filename(prefix)
            content = content.translate(str.maketrans('', '', '💬🎁🚢💎🚪🎮❤️⭐🔄👍'))
            with open(filename, 'a', encoding='utf-8') as f:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f'[{timestamp}] {content}\n')
        except Exception as e:
            logger.error(f"写入日志失败: {e}")

    async def _handle_message(self, prefix: str, content: str, tg_content: str, use_alt_bot=False):
        try:
            print(content)
            self._write_log(prefix, content)
            await send_telegram(self.session, tg_content, use_alt_bot)
        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}")

    # ---------------- 覆盖 handle，处理额外互动消息 ----------------
    def handle(self, client, command):
        cmd = command.get('cmd', '')

        # 额外互动消息
        if cmd == 'LIKE_INFO_V3_CLICK':
            data = command.get('data', {})
            uname = data.get('uname') or '未知用户'
            uid = data.get('uid') or 0
            user_link = f'<a href="https://space.bilibili.com/{uid}">{uname}</a>'
            content = f'👍 [{client.room_id}] {uname} 点赞了直播间'
            tg_content = f'👍 [{client.room_id}] {user_link} 点赞了直播间'
            asyncio.create_task(self._handle_message('like', content, tg_content))
            return

        if cmd == 'LIKE_INFO_V3_UPDATE':
            # 总点赞更新，可忽略
            return

        # 父类处理标准消息
        super().handle(client, command)

    # ---------------- 弹幕/礼物/上舰/SC/互动 ----------------
    def _on_danmaku(self, client, message: web_models.DanmakuMessage):
        if not message.msg or not message.uname:
            return
        medal_info = f'[{message.medal_name}LV{message.medal_level}]' if message.medal_level else ''
        user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.uname}</a>'
        content = f'💬 [{client.room_id}] {medal_info} {message.uname}: {message.msg}'
        tg_content = f'💬 [{client.room_id}] {medal_info} {user_link}: {message.msg}'
        asyncio.create_task(self._handle_message('danmaku', content, tg_content))

    def _on_gift(self, client, message: web_models.GiftMessage):
        if not message.gift_name or not message.uname:
            return
        user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.uname}</a>'
        coin_display = f'{message.total_coin}{"金" if message.coin_type=="gold" else "银"}瓜子'
        content = f'🎁 [{client.room_id}] {message.uname} 赠送 {message.gift_name}x{message.num} ({coin_display})'
        tg_content = f'🎁 [{client.room_id}] {user_link} 赠送 {message.gift_name}x{message.num} ({coin_display})'
        asyncio.create_task(self._handle_message('gift', content, tg_content))

    def _on_user_toast_v2(self, client, message: web_models.UserToastV2Message):
        if message.source == 2 or not message.username:
            return
        guard_names = {1:'总督',2:'提督',3:'舰长'}
        guard_name = guard_names.get(message.guard_level,'舰长')
        user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.username}</a>'
        content = f'🚢 [{client.room_id}] {message.username} 开通了{guard_name} x{message.num}{message.unit}'
        tg_content = f'🚢 [{client.room_id}] {user_link} 开通了{guard_name} x{message.num}{message.unit}'
        asyncio.create_task(self._handle_message('guard', content, tg_content))

    def _on_super_chat(self, client, message: web_models.SuperChatMessage):
        if not message.uname or not message.message:
            return
        user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.uname}</a>'
        content = f'💎 [{client.room_id}] SC ¥{message.price} {message.uname}: {message.message}'
        tg_content = f'💎 [{client.room_id}] SC ¥{message.price} {user_link}: {message.message}'
        asyncio.create_task(self._handle_message('superchat', content, tg_content))

    def _on_interact_word_v2(self, client, message: web_models.InteractWordV2Message):
        if not message.username:
            return
        user_link = f'<a href="https://space.bilibili.com/{message.uid}">{message.username}</a>'
        msg_type_map = {
            1:('🚪','进入房间'),
            2:('❤️','关注了主播'),
            3:('🔄','分享了直播间'),
            4:('⭐','特别关注了主播'),
            5:('🔄❤️','与主播互粉了'),
            6:('👍','为主播点赞了')
        }
        emoji, action = msg_type_map.get(message.msg_type,('',''))
        if not emoji:
            return
        content = f'{emoji} [{client.room_id}] {message.username} {action}'
        tg_content = f'{emoji} [{client.room_id}] {user_link} {action}'
        use_alt = message.msg_type in [1,3]
        asyncio.create_task(self._handle_message('interact', content, tg_content, use_alt_bot=use_alt))

# ================= 多房间守护 + -352 风控 =================
async def run_forever(room_id: int, session: aiohttp.ClientSession, handler: MyHandler):
    cooldown_352 = 4 * 3600
    delay = 1.0
    max_delay = 60.0

    while True:
        client = blivedm.BLiveClient(room_id, session=session)
        client.set_handler(handler)

        try:
            logger.info(f'房间 {room_id} 启动监听')
            client.start()
            await client.join()
            delay = 1.0

        except aiohttp.ClientError as e:
            logger.error(f'房间 {room_id} Session 异常: {e}')
            await send_telegram(session, f'❌ 房间 {room_id} Session 异常，请检查 SESSDATA')
            return

        except Exception as e:
            # 处理 B 站 -352 风控
            if getattr(e, 'code', None) == -352:
                logger.warning(f'房间 {room_id} 遇到 -352 风控，冷却 4 小时')
                await send_telegram(session, f'⚠ 房间 {room_id} 遇到 -352 风控，4 小时后重试')
                await asyncio.sleep(cooldown_352)
            else:
                logger.error(f'房间 {room_id} 异常: {e}，{delay}s 后重连')
                await asyncio.sleep(delay)
                delay = min(delay * 2, max_delay)

        finally:
            client.stop()
            await asyncio.sleep(1)

# ================= main =================
async def main():
    async with aiohttp.ClientSession(cookies={'SESSDATA': SESSDATA}) as session:
        handler = MyHandler(session)
        tasks = []
        for room in ROOM_ID:
            room = room.strip()
            if not room:
                continue
            tasks.append(run_forever(int(room), session, handler))
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
