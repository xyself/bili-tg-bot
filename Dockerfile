# 使用 Python 3.12 作为基础镜像
FROM python:3.12-alpine

# 设置时区和 Python 环境
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

# 设置工作目录
WORKDIR /app

# 安装编译依赖
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    tzdata

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 删除不必要的编译依赖，减小镜像体积
RUN apk del gcc musl-dev python3-dev libffi-dev openssl-dev

# 复制项目文件
COPY blivedm ./blivedm
COPY blivedm_tg_bot.py .

# 创建日志目录并赋权
RUN mkdir -p /app/logs && chmod -R 777 /app/logs

# 设置日志目录为卷
VOLUME ["/app/logs"]

# 运行主程序
CMD ["python3", "blivedm_tg_bot.py"]
