from flask import Flask, request, render_template, send_from_directory, jsonify
import os
import shutil
import re
import time
from threading import Lock

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SHARED_FOLDER'] = 'shared_files'  # Thư mục chia sẻ riêng

# Đảm bảo các thư mục tồn tại
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SHARED_FOLDER'], exist_ok=True)

# Khóa luồng và lưu trữ trạng thái thiết bị online cho WebRTC Signaling
devices_lock = Lock()
devices = {}  # device_id -> {id, name, ip, last_seen, mailbox: []}

def safe_filename(filename):
    """
    Làm sạch tên file để tránh tấn công path traversal mà vẫn giữ nguyên tiếng Việt có dấu và dấu cách.
    """
    filename = os.path.basename(filename)
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    filename = filename.replace('/', '').replace('\\', '').replace('..', '')
    return filename

def clean_upload_id(upload_id):
    return re.sub(r'[^a-zA-Z0-9\-_]', '', upload_id)

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{round(size_bytes / 1024, 2)} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{round(size_bytes / (1024 * 1024), 2)} MB"
    else:
        return f"{round(size_bytes / (1024 * 1024 * 1024), 2)} GB"

@app.route('/')
def index():
    uploaded_files = []
    upload_folder = app.config['UPLOAD_FOLDER']
    if os.path.exists(upload_folder):
        for f in os.listdir(upload_folder):
            file_path = os.path.join(upload_folder, f)
            if os.path.isfile(file_path) and not f.startswith('.'):
                size = os.path.getsize(file_path)
                uploaded_files.append({
                    'name': f,
                    'size': size,
                    'size_formatted': format_size(size)
                })
    
    shared_files = []
    shared_folder = app.config['SHARED_FOLDER']
    if os.path.exists(shared_folder):
        for f in os.listdir(shared_folder):
            file_path = os.path.join(shared_folder, f)
            if os.path.isfile(file_path) and not f.startswith('.'):
                size = os.path.getsize(file_path)
                shared_files.append({
                    'name': f,
                    'size': size,
                    'size_formatted': format_size(size)
                })
    
    return render_template('index.html', 
                          uploaded_files=uploaded_files,
                          shared_files=shared_files)

# --- CHUNKED UPLOAD ROUTES ---

@app.route('/upload/status', methods=['GET'])
def upload_status():
    upload_id = clean_upload_id(request.args.get('upload_id', ''))
    if not upload_id:
        return jsonify({'error': 'Thiếu upload_id'}), 400
    
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], f".tmp_{upload_id}")
    completed_chunks = []
    
    if os.path.exists(temp_dir):
        for f in os.listdir(temp_dir):
            match = re.match(r'^chunk_(\d+)$', f)
            if match:
                completed_chunks.append(int(match.group(1)))
                
    completed_chunks.sort()
    return jsonify({
        'upload_id': upload_id,
        'completed_chunks': completed_chunks
    })

@app.route('/upload/chunk', methods=['POST'])
def upload_chunk():
    upload_id = clean_upload_id(request.form.get('upload_id', ''))
    chunk_index = request.form.get('chunk_index')
    
    if not upload_id or chunk_index is None:
        return 'Thiếu upload_id hoặc chunk_index', 400
        
    try:
        chunk_index = int(chunk_index)
    except ValueError:
        return 'chunk_index phải là số nguyên', 400
        
    if 'file' not in request.files:
        return 'Không có dữ liệu file chunk', 400
        
    file = request.files['file']
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], f".tmp_{upload_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
    file.save(chunk_path)
    return f'Chunk {chunk_index} đã tải lên thành công', 200

@app.route('/upload/merge', methods=['POST'])
def upload_merge():
    data = request.json or {}
    upload_id = clean_upload_id(data.get('upload_id', ''))
    filename = safe_filename(data.get('filename', ''))
    total_chunks = data.get('total_chunks')
    
    if not upload_id or not filename or total_chunks is None:
        return jsonify({'error': 'Thiếu upload_id, filename hoặc total_chunks'}), 400
        
    try:
        total_chunks = int(total_chunks)
    except ValueError:
        return jsonify({'error': 'total_chunks phải là số nguyên'}), 400
        
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], f".tmp_{upload_id}")
    if not os.path.exists(temp_dir):
        return jsonify({'error': 'Thư mục tạm không tồn tại hoặc file đã được ghép trước đó.'}), 404
        
    missing_chunks = []
    for i in range(total_chunks):
        chunk_path = os.path.join(temp_dir, f"chunk_{i}")
        if not os.path.exists(chunk_path):
            missing_chunks.append(i)
            
    if missing_chunks:
        return jsonify({
            'error': 'Chưa đủ các chunk để ghép file',
            'missing_chunks': missing_chunks
        }), 400
        
    dest_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        with open(dest_path, 'wb') as outfile:
            for i in range(total_chunks):
                chunk_path = os.path.join(temp_dir, f"chunk_{i}")
                with open(chunk_path, 'rb') as infile:
                    while True:
                        block = infile.read(64 * 1024)
                        if not block:
                            break
                        outfile.write(block)
                        
        shutil.rmtree(temp_dir)
        file_size = os.path.getsize(dest_path)
        return jsonify({
            'message': 'Ghép file thành công',
            'filename': filename,
            'size': file_size,
            'size_formatted': format_size(file_size)
        }), 200
        
    except Exception as e:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except:
                pass
        return jsonify({'error': f'Lỗi trong quá trình ghép file: {str(e)}'}), 500

