from logging import log
import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import TokenTextSplitter
from sentence_transformers import SentenceTransformer

from models import db_models

client = chromadb.PersistentClient(path=".chroma_store/")

documents_collection = client.get_or_create_collection(name="documents")
notes_collection = client.get_or_create_collection(name="notes")

embedding_model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    cache_folder=".embedding_model/",
)

splitter = TokenTextSplitter.from_huggingface_tokenizer(
    tokenizer=embedding_model.tokenizer,
)


async def chroma_save_document(doc: db_models.Document):
    loader = PyPDFLoader(doc.file_path)
    page_index = 0

    async for page in loader.alazy_load():
        chunks = splitter.split_text(page.page_content)

        if not chunks:
            page_index += 1
            continue

        embeddings = embedding_model.encode(chunks, convert_to_numpy=True).tolist()

        for j, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            documents_collection.add(
                ids=[f"{doc.id}_{page_index}_{j}"],
                documents=[chunk],
                embeddings=[embedding],
                metadatas=[{"doc_id": doc.id, "page_num": page_index, "chunk_num": j}],
            )
        page_index += 1
    print("document is saved to chroma")


def chroma_remove_document(doc_id: int):
    docs = documents_collection.get(where={"doc_id": doc_id})

    if not docs["ids"]:
        return

    documents_collection.delete(ids=docs["ids"])

    print("document is removed from chroma")


def chroma_query_documents(doc_id: int, query: str, top_k: int = 5):
    results = documents_collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"doc_id": doc_id},
    )

    top_docs = results.get("documents", [[]])

    if not top_docs or not top_docs[0]:
        return []

    print("document is queried from chroma")

    return top_docs[0]


def chroma_save_note(note_id: int, doc_id: int, content: str):
    embedding = embedding_model.encode(content, convert_to_numpy=True).tolist()

    notes_collection.add(
        ids=str(note_id),
        documents=content,
        embeddings=embedding,
        metadatas={"doc_id": doc_id},
    )

    print("note is saved to chroma")


def chroma_remove_note(note_id: int):
    documents_collection.delete(ids=[str(note_id)])
    print("note is removed from chroma")


def chroma_query_notes(doc_id: int, query: str, top_k: int = 5):
    results = notes_collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"doc_id": doc_id},
    )

    top_notes = results.get("documents", [[]])

    if not top_notes:
        return

    print("note is queried from chroma")

    return top_notes[0]


def chroma_update_note(note_id: int, content: str):
    new_embed = embedding_model.encode(content, convert_to_numpy=True).tolist()

    notes_collection.update(ids=str(note_id), embeddings=new_embed, documents=content)

    print("note is updated at chroma")
