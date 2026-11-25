import os, requests
from dotenv import load_dotenv
load_dotenv()

res = requests.get(
    "http://data4library.kr/api/srchBooks",
    params={"authKey": os.getenv("DATA4LIBRARY_API_KEY"), "keyword": "그림책", "pageSize": 3, "format": "json"}
)
print(res.json())