FROM python:3.11-slim

WORKDIR /app

# 包含main.py requirements.txt等
COPY . .

# 安装依赖工具、 Nuitka 和你项目需要的依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    zlib1g-dev \
    patchelf \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install nuitka psutil \
    && pip install -r requirements.txt

CMD ["nuitka", "--onefile", "--standalone", "--show-progress", "main.py"]
