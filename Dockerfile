
FROM python:3.12-alpine as builder

WORKDIR /install
COPY requirements.txt .
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev git && \
    pip install --prefix=/install/deps -r requirements.txt

# 第二步：仅复制运行所需的部分
FROM python:3.12-alpine

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app
COPY --from=builder /install/deps /usr/local
COPY blivedm_tg_bot.py ./
COPY blivedm ./blivedm

RUN mkdir -p logs
VOLUME ["/app/logs"]

CMD ["python", "blivedm_tg_bot.py"]