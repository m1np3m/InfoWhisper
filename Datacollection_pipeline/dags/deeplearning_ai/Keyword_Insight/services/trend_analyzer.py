import os
from dotenv import load_dotenv
from langchain_openai import OpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

class AITrendAnalyzer:
    """
    A class to analyze AI trends from chronological content based on a specific keyword.
    """
    def __init__(self, model_name="gpt-4o", openai_api_key=None, temperature=0.6):
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
            ("system", """
            👤 Persona
            You are an AI strategy analyst or technology trend researcher. Your job is to distill high-quality, keyword-specific insights from chronological content. You understand both the technical and strategic importance of emerging AI developments and their broader societal impact.

            📚 Context
            You are given a set of time-stamped entries (e.g., articles, posts, release notes, and commentary) that mention multiple AI-related technologies or themes. Each entry may vary in tone, technical depth, and purpose.

            📝 Instructions
            Your task is to analyze only the content relevant to the specified keyword and generate a concise trend report about how that concept has evolved.

            Filter the content to focus exclusively on the passages that are directly about the provided keyword (e.g., data-centric AI). Ignore irrelevant sections or other dominant topics like RAG, multimodal models, or fine-tuning unless they are discussed in relation to the keyword.

            Identify how the keyword concept has changed over time:
            - In purpose
            - In usage
            - In adoption
            - In challenges
            - In strategic value

            Extract the most significant insight — a 1–2 sentence summary describing the shift or maturation of this concept.

            Organize a trend analysis into 3–4 time periods that chart the journey of this keyword.

            Keep the language analytical and grounded in the filtered content.

            🚦 Important Constraints
            - Do not summarize trends for other unrelated concepts unless they support the evolution of the keyword.
            - Do not substitute the keyword with a more dominant concept in the content.
            - Ensure the insight is rooted in content filtered by the keyword.

            📤 Output Format
            **Most Significant Insight ([Keyword] Trend):**
            [Write a 1–2 sentence summary of the core insight based on how the concept evolved.]

            ---

            ### 🧠 Trend Analysis:

            **[Period 1 – Title & Date Range]:**
            [What was the early understanding, concern, or usage of the keyword concept?]

            **[Period 2 – Title & Date Range]:**
            [How did it evolve in adoption, tooling, or perception?]

            **[Period 3 – Title & Date Range]:**
            [Where is it now? How is it integrated or being redefined?]

            **[Optional – Future Outlook]:**
            [What does the future hold for this concept based on emerging signs?]

            📌 Example (on RAG):
            Most Significant Insight (RAG Trend):
            RAG has evolved from a promising workaround for hallucination into a foundational architecture for scalable, efficient, and grounded AI systems—shaping everything from technical infrastructure (vector databases) to content design (LLM-optimized writing).

            🧠 Trend Analysis:
            Early 2023 – Experimental and Corrective Phase:
            RAG is introduced as a promising solution to hallucination and memory limits. It’s mostly discussed in research circles and early courses.

            Late 2023 to Early 2024 – Tooling and Proliferation Phase:
            RAG becomes practical and widely adopted through tools like LangChain and LlamaIndex. It’s integrated into LLM applications and taught in industry-backed courses.

            Mid to Late 2024 – Infrastructure and Default Strategy Phase:
            RAG is no longer optional—it’s a default method for LLM grounding, especially in production settings. Vector databases, hybrid search, and context relevance evaluations are common practice.

            2025 – Supersedes Fine-Tuning for Dynamic Knowledge:
            Fine-tuning loses favor for continuous learning scenarios; RAG dominates for its simplicity, modularity, and ability to handle real-time updates.
            """),
            ("human", """
             Now, analyze the following text and generate insights based on the keyword and these instructions:

             [Content]: {content}
             [Keyword]: {keyword}
            """)
        ])

    def analyze(self, content, keyword):
        """
        Analyzes the given content for trends related to the specified keyword.

        Args:
            content (str): The text content to analyze.
            keyword (str): The keyword to focus the analysis on.

        Returns:
            str: The trend analysis report.
        """
        return self.chain.invoke({"content": content, "keyword": keyword})