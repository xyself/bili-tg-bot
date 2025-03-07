FROM python:3.9-alpine

WORKDIR /app

# 安装编译依赖
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 清理编译依赖
RUN apk del \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo

# 复制应用代码
COPY blivedm_tg_bot.py .

# 创建日志目录
RUN mkdir -p logs

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 设置时区
ENV TZ=Asia/Shanghai

# 运行应用
CMD ["python", "blivedm_tg_bot.py"]

   
