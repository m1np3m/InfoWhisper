from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class QueryGenerator:
    def __init__(self, gemini_api_key: str):
        """
        Initialize Query Generator
        
        Args:
            gemini_api_key: Google Gemini API key
        """
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            temperature=0.3,
            max_output_tokens=512,
            api_key=gemini_api_key
        )
        
        self.prompt_template = PromptTemplate(
            template="""
Dựa vào lịch sử trò chuyện gần đây, hãy tối ưu hóa câu hỏi hiện tại để tìm kiếm thông tin chính xác hơn.

### Lịch sử trò chuyện gần đây:
{chat_history}

### Câu hỏi hiện tại:
{current_question}

### Hướng dẫn:
1. Phân tích ngữ cảnh từ lịch sử trò chuyện
2. Xác định chủ đề, từ khóa chính liên quan
3. Tối ưu hóa câu hỏi để tìm kiếm chính xác hơn
4. Giữ nguyên ý định của người dùng
5. Trả lời CHỈ câu hỏi được tối ưu hóa, không giải thích

### Câu hỏi tối ưu hóa:
""",
            input_variables=["chat_history", "current_question"]
        )
    
    def generate_optimized_query(self, current_question: str, chat_history: List[Dict]) -> str:
        """
        Generate optimized query based on chat history
        
        Args:
            current_question: Current user question
            chat_history: List of recent conversation pairs
            
        Returns:
            Optimized query string
        """
        try:
            # Format chat history for prompt
            formatted_history = self._format_chat_history(chat_history)
            
            # Generate optimized query
            prompt = self.prompt_template.format(
                chat_history=formatted_history,
                current_question=current_question
            )
            
            response = self.llm.invoke(prompt)
            optimized_query = response.content.strip()
            
            logger.info(f"Original query: {current_question}")
            logger.info(f"Optimized query: {optimized_query}")
            
            return optimized_query
            
        except Exception as e:
            logger.error(f"Error generating optimized query: {e}")
            return current_question  # Return original if optimization fails
    
    def _format_chat_history(self, chat_history: List[Dict]) -> str:
        """Format chat history for prompt"""
        if not chat_history:
            return "Không có lịch sử trò chuyện."
        
        formatted = []
        for i, conv in enumerate(chat_history, 1):
            user_msg = conv["user"]["content"]
            assistant_msg = conv["assistant"]["content"][:200] + "..." if len(conv["assistant"]["content"]) > 200 else conv["assistant"]["content"]
            
            formatted.append(f"""
Lượt {i}:
- Người dùng: {user_msg}
- Trợ lý: {assistant_msg}
""")
        
        return "\n".join(formatted)