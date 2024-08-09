from flask import Flask, request, render_template
import requests
from embeddings import get_embeddings
from llama_index.core import SimpleDirectoryReader
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

def make_request(query):
    target_url = 'http://localhost:8080/query'
    
    # Convert NumPy array to list for JSON serialization
    embeddings_list = embeddings.tolist()
    
    # Prepare the data to be sent
    data = {
        'query': query,
        'embeddings': embeddings_list,
        'documents': documents
    }
    
    try:
        # Send a POST request with JSON data
        response = requests.post(target_url, json=data)

        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        return {
            'status': 'success',
            'sent_query': query,
            'response_data': response.json(),
            'status_code': response.status_code
        }
    except requests.RequestException as e:
        return {
            'status': 'error',
            'message': str(e)
        }

if __name__ == '__main__':
    app.run(debug=True, port=5000)