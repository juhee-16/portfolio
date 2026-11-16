"""누리과정 JSON을 벡터DB(Chroma) 컬렉션에 색인한다."""
import json
import os

import chromadb
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import config

load_dotenv()

GMS_BASE_URL = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/"
CURRICULUM_PATH = config.BASE_DIR / "data" / "nuri_curriculum.json"


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=config.EMBED_MODEL,
        api_key=os.environ["GMS_KEY"],
        base_url=GMS_BASE_URL,
    )


def get_collection(name: str):
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    # 임베딩은 우리가 직접 계산해서 넣으므로 chroma 기본 임베딩은 쓰지 않는다
    return client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})


def load_items() -> list[dict]:
    """JSON에서 내용(content) 한 줄씩을 항목으로 꺼낸다."""
    with open(CURRICULUM_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for a in data["areas"]:
        for c in a["categories"]:
            for x in c["contents"]:
                items.append({
                    "area_id": a["area_id"],
                    "area": a["area"],
                    "category_id": c["category_id"],
                    "category": c["category"],
                    "content_id": x["content_id"],
                    "content": x["content"],
                })
    return items


def build_chunks(items: list[dict]) -> list[dict]:
    """항목을 청크로 나눈다. 색인 텍스트에 영역·내용범주를 함께 넣는다."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
    )
    chunks = []
    for it in items:
        header = f"[{it['area']} > {it['category']}] "
        for n, piece in enumerate(splitter.split_text(it["content"])):
            chunks.append({
                "id": f"{it['content_id']}#{n}",   # 고정 ID → 재실행해도 안 늘어남
                "text": header + piece,
                "metadata": {
                    "area_id": it["area_id"],
                    "area": it["area"],
                    "category_id": it["category_id"],
                    "category": it["category"],
                    "content_id": it["content_id"],
                    "source": "누리과정",
                },
            })
    return chunks


def index_nuri() -> dict:
    items = load_items()
    chunks = build_chunks(items)
    col = get_collection(config.NURI_COLLECTION)

    vectors = get_embeddings().embed_documents([c["text"] for c in chunks])
    col.upsert(   # add가 아니라 upsert: 같은 ID면 덮어쓴다
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=vectors,
        metadatas=[c["metadata"] for c in chunks],
    )
    return {"loaded": len(items), "chunks": len(chunks), "collection": col.count()}

if __name__ == "__main__":
    result = index_nuri()
    print(f"로드한 항목 수: {result['loaded']}")
    print(f"만든 청크 수:  {result['chunks']}")
    print(f"컬렉션 건수:   {result['collection']}")
    sample = get_collection(config.NURI_COLLECTION).get(limit=1)
    print("--- 색인 텍스트 1건 ---")
    print(sample["documents"][0])
    print(sample["metadatas"][0])