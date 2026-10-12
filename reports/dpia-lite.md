# CP5 — DPIA-lite

Đây là mô tả luồng dữ liệu và rủi ro trong bài học,
không phải hồ sơ đánh giá tác động pháp lý chính thức.

## 1. Dữ liệu và phân loại

- corpus/: ticket tổng hợp, gồm tên và các giá trị PII giả.
- data/customers.json: hồ sơ khách hàng synthetic, gồm
  customer_id, name, cccd, phone, bank_account, email
  và related_tickets.
- data/principals.json: danh tính, tool và purpose giả lập.
- Token trong lịch sử Git là token giả vô hiệu.

Phân loại của lab:
- search_docs sử dụng context internal.
- Truy cập customer sử dụng context restricted.
- Yêu cầu gửi hồ sơ được kiểm là restricted + egress.

Các nhãn này là lựa chọn kỹ thuật của lab,
không phải kết luận phân loại dữ liệu theo điều khoản pháp luật.

## 2. Mục đích và principal

- Run A: summarize-tickets.
- Run B: support-reply.
- support_l1 được tìm ticket, bị chặn trước private store.
- dpo được đọc hồ sơ gắn với ticket hợp lệ.
- Quyền hiệu lực bị giới hạn bởi principal, agent scope,
  parent scope, purpose và TTL.
- Mỗi lượt handle tạo định danh run và thời hạn 5 phút.

--as chỉ chọn fixture trong principals.json;
không xác minh người đang sử dụng máy.

## 3. Luồng và nơi dữ liệu đi

### Run A

search_docs đọc ticket không đáng tin.
Runner lấy số ticket từ tên file, không lấy customer ID
trong lời chỉ thị của attacker.

Nội dung ticket được redact trước khi đưa vào summarize.
Run B chỉ nhận danh sách ticket ID dạng số.

### Run B

Policy được kiểm trước khi mở customers.json.
Sau khi được phép, runner ánh xạ ticket qua related_tickets,
rồi kiểm policy trước mỗi read_customer.

Hồ sơ riêng không được truyền sang chặng kiểm egress
hoặc đưa vào bản tóm tắt của runner.

### Egress

Lượt kiểm gửi chỉ có URL:
http://127.0.0.1:10024/reconcile.

Context restricted + egress bị deny.
Chỉ thị attacker không làm tools.http_post thực thi.

### Ledger và evidence

Ledger lưu định danh, principal, thời hạn, tool, scope,
classification, decision, reason và hash tham số.
Runner không ghi nguyên hồ sơ khách vào ledger.

attack-before.log giữ các POST synthetic của baseline.
attack-after.log giữ kết quả sink của lượt replay sau containment.

## 4. Bằng chứng và giới hạn

Kết quả:
- Toàn bộ test suite: 33 passed.
- OBO: 5 passed; split: 1 passed; injection: 8 passed.
- Before: 4 dòng POST, 1192 byte.
- After: 0 byte.
- Ledger: 51 entry, verify=True.
- Lượt DPO cuối: 24 entry, 21 allow đọc customer.
- Deny http_post: reports/ledger.jsonl:51.
- Support deny private access: reports/ledger.jsonl:26.
- Bản sao ledger bị sửa dòng giữa tại CP3: verify=False.

Giới hạn:
- Chỉ kiểm --mock, chưa kiểm hành vi của model thật.
- Regex nhận diện bốn loại; tên người vẫn có thể còn trong ticket.
- Run A/B tách luồng và scope trong cùng process Python,
  chưa có cô lập hệ điều hành.
- Registry quyền, TTL và --as là mô phỏng.
- Hash tham số không đồng nghĩa ẩn danh tuyệt đối.
- Hash chain không tự phát hiện cắt đuôi hoặc viết lại cả chuỗi
  nếu thiếu mốc tin cậy bên ngoài.
- Chưa triển khai retention/delete cascade hoặc quyền chủ thể.
- Chưa xác minh nghĩa vụ pháp lý cụ thể cho hệ thống production.
