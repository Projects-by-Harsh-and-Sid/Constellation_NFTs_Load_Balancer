import numpy as np
from llama_index.core import SimpleDirectoryReader
from llama_index.embeddings.langchain import LangchainEmbedding
from langchain.embeddings import HuggingFaceEmbeddings
from llama_index.llms.ollama import Ollama

def get_embeddings():
    documents = SimpleDirectoryReader('./documents').load_data()
    embed_model = LangchainEmbedding(HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"))
    texts = [doc.text for doc in documents]
    embeddings = embed_model.get_text_embedding_batch(texts)
    embeddings_array = np.array(embeddings)
    return embeddings

