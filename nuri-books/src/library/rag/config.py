from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  
CHROMA_DIR = BASE_DIR / "chroma_db"

NURI_COLLECTION = "nuri_curriculum"  
BOOK_COLLECTION = "picture_books"     

EMBED_MODEL = "text-embedding-3-small"

CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
TOP_K = 4
MIN_SCORE = 0.30

BOOK_CANDIDATES = 30        
BOOK_KEEP = 8                
MAX_QUERY_TERMS = 4        
COLLECTED_PATH = CHROMA_DIR / "collected_queries.json"  
BOOK_INTENT_WORDS = ("책", "그림책", "추천", "도서", "읽어", "읽을") 