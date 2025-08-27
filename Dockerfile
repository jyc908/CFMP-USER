# 使用官方 Python 3.11 的精简镜像，固定版本避免自动升级
FROM python:3.11.10-slim-bookworm

# 环境变量设置
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive


#COPY noble-security.gpg /etc/apt/trusted.gpg.d/
<<<<<<< HEAD
=======
RUN rm -rf /etc/apt/sources.list.d/* && \
    rm -f /etc/apt/sources.list
>>>>>>> 343b6be90b50ced013aeadb2782a2c7f5d0d816a

ADD sources.list /etc/apt/


# 安装系统依赖，支持 cryptography、Pillow、minio 等编译
RUN  apt-get update  && apt-get install -y \
  build-essential \
  libmariadb-dev-compat \
  libmariadb-dev \
  libjpeg-dev \
  zlib1g-dev \
  libffi-dev \
  libssl-dev \
  python3-dev \
  pkg-config \
  git \
  curl \
  rustc \
  cargo \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 拷贝 requirements.txt 并安装依赖
COPY requirements.txt .

RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
# 升级 pip 和安装构建工具
RUN python -m pip install --upgrade pip setuptools wheel

# 验证Python版本
RUN python --version && python -c "import sys; print(f'Python version: {sys.version}')"

RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
# 安装依赖包，使用缓存和更好的错误处理
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝项目源代码
COPY . .

# 端口暴露
EXPOSE 8000

# 启动命令
CMD ["daphne", "config.asgi:application", "--port", "8000", "--bind", "0.0.0.0"]
