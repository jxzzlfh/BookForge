FROM python:3.9-slim

# 安装Calibre（必须的依赖）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    xz-utils \
    xdg-utils \
    libegl1 \
    libxkbcommon0 \
    libfontconfig \
    libgl1-mesa-glx \
    libopengl0 \
    libxcb-cursor0 \
    ca-certificates && \
    wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sh /dev/stdin && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建所需目录
RUN mkdir -p uploads converted downloads

# 暴露端口
EXPOSE 5000

# 启动应用
CMD ["python", "app.py"] 