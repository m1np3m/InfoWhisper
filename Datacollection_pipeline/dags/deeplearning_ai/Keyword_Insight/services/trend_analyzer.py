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
            You are given a set of time-stamped entries (e.g., articles, posts, release notes, and commentary) that mention multiple AI-related technologies or themes. Each entry is associated with a source URL and may vary in tone, technical depth, and purpose.

            📝 Instructions
            Your task is to analyze only the content relevant to the specified keyword and generate a concise trend report about how that concept has evolved.

            Filter the content to focus exclusively on passages directly related to the specified keyword (e.g., data-centric AI).

            Ignore unrelated concepts like RAG, multimodal models, or fine-tuning unless discussed in direct relation to the keyword.

            Your report should address how the keyword has evolved over time in terms of:

            Purpose

            Usage

            Adoption

            Challenges

            Strategic value

            Extract the most significant insight — a 1–2 sentence summary describing the overall shift or maturation of the keyword.

            Then, organize a trend analysis into 3–4 time periods that describe its journey over time.

            📌 Source Referencing Rules (NEW – Strict Source Ordering):

            ✅ Use [Source #] notation in the trend body.
            ✅ Always cite when insights are derived from source content.
            ✅ Number sources in the order they first appear in the report — starting from [Source 1], [Source 2], etc.
            ✅ If a URL appears multiple times, reuse the same source number.
            ✅ At the end of the report, list the original URLs under a 🔗 References: section, matching the source numbers used.

            🚦 Important Constraints

            Do not summarize unrelated trends unless directly tied to the keyword’s evolution.

            Do not substitute the keyword with a more dominant concept in the data.

            Ensure the insight is rooted strictly in keyword-relevant content.

            Retain all URLs used, unchanged, in the final References section.

            Ensure source numbers in the body follow strict order of appearance.

            📤 Output Format

            Most Significant Insight ([Keyword] Trend):
            [1–2 sentence summary of the core insight based on the keyword’s evolution.]

            🧠 Trend Analysis:
            [Period 1 – Title & Date Range]:
            [Describe early usage, concerns, or understanding of the keyword. Cite sources as [Source 1], [Source 2], etc.]

            [Period 2 – Title & Date Range]:
            [Describe development in adoption, tooling, or perception. Continue using new source numbers as they appear.]

            [Period 3 – Title & Date Range]:
            [Explain the current state or integration of the keyword.]

            [Optional – Future Outlook]:
            [Speculate on future directions based on content.]

            🔗 References:
            [List each source in order of first mention as below:]
            [Source 1]: [URL from original content]

            [Source 2]: [Another URL]

            ...

            🧪 Example (on RAG)
            Most Significant Insight (RAG Trend):
            RAG has evolved from a promising workaround for hallucination into a foundational architecture for scalable, efficient, and grounded AI systems—shaping everything from technical infrastructure (vector databases) to content design (LLM-optimized writing).

            🧠 Trend Analysis:

            Early 2023 – Experimental and Corrective Phase:
            RAG is introduced as a promising solution to hallucination and memory limits. It’s mostly discussed in research circles and early courses. [Source 1]

            Late 2023 to Early 2024 – Tooling and Proliferation Phase:
            RAG becomes practical and widely adopted through tools like LangChain and LlamaIndex. It’s integrated into LLM applications and taught in industry-backed courses. [Source 2]

            Mid to Late 2024 – Infrastructure and Default Strategy Phase:
            RAG is no longer optional—it’s a default method for LLM grounding, especially in production settings. Vector databases, hybrid search, and context relevance evaluations are common practice. [Source 3]

            2025 – Supersedes Fine-Tuning for Dynamic Knowledge:
            Fine-tuning loses favor for continuous learning scenarios; RAG dominates for its simplicity, modularity, and ability to handle real-time updates. [Source 4]

            🔗 References:
            [Source 1]: https://example.com/research-rag
            [Source 2]: https://example.com/langchain-tools
            [Source 3]: https://example.com/rag-infrastructure
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