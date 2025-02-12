import os
import asyncio
import logging
from telegram import Bot
from blivedm import BLiveClient, BaseHandler, DanmakuMessage, GiftMessage, SuperChatMessage

# 从环境变量中读取配置
TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN', '')
TG_CHAT_ID = os.getenv('TG_CHAT_ID', '')
ROOM_IDS = os.getenv('TEST_ROOM_IDS', '').split(',')
SESSDATA = os.getenv('SESSDATA', '')

# 初始化 Telegram Bot
bot = Bot(token=TG_BOT_TOKEN)


class MyHandler(BaseHandler):
    """ 处理 B 站弹幕的自定义 Handler """

    async def _on_danmaku(self, client: BLiveClient, message: DanmakuMessage):
        """ 处理普通弹幕 """
        text = f"🎤 {message.uname}: {message.msg}"
        logging.info(text)
        await bot.send_message(chat_id=TG_CHAT_ID, text=text)

    async def _on_gift(self, client: BLiveClient, message: GiftMessage):
        """ 处理礼物消息 """
        text = f"🎁 {message.uname} 送出了 {message.num} 个 {message.gift_name}！"
        logging.info(text)
        await bot.send_message(chat_id=TG_CHAT_ID, text=text)

    async def _on_super_chat(self, client: BLiveClient, message: SuperChatMessage):
        """ 处理 Super Chat（SC）"""
        text = f"💰 SC - {message.uname} ¥{message.price}: {message.message}"
        logging.info(text)
        await bot.send_message(chat_id=TG_CHAT_ID, text=text)


async def run():
    """ 运行弹幕监听 """
    for room_id in ROOM_IDS:
        client = BLiveClient(room_id)
        handler = MyHandler()
        client.add_handler(handler)
        await client.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
