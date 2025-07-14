import os
from dotenv import load_dotenv
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langfuse import get_client
from langfuse.langchain import CallbackHandler
import time
import langfuse
# 1. Load .env before anything else
load_dotenv()

# # 2. Init Langfuse client and custom handler
# lf = get_client()  # picks SECRET_KEY, PUBLIC_KEY, HOST from env
# handler=CallbackHandler()

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info(langfuse.__version__)

logging.getLogger("langfuse").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)



from langchain.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate

def load_langfuse_prompt_to_langchain(prompt_name: str, label: str = "production") -> ChatPromptTemplate:
    lf = get_client()
    prompt_client = lf.get_prompt(prompt_name, label=label)
    messages_data = prompt_client.prompt

    messages = []
    for msg in messages_data:
        role = msg["role"]
        content = msg["content"].replace("{{context}}", "{content}")
        if role == "system":
            messages.append(SystemMessagePromptTemplate.from_template(content))
        elif role == "user":
            messages.append(HumanMessagePromptTemplate.from_template(content))
        else:
            raise ValueError(f"Unsupported role '{role}' in Langfuse prompt.")
    return ChatPromptTemplate.from_messages(messages)



class ArticleSummarizer:
    def __init__(self, model_name="gemini-2.0-flash-lite",lf = None, handler = None):
        self.lf=lf
        self.handler=handler
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY không tìm thấy trong .env")
        # Initialize LLM with our custom handler
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.api_key,
            temperature=0.1,
            max_tokens=1024,
            callbacks=[self.handler],
            name="Summary_News"
        )
        # Define prompts
        self.summary_prompt = ChatPromptTemplate.from_messages([
        ("system", """Bạn là một trợ lý AI có nhiệm vụ tóm tắt các bài viết khoa học, kỹ thuật hoặc công nghệ được viết bằng tiếng Anh, và cung cấp bản tóm tắt ngắn gọn bằng tiếng Việt.
        
        Yêu cầu:
        1. Tóm tắt phải ngắn gọn, không quá 3 câu, súc tích và dễ hiểu đối với người Việt.
        2. Phải giữ lại những thông tin cốt lõi, chính xác và quan trọng nhất trong bài viết.
        3. Không thêm bình luận cá nhân, ý kiến chủ quan hoặc phóng đại nội dung.
        4. Viết bằng tiếng Việt chuẩn, trung lập, đúng ngữ pháp, phong cách rõ ràng, khách quan.
        5. Nếu bài viết có nhiều nội dung, hãy tập trung vào nội dung chính yếu.
        
        Dưới đây là nội dung bài viết tiếng Anh, hãy phân tích và tóm tắt bằng tiếng Việt:"""),
        ("human", "{content}")
        ])
        
        # Tạo prompt cho việc tóm tắt dạng bullet points
        self.bullet_summary_prompt = load_langfuse_prompt_to_langchain("3 Points")

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
        
        # Giới hạn độ dài nội dung nếu quá dài (Gemini có thể xử lý nhiều hơn)
        if len(content) > 8000:
            logger.info(f"Nội dung quá dài ({len(content)} ký tự), cắt bớt xuống 8000 ký tự")
            content = content[:8000]
        
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
                    return "Không thể tạo tóm tắt do lỗi kết nối đến Gemini API."
        
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
        if len(content) > 8000:
            logger.info(f"Nội dung quá dài ({len(content)} ký tự), cắt bớt xuống 8000 ký tự")
            content = content[:8000]
        
        chain = self.bullet_summary_prompt | self.llm
        
        retry_count = 0
        while retry_count <= max_retry:
            try:
                result = chain.invoke({"content": content},config={"run_name": "Summary_Bullet_News_Tesst"})
                return result.content
            except Exception as e:
                retry_count += 1
                logger.error(f"Lỗi khi tạo tóm tắt bullet (lần {retry_count}): {str(e)}")
                if retry_count > max_retry:
                    return "Không thể tạo tóm tắt do lỗi kết nối đến Gemini API."
        
        return "Không thể tạo tóm tắt do lỗi không xác định."

