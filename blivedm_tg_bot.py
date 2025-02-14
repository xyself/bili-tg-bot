import os
import asyncio
import logging
from telegram import Bot
from blivedm import BLiveClient, BaseHandler, DanmakuMessage, GiftMessage, SuperChatMessage

# 从环境变量中读取配置
TG_BOT_TOKEN_ROOM = os.getenv('TG_BOT_TOKEN_ROOM', '')  # 房间机器人令牌
TG_BOT_TOKEN_DM = os.getenv('TG_BOT_TOKEN_DM', '')      # 弹幕机器人令牌
TG_CHAT_ID = os.getenv('TG_CHAT_ID', '')
ROOM_IDS = os.getenv('TEST_ROOM_IDS', '').split(',')
SESSDATA = os.getenv('SESSDATA', '')

# 初始化 Telegram Bot
room_bot = Bot(token=TG_BOT_TOKEN_ROOM)  # 房间机器人
dm_bot = Bot(token=TG_BOT_TOKEN_DM)      # 弹幕机器人

class MyHandler(BaseHandler):
    """ 处理 B 站弹幕的自定义 Handler """

    async def _on_danmaku(self, client: BLiveClient, message: DanmakuMessage):
        """ 处理普通弹幕 """
        text = f"🎤 {message.uname}: {message.msg}"
        logging.info(text)
        try:
            await dm_bot.send_message(chat_id=TG_CHAT_ID, text=text)  # 使用弹幕机器人发送消息
        except Exception as e:
            logging.error(f"发送弹幕消息失败: {e}")

    async def _on_gift(self, client: BLiveClient, message: GiftMessage):
        """ 处理礼物消息 """
        text = f"🎁 {message.uname} 送出了 {message.num} 个 {message.gift_name}！"
        logging.info(text)
        try:
            await dm_bot.send_message(chat_id=TG_CHAT_ID, text=text)  # 使用弹幕机器人发送消息
        except Exception as e:
            logging.error(f"发送礼物消息失败: {e}")

    async def _on_super_chat(self, client: BLiveClient, message: SuperChatMessage):
        """ 处理 Super Chat（SC）"""
        text = f"💰 SC - {message.uname} ¥{message.price}: {message.message}"
        logging.info(text)
        try:
            await dm_bot.send_message(chat_id=TG_CHAT_ID, text=text)  # 使用弹幕机器人发送消息
        except Exception as e:
            logging.error(f"发送 Super Chat 消息失败: {e}")

    async def _on_enter_room(self, client: BLiveClient):
        """ 处理进房消息 """
        text = "🎉 进入房间！"
        logging.info(text)
        try:
            await room_bot.send_message(chat_id=TG_CHAT_ID, text=text)  # 使用房间机器人发送消息
        except Exception as e:
            logging.error(f"发送进房消息失败: {e}")

async def run():
    """ 运行弹幕监听 """
    for room_id in ROOM_IDS:
        client = BLiveClient(room_id)
        handler = MyHandler()
        client.add_handler(handler)
        client.add_handler(handler._on_enter_room)  # 添加进房处理
        await client.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
