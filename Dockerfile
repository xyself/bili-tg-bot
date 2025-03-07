# 第一阶段：构建阶段
FROM python:3.12-alpine AS builder

# 安装编译依赖并清理缓存
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev

WORKDIR /app

# 复制所有文件
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt && \
    # 安装本地的 blivedm
    pip install -e . && \
    find /usr/local/lib/python3.12/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python3.12/site-packages -name "__pycache__" -exec rm -r {} + && \
    rm -rf /root/.cache/pip/*

# 第二阶段：运行阶段
FROM python:3.12-alpine

# 设置时区和Python环境
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 复制所有必要的文件
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY blivedm ./blivedm
COPY blivedm_tg_bot.py .

RUN apk add --no-cache tzdata && \
    mkdir -p logs && \
    rm -rf /var/cache/apk/*

# 运行应用
CMD ["python", "blivedm_tg_bot.py"]
