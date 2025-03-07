   # 第一阶段：构建阶段
   FROM python:3.12-alpine AS builder

   RUN apk add --no-cache gcc musl-dev libffi-dev

   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # 第二阶段：运行阶段
   FROM python:3.12-alpine

   WORKDIR /app
   COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
   COPY . .

   CMD ["python", "blivedm_tg_bot.py"]
