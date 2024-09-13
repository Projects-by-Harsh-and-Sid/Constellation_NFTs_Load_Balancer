
from app import app

from flask import request, jsonify


import requests
import PyPDF2  # For handling PDFs
import tempfile
from app.module.embeddings import get_embeddings, get_documents
from werkzeug.utils import secure_filename

from app.module.helper_functions import generate_api_key, allowed_file, api_key_required, generate_jwt_token, token_required

import os

CHAT_URL = app.config['CHAT_URL']
MASTER_API_KEY = app.config['MASTER_API_KEY']
UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']


#  to be replace by reddis or on chain session management storage
api_keys            = app.config['API_KEYS'] 
chat_sessions       = app.config['CHAT_SESSIONS']




########################## converting PDF to text ##########################

# Endpoint to convert PDF to text
@app.route('/convert_pdf', methods=['POST'])
def convert_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part provided'}), 400

    file = request.files['file']
    
    if file and allowed_file(file.filename) and file.filename.lower().endswith('.pdf'):
        try:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text()
            return jsonify({'text': text}), 200
        except Exception as e:
            return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Invalid file type. Only PDF files are allowed for this endpoint.'}), 400



############################ generating API Key ############################


# # Modified /generate_key to accept text string instead of file data
# @app.route('/generate_key', methods=['POST'])
# def generate_key():
    
    
#     data    = request.get_json()
    
#     if not data or 'text' not in data:
#         return jsonify({'error': 'No text data provided'}), 400

#     text_content = data['text']

#     with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp_file:
#         temp_file.write(text_content)
#         temp_file_path = temp_file.name

#     try:
#         embeddings = get_embeddings(temp_file_path)
#         documents = get_documents(temp_file_path)
#     finally:
#         os.unlink(temp_file_path)

#     api_key = generate_api_key()
#     api_keys[api_key] = {
#         'embeddings': embeddings,
#         'documents': documents
#     }

#     return jsonify({'api_key': api_key}), 200



@app.route('/generate_key', methods=['POST'])
def generate_key():
    data = request.get_json()
    
    if not data or 'AI_Data' not in data or 'baseModel' not in data:
        return jsonify({'error': 'AI_Data and baseModel are required'}), 400

    # Prepare the content for the temporary file
    content = f"AI_Data: {data['AI_Data']}\n"
    content += f"baseModel: {data['baseModel']}\n"

    # Add optional fields if they exist
    optional_fields = [
        'collection owner', 'collection name', 'collection description',
        'nft name', 'nft description', 'nft owner'
    ]
    
    additional_content = []
    for field in optional_fields:
        if field in data:
            additional_content.append(f"{field}: {data[field]}")
    
    if additional_content:
        content += "Additional Data: " + ", ".join(additional_content) + "\n"

    content += "\n"  # Add a newline before the main AI_Data content

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp_file:
        temp_file.write(content)
        temp_file_path = temp_file.name

    try:
        embeddings = get_embeddings(temp_file_path)
        documents = get_documents(temp_file_path)
    finally:
        os.unlink(temp_file_path)

    api_key = generate_api_key()
    api_keys[api_key] = {
        'embeddings': embeddings,
        'documents': documents
    }

    return jsonify({'api_key': api_key}), 200







@app.route('/start_chat', methods=['POST'])
@api_key_required
def start_chat():
    api_key = request.headers.get('X-API-Key')
    jwt_token = generate_jwt_token(api_key)

    return jsonify({
        'jwt_token': jwt_token,
        'url': CHAT_URL
    }), 200

@app.route('/chat', methods=['POST'])
@token_required
def chat(api_key):
    data = request.json
    query = data.get('query', '')
    url = data.get('url', '')

    session_data = api_keys[api_key]
    embeddings = session_data['embeddings']
    documents = session_data['documents']

    result = make_request(query, embeddings, documents, url)
    return jsonify(result)

def make_request(query, embeddings, documents, url):
    data = {
        'query': query,
        'embeddings': embeddings,
        'document': documents
    }

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        response_data = response.json()
        return {
            'query': query,
            'answer': response_data.get('answer', 'No answer provided')
        }
    except requests.RequestException as e:
        return {
            'query': query,
            'answer': f"An error occurred: {str(e)}"
        }