import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class APIKeyManager:
    """
    Quản lý và xoay vòng API keys khi gặp lỗi giới hạn
    """
    def __init__(self):
        """
        Khởi tạo APIKeyManager với danh sách các API keys từ biến môi trường
        """
        self.primary_key = os.environ.get("GEMINI_API_KEY", "")

        # Thu thập tất cả các API keys có sẵn
        self.api_keys = [self.primary_key]

        # Thêm các API keys phụ nếu có
        for i in range(2, 4):  # Hỗ trợ tối đa 5 API keys phụ
            key_name = f"GEMINI_API_KEY_{i}"
            if key_name in os.environ and os.environ[key_name]:
                self.api_keys.append(os.environ[key_name])

        self.current_key_index = 0
        logger.info(f"Đã tải {len(self.api_keys)} API keys")

    def get_current_key(self):
        """
        Lấy API key hiện tại đang sử dụng
        """
        return self.api_keys[self.current_key_index]

    def rotate_key(self):
        """
        Xoay vòng sang API key tiếp theo

        Returns:
            str: API key mới sau khi xoay vòng
            None: Nếu đã hết API keys
        """
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

        # Nếu đã quay vòng về key đầu tiên, báo lỗi
        if self.current_key_index == 0:
            logger.warning("Đã sử dụng hết tất cả API keys, quay lại key đầu tiên")

        new_key = self.get_current_key()
        logger.info(f"Đã chuyển sang API key #{self.current_key_index+1}")
        return new_key

    def has_alternative_keys(self):
        """
        Kiểm tra xem còn API key thay thế không (nhiều hơn 1 key)
        """
        return len(self.api_keys) > 1