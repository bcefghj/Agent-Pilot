FROM python:3.11-slim

WORKDIR /app

# 系统依赖（slidev / pptx 渲染）
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates fonts-noto-cjk fontconfig \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Slidev for HTML PPT
RUN npm install -g @slidev/cli @slidev/theme-default 2>/dev/null || true

# Python 依赖
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 项目文件
COPY pilot /app/pilot
COPY pyproject.toml AGENTS.md README.md /app/
COPY data /app/data

# 默认端口
EXPOSE 8001 8002 8003

CMD ["python", "-m", "pilot", "all"]
