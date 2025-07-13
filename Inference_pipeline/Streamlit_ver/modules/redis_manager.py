import redis
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self, redis_url: str = "redis://localhost:6379", db: int = 0):
        """
        Initialize Redis manager
        
        Args:
            redis_url: Redis connection URL
            db: Redis database number
        """
        try:
            self.redis_client = redis.from_url(redis_url, db=db, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
            # Initialize query cache manager
            from modules.query_cache import QueryCacheManager
            self.query_cache = QueryCacheManager(redis_url, db=db+1)
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise e
    
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        return str(uuid.uuid4())
    
    def save_message(self, session_id: str, role: str, content: str, sources: List[Dict] = None):
        """
        Save message to Redis
        
        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            content: Message content
            sources: Sources for assistant messages
        """
        try:
            message_data = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "sources": sources or []
            }
            
            # Use Redis list to store messages for each session
            key = f"chat_history:{session_id}"
            self.redis_client.lpush(key, json.dumps(message_data))
            
            # Set expiration (15 mins)
            self.redis_client.expire(key, 15 * 60)
            
            logger.info(f"Message saved for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
    
    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """
        Get chat history for a session
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of messages
        """
        try:
            key = f"chat_history:{session_id}"
            messages = self.redis_client.lrange(key, 0, limit - 1)
            
            # Parse JSON and reverse to get chronological order
            parsed_messages = []
            for msg in reversed(messages):
                try:
                    parsed_messages.append(json.loads(msg))
                except json.JSONDecodeError:
                    continue
            
            return parsed_messages
            
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}")
            return []
    
    def get_last_n_conversations(self, session_id: str, n: int = 5) -> List[Dict]:
        """
        Get last N conversation pairs (user question + assistant answer)
        
        Args:
            session_id: Session identifier
            n: Number of conversation pairs to retrieve
            
        Returns:
            List of conversation pairs
        """
        try:
            # Get more messages to ensure we have enough pairs
            all_messages = self.get_chat_history(session_id, limit=n * 2 + 10)
            
            conversations = []
            temp_user_msg = None
            
            for message in all_messages:
                if message["role"] == "user":
                    temp_user_msg = message
                elif message["role"] == "assistant" and temp_user_msg:
                    conversations.append({
                        "user": temp_user_msg,
                        "assistant": message
                    })
                    temp_user_msg = None
                    
                    if len(conversations) >= n:
                        break
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error retrieving conversations: {e}")
            return []
    
    def clear_session_history(self, session_id: str):
        """Clear chat history for a session"""
        try:
            key = f"chat_history:{session_id}"
            self.redis_client.delete(key)
            logger.info(f"Chat history cleared for session {session_id}")
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session"""
        try:
            key = f"chat_history:{session_id}"
            total_messages = self.redis_client.llen(key)
            
            return {
                "total_messages": total_messages,
                "user_messages": total_messages // 2,
                "assistant_messages": total_messages // 2
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {"total_messages": 0, "user_messages": 0, "assistant_messages": 0}
    
    # New cache-related methods
    def get_cached_response(self, query: str, source: str) -> Optional[Dict]:
        """Get cached response for query"""
        return self.query_cache.get_cached_response(query, source)
    
    def cache_response(self, query: str, source: str, response: str, sources: List[Dict], 
                      optimized_query: str = None, ttl: int = 600) -> None:
        """Cache response for query"""
        self.query_cache.cache_response(query, source, response, sources, optimized_query, ttl)
    
    def find_similar_cached_queries(self, query: str, source: str, limit: int = 5) -> List[Dict]:
        """Find similar cached queries"""
        return self.query_cache.find_similar_cached_queries(query, source, limit)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return self.query_cache.get_cache_stats()
    
    def clear_cache(self) -> None:
        """Clear all cached queries"""
        self.query_cache.clear_cache()
    
    def clear_expired_cache(self) -> int:
        """Clear expired cache entries"""
        return self.query_cache.clear_expired_cache()