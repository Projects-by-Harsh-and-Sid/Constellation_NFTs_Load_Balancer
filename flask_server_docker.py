from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import tempfile
from app.module.embeddings import get_embeddings
import os
from app.module.embeddings import get_documents
from flask_cors import CORS
import requests
import jwt
import datetime
from functools import wraps
from random import randint
import datetime
import secrets



app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'chatwithme') # do random key generation
CHAT_URL = os.environ.get('CHAT_URL', 'http://localhost:8000/query')
MASTER_API_KEY = os.environ.get('MASTER_API_KEY', '1234567890')
chat_sessions = {}
temp_api_keys = {}



def generate_temp_api_key(model, embeddings, document):
    temp_key = secrets.token_urlsafe(32)
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    temp_api_keys[temp_key] = {
        'expiration': expiration,
        'model': model,
        'embeddings': embeddings,
        'document': document
    }
    return temp_key

def clean_expired_api_keys():
    now = datetime.datetime.utcnow()
    expired_keys = [key for key, data in temp_api_keys.items() if data['expiration'] < now]
    for key in expired_keys:
        del temp_api_keys[key]
        
def api_key_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'message': 'Missing API key'}), 401
        
        clean_expired_api_keys()
        
        if api_key == MASTER_API_KEY or api_key in temp_api_keys:
            return f(*args, **kwargs)
        else:
            return jsonify({'message': 'Invalid API key'}), 401
    return decorated

def generate_jwt_token(model, embeddings, document):
    session_id = str(randint(1000000000, 99999999999))
    chat_sessions[session_id] = {
        'model': model,
        'embeddings': embeddings,
        'document': document
    }
    payload = {
        'session_id': session_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        print("Token:", token)
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            print("data",data)
            session_id = data['session_id']
            if session_id not in chat_sessions:
                return jsonify({'message': 'Invalid session'}), 401
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(session_id, *args, **kwargs)
    return decorated

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           
           
def make_request(query, embeddings, documents_list,url):
    target_url = url
    
    # Convert NumPy array to list for JSON serialization
    embeddings_list = embeddings
    
    # Prepare the data to be sent
    # documents_list = [document_to_dict(doc) for doc in documents]
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
        
        
@app.route('/get_temp_api_key', methods=['POST'])
def get_temp_api_key():
    master_key = request.headers.get('X-Master-API-Key')
    if master_key != MASTER_API_KEY:
        return jsonify({'message': 'Invalid master API key'}), 401
    
    data = request.json
    model = data.get('model')
    embeddings = data.get('embeddings')
    document = data.get('document')

    if not all([model, embeddings, document]):
        return jsonify({'error': 'Missing required fields (model, embeddings, document)'}), 400
    
    temp_key = generate_temp_api_key(model, embeddings, document)
    return jsonify({'temp_api_key': temp_key}), 200

@app.route('/api/start_chat', methods=['POST'])
@api_key_required
def api_initiate_chat():
    api_key = request.headers.get('X-API-Key')
    
    if api_key == MASTER_API_KEY:
        return jsonify({'error': 'Master API key cannot be used to start a chat. Please use a temporary API key.'}), 400
    
    if api_key not in temp_api_keys:
        return jsonify({'error': 'Invalid API key'}), 401
    
    key_data = temp_api_keys[api_key]
    model = key_data['model']
    embeddings = key_data['embeddings']
    document = key_data['document']

    jwt_token = generate_jwt_token(model, embeddings, document)

    return jsonify({
        'jwt_token': jwt_token,
        'url': CHAT_URL
    }), 200
    
@app.route('/api/chat', methods=['POST'])
@token_required
def api_chat(session_id):
    result = None
    if request.method == 'POST':
        data = request.json
        query = data.get('query', '')
        url = data.get('url', '')
        session_data = chat_sessions[session_id]
        
        model = session_data['model']
        embeddings = session_data['embeddings']
        document = session_data['document']
        
        result = make_request(query, embeddings, document, url)

        
    return jsonify(result)


@app.route('/make_embedding', methods=['POST'])
def make_embedding():
    print("Request Headers:", request.headers)
    print("Request Data:", request.data)
    print("Request Files:", request.files)
    print("Request Form:", request.form)
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('file')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    print("Files:", files)
    with tempfile.TemporaryDirectory() as tmpdirname:
        saved_files = []
        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                filename, extension = os.path.splitext(original_filename)
                unique_filename = f"{filename}_{i}{extension}"
                filepath = os.path.join(tmpdirname, unique_filename)
                file.save(filepath)
                print(f"Saved file: {filepath}")
                saved_files.append(unique_filename)
            else:
                return jsonify({'error': f'File type not allowed: {file.filename}'}), 400
        
        # List all files in the temporary directory
        print("Files in temporary directory:", os.listdir(tmpdirname))
        
        # Generate embeddings and documents for all files in the directory
        embeddings = get_embeddings(tmpdirname)
        document_list = get_documents(tmpdirname)
        # print("Embeddings:", embeddings)
        
        print("Document List:", len(document_list))
        print("Embeddings:", len(embeddings))
        result = {
            'message': f'{len(files)} files processed successfully',
            'embeddings': embeddings,
            'document': document_list
        }
        # print("Result:", result)
        return jsonify(result), 200
    
@app.route('/start_chat', methods=['POST'])
def initiate_chat():
    data = request.json
    # print("Data:", data)
    model = data.get('model')
    embeddings = data.get('embeddings')
    document = data.get('document')
    # query = data.get('query')

    if not all([model, embeddings, document]):
        return jsonify({'error': 'Missing required fields'}), 400

    jwt_token = generate_jwt_token(model, embeddings, document)
    print("JWT Token:", jwt_token)

    return jsonify({
        'jwt_token': jwt_token,
        'url': CHAT_URL
    }), 200


@app.route('/query')
def hello():
    return "https://127.0.0.1:5000"

def covert_list_to_dic(doc):
    doc_list = []
    for i in doc:
        dict_doc = {}
        dict_doc[i[0][0]] = i[0][1]
        dict_doc[i[1][0]] = i[1][1]
        doc_list.append(dict_doc)
    return doc_list        
        

@app.route('/chat',methods=['POST'])
@token_required
def chat(session_id):
    result = None
    if request.method == 'POST':
        data = request.json  # This will parse the JSON data
        query = data.get('query', '')
        url = data.get('url', '')
        session_data = chat_sessions[session_id]
        
        # document = data.get('document', [])
        # embeddings = data.get('embeddings', [[]])
        # print("document:", session_data['document'])
        model = session_data['model']
        embeddings = session_data['embeddings']
        document = session_data['document']
        # document_list = covert_list_to_dic(document)
        # print(document_list)
        result = make_request(query,embeddings,document,url)
        # print("Result:", result)
    return jsonify(result)



if __name__ == '__main__':
    # app.run(port=5996,debug=True,host='0.0.0.0')
    app.run(port=5996,debug=True,ssl_context=('certificate.crt','private.key'))