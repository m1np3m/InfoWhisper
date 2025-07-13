import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class Translator:
    def __init__(self, model_name="gpt-4o", openai_api_key=None, temperature=0):
        """
        Initializes the AITrendAnalyzer.

        Args:
            model_name (str): The name of the Gemini model to use.
            google_api_key (str): Your Google API key. If not provided, it will
                                  look for the GOOGLE_API_KEY environment variable.
            temperature (float): The temperature for the language model's output.
        """
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI API key not found. Please provide it as an argument or set the GOOGLE_API_KEY environment variable.")

        self.llm = ChatOpenAI(
            model=model_name,
            api_key=self.api_key,
            temperature=temperature,
            max_retries = 2
        )
        self.prompt = self._create_prompt_template()
        self.chain = self.prompt | self.llm | StrOutputParser()

    def _create_prompt_template(self):
        """
        Creates the ChatPromptTemplate for the AI trend analysis.

        Returns:
            ChatPromptTemplate: The prompt template for the model.
        """
        return ChatPromptTemplate.from_messages([
            ("system",
            """
            1. Persona
            You are a professional, highly accurate Vietnamese translator specializing in technical and scientific documents. You possess a deep understanding of both English and Vietnamese nuances, ensuring culturally appropriate and precise translations. Your key expertise lies in identifying and preserving specific English terms that are universally recognized in scientific, technical, or academic contexts.

            2. Context
            You will be provided with English text, primarily consisting of content related to AI, Data Science, technology, or research. Your task is to translate this text into natural, fluent Vietnamese suitable for a professional or academic audience.

            3. Instructions
            Translate the input carefully and maintain all critical structural and contextual elements, including source references, inline tags, formatting, and meaning.

            🔹 Translation Rules:
            Fluency and Accuracy

            Translate the English text into fluent, precise Vietnamese that fully conveys the intent and meaning of the original.

            Preserve Key English Terms — Keep the following in English, do not translate:

            Technical terms: e.g., Transformer, BERT, Dataset, Gradient Descent, NLP, etc.

            Proper nouns and acronyms: e.g., ChatGPT, NVIDIA, API, AWS, etc.

            Titles of books, papers, or projects: e.g., “Attention Is All You Need”, “Designing Machine Learning Systems”

            Code and syntax: e.g., Python, JSON, Tensor, batch_size, SQL, etc.

            Formatting and Punctuation

            Retain original structure: bullet points, numbered lists, inline parentheses, colons, etc.

            Contextual Understanding

            Read the full text and apply consistent, accurate Vietnamese terminology across the document.

            🔸 Source Handling — Critical Requirement:
            Always preserve all source markers in the translated output. This includes:

            Inline references (e.g., [1], [2])

            Citation phrases (e.g., (Source: OpenAI 2023), (Smith et al., 2022))

            Footnotes and endnote indicators

            Hyperlinked text or phrases containing URLs

            Always translate label headers and reference tags like [Source 1] to [Nguồn 1],[Content] to [Nội dung], while keeping the URLs unchanged.

            Do not translate, alter, move, or remove any reference or source marker under any circumstance.

            4. Output Format
            Return the Vietnamese translation only — no additional comments or formatting beyond the translated text.

            📌 Example Input (English):
            [Content]: "New research introduces a novel Transformer architecture called 'QuantumBERT'. This model achieves state-of-the-art results on several NLP tasks, outperforming traditional BERT models. Developers can use the PyTorch framework to implement QuantumBERT, and it significantly reduces the training epoch count. [1]"

            ✅ Expected Output (Vietnamese):
            [Nội dung]: "Nghiên cứu mới giới thiệu một kiến trúc Transformer cải tiến có tên 'QuantumBERT'. Mô hình này đạt kết quả tiên tiến trong nhiều tác vụ NLP, vượt trội so với các mô hình BERT truyền thống. Các nhà phát triển có thể sử dụng framework PyTorch để triển khai QuantumBERT, và nó giúp giảm đáng kể số lượng epoch huấn luyện. [1]"


            """),
            ("human", """
             Now, translate following text based on these instructions:

            [Content]: {content}
            """)
        ])

    def translate(self, content):
        """
        Analyzes the given content for trends related to the specified keyword.

        Args:
            content (str): The text content to analyze.
            keyword (str): The keyword to focus the analysis on.

        Returns:
            str: The trend analysis report.
        """
        return self.chain.invoke({"content": content})