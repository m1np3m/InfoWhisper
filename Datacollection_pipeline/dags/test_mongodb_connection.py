from pymongo import MongoClient
import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_mongodb_connection():
    """
    Test kết nối tới MongoDB Atlas và insert một document thử nghiệm
    """
    mongo_uri = os.getenv('MONGO_URI')
    
    try:
        # Thiết lập kết nối
        client = MongoClient(mongo_uri)
        
        # Kiểm tra kết nối
        client.admin.command('ping')
        print("Kết nối tới MongoDB Atlas thành công!")
        
        # Thử insert một document test
        db = client[os.getenv('MONGO_DB_NAME', 'vietnamnet_news')]
        collection = db['test_connection']
        
        test_document = {
            'message': 'Test kết nối thành công',
            'timestamp': datetime.datetime.now(),
            'source': 'Airflow test script'
        }
        
        result = collection.insert_one(test_document)
        print(f"Test document đã được insert với ID: {result.inserted_id}")
        
        # Lấy ra document vừa insert để kiểm tra
        retrieved = collection.find_one({'_id': result.inserted_id})
        print(f"Retrieved document: {retrieved}")
        
        # Xóa document test
        collection.delete_one({'_id': result.inserted_id})
        print("Đã xóa test document")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"Lỗi kết nối MongoDB: {e}")
        return False

if __name__ == "__main__":
    mongo_uri = os.getenv('MONGO_URI')
    print(f"Mongo URI: {mongo_uri}")
    test_mongodb_connection()