import re
import json
import time
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from deeplearning_ai.Keyword_Insight.utils.api_manager import APIKeyManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class KeywordMaker:
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

        # Tạo prompt cho việc sinh keywords
        self.keyword_prompt = ChatPromptTemplate.from_messages([
            """
            You are an expert AI and Data Science researcher specializing in identifying key technical concepts in documents.

            Your task is to analyze the provided text and extract exactly 5 of the most important and specific keywords related to Artificial Intelligence and Data Science.

            Instructions:

            Prioritize Specificity: Focus on precise terms, such as the names of models, algorithms, libraries, or techniques. For example, prioritize "BERT," "TensorFlow," "Reinforcement Learning," or "Computer Vision" over general terms.
            Limit General Keywords: Avoid broad and common words like "artificial intelligence," "machine learning," "data," "generative AI," and "large language model." Only include these if they are the most significant and specific concepts in the text and no better alternatives are present.
            Identify Core Concepts: The keywords should represent the central ideas and technologies discussed in the content.
            Format the Output: Return the keywords as a JSON object with a single key, "keywords," which contains a list of the 5 extracted keyword strings.
            Example of desired behavior:

            Content:
            "This week, Google announced the next generation of its large language model, Gemini 1.5, which shows significant improvements in handling long contexts. This new model builds on the Transformer architecture, similar to OpenAI's ChatGPT. The researchers also highlighted its advanced capabilities in multimodal tasks, including cutting-edge Text-to-Speech (TTS) synthesis. The training process utilized techniques in deep learning and was facilitated by JAX, a popular framework for high-performance machine learning research."

            Your Output: "keywords": [
                "Gemini 1.5",
                "Transformer",
                "ChatGPT",
                "Text-to-Speech (TTS)",
                "JAX"
              ]
            Now, analyze the following text and extract the 5 most relevant keywords based on these instructions:

            {content}
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
            google_api_key=current_key,
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

    def create_keyword(self, content, max_retry=5):
        """
        Tạo keyword cho bài viết (không ép LLM trả về JSON, chỉ lấy keyword)
        """
        time.sleep(2)
        retry_count = 0
        max_api_rotations = len(self.api_key_manager.api_keys)
        while retry_count <= max_retry and self.api_key_manager.current_key_index < max_api_rotations:
            try:
                chain = self.keyword_prompt | self.llm
                result = chain.invoke({"content": content})
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

    def _parse_json_from_response(self, text):
        """
        Extracts and parses the JSON object from the LLM's string response.
        """
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            logger.error(f"Could not find JSON in response: {text}")
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from response: {match.group(0)} - Error: {e}")
            return None

    def create_keywords_from_content(self, content, max_retry=5):
        """
        Creates and returns a list of keywords for the given content.

        Returns:
            list: A list of keyword strings.
            str: An error message if keyword creation fails.
        """
        time.sleep(2)
        retry_count = 0
        total_keys = len(self.api_key_manager.api_keys)
        keys_used = 0

        while keys_used < total_keys:
            try:
                chain = self.keyword_prompt | self.llm
                result = chain.invoke({"content": content})
                parsed_json = self._parse_json_from_response(result.content)

                if parsed_json and "keywords" in parsed_json and isinstance(parsed_json["keywords"], list):
                    return parsed_json["keywords"]
                else:
                    logger.error("Parsed JSON is invalid or does not contain 'keywords' list. Retrying...")
                    raise ValueError("Invalid JSON response format")

            except Exception as e:
                if self._is_rate_limit_error(e) and self.api_key_manager.has_alternative_keys():
                    logger.warning(f"Rate limit error encountered: {e}")
                    self.api_key_manager.rotate_key()
                    self.llm = self._create_llm() # Re-create LLM with the new key
                    keys_used += 1
                    retry_count = 0 # Reset retry count for the new key
                    logger.info(f"Rotated to key #{self.api_key_manager.current_key_index + 1}. Retrying...")
                    continue
                else:
                    retry_count += 1
                    logger.error(f"Error creating keywords (Attempt {retry_count}/{max_retry}): {e}")
                    if retry_count >= max_retry:
                        return "Failed to create keywords after multiple retries."
                    time.sleep(15 * retry_count)

        return "Failed to create keywords; all API keys encountered errors."