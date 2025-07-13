import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """
    Centralized configuration management for the AI content processing system.
    """
    
    # MongoDB Configuration
    MONGODB_URI_1 = os.getenv("MONGODB_URI_1", "").replace("<PASSWORD>", os.getenv("MONGODB_PASSWORD_1", ""))
    MONGODB_URI_2 = os.getenv("MONGODB_URI_2", "").replace("<PASSWORD>", os.getenv("MONGODB_PASSWORD_2", ""))
    MONGODB_PASSWORD_1 = os.getenv("MONGODB_PASSWORD_1")
    MONGODB_PASSWORD_2 = os.getenv("MONGODB_PASSWORD_2")
    
    # Database Names
    SOURCE_DB_NAME = "deeplearning"
    SOURCE_COLLECTION_NAME = "letters"
    TARGET_DB_NAME = "Content"
    TARGET_COLLECTION_NAME = "Content"
    INSIGHT_DB_NAME = "Insight"
    
    # Qdrant Configuration
    QDRANT_URL = "https://9ddcf734-0817-4421-bf16-333e56ed4a9b.eu-central-1-0.aws.cloud.qdrant.io:6333"
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    QDRANT_COLLECTION_NAME = "content_embedding_with_url"
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = "gpt-4o"
    OPENAI_TEMPERATURE = 0.6
    
    # Gemini Configuration (Dynamic API Keys)
    # Note: API keys are managed by APIKeyManager, not hardcoded here
    GEMINI_MODEL = "gemini-2.5-flash-preview-04-17"
    GEMINI_TEMPERATURE = 0
    
    # Processing Configuration
    MAX_RETRIES = 5
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    EMBEDDING_MODEL = "BAAI/bge-m3"
    
    # Analysis Keywords
    ANALYSIS_KEYWORDS = ["RAG", "data centric ai", "computer vision", "ChatGPT"]
    
    # Output Configuration
    OUTPUT_JSON_FILE = "contents_summaries_keywords.json"
    SEARCH_LIMIT = 20
    
    # Rate Limiting
    API_RETRY_DELAY = 25  # seconds
    API_ROTATION_DELAY = 2  # seconds
    
    @classmethod
    def validate_config(cls):
        """
        Validate required configuration parameters.
        
        Raises:
            ValueError: If required configuration is missing.
        """
        required_configs = [
            ("MONGODB_URI_1", cls.MONGODB_URI_1),
            ("MONGODB_URI_2", cls.MONGODB_URI_2),
            ("QDRANT_API_KEY", cls.QDRANT_API_KEY),
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
        ]
        
        missing_configs = []
        for config_name, config_value in required_configs:
            if not config_value:
                missing_configs.append(config_name)
        
        if missing_configs:
            raise ValueError(f"Missing required configuration: {', '.join(missing_configs)}")
        
        return True
    
    @classmethod
    def get_mongodb_source_uri(cls):
        """Get source MongoDB URI."""
        return cls.MONGODB_URI_1
    
    @classmethod
    def get_mongodb_target_uri(cls):
        """Get target MongoDB URI."""
        return cls.MONGODB_URI_2