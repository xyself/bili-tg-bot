# 第一阶段：构建阶段
FROM python:3.12-alpine AS builder

# 安装编译依赖
RUN apk add --no-cache \
    gcc \
    musl-dev

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 第二阶段：运行阶段
FROM python:3.12-alpine

# 设置时区和Python环境
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 只复制必要的Python包
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# 复制应用代码
COPY blivedm_tg_bot.py .

# 创建日志目录
RUN mkdir -p logs

# 运行应用
CMD ["python", "blivedm_tg_bot.py"]