@app.route('/upload/cancel', methods=['POST'])
def upload_cancel():
    data = request.json or {}
    upload_id = clean_upload_id(data.get('upload_id', ''))
    
    if not upload_id:
        return jsonify({'error': 'Thiếu upload_id'}), 400
        
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], f".tmp_{upload_id}")
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            return jsonify({'message': 'Đã hủy tải lên và dọn dẹp bộ nhớ tạm.'}), 200
        except Exception as e:
            return jsonify({'error': f'Lỗi khi dọn dẹp: {str(e)}'}), 500
    
    return jsonify({'message': 'Không tìm thấy dữ liệu tạm.'}), 200

# --- WEBRTC SIGNALING ROUTES ---

@app.route('/api/webrtc/register', methods=['POST'])
def webrtc_register():
    """
    Đăng ký thiết bị online (Heartbeat).
    """
    data = request.json or {}
    device_id = clean_upload_id(data.get('device_id', ''))
    name = data.get('name', 'Thiết bị không tên')
    
    if not device_id:
        return jsonify({'error': 'Thiếu device_id'}), 400
        
    current_time = time.time()
    
    with devices_lock:
        # Làm sạch các thiết bị quá hạn (stale devices > 12 giây không heartbeat)
        for did in list(devices.keys()):
            if current_time - devices[did]['last_seen'] > 12:
                devices.pop(did, None)
                
        # Cập nhật thiết bị hiện tại
        if device_id not in devices:
            devices[device_id] = {
                'id': device_id,
                'name': name,
                'ip': request.remote_addr,
                'last_seen': current_time,
                'mailbox': []
            }
        else:
            devices[device_id]['name'] = name
            devices[device_id]['ip'] = request.remote_addr;
            devices[device_id]['last_seen'] = current_time
            
    return jsonify({'status': 'ok', 'active_count': len(devices)})

@app.route('/api/webrtc/devices', methods=['GET'])
def webrtc_devices():
    """
    Lấy danh sách các thiết bị LAN đang online khác.
    """
    exclude_id = request.args.get('exclude_id', '')
    current_time = time.time()
    active_list = []
    
    with devices_lock:
        # Quét dọn trước
        for did in list(devices.keys()):
            if current_time - devices[did]['last_seen'] > 12:
                devices.pop(did, None)
                
        # Lọc ra danh sách thiết bị ngoại trừ thiết bị gửi request
        for did, d in devices.items():
            if did != exclude_id:
                active_list.append({
                    'id': d['id'],
                    'name': d['name'],
                    'ip': d['ip']
                })
                
    return jsonify(active_list)

@app.route('/api/webrtc/signal/send', methods=['POST'])
def webrtc_signal_send():
    """
    Gửi tín hiệu WebRTC (Offer, Answer, ICE Candidates) cho một thiết bị khác.
    """
    data = request.json or {}
    sender_id = clean_upload_id(data.get('sender_id', ''))
    receiver_id = clean_upload_id(data.get('receiver_id', ''))
    signal_data = data.get('data')
    
    if not sender_id or not receiver_id or signal_data is None:
        return jsonify({'error': 'Thiếu sender_id, receiver_id hoặc data'}), 400
        
    with devices_lock:
        if receiver_id in devices:
            devices[receiver_id]['mailbox'].append({
                'sender_id': sender_id,
                'data': signal_data
            })
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Thiết bị nhận đã offline'}), 404

@app.route('/api/webrtc/signal/receive', methods=['POST'])
def webrtc_signal_receive():
    """
    Lấy tất cả tin nhắn signaling chưa đọc từ hộp thư của thiết bị.
    """
    data = request.json or {}
    device_id = clean_upload_id(data.get('device_id', ''))
    
    if not device_id:
        return jsonify({'error': 'Thiếu device_id'}), 400
        
    mailbox_content = []
    with devices_lock:
        if device_id in devices:
            # Lấy và xóa hộp thư
            mailbox_content = devices[device_id]['mailbox']
            devices[device_id]['mailbox'] = []
            # Cập nhật heartbeat luôn
            devices[device_id]['last_seen'] = time.time()
            
    return jsonify(mailbox_content)

# --- FILE SERVING AND UTILITIES ---

@app.route('/api/uploaded')
def get_uploaded_files():
    """API để lấy danh sách file đã upload"""
    files = []
    upload_folder = app.config['UPLOAD_FOLDER']
    if os.path.exists(upload_folder):
        for f in os.listdir(upload_folder):
            file_path = os.path.join(upload_folder, f)
            if os.path.isfile(file_path) and not f.startswith('.'):
                size = os.path.getsize(file_path)
                files.append({
                    'name': f,
                    'size': size,
                    'size_formatted': format_size(size)
                })
    return jsonify(files)

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
            if os.path.isfile(file_path) and not f.startswith('.'):
                size = os.path.getsize(file_path)
                files.append({
                    'name': f,
                    'size': size,
                    'size_formatted': format_size(size)
                })
    return jsonify(files)

if __name__ == '__main__':
    # Chạy Flask dưới dạng HTTPS với chứng chỉ tự ký sinh tự động ('adhoc')
    # Cho phép truy cập từ mọi địa chỉ IP qua cổng 5001
    print("MỞ TRÌNH DUYỆT VÀ TRUY CẬP BẰNG HTTPS: https://localhost:5001 hoặc https://<IP-LAN>:5001")
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True, ssl_context='adhoc')