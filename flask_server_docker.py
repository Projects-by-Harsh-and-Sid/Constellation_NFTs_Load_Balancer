from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import tempfile
from embeddings import get_embeddings
import os
from embeddings import get_documents
from flask_cors import CORS
import requests
import jwt
import datetime
from functools import wraps



app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'chatwithme')
CHAT_URL = os.environ.get('CHAT_URL', 'http://localhost:8000/query')
chat_sessions = {}

def generate_jwt_token(model, embeddings, document):
    session_id = str(len(chat_sessions) + 1)
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
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
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
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(tmpdirname, filename)
                file.save(filepath)
            else:
                return jsonify({'error': f'File type not allowed: {file.filename}'}), 400
        
        # Generate embeddings and documents for all files in the directory
        embeddings = get_embeddings(tmpdirname)
        document_list = get_documents(tmpdirname)
        # print("Embeddings:", embeddings)
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
    
    return jsonify(result)



if __name__ == '__main__':
    # app.run(port=5996,debug=True,host='0.0.0.0')
    app.run(port=5996,debug=True,ssl_context=('certificate.crt','private.key'))