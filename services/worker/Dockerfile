FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
# Copy application code
COPY app/ ./app/

# 暴露端口
# Expose port
EXPOSE 8001

# 启动应用
# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
