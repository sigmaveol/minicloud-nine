# 🚀 MyMiniCloud - Hệ thống Mô phỏng Điện toán Đám mây (Nhóm G09)

Chào mừng đến với **MyMiniCloud**, một dự án mô phỏng nền tảng Điện toán đám mây (Cloud Platform) thu nhỏ được xây dựng bằng Docker Container. Dự án tái hiện gần như đầy đủ kiến trúc của các hệ thống Cloud lớn như AWS, Azure hay GCP, bao gồm 9 loại máy chủ cốt lõi và các thành phần mở rộng (Load Balancing, Logging).

## ✨ Tính năng nổi bật

- **Kiến trúc Microservices:** 13 container độc lập giao tiếp qua mạng nội bộ `g09-minicloud-network`.
- **Web & Reverse Proxy:** Nginx phục vụ giao diện tĩnh và định tuyến API, tích hợp **Load Balancing** (Round Robin) cho 2 Web Server.
- **Backend API:** Flask cung cấp các API RESTful (Hello, Secure, CRUD Sinh viên) kết nối trực tiếp MariaDB.
- **Xác thực OIDC:** Keycloak quản lý định danh, cấp phát JWT Token và bảo vệ API `/secure`.
- **Lưu trữ Đối tượng (S3-like):** MinIO quản lý file, hình ảnh và tài liệu.
- **Giám sát & Logging:** Prometheus thu thập metrics, Loki & Promtail thu thập log, Grafana trực quan hóa dữ liệu.
- **Internal DNS:** Bind9 phân giải tên miền nội bộ `cloud.local`.

## 🛠️ Công nghệ sử dụng

- **Hạ tầng & Triển khai:** Docker, Docker Compose
- **Web & Proxy:** Nginx
- **Backend:** Python (Flask), PyMySQL
- **Database:** MariaDB 11
- **Xác thực:** Keycloak (OIDC)
- **Storage:** MinIO
- **Giám sát:** Prometheus, Node Exporter, Grafana, Loki, Promtail
- **DNS:** Bind9

## 📂 Cấu trúc thư mục

```text
minicloud-nine/
├── app/                  # Source code Flask Backend & Dockerfile
├── auth/                 # Cấu hình Keycloak (nếu có)
├── db/init/              # Script SQL khởi tạo Database (001_init.sql, 002_studentdb.sql)
├── dns/                  # Cấu hình Bind9 (named.conf, db.cloud.local)
├── grafana/              # Cấu hình Grafana (nếu có)
├── monitor/              # Cấu hình Prometheus (prometheus.yml) & Promtail
├── proxy/                # Cấu hình Nginx Reverse Proxy (nginx.conf)
├── storage/data/         # Thư mục mount dữ liệu MinIO
├── web/                  # Source code HTML, Dockerfile & cấu hình Nginx Web Server
├── docker-compose.yml    # File điều phối toàn bộ hệ thống
└── README.md             # Tài liệu hướng dẫn

## 🚀 Hướng dẫn Cài đặt & Triển khai

### Yêu cầu hệ thống
- Đã cài đặt [Docker](https://docs.docker.com/get-docker/) và [Docker Compose](https://docs.docker.com/compose/install/).
- Cổng 80, 8080, 8081, 8085, 9000, 9001, 9090, 3000 chưa bị chiếm dụng.

### 1. Chạy trên môi trường Local (WSL/Ubuntu/macOS)
```bash
# Clone dự án
git clone https://github.com/sigmaveol/minicloud-nine.git
cd minicloud-nine

# Khởi chạy toàn bộ hệ thống
docker compose up -d --build

# Kiểm tra trạng thái các container
docker compose ps
```

### 2. Triển khai trên AWS EC2
```bash
# 1. Phân quyền file key và kết nối SSH
chmod 400 g09-key.pem
ssh -i "g09-key.pem" ubuntu@<EC2_PUBLIC_IP>

# 2. Cài đặt Docker & Git
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER && newgrp docker

# 3. Clone và chạy dự án
git clone https://github.com/sigmaveol/minicloud-nine.git
cd minicloud-nine
docker compose up -d
```

## 🌐 Các điểm truy cập (Access Points)

Sau khi hệ thống khởi chạy thành công, bạn có thể truy cập các dịch vụ tại:

| Dịch vụ | Địa chỉ (Local) | Địa chỉ (AWS EC2) | Tài khoản / Ghi chú |
| :--- | :--- | :--- | :--- |
| **Trang Web (Proxy)** | http://localhost/ | http://\<EC2_PUBLIC_IP\>/ | Giao diện MyMiniCloud |
| **Web Server 1** | http://localhost:8080 | http://\<EC2_PUBLIC_IP\>:8080 | (Truy cập trực tiếp) |
| **API Backend** | http://localhost:8085 | http://\<EC2_PUBLIC_IP\>:8085 | `/hello`, `/student`, `/students-db` |
| **Keycloak (Auth)** | http://localhost:8081 | http://\<EC2_PUBLIC_IP\>:8081 | `admin` / `admin` |
| **MinIO Console** | http://localhost:9001 | http://\<EC2_PUBLIC_IP\>:9001 | `minioadmin` / `minioadmin` |
| **Prometheus** | http://localhost:9090 | http://\<EC2_PUBLIC_IP\>:9090 | Xem Targets & Graph |
| **Grafana** | http://localhost:3000 | http://\<EC2_PUBLIC_IP\>:3000 | `admin` / `admin` |

## 🧪 Kịch bản Kiểm thử nhanh (Test Cases)

1. **Kiểm tra Web & Load Balancing:**
   ```bash
   curl -I http://localhost/
   ```
   *Kết quả:* HTTP 200 OK. (Chạy nhiều lần và kiểm tra header `X-Backend` để thấy sự luân phiên giữa 2 Web Server).

2. **Kiểm tra API lấy dữ liệu từ DB:**
   ```bash
   curl http://localhost/api/students-db
   ```
   *Kết quả:* Trả về JSON danh sách sinh viên từ MariaDB.

3. **Kiểm tra Xác thực OIDC:**
   Lấy token từ Keycloak và gọi API bảo mật:
   ```bash
   TOKEN=$(curl -s -d "client_id=flask-app" -d "username=sv01" -d "password=123456" -d "grant_type=password" "http://localhost:8081/realms/realm_HoangSinhHung/protocol/openid-connect/token" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8085/secure
   ```

## 👥 Thành viên thực hiện (Nhóm G09)

| Họ và Tên | MSSV | Nhiệm vụ chính |
| :--- | :--- | :--- |
| **Nguyễn Trí Nhân** | 52300138 | Web Server, Internal DNS, Reverse Proxy & Load Balancing |
| **Đoàn Lâm Phúc Khang** | 52200115 | Application Server (Flask), Authentication Server (Keycloak) |
| **Hoàng Sinh Hùng** | 52300106 | Relational Database (MariaDB), Object Storage (MinIO) |
| **Trần Đình Lâm** | 52300125 | Monitoring (Prometheus), Logging (Loki), Grafana Dashboard |

---
*Đồ án môn học Điện toán đám mây - Trường Đại học Tôn Đức Thắng (2026).*