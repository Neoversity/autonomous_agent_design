
import chromadb
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ============================================================
# CONFIG
# ============================================================

CHROMA_DIR = Path("/content/hw3_mas/chroma_db")

client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

collection = client.get_or_create_collection(
    name="support_knowledge"
)


# ============================================================
# KNOWLEDGE BASE
# ============================================================

KNOWLEDGE_DOCS = [
    {
        "id": "refund-policy",
        "text": (
            "Повернення коштів за невикористаний період можливе, "
            "якщо послуга не була використана після дати списання. "
            "Стандартний термін обробки повернення — 3–5 робочих днів."
        ),
        "source": "faq://refund-policy",
    },
    {
        "id": "device-se23",
        "text": (
            "Помилка SE-23 після оновлення прошивки може означати "
            "помилку ініціалізації пристрою. Рекомендовано виконати "
            "повне перезавантаження, перевірити живлення та повторно "
            "встановити актуальну версію прошивки."
        ),
        "source": "kb://device-errors/se23",
    },
    {
        "id": "support-sla",
        "text": (
            "Час відповіді служби підтримки залежить від тарифу: "
            "Gold — до 1 години, Silver — до 4 годин, "
            "Standard — до 24 годин."
        ),
        "source": "faq://support-sla",
    },
    {
        "id": "billing-payment",
        "text": (
            "Якщо платіж за тариф не був списаний, billing-агент "
            "повинен перевірити тікет, дані клієнта та статус платежу. "
            "Не слід повторно проводити списання без перевірки."
        ),
        "source": "kb://billing/payment-failure",
    },
]


# ============================================================
# INITIALIZE COLLECTION
# ============================================================

def initialize_knowledge_base():
    """
    Ініціалізує ChromaDB knowledge base.
    Повторний запуск не створює дублікати.
    """

    existing = collection.get()

    existing_ids = set(existing.get("ids", []))

    new_docs = [
        doc
        for doc in KNOWLEDGE_DOCS
        if doc["id"] not in existing_ids
    ]

    if not new_docs:
        return 0

    collection.add(
        ids=[doc["id"] for doc in new_docs],
        documents=[doc["text"] for doc in new_docs],
        metadatas=[
            {
                "source": doc["source"],
            }
            for doc in new_docs
        ],
    )

    return len(new_docs)


# ============================================================
# PYDANTIC SCHEMA
# ============================================================

class KnowledgeSearchInput(BaseModel):
    query: str = Field(
        description="Запит для семантичного пошуку у knowledge base"
    )

    top_k: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Кількість документів для повернення"
    )


# ============================================================
# RAG TOOL
# ============================================================

@tool(args_schema=KnowledgeSearchInput)
def search_knowledge(
    query: str,
    top_k: int = 3,
) -> str:
    """
    Виконує семантичний пошук у ChromaDB knowledge base.

    Використовується researcher-агентом як Agentic RAG tool.
    """

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not documents:
        return "No relevant knowledge found."

    formatted = []

    for i, document in enumerate(documents):
        metadata = (
            metadatas[i]
            if i < len(metadatas)
            else {}
        )

        distance = (
            distances[i]
            if i < len(distances)
            else None
        )

        formatted.append(
            {
                "text": document,
                "source": metadata.get(
                    "source",
                    "unknown"
                ),
                "distance": distance,
            }
        )

    import json

    return json.dumps(
        formatted,
        ensure_ascii=False,
        indent=2,
    )


# Ініціалізація при імпорті
initialize_knowledge_base()
