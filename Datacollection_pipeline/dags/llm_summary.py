import os
import nest_asyncio
from dotenv import load_dotenv
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

nest_asyncio.apply()

class ArticleSummarizer:
    """
    Tạo tóm tắt bài viết sử dụng ChatGroq thông qua LangChain
    """
    
    def __init__(self, api_key=None, model_name="gemma2-9b-it"):
        """
        Khởi tạo ArticleSummarizer
        
        Args:
            api_key (str): Groq API key
            model_name (str): Tên model. Mặc định là "gemma2-9b-it"
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY không tìm thấy. Hãy cung cấp qua tham số hoặc biến môi trường.")
        
        self.model_name = model_name
        
        # Khởi tạo LLM
        self.llm = ChatGroq(
            api_key=self.api_key, 
            model_name=self.model_name
        )
        
        # Tạo prompt cho việc tóm tắt
        self.summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """Bạn là một trợ lý AI chuyên tóm tắt nội dung bài báo tiếng Việt. 
            Nhiệm vụ của bạn là tạo ra bản tóm tắt ngắn gọn, súc tích, chứa các thông tin quan trọng nhất từ bài viết đầu vào.

            Yêu cầu:
            1. Tóm tắt phải ngắn gọn (không quá 3-5 câu)
            2. Bảo toàn ý chính và thông tin quan trọng nhất
            3. Không thêm ý kiến cá nhân hay đánh giá
            4. Sử dụng ngôn ngữ trung lập, khách quan
            5. Phản ánh đúng quan điểm của bài viết gốc
            6. Viết bằng tiếng Việt chuẩn, mạch lạc

            Hãy phân tích nội dung bài viết sau và cung cấp bản tóm tắt chất lượng:"""),
            ("human", "{content}")
        ])
        
        # Tạo prompt cho việc tóm tắt dạng bullet points
        self.bullet_summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """Bạn là một trợ lý AI chuyên tóm tắt nội dung bài báo tiếng Việt. 
            Nhiệm vụ của bạn là tạo ra bản tóm tắt dạng bullet points (không quá 5 điểm), chứa các thông tin quan trọng nhất từ bài viết đầu vào.

            Yêu cầu:
            1. Tóm tắt thành 3-5 bullet points ngắn gọn
            2. Mỗi bullet point chỉ nêu một ý chính hoặc thông tin quan trọng
            3. Không thêm ý kiến cá nhân hay đánh giá
            4. Sử dụng ngôn ngữ trung lập, khách quan
            5. Phản ánh đúng quan điểm của bài viết gốc
            6. Viết bằng tiếng Việt chuẩn, mạch lạc

            Hãy phân tích nội dung bài viết sau và cung cấp bản tóm tắt dạng bullet points:"""),
            ("human", "{content}")
        ])
        
    def create_summary(self, content, max_retry=2):
        """
        Tạo tóm tắt cho bài viết
        
        Args:
            content (str): Nội dung bài viết cần tóm tắt
            max_retry (int): Số lần thử lại tối đa nếu lỗi
            
        Returns:
            str: Bản tóm tắt của bài viết
        """
        if not content or len(content.strip()) < 100:
            logger.warning("Nội dung quá ngắn hoặc rỗng để tóm tắt")
            return "Không đủ nội dung để tạo tóm tắt."
        
        # Giới hạn độ dài nội dung nếu quá dài
        if len(content) > 2500:
            logger.info(f"Nội dung quá dài ({len(content)} ký tự), cắt bớt xuống 8000 ký tự")
            content = content[:2500]
        
        chain = self.summary_prompt | self.llm
        
        retry_count = 0
        while retry_count <= max_retry:
            try:
                result = chain.invoke({"content": content})
                return result.content
            except Exception as e:
                retry_count += 1
                logger.error(f"Lỗi khi tạo tóm tắt (lần {retry_count}): {str(e)}")
                if retry_count > max_retry:
                    return "Không thể tạo tóm tắt do lỗi kết nối đến LLM API."
        
        return "Không thể tạo tóm tắt do lỗi không xác định."
    
    def create_bullet_summary(self, content, max_retry=2):
        """
        Tạo tóm tắt dạng bullet points cho bài viết
        
        Args:
            content (str): Nội dung bài viết cần tóm tắt
            max_retry (int): Số lần thử lại tối đa nếu lỗi
            
        Returns:
            str: Bản tóm tắt dạng bullet points của bài viết
        """
        if not content or len(content.strip()) < 100:
            logger.warning("Nội dung quá ngắn hoặc rỗng để tóm tắt")
            return "Không đủ nội dung để tạo tóm tắt."
        
        # Giới hạn độ dài nội dung nếu quá dài
        if len(content) > 2500:
            logger.info(f"Nội dung quá dài ({len(content)} ký tự), cắt bớt xuống 25002500 ký tự")
            content = content[:2500]
        
        chain = self.bullet_summary_prompt | self.llm
        
        retry_count = 0
        while retry_count <= max_retry:
            try:
                result = chain.invoke({"content": content})
                return result.content
            except Exception as e:
                retry_count += 1
                logger.error(f"Lỗi khi tạo tóm tắt bullet (lần {retry_count}): {str(e)}")
                if retry_count > max_retry:
                    return "Không thể tạo tóm tắt do lỗi kết nối đến LLM API."
        
        return "Không thể tạo tóm tắt do lỗi không xác định."
