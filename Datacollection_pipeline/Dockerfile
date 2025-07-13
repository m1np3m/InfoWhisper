FROM apache/airflow:2.9.2

USER root

# Cài đặt các gói phụ thuộc hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    # Dependencies for Playwright chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libxcb1 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Cài đặt các package Python cần thiết
RUN pip install --no-cache-dir --upgrade \
    crawl4ai \
    nest_asyncio \
    playwright \
    pymongo \
    pymongo[srv] \
    dnspython \
    python-dotenv \
    langchain \
    langchain_core \
    langchain_google_genai \
    tiktoken \
    prometheus-client \
    langfuse 


# Install Playwright browsers
RUN playwright install chromium

# Run the post-installation setup for crawl4ai
RUN crawl4ai-setup

# Tạo thư mục cho code
WORKDIR /opt/airflow

# Các lệnh khác nếu cần thiết