# 使用官方 Python 3.11 的精简镜像，固定版本避免自动升级
FROM python:3.11.10-slim-bookworm

# 环境变量设置
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 删除默认源并添加国内源
RUN rm -rf /etc/apt/sources.list.d/* && \
    rm -f /etc/apt/sources.list
ADD sources.list /etc/apt/

# 更新包列表
RUN apt-get update -y

# 安装系统依赖
RUN apt-get install -y \
        build-essential \
        libmariadb-dev-compat \
        libmariadb-dev \
        libjpeg-dev \
        zlib1g-dev \
        libffi-dev \
        libssl-dev \
        python3-dev \
        pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 拷贝 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# 拷贝项目源代码（只复制必要的文件）
COPY config/ config/
COPY user/ user/
COPY manage.py .
COPY service_utils.py .

# 收集静态文件（如果需要）
# RUN python manage.py collectstatic --noinput --clear

# 创建非root用户并设置权限
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# 端口暴露
EXPOSE 8000

# 启动命令
CMD ["daphne", "config.asgi:application", "--port", "8000", "--bind", "0.0.0.0"]