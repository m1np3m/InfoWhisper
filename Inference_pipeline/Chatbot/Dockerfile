# Use the official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy all files (including UI.py)
COPY . .

# Install dependencies (assume you have requirements.txt)
RUN pip install -r requirements.txt

# Expose the Streamlit default port
EXPOSE 8501

# Run Streamlit app
CMD ["streamlit", "run", "UI.py", "--server.port=8501", "--server.address=0.0.0.0"]
