# File Transfer LAN

Ứng dụng web đơn giản để truyền file qua mạng LAN giữa các thiết bị.

## Tính năng

- 📤 **Upload file**: Tải file từ điện thoại lên máy chủ
- 📁 **Xem file đã upload**: Danh sách và tải xuống các file đã upload
- 💻 **Chia sẻ file từ máy chủ**: Tải xuống file từ thư mục `shared_files`

## Cài đặt và chạy

1. **Tạo môi trường ảo:**
```bash
python3 -m venv venv
```

2. **Kích hoạt môi trường ảo:**
```bash
source venv/bin/activate
```

3. **Cài đặt thư viện:**
```bash
pip install -r requirements.txt
```

4. **Chạy ứng dụng:**
```bash
python app.py
```

5. **Truy cập từ điện thoại:**
   - Đảm bảo điện thoại kết nối cùng mạng WiFi với máy tính
   - Mở trình duyệt và truy cập: `http://<IP_máy_chủ>:5001`

## Cấu trúc thư mục

```
file_transfer/
├── app.py              # Ứng dụng Flask chính
├── requirements.txt    # Thư viện cần thiết
├── templates/          # Giao diện HTML
│   └── index.html
├── uploads/           # File được upload từ điện thoại
├── shared_files/      # File chia sẻ từ máy chủ (CHỈ HIỂN THỊ FILE TỪ THƯ MỤC NÀY)
└── venv/              # Môi trường ảo
```

## Cách sử dụng

### Để chia sẻ file từ máy chủ:
1. Copy file vào thư mục `shared_files/`
2. Refresh trang web hoặc nhấn nút "🔄 Làm mới"
3. File sẽ xuất hiện trong danh sách và có thể tải xuống

### Để upload file từ điện thoại:
1. Chọn file trong phần "📤 Tải file lên máy chủ"
2. Nhấn "Tải lên"
3. File sẽ được lưu vào thư mục `uploads/`

## Lưu ý

- Server chạy trên port 5001 (tránh xung đột với AirPlay trên macOS)
- Chỉ file trong thư mục `shared_files/` mới được hiển thị để tải xuống
- Đảm bảo firewall cho phép kết nối đến port 5001
- Ứng dụng chỉ dành cho mục đích phát triển, không nên sử dụng trong môi trường production

## Tắt ứng dụng

- Nhấn `Ctrl+C` trong terminal để dừng server
- Gõ `deactivate` để thoát khỏi môi trường ảo 
