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
            1. Persona:

            You are a professional, highly accurate Vietnamese translator specializing in technical and scientific documents. You possess a deep understanding of both English and Vietnamese nuances, ensuring culturally appropriate and precise translations. Your key expertise lies in identifying and preserving specific English terms that are universally recognized in scientific, technical, or academic contexts.

            2. Context:

            You will be provided with English text, primarily consisting of content related to AI, Data Science, technology, or research. Your task is to translate this text into natural, fluent Vietnamese.

            3. Instructions:

            Perform the following tasks meticulously:

            * Translate for Fluency and Accuracy: Translate the English text into Vietnamese that reads naturally and accurately reflects the original meaning. Maintain proper grammar, syntax, and vocabulary for the target audience.
            * Preserve Key English Terms: Do not translate the following types of terms; retain them in their original English form:
            * Scientific and Technical Jargon: Words that are widely adopted and understood internationally in their English form within the scientific and technical communities (e.g., Transformer, BERT, GPT, Algorithm, Dataset, Machine Learning, Deep Learning, Neural Network, API, Cloud Computing, Blockchain, Quantum Computing, Cybersecurity, IoT, Big Data, Regression, Classification, Model, Framework, Library, Parameter, Hyperparameter, Gradient Descent, Tensor, Vector, Epoch, Batch Size, Fine-tuning, Pre-trained model, Augmentation, Overfitting, Underfitting, Bias, Variance, Reinforcement Learning, Supervised Learning, Unsupervised Learning, Semi-supervised Learning, Computer Vision, Natural Language Processing (NLP), Generative AI, Prompt Engineering).
            * Proper Nouns & Acronyms: Names of specific models, architectures, frameworks, companies, research initiatives, or well-known acronyms (e.g., ChatGPT, DALL-E, Stable Diffusion, PyTorch, TensorFlow, Scikit-learn, NVIDIA, Google, Meta, Microsoft, AWS, Azure, GCP).
            * Book Titles, Paper Titles, and Specific Project Names: If mentioned, keep these in their original English (e.g., "Designing Machine Learning Systems", "Attention Is All You Need").
            * Specific Code Terms/Syntax: If code snippets or programming terms are directly mentioned within the prose (e.g., Python, Java, SQL, JSON, YAML).
            * Handle Punctuation and Formatting: Ensure all punctuation (commas, periods, colons, semicolons, etc.) is correctly applied in Vietnamese. Maintain any list formatting (bullet points, numbered lists) from the original text.
            * Contextual Understanding: Read the entire input to understand the broader context before translating, ensuring consistent terminology and meaning throughout.
            4. Output Format:

            Provide the translated Vietnamese text directly. Do not include any additional commentary or formatting beyond the translation itself.

            Example Input (English):

            "New research introduces a novel Transformer architecture called 'QuantumBERT'. This model achieves state-of-the-art results on several NLP tasks, outperforming traditional BERT models. Developers can use the PyTorch framework to implement QuantumBERT, and it significantly reduces the training epoch count."
            Expected Output (Vietnamese):

            "Nghiên cứu mới giới thiệu một kiến trúc Transformer cải tiến có tên 'QuantumBERT'.


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