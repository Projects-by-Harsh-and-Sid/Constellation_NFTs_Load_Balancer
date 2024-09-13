import numpy as np
from llama_index.core import SimpleDirectoryReader, Document
from llama_index.embeddings.langchain import LangchainEmbedding
from langchain.embeddings import HuggingFaceEmbeddings
from llama_index.llms.ollama import Ollama

def get_embeddings(directory):
    documents = SimpleDirectoryReader(directory).load_data()
    embed_model = LangchainEmbedding(HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"))
    texts = [doc.text for doc in documents]
    embeddings = embed_model.get_text_embedding_batch(texts)
    embeddings_array = np.array(embeddings)
    return embeddings

def document_to_dict(doc):
    if isinstance(doc, Document):
        return {
            'id': doc.doc_id,  # Use doc_id instead of id_
            'text': doc.text,
            # You can include other attributes here as neede
        }
    return doc  # Return as-is if it's not a Document object

def get_documents(directory):
    documents = SimpleDirectoryReader(directory).load_data()
    documents_list = [document_to_dict(doc) for doc in documents]
    return documents_list

