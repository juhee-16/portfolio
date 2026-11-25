import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "Nuri Town"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")  # GMS 등 프록시 사용 시 대비
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    DATA4LIBRARY_API_KEY: str = os.getenv("DATA4LIBRARY_API_KEY", "")
    KAKAO_REST_API_KEY: str = os.getenv("KAKAO_REST_API_KEY", "")
    TOUR_API_KEY: str = os.getenv("TOUR_API_KEY", "")

settings = Settings()