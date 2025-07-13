# Sử dụng Python 3.10
FROM python:3.10-slim

# Cài đặt MLflow và PostgreSQL driver
RUN pip install mlflow psycopg2-binary

# Tạo thư mục lưu logs
RUN mkdir -p /mlflow

# Cấu hình biến môi trường với database mới
# ENV BACKEND_STORE_URI="postgresql://db_p0uw_user:eMA3bVSJdjsyEQx3iRmFD0aZUrzLKXFh@dpg-d1g1df7fte5s73845g5g-a.oregon-postgres.render.com/db_p0uw"
ENV BACKEND_STORE_URI="postgresql://hth:VHJYHnTrERdpovAt1DwojUHacWgyuFwX@dpg-d1go8pripnbc73b0hfv0-a.oregon-postgres.render.com/hth_wuya"

ENV ARTIFACT_ROOT="/mlflow/artifacts"

EXPOSE $PORT

CMD mlflow server \
    --backend-store-uri $BACKEND_STORE_URI \
    --default-artifact-root $ARTIFACT_ROOT \
    --host 0.0.0.0 --port $PORT --workers 1