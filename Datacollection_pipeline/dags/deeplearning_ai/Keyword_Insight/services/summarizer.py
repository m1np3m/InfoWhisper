import time
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from deeplearning_ai.Keyword_Insight.utils.api_manager import APIKeyManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BulletPointSummarizer:
    """
    Tạo tóm tắt bài viết sử dụng Gemini thông qua LangChain với hỗ trợ xoay vòng API keys
    """

    def __init__(self, model_name="gemini-2.5-flash-preview-04-17"):
        """
        Khởi tạo ArticleSummarizer

        Args:
            api_key (str): Gemini API key
            model_name (str): Tên model. Mặc định là "gemini-2.5-flash-preview-04-17"
        """
        # Khởi tạo API key manager
        self.api_key_manager = APIKeyManager()

        self.model_name = model_name

        # Khởi tạo LLM với API key hiện tại
        self.llm = self._create_llm()

        # Tạo prompt cho việc tóm tắt
        self.summarize_prompt = ChatPromptTemplate.from_messages([
            """
            [ROLE]
            You are an expert in Artificial Intelligence (AI) and Data Science. Your task is to summarize the user-provided content, strictly related to AI and Data Science, into 3 to 5 concise bullet points.

            [INSTRUCTIONS]
            Based on the [Content] provided below, generate a summary of 3 to 5 main points in a bulleted list.

            Requirements:

            Core Focus: Prioritize the most critical and accurate information directly pertaining to the central themes and keywords of the provided content.
            Precision: Retain all original numbers, technical terms, and significant findings exactly as presented.
            Conciseness & Clarity: Express each point with maximum brevity and clarity, avoiding any introductory or concluding remarks (e.g., "Hello," "Below is a summary," "Based on the information provided").
            Objectivity: Present only the information explicitly stated in the source content, without incorporating any personal inferences, interpretations, or external knowledge.
            Depth: Each bullet point should comprehensively capture a distinct main idea from the source, contributing to a thorough understanding of the summarized material.

            [Content]:
            "The transformer architecture, introduced in the 'Attention Is All You Need' paper in 2017 by Vaswani et al., has revolutionized natural language processing (NLP). Unlike recurrent neural networks (RNNs) and convolutional neural networks (CNNs), transformers rely solely on attention mechanisms, specifically self-attention, to draw global dependencies between input and output. This allows for parallelization during training, significantly reducing training times compared to sequential models. Large language models (LLMs) like GPT-3, which boasts 175 billion parameters, are built upon the transformer architecture. The encoder-decoder structure of the original transformer enables tasks like machine translation, while decoder-only variants are prominent in generative AI applications."

            [EXPECTED OUTPUT]

            * The transformer architecture, introduced in 2017, revolutionized NLP by exclusively using attention mechanisms for global dependency capture, allowing parallel training.
            * It significantly reduces training times compared to sequential models like RNNs and CNNs due to its parallelizable nature.
            * Large Language Models (LLMs), such as GPT-3 with 175 billion parameters, are based on the transformer architecture.
            * The original transformer's encoder-decoder structure supports tasks like machine translation, while decoder-only versions are used in generative AI.

            Now, analyze the following text and generate bullet summaries based on these instructions:

            [Content]: {content}
            """
        ])

    def _create_llm(self):
        """
        Creates a new ChatGoogleGenerativeAI instance using the current API key.
        """
        current_key = self.api_key_manager.get_current_key()
        logger.info(f"Creating LLM instance with API key ending in '...{current_key[-4:]}'")
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=current_key, # <-- CRITICAL FIX: Pass the current key
            temperature=0,
            max_retries=2,
        )


    def _is_rate_limit_error(self, error):
        """
        Kiểm tra xem lỗi có phải do giới hạn API không
        """
        error_str = str(error).lower()
        rate_limit_indicators = [
            "rate limit", "ratelimit", "too many requests",
            "429", "quota exceeded", "limit exceeded"
        ]
        return any(indicator in error_str for indicator in rate_limit_indicators)

    def create_summary(self, content, max_retry=5):
        """
        Tạo keyword cho bài viết (không ép LLM trả về JSON, chỉ lấy keyword)
        """
        time.sleep(2)
        retry_count = 0
        #api_rotation_count = 0
        max_api_rotations = len(self.api_key_manager.api_keys)
        while retry_count <= max_retry and self.api_key_manager.current_key_index < max_api_rotations:
            try:
                chain = self.summarize_prompt | self.llm
                result = chain.invoke({"content": content})
                # Lấy text tóm tắt, không cần ép kiểu JSON
                return result.content.strip()
            except Exception as e:
                if self._is_rate_limit_error(e) and self.api_key_manager.has_alternative_keys():
                    logger.warning(f"Gặp lỗi giới hạn API: {str(e)}")
                    self.api_key_manager.rotate_key()
                    self.llm = self._create_llm()
                    logger.info(f"Đang thử lại với API key mới ({self.api_key_manager.current_key_index}/{max_api_rotations})")
                else:
                    retry_count += 1
                    logger.error(f"Lỗi khi tạo keyword (lần {retry_count}): {str(e)}")
                    if retry_count > max_retry:
                        return "Không thể tạo keyword do lỗi kết nối đến LLM API."
                    time.sleep(25)
        return "Không thể tạo keyword do đã hết tất cả API keys hoặc quá số lần thử lại."