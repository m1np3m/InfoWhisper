# ---- Base image ----
FROM python:3.10-slim

# ---- Set environment variables ----
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- Set working directory ----
WORKDIR /app

# ---- Install dependencies ----
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---- Copy application files ----
COPY . .

# ---- Expose Streamlit port ----
EXPOSE 8501

# ---- Run Streamlit ----
CMD ["streamlit", "run", "News.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
