#  Cấu trúc thư mục dự án

- **cdc_local**: Change Data Capture (CDC), RABBITMQ.
- **Datacollection_pipeline**: Airflow, Crawler,...
- **Error_handling_UI**: UI kết nối với Database để làm Dashboard hiển thị lỗi.
- **feature_pipeline**: Code Celery-Consumer-Worker.
- **Inference_pipeline**: Code UI, Naive RAG Pipeline, Phoenix.
- **MLflow**: Bản MLflow chạy dưới local.
- **MLflow_onserver**: Bản MLflow đang chạy trên server.
- **notebook**: Chứa các notebook Jupyter (hoặc các loại notebook khác) dùng cho thử nghiệm,...
- **Training_pipeline**: Chứa notebook cho code training ở Kaggle/Colab.

---

##  Phiên bản web

| Tính năng                      | Đường dẫn                                                                 |
|-------------------------------|--------------------------------------------------------------------------|
|  Dashboard show lỗi         | [ai-news-report-handle.onrender.com](https://ai-news-report-handle.onrender.com/) |
|  Chatbot & Góp ý người dùng | [demo-news.onrender.com/Feedback](https://demo-news.onrender.com/Feedback)       |
|  MLflow theo dõi metrics    | [mlflow-server-aiteamabc.onrender.com](https://mlflow-server-aiteamabc.onrender.com/) |

đăng nhập cho dashboard:
tk: demo
mk: demo
Lưu ý tài khoản được cấp chỉ có thể xem
---

##  Bảo mật

- Các tệp `.env` đã được cấu hình và **ẩn toàn bộ API key**.
- Đảm bảo an toàn khi làm việc nhóm hoặc public code.
- Khi sử dụng chỉ cần thay các giá trị trong file .env

## Python: 3.10
