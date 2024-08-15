from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import tempfile
from embeddings import get_embeddings
import os
from embeddings import get_documents
from flask_cors import CORS
import requests



app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# @app.route('/make_embedding', methods=['POST'])
# def make_embedding():
#     if 'file' not in request.files:
#         return jsonify({'error': 'No file part'}), 400
    
#     file = request.files['file']
    
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'}), 400
    
#     if file and allowed_file(file.filename):
#         filename = secure_filename(file.filename)
        
#         # Create a temporary directory
#         with tempfile.TemporaryDirectory() as tmpdirname:
#             # Save the file to the temporary directory
#             filepath = os.path.join(tmpdirname, filename)
#             file.save(filepath)
            
#             # Generate embeddings
#             embeddings = get_embeddings(tmpdirname)
#             document_list = get_documents(tmpdirname)
            
#             # Convrt numpy array to list for JSON serialization
            
            
#             return jsonify({
#                 'message': f'File {filename} processed successfully',
#                 'embeddings': embeddings,
#                 'document': document_list
#             }), 200
    
#     return jsonify({'error': 'File type not allowed'}), 400
@app.route('/make_embedding', methods=['POST'])
def make_embedding():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('file')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Create a temporary directory
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
        
        return jsonify({
            'message': f'{len(files)} files processed successfully',
            'embeddings': embeddings,
            'document': document_list
        }), 200

def make_request(query, embeddings, documents_list):
    target_url = 'http://localhost:8000/query'
    
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
def chat():
    result = None
    if request.method == 'POST':
        data = request.json  # This will parse the JSON data
        query = data.get('query', '')
        document = data.get('document', [])
        embeddings = data.get('embeddings', [[]])
        document_list = covert_list_to_dic(document)
        # print(document_list)
        result = make_request(query,embeddings,document_list)
    
    return jsonify(result)



if __name__ == '__main__':
    # app.run(port=5996,debug=True,host='0.0.0.0')
    app.run(port=5996,debug=True,ssl_context=('certificate.crt','private.key'))