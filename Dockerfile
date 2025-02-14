FROM python:3.9-alpine

# 安装系统依赖
RUN apk add --no-cache gcc musl-dev

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "blivedm_tg_bot.py"]