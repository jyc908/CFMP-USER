# 使用官方 Python 3.11 的精简镜像，固定版本避免自动升级
FROM python:3.11.10-slim-bookworm

# 环境变量设置和系统依赖安装
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 删除默认源并添加国内源，安装系统依赖，配置pip源，升级pip工具
RUN rm -rf /etc/apt/sources.list.d/* && \
    rm -f /etc/apt/sources.list && \
    cp /etc/apt/sources.list /etc/apt/sources.list.backup || true && \
    COPY sources.list /etc/apt/ && \
    apt-get update && apt-get install -y \
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
    && rm -rf /var/lib/apt/lists/* \
    && pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/ \
    && python -m pip install --upgrade pip setuptools wheel

# 设置工作目录
WORKDIR /app

# 拷贝 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝项目源代码
COPY . .

# 创建非root用户并设置权限
RUN useradd --create-home --shell /bin/bash django \
    && chown -R django:django /app

# 切换到非root用户
USER django

# 端口暴露和启动命令
EXPOSE 8000
CMD ["daphne", "config.asgi:application", "--port", "8000", "--bind", "0.0.0.0"]