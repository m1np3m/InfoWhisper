# Sử dụng Python 3.10
FROM python:3.10-slim

# Cài đặt MLflow và PostgreSQL driver
RUN pip install mlflow psycopg2-binary

# Tạo thư mục lưu logs
RUN mkdir -p /mlflow

# Cấu hình biến môi trường với database mới
ENV BACKEND_STORE_URI="postgresql://mlflow_aiteam_user:SLSGRGwdieSECrZPWgMlTouCYiuR50Nj@dpg-d0pcreje5dus73dm71dg-a.oregon-postgres.render.com/mlflow_aiteam"
ENV ARTIFACT_ROOT="/mlflow/artifacts"

EXPOSE $PORT

CMD mlflow server \
    --backend-store-uri $BACKEND_STORE_URI \
    --default-artifact-root $ARTIFACT_ROOT \
    --host 0.0.0.0 --port $PORT --workers 1