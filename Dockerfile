# 使用 Python 作为基础镜像
FROM python:3.9

# 设置工作目录
WORKDIR /app

# 复制项目文件到容器中
COPY . .

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 容器启动时执行的命令
CMD ["python", "blivedm_tg_bot.py"]
