from flask import Flask, request, render_template
import requests
from embeddings import get_embeddings
from llama_index.core import SimpleDirectoryReader,Document
import json

app = Flask(__name__)

# Load pre-generated embeddings and documents
embeddings = get_embeddings()
documents = SimpleDirectoryReader('./documents').load_data()

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        query = request.form.get('query', '')
        result = make_request(query)
    return render_template('input.html', result=result)

def document_to_dict(doc):
    if isinstance(doc, Document):
        return {
            'id': doc.doc_id,  # Use doc_id instead of id_
            'text': doc.text,
            # You can include other attributes here as neede
        }
    return doc  # Return as-is if it's not a Document object

def make_request(query):
    target_url = 'http://localhost:8000/query'
    
    # Convert NumPy array to list for JSON serialization
    embeddings_list = embeddings
    
    # Prepare the data to be sent
    documents_list = [document_to_dict(doc) for doc in documents]
    data = {
        'query': query,
        'embeddings': embeddings_list,
        'document': documents_list
    }
    
    try:
        # Send a POST request with JSON data
        response = requests.post(target_url, json=data)

        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        response_data = response.json()
        return {
            'query': query,
            'answer': response_data.get('answer', 'No answer provided')
        }
    except requests.RequestException as e:
        print(f"Error occurred: {str(e)}")
        return {
            'query': query,
            'answer': f"An error occurred: {str(e)}"
        }

if __name__ == '__main__':
    app.run(debug=True, port=5000)