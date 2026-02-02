from typing import Any, Dict, List, Union

from langchain_community.vectorstores.chroma import Chroma
from langchain_community.vectorstores.pgvector import PGVector
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.core.constants import APP_NAME, RAG_MAX_CONTEXT_CHARS, RAG_TOP_K
from src.core.logging import get_logger
from src.models import SETTINGS

logger = get_logger(APP_NAME)

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a legal-document assistant. Use only the provided context. "
            "If the answer is not in the context, say you don't know.",
        ),
        (
            "human",
            "Question:\n{question}\n\nContext:\n{context}\n\nAnswer clearly and concisely.",
        ),
    ]
)


def answer_with_rag(
    vectorstore: Union[PGVector, Chroma],
    question: str,
    k: int = RAG_TOP_K,
) -> Dict[str, Any]:
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    retrieved_docs = retriever.get_relevant_documents(question)

    parts: List[str] = []
    total = 0
    for doc in retrieved_docs:
        chunk = (
            f"[Source: {doc.metadata.get('source')} | Page: {doc.metadata.get('page')}]\n"
            f"{doc.page_content}"
        )
        if total + len(chunk) > RAG_MAX_CONTEXT_CHARS:
            break
        parts.append(chunk)
        total += len(chunk)

    context = "\n\n---\n\n".join(parts)

    llm = ChatOpenAI(model=SETTINGS.chat_model, temperature=0.2)
    msg = RAG_PROMPT.format_messages(question=question, context=context)
    resp = llm.invoke(msg)

    sources = [
        {
            "source": doc.metadata.get("source"),
            "page": doc.metadata.get("page"),
            "used_ocr": doc.metadata.get("used_ocr"),
        }
        for doc in retrieved_docs
    ]

    return {"answer": resp.content, "sources": sources}
