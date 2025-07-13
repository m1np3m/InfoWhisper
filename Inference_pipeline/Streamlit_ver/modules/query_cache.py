import redis
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class QueryCacheManager:
    def __init__(self, redis_url: str = "redis://localhost:6379", db: int = 1):
        """
        Initialize Query Cache Manager
        
        Args:
            redis_url: Redis connection URL
            db: Redis database number (use different db for cache)
        """
        try:
            self.redis_client = redis.from_url(redis_url, db=db, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis query cache connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for query cache: {e}")
            raise e
    
    def _generate_cache_key(self, query: str, source: str) -> str:
        """
        Generate cache key from query and source
        
        Args:
            query: User query
            source: Data source name
            
        Returns:
            Cache key string
        """
        # Normalize query (lowercase, strip whitespace)
        normalized_query = query.lower().strip()
        
        # Create hash from query and source
        content = f"{normalized_query}:{source}"
        cache_key = hashlib.md5(content.encode()).hexdigest()
        
        return f"query_cache:{cache_key}"
    
    def get_cached_response(self, query: str, source: str) -> Optional[Dict]:
        """
        Get cached response for query
        
        Args:
            query: User query
            source: Data source name
            
        Returns:
            Cached response data or None if not found
        """
        try:
            cache_key = self._generate_cache_key(query, source)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                response_data = json.loads(cached_data)
                logger.info(f"Cache hit for query: {query[:50]}...")
                return response_data
            
            logger.info(f"Cache miss for query: {query[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached response: {e}")
            return None
    
    def cache_response(self, query: str, source: str, response: str, sources: List[Dict], 
                      optimized_query: str = None, ttl: int = 600) -> None:
        """
        Cache response for query
        
        Args:
            query: Original user query
            source: Data source name
            response: Generated response
            sources: Source documents
            optimized_query: Optimized query if available
            ttl: Time to live in seconds (default: 10 minutes)
        """
        try:
            cache_key = self._generate_cache_key(query, source)
            
            cache_data = {
                "original_query": query,
                "optimized_query": optimized_query or query,
                "response": response,
                "sources": sources,
                "source_collection": source,
                "cached_at": datetime.now().isoformat(),
                "ttl": ttl
            }
            
            # Cache with TTL
            self.redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(cache_data)
            )
            
            logger.info(f"Response cached for query: {query[:50]}... (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
    
    def is_similar_query(self, query1: str, query2: str, threshold: float = 0.8) -> bool:
        """
        Check if two queries are similar using simple similarity
        
        Args:
            query1: First query
            query2: Second query
            threshold: Similarity threshold (0-1)
            
        Returns:
            True if queries are similar
        """
        try:
            # Simple similarity check using common words
            words1 = set(query1.lower().split())
            words2 = set(query2.lower().split())
            
            if not words1 or not words2:
                return False
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            similarity = len(intersection) / len(union)
            return similarity >= threshold
            
        except Exception as e:
            logger.error(f"Error checking query similarity: {e}")
            return False
    
    def find_similar_cached_queries(self, query: str, source: str, limit: int = 5) -> List[Dict]:
        """
        Find similar cached queries
        
        Args:
            query: User query
            source: Data source name
            limit: Maximum number of similar queries to return
            
        Returns:
            List of similar cached queries
        """
        try:
            # Get all cache keys for this source
            pattern = f"query_cache:*"
            cache_keys = self.redis_client.keys(pattern)
            
            similar_queries = []
            
            for key in cache_keys:
                try:
                    cached_data = self.redis_client.get(key)
                    if cached_data:
                        response_data = json.loads(cached_data)
                        
                        # Check if it's the same source
                        if response_data.get("source_collection") == source:
                            original_query = response_data.get("original_query", "")
                            
                            # Check similarity
                            if self.is_similar_query(query, original_query):
                                similar_queries.append({
                                    "original_query": original_query,
                                    "cached_data": response_data,
                                    "cache_key": key
                                })
                                
                                if len(similar_queries) >= limit:
                                    break
                                    
                except json.JSONDecodeError:
                    continue
            
            return similar_queries
            
        except Exception as e:
            logger.error(f"Error finding similar queries: {e}")
            return []
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        try:
            pattern = "query_cache:*"
            cache_keys = self.redis_client.keys(pattern)
            
            total_cached = len(cache_keys)
            
            # Get memory usage info
            memory_info = self.redis_client.info('memory')
            memory_usage = memory_info.get('used_memory_human', 'N/A')
            
            return {
                "total_cached_queries": total_cached,
                "memory_usage": memory_usage,
                "cache_pattern": pattern
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"total_cached_queries": 0, "memory_usage": "N/A"}
    
    def clear_cache(self) -> None:
        """Clear all cached queries"""
        try:
            pattern = "query_cache:*"
            cache_keys = self.redis_client.keys(pattern)
            
            if cache_keys:
                self.redis_client.delete(*cache_keys)
                logger.info(f"Cleared {len(cache_keys)} cached queries")
            else:
                logger.info("No cached queries to clear")
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def clear_expired_cache(self) -> int:
        """Clear expired cache entries and return count"""
        try:
            pattern = "query_cache:*"
            cache_keys = self.redis_client.keys(pattern)
            
            expired_count = 0
            for key in cache_keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired)
                    expired_count += 1
            
            logger.info(f"Found {expired_count} expired cache entries")
            return expired_count
            
        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")
            return 0