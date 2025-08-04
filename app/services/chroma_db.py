import chromadb
from langchain_community.document_loaders import PyPDFLoader
from sentence_transformers import SentenceTransformer

from models import db_models

client = chromadb.PersistentClient(path=".chroma_store/")

documents_collection = client.get_or_create_collection(name="documents")
notes_collection = client.get_or_create_collection(name="notes")

embedding_model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    cache_folder=".embedding_model/",
)


async def chroma_save_document(doc: db_models.Document):
    loader = PyPDFLoader(doc.file_path)

    doc_texts = []
    async for page in loader.alazy_load():
        doc_texts.append(page.page_content)

    embeddings = embedding_model.encode(doc_texts, convert_to_numpy=True).tolist()

    for i, (text, embedding) in enumerate(zip(doc_texts, embeddings)):
        documents_collection.add(
            ids=[f"{doc.id}_{i}"],
            documents=[text],
            embeddings=[embedding],
            metadatas=[{"doc_id": doc.id, "page_num": i}],
        )


def chroma_remove_document(doc_id: int):
    docs = documents_collection.get(where={"doc_id": doc_id})

    if not docs["ids"]:
        return

    documents_collection.delete(ids=docs["ids"])


def chroma_query_documents(doc_id: int, query: str, top_k: int = 5):
    results = documents_collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"doc_id": doc_id},
    )

    top_docs = results.get("documents", [[]])

    if not top_docs:
        return

    return top_docs[0]


def chroma_save_note(note_id: int, doc_id: int, content: str):
    embedding = embedding_model.encode(content, convert_to_numpy=True).tolist()

    notes_collection.add(
        ids=str(note_id),
        documents=content,
        embeddings=embedding,
        metadatas={"doc_id": doc_id},
    )


def chroma_remove_note(note_id: int):
    documents_collection.delete(ids=[str(note_id)])


def chroma_query_note(doc_id: int, query: str, top_k: int = 5):
    results = notes_collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"doc_id": doc_id},
    )

    top_notes = results.get("documents", [[]])

    if not top_notes:
        return

    return top_notes[0]


def chroma_update_note(note_id: int, content: str):
    new_embed = embedding_model.encode(content, convert_to_numpy=True).tolist()

    notes_collection.update(ids=str(note_id), embeddings=new_embed, documents=content)
