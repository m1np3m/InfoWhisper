# Dùng image Python chính thức
FROM python:3.10-slim

# Cài đặt các thư viện hệ thống cần thiết
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Tạo thư mục làm việc
WORKDIR /app

# Sao chép file app và requirements.txt vào container
COPY UI.py /app/
COPY requirements.txt /app/

# Cài thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Chạy ứng dụng Streamlit
CMD ["streamlit", "run", "UI.py", "--server.port=8501", "--server.address=0.0.0.0"]
