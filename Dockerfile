# 使用 Python 3.12 作为基础镜像
FROM python:3.12-alpine

# 设置时区和Python环境
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

# 设置工作目录
WORKDIR /app

# 安装编译依赖并清理缓存
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    tzdata && \
    cp /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    # 安装 Python 依赖
    pip install --no-cache-dir -r requirements.txt && \
    # 清理不必要的文件和缓存
    find /usr/local/lib/python3.12/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python3.12/site-packages -name "__pycache__" -exec rm -r {} + 2>/dev/null || true && \
    rm -rf /root/.cache/pip/* && \
    # 删除临时构建依赖
    apk del gcc musl-dev python3-dev libffi-dev openssl-dev

# 复制项目文件（放在 requirements.txt 后面，可以利用 Docker 缓存机制）
COPY blivedm ./blivedm
COPY blivedm_tg_bot.py .

# 创建日志目录
RUN mkdir -p logs

# 设置日志目录为卷
VOLUME ["/app/logs"]

# 运行主程序
CMD ["python", "blivedm_tg_bot.py"]
