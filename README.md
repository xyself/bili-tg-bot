# B站直播弹幕Telegram转发机器人

基于[blivedm](https://github.com/xfgryujk/blivedm)开发的B站直播弹幕转发到Telegram的机器人。

## 使用说明

本项目使用blivedm库获取B站直播弹幕，支持将弹幕、礼物、上舰等消息转发到Telegram频道。

### 依赖

项目通过git依赖安装blivedm库，无需手动管理blivedm代码：

```bash
pip install -r requirements.txt
```

### 环境变量

请配置以下环境变量：

- `TELEGRAM_BOT_TOKEN`: Telegram机器人token
- `TELEGRAM_CHAT_ID`: 接收消息的Telegram频道ID
- `ALT_TELEGRAM_BOT_TOKEN`: 备用Telegram机器人token（可选）
- `ROOM_ID`: B站直播间ID，多个ID用逗号分隔
- `SESSDATA`: B站登录cookie中的SESSDATA值（可选）

### 运行

```bash
python blivedm_tg_bot.py
```

### Docker部署

```bash
docker-compose up -d
```

### 系统要求

- Python 3.8 或更高版本
