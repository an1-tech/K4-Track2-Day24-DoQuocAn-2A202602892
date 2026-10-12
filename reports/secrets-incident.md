# CP4 — Token giả trong lịch sử Git

## Scanner

- Công cụ: Gitleaks v8.30.1.
- Cấu hình: `.gitleaks.toml`, gồm default rules và rule lab.
- Dùng --redact để che token trong output.

## Kết quả quét lịch sử

Lệnh:
`gitleaks git --config .gitleaks.toml --redact --verbose .`

Kết quả:
- Scanner báo 7 commits scanned.
- Có 1 finding.
- Exit code: 1.
- RuleID: lab24-synthetic-token.
- File: lab-fake-secret.txt.
- Dòng: 1.
- Commit: 1bdd849922156c868a5ee9293d68f5b72e242d2c.
- Finding và Secret được hiển thị là REDACTED.
- Fingerprint:
  1bdd849922156c868a5ee9293d68f5b72e242d2c:lab-fake-secret.txt:lab24-synthetic-token:1

Đây là token giả vô hiệu được cài sẵn cho bài lab,
không phải bằng chứng một credential thật đã bị lộ.

## Kết quả quét file hiện tại

Lệnh:
`gitleaks dir --config .gitleaks.toml --redact --verbose .`

Kết quả:
- no leaks found.
- Exit code: 0.
- Không cần thêm allowlist hoặc tắt rule.

File token đã bị xóa khỏi HEAD nhưng vẫn tồn tại trong
commit cũ, nên quét lịch sử vẫn phát hiện được.

## Nếu đây là credential thật

1. Thu hồi hoặc rotate tại dịch vụ cấp credential.
2. Cập nhật ứng dụng sang credential mới qua nơi quản lý secret.
3. Kiểm tra audit log để xác định việc sử dụng ngoài dự kiến.
4. Xác định và xử lý các bản sao trong lịch sử Git, CI log,
   artifact, cache và các clone liên quan.
5. Quét lại và bổ sung kiểm soát ngăn tái diễn.

Xóa file ở commit mới không thu hồi credential tại dịch vụ.
Xử lý lịch sử Git cũng không bảo đảm mọi bản sao đã biến mất,
vì vậy thu hồi/rotate là bước cần thiết với credential thật.

## Dependency và hook

- `requirements.lock` được sinh bằng pip-tools với
  --generate-hashes, ghi phiên bản cụ thể và SHA-256.
- Cài đặt từ lock sử dụng --require-hashes.
- `.pre-commit-config.yaml` dùng repo Gitleaks chính thức,
  pin rev v8.30.1, hook gitleaks-system.
- pass_filenames=false để không truyền danh sách filename
  vào lệnh Gitleaks vốn nhận repo path.
- Binary Gitleaks trong môi trường là 8.30.1.
- Kết quả chạy hook và test CP4 được ghi trong verification.md.

Pin dependency và hash kiểm soát artifact được cài.
Hook giúp phát hiện secret trong thay đổi staged.
Các biện pháp này không thu hồi credential đã lộ,
nên không thay thế việc rotate tại dịch vụ cấp token.

## Giới hạn

Scanner sạch không chứng minh tuyệt đối rằng không còn secret.
Bài lab chỉ dùng token giả và dữ liệu synthetic.