import json
import logging
import pymongo
from qdrant_client import QdrantClient
from pymongo import MongoClient

from config import Config
from services.summarizer import BulletPointSummarizer
from services.keyword_extractor import KeywordMaker
from services.trend_analyzer import AITrendAnalyzer
from services.translator import Translator
from utils.database import get_mongodb_data, generate_embeddings_from_field

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_source_data():
    """
    Extract data from source MongoDB collection.
    
    Returns:
        tuple: (titles, abstracts, contents, publish_dates)
    """
    logger.info("Extracting data from source MongoDB...")
    
    # Connect to source MongoDB
    client = pymongo.MongoClient(Config.get_mongodb_source_uri())
    db = client[Config.SOURCE_DB_NAME]
    collection = db[Config.SOURCE_COLLECTION_NAME]
    
    # Extract data
    docs = collection.find()
    titles, abstracts, contents, publish_dates = [], [], [], []
    
    for doc in docs:
        titles.append(doc["title"])
        abstracts.append(doc["abstract"])
        contents.append(doc["content"])
        publish_dates.append(doc["published"])
    
    logger.info(f"Extracted {len(titles)} documents from source")
    return titles, abstracts, contents, publish_dates

def process_content(contents):
    """
    Process content by generating summaries and keywords.
    
    Args:
        contents (list): List of content strings
        
    Returns:
        tuple: (summaries, keywords)
    """
    logger.info("Processing content: generating summaries...")
    
    # Generate summaries
    summarizer = BulletPointSummarizer()
    summaries = []
    for i, content in enumerate(contents):
        logger.info(f"Processing summary {i+1}/{len(contents)}")
        summary = summarizer.create_summary(content)
        summaries.append(summary)
    
    logger.info("Processing content: extracting keywords...")
    
    # Extract keywords
    keyword_maker = KeywordMaker()
    keywords = []
    for i, summary in enumerate(summaries):
        logger.info(f"Processing keywords {i+1}/{len(summaries)}")
        keyword_list = keyword_maker.create_keywords_from_content(summary)
        keywords.append(keyword_list)
    
    return summaries, keywords

def save_processed_data(titles, abstracts, contents, summaries, keywords, publish_dates):
    """
    Save processed data to JSON file and target MongoDB.
    
    Args:
        titles, abstracts, contents, summaries, keywords, publish_dates: Data lists
    """
    logger.info("Saving processed data...")
    
    # Prepare data structure
    data = []
    for t, a, c, s, k, p in zip(titles, abstracts, contents, summaries, keywords, publish_dates):
        data.append({
            "title": t,
            "abstract": a,
            "content": c,
            "summary": s,
            "keywords": k,
            "published": p
        })
    
    # Save to JSON file
    with open(Config.OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info(f"Data saved to {Config.OUTPUT_JSON_FILE}")
    
    # Save to target MongoDB
    client = pymongo.MongoClient(Config.get_mongodb_target_uri())
    db = client[Config.TARGET_DB_NAME]
    collection = db[Config.TARGET_COLLECTION_NAME]
    
    # Clear existing data and insert new data
    collection.delete_many({})
    collection.insert_many(data)
    logger.info(f"Data saved to MongoDB: {Config.TARGET_DB_NAME}.{Config.TARGET_COLLECTION_NAME}")

def generate_embeddings():
    """
    Generate and store embeddings in Qdrant.
    
    Returns:
        tuple: (qdrant_content, embeddings)
    """
    logger.info("Generating embeddings...")
    
    # Get data from MongoDB
    data = get_mongodb_data(Config.get_mongodb_target_uri())
    
    # Generate embeddings
    qdrant_content, embeddings = generate_embeddings_from_field(
        data,
        field_name="content",
        collection_name=Config.QDRANT_COLLECTION_NAME,
        qdrant_url=Config.QDRANT_URL,
        qdrant_api_key=Config.QDRANT_API_KEY
    )
    
    return qdrant_content, embeddings

def generate_insights(embeddings):
    """
    Generate insights for each keyword.
    
    Args:
        embeddings: Embedding model instance
    """
    logger.info("Generating insights...")
    
    # Initialize clients
    qdrant_client = QdrantClient(url=Config.QDRANT_URL, api_key=Config.QDRANT_API_KEY)
    mongo_client = MongoClient(Config.get_mongodb_target_uri())
    insight_db = mongo_client[Config.INSIGHT_DB_NAME]
    
    # Initialize services
    analyzer = AITrendAnalyzer()
    translator = Translator()
    
    for k, keyword in enumerate(Config.ANALYSIS_KEYWORDS):
        logger.info(f"Processing keyword: {keyword}")
        
        # Search for relevant content
        query_vector = embeddings.embed_query(f"Most relevant contents with keyword {keyword}")
        results = qdrant_client.search(
            collection_name=Config.QDRANT_COLLECTION_NAME,
            query_vector=query_vector,
            limit=Config.SEARCH_LIMIT
        )
        
        # Extract content and dates
        contents, dates = [], []
        for result in results:
            contents.append(result.payload["page_content"])
            dates.append(result.payload["metadata"]["date"])
        
        # Sort by date
        zipped = sorted(zip(dates, contents), key=lambda x: x[0])
        formatted_content = "\n\n".join([f"Date: {d}\nContent: {c}" for d, c in zipped])
        
        # Generate insights
        insight = analyzer.analyze(formatted_content, keyword)
        vi_insight = translator.translate(insight)
        
        # Prepare document
        doc = {
            "llms": Config.OPENAI_MODEL,
            "keyword": keyword,
            "content": contents,
            "date": dates,
            "en_insight": insight,
            "vi_insight": vi_insight
        }
        
        # Save to MongoDB
        collection_name = f"Topic{k+1}"
        insight_db[collection_name].insert_one(doc)
        logger.info(f"Insight saved to collection: {collection_name}")

def main():
    """
    Main execution function.
    """
    try:
        # Validate configuration
        Config.validate_config()
        logger.info("Configuration validated successfully")
        
        # Extract source data
        titles, abstracts, contents, publish_dates = extract_source_data()
        
        # Process content
        summaries, keywords = process_content(contents)
        
        # Save processed data
        save_processed_data(titles, abstracts, contents, summaries, keywords, publish_dates)
        
        # Generate embeddings
        qdrant_content, embeddings = generate_embeddings()
        
        # Generate insights
        generate_insights(embeddings)
        
        logger.info("✅ Pipeline completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()