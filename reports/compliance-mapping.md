# CP5 — Compliance mapping

Ngày đối chiếu nguồn: 12/10/2026.

Các liên hệ control dưới đây là phân tích kỹ thuật của bài lab,
không phải kết luận đã đáp ứng từng nghĩa vụ pháp luật.
Tên và số hiệu văn bản được xác nhận từ nguồn chính thức.
Đối chiếu điều khoản pháp luật cụ thể: chưa xác minh.

## Nguồn

- [Luật 91/2025/QH15 — Bảo vệ dữ liệu cá nhân](https://vanban.chinhphu.vn/?docid=214590&pageid=27160)
- [Nghị định 356/2025/NĐ-CP](https://vanban.chinhphu.vn/?docid=216387&pageid=27160)
- [Luật 134/2025/QH15 — Trí tuệ nhân tạo](https://vanban.chinhphu.vn/?docid=216334&pageid=27160)
- [OWASP Agentic Top 10](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/)

## Mapping

| Nguồn / chủ đề đối chiếu | Control đã làm | Evidence file:dòng | Giới hạn |
|---|---|---|---|
| Luật 91/2025/QH15: liên hệ với bảo vệ dữ liệu cá nhân | Nhận diện và che CCCD, SĐT, STK, email; chặn egress với dữ liệu restricted | agent/pii.py:35; agent/pii.py:58; agent/runner.py:63; agent/policy.py:49; reports/ledger.jsonl:51 | Dữ liệu synthetic; regex chưa bao phủ mọi PII; điều khoản tương ứng chưa xác minh |
| NĐ 356/2025/NĐ-CP: liên hệ với biện pháp kiểm soát xử lý dữ liệu | Kiểm quyền trước khi mở private store và trước từng lần đọc; mô tả luồng, mục đích và giới hạn trong DPIA-lite | agent/runner.py:82; agent/runner.py:108; agent/runner.py:123; reports/ledger.jsonl:26 | Chưa đánh giá nghĩa vụ hồ sơ, quyền chủ thể hoặc quy trình thực tế; điều khoản tương ứng chưa xác minh |
| Luật AI 134/2025/QH15: liên hệ với quản trị hành động của agent | Gắn principal, scope, TTL; ghi allow/deny cùng reason và định danh run | agent/policy.py:99; agent/policy.py:146; agent/runner.py:196; reports/ledger.jsonl:51 | --as là fixture; chưa phân loại rủi ro hệ thống hoặc đánh giá nghĩa vụ pháp lý cụ thể |
| OWASP ASI01 — Agent Goal Hijack | Run B nhận ticket ID từ tên file; ánh xạ customer qua related_tickets; chỉ thị trong text không chọn hồ sơ | agent/runner.py:55; agent/runner.py:108; agent/runner.py:119; tests/test_split.py:1; reports/ledger.jsonl:51 | Split là tách luồng và scope trong cùng process, chưa phải sandbox hệ điều hành |
| OWASP ASI03 — Identity & Privilege Abuse | Giao quyền principal, agent và parent; kiểm purpose/TTL; support_l1 bị chặn trước private access | agent/policy.py:39; agent/policy.py:146; agent/runner.py:82; reports/ledger.jsonl:26 | Chưa có authentication production, credential riêng hoặc cơ chế thu hồi phiên thật |
| OWASP ASI04 — Agentic Supply Chain Vulnerabilities | Dependency pin/hash; hook Gitleaks pin; quét lịch sử và báo cáo token giả | .pre-commit-config.yaml:3; .pre-commit-config.yaml:6; requirements.lock:7; reports/secrets-incident.md:1 | Hash không chứng minh package lành tính; chưa đánh giá MCP runtime hoặc toàn bộ chuỗi cung ứng |

## Kết quả kỹ thuật

- Toàn bộ test suite: 33 passed.
- Bốn lure được kiểm dưới cả support_l1 và dpo.
- Before: reports/attack-before.log, 4 POST, 1192 byte.
- After: reports/attack-after.log, 0 byte.
- Ledger: 51 entry, verify=True.
- Lượt DPO cuối có 21 allow đọc customer và deny http_post ở dòng 51.
