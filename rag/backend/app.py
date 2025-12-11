import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import traceback # <--- CRITICAL IMPORT for debugging

# FINAL FIX: Correct relative imports for sibling modules
from .config import UPLOAD_FOLDER, LLM_MODEL_NAME
from .rag.vector_store import add_documents, query_index

app = Flask(__name__)
CORS(app) 

# Configuration for file uploads
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file_saved = False

        try:
            # Save file to disk
            file.save(filepath)
            file_saved = True

            # Call RAG Indexing
            chunks_indexed = add_documents(filepath)
            
            # Successful cleanup
            os.remove(filepath)
            
            return jsonify({
                'message': 'File processed successfully', 
                'chunks_indexed': chunks_indexed
            })
            
        except Exception as e:
            # --- CRITICAL ACTION: Print full traceback for debugging ---
            traceback.print_exc()
            # --------------------------------------------------------
            
            # Cleanup the saved file if the error occurred after saving
            if file_saved and os.path.exists(filepath):
                os.remove(filepath)
                
            # Return the error message to the frontend
            return jsonify({'error': f'Indexing failed: {str(e)}'}), 500

    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question')

    if not question:
        return jsonify({'error': 'No question provided'}), 400

    try:
        answer, sources = query_index(question)
        
        return jsonify({
            'answer': answer,
            'sources': sources
        })
    except Exception as e:
        # --- CRITICAL ACTION: Print full traceback for debugging ---
        traceback.print_exc()
        # --------------------------------------------------------
        
        print(f"Error querying index: {e}")
        return jsonify({'error': 'Failed to retrieve answer from RAG system. Check backend logs for traceback.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)