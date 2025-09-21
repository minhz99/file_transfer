from flask import Flask, request, render_template, send_from_directory, jsonify
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SHARED_FOLDER'] = 'shared_files'  # Thư mục chia sẻ riêng

# Đảm bảo thư mục uploads tồn tại
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# Đảm bảo thư mục shared_files tồn tại
os.makedirs(app.config['SHARED_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    # Lấy danh sách các file đã upload
    uploaded_files = os.listdir(app.config['UPLOAD_FOLDER'])
    
    # Lấy danh sách file từ thư mục chia sẻ
    shared_files = []
    if os.path.exists(app.config['SHARED_FOLDER']):
        shared_files = [f for f in os.listdir(app.config['SHARED_FOLDER']) 
                       if os.path.isfile(os.path.join(app.config['SHARED_FOLDER'], f))]
    
    return render_template('index.html', 
                         uploaded_files=uploaded_files,
                         shared_files=shared_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'Không có file nào được chọn', 400
    
    file = request.files['file']
    if file.filename == '':
        return 'Không có file nào được chọn', 400
    
    # Lưu file với tên gốc
    filename = file.filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    # Lấy thông tin file
    file_size = os.path.getsize(file_path)
    file_size_mb = round(file_size / (1024 * 1024), 2)
    
    return f'File "{filename}" ({file_size_mb} MB) đã được upload thành công', 200

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/shared/<filename>')
def shared_file(filename):
    return send_from_directory(app.config['SHARED_FOLDER'], filename)

@app.route('/api/files')
def get_files():
    """API để lấy danh sách file từ thư mục chia sẻ"""
    files = []
    if os.path.exists(app.config['SHARED_FOLDER']):
        for f in os.listdir(app.config['SHARED_FOLDER']):
            file_path = os.path.join(app.config['SHARED_FOLDER'], f)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                files.append({
                    'name': f,
                    'size': size,
                    'size_mb': round(size / (1024 * 1024), 2)
                })
    return jsonify(files)

if __name__ == '__main__':
    # Chạy server trên tất cả các interface với port 5001
    app.run(host='0.0.0.0', port=5001, debug=True) 