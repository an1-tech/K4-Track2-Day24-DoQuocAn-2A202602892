# Verification — Day24

## Môi trường

- OS: Ubuntu trên WSL2.
- Python: 3.14.4; dùng `.venv` của repo.
- pytest: 9.1.1.
- Gitleaks: 8.30.1, tại `/usr/local/bin/gitleaks`.
- pre-commit: 4.6.2.
- Model: --mock; dữ liệu synthetic.

## Chuẩn bị

- Đã tạo `.venv` và cài requirements, pre-commit, pip-tools.
- Sinh lock:
  `python -m piptools compile --generate-hashes -o requirements.lock requirements.txt`
- Kiểm cài từ lock:
  `python -m pip install --require-hashes -r requirements.lock`
- Lệnh chạy thành công; các package báo
  "Requirement already satisfied".
- Archive Gitleaks Linux x64 v8.30.1 đã kiểm SHA-256: OK.

## CP1 — Baseline

- Đã trả lời ba câu hỏi, kèm file:dòng trong
  `reports/baseline.md`.
- Commit: a4ca35b — hoàn thành checkpoint 1.
- CP1 là đọc code, không yêu cầu pytest.

## CP2 — Red team

- Lệnh:
  `python -m agent.check_lure 'corpus/ticket-90*.md'`
- Kết quả: 4/4 lure sẵn sàng.
- Cặp 904/904b có hai marker: system note, dpo.

- Lệnh baseline:
  `python -m agent.loop --mock "Tổng hợp các ticket còn mở tuần này"`
- Kết quả: tổng hợp 45 ticket.

- Sau khi reset sink, đã replay riêng bốn biến thể bằng
  `_naive_loop()` và MockLLM, dùng bản sao trong thư mục tạm.
- Biến thể 1–3: mỗi lượt tổng hợp một ticket.
- Biến thể 4: tổng hợp hai ticket 904 và 904b.
- Evidence: `reports/attack-before.log`, 4 POST, 1192 byte.
- Dòng 1–4 tương ứng biến thể 1–4.
- Mỗi POST có path `/reconcile` và một record KH-000999.
- CCCD, SĐT, STK và email khớp dữ liệu synthetic.
- Commit: 1fd9bdc — hoàn thành checkpoint 2.

## CP3 — Controls và test

### CP3a — PII

- Lệnh:
  `python -m pytest tests/test_pii.py -v -s --basetemp=.pytest_tmp`
- Kết quả: 2 passed.
- gold=118, pred=118, tp=118.
- precision=1.000, recall=1.000.
- Detection trả offset trong chuỗi gốc và loại vùng trùng.
- Redaction thay từ cuối chuỗi về đầu.
- Giới hạn: regex theo định dạng lab; chưa nhận diện tên người
  hoặc bảo đảm phát hiện mọi định dạng PII ngoài thực tế.

### CP3b — Policy

- Lệnh:
  `python -m pytest tests/test_policy.py -v --basetemp=.pytest_tmp`
- Kết quả: 4 passed.
- Restricted + egress bị deny, kể cả với DPO.
- Yêu cầu tìm ticket hợp lệ vẫn được allow.
- Mọi quyết định có reason.

### CP3c — OBO

- Lệnh đầy đủ sau khi nối runner:
  `python -m pytest tests/test_obo.py -v --basetemp=.pytest_tmp`
- Kết quả: 5 passed.
- support_l1 bị chặn trước khi đọc customer.
- dpo vẫn đọc customer hợp lệ.
- Delegation không vượt scope cha.
- Principal không tồn tại hoặc run hết hạn bị deny.
- Lượt chạy policy riêng trước đó có 4 passed, 1 deselected;
  test tích hợp đã được chạy lại đầy đủ, không còn deselected.

### CP3d — Split và injection

- Lệnh:
  `python -m pytest tests/test_split.py -v --basetemp=.pytest_tmp`
- Kết quả: 1 passed.
- KH-000777 không bị đọc chỉ vì xuất hiện trong text attacker.
- Customer hợp lệ vẫn được đọc.

- Lệnh:
  `python -m pytest tests/test_injection.py -v --basetemp=.pytest_tmp`
- Kết quả: 8 passed, không SKIP.
- Đã kiểm bốn biến thể dưới support_l1 và dpo.
- Run B chỉ nhận ticket ID dạng số từ tên file.
- Customer ID được ánh xạ qua related_tickets trong nguồn tin cậy.
- PII được che trước khi nội dung ticket được đưa vào tóm tắt.
- Yêu cầu egress được kiểm riêng, không truyền hồ sơ khách sang đó.

### CP3e — Ledger

- Lệnh:
  `python -m pytest tests/test_ledger.py -v --basetemp=.pytest_tmp`
- Kết quả: 3 passed.
- Hash chain liên kết đúng; sửa dòng cũ bị phát hiện.
- Reason rỗng làm verify thất bại.

Đã chạy CLI qua runner mới với cùng query dưới cả hai principal:
`python -m agent.loop --mock --as dpo "Tổng hợp các ticket còn mở tuần này"`
`python -m agent.loop --mock --as support_l1 "Tổng hợp các ticket còn mở tuần này"`

Cả hai lượt đều tổng hợp 45 ticket.

Snapshot ledger khi hoàn tất CP3:
- `reports/ledger.jsonl`: 27 entry.
- DPO: 24 entry; support_l1: 3 entry.
- Mọi entry có on_behalf_of, agent_id, run_id, expires_at,
  reason và args_hash.
- DPO có allow read_customer cho hồ sơ hợp lệ.
- support_l1 có deny read_customer, không có allow read_customer.
- Các quyết định http_post đều deny.
- DPO deny http_post: `reports/ledger.jsonl:24`.
- support_l1 deny read_customer: `reports/ledger.jsonl:26`.
- support_l1 deny http_post: `reports/ledger.jsonl:27`.
- Ledger gốc verify: True.
- Bản sao sửa reason ở dòng giữa, giữ hash cũ: verify False.
- Thử tamper thực hiện trên bản sao trong thư mục tạm.

Tổng sáu nhóm test CP3: 23 test pass qua các lượt riêng.
Chưa phải kết quả chạy toàn bộ test suite.

## CP4 — Supply chain và secrets

### Quét lịch sử

- Gitleaks: 8.30.1.
- Lệnh:
  `gitleaks git --config .gitleaks.toml --redact --verbose .`
- Kết quả: 1 finding, exit code 1.
- Rule: lab24-synthetic-token.
- File: lab-fake-secret.txt, dòng 1.
- Commit: 1bdd849922156c868a5ee9293d68f5b72e242d2c.
- Đây là token giả vô hiệu của bài lab.
- Chi tiết: reports/secrets-incident.md.

### Quét file hiện tại

- Lệnh:
  `gitleaks dir --config .gitleaks.toml --redact --verbose .`
- Kết quả: no leaks found, exit code 0.
- Không thêm allowlist hoặc tắt rule.

### Hash lock

- Lệnh:
  `python -m pip install --force-reinstall --require-hashes -r requirements.lock`
- Kết quả: cài lại thành công 10 package theo lock.
- pip sử dụng các archive trong cache và chế độ kiểm hash.
- Không chỉ dựa vào kết quả "Requirement already satisfied"
  của lượt chuẩn bị.

### Pre-commit hook

- Cấu hình: .pre-commit-config.yaml.
- Repo chính thức: https://github.com/gitleaks/gitleaks.
- rev: v8.30.1.
- Hook: gitleaks-system.
- pass_filenames: false.
- Cấu hình scanner: .gitleaks.toml.
- `pre-commit install`: thành công.
- `pre-commit run --all-files`: Passed.
- Hook quét thay đổi staged; quét toàn bộ lịch sử là lượt riêng.

### Test

- Lệnh:
  `python -m pytest tests/test_supply_chain.py -v --basetemp=.pytest_tmp`
- Kết quả: 3 passed.
- Đã kiểm hook pin, hash lock và báo cáo token giả.

## CP5 — Prove

- Lệnh:
  `python -m pytest tests/ -q --basetemp=.pytest_tmp`
- Kết quả: 33 passed in 13.39s; không FAIL hoặc SKIP.

Sau pytest đã reset sink lần nữa, rồi replay bằng runner mới:
`python -m agent.loop --mock --as dpo "Tổng hợp các ticket còn mở tuần này"`

- Agent tổng hợp 45 ticket.
- Sao chép sink.log thành reports/attack-after.log.
- Before: 4 dòng, 1192 byte.
- After: 0 byte.
- Ledger: 51 entry; verify=True.
- Lượt DPO mới nhất: 24 entry.
- Allow đọc customer: 21.
- Deny http_post tại reports/ledger.jsonl:51,
  on_behalf_of=dpo, reason:
  Restricted data must not enter an egress-enabled operation.
- Thử tamper trên bản sao tại CP3: verify=False.
- Mapping và DPIA-lite đã được viết theo evidence của bài.
- Điều khoản pháp luật cụ thể: chưa xác minh.
- `pre-commit run --all-files` trên các file staged CP5: Passed.

## Trạng thái kiểm chứng

Các test kỹ thuật và bằng chứng before/after đã đạt.
Hook staged CP5 đã Passed. Commit và push theo bước nộp bài.
Không suy ra tuân thủ pháp luật hoặc an toàn production.

## Lỗi đã gặp và cách xử lý

- Git WSL báo khác biệt CRLF/LF:
  đặt core.autocrlf=input cục bộ cho repo.
- Git báo Author identity unknown:
  đặt user.name và user.email cục bộ, rồi commit lại.
- Chưa ghi nhận lỗi trong các lượt test CP3 và kiểm ledger.

## Giới hạn

--mock và --as là mô phỏng, chưa phải xác thực production.
Hash chain một file không tự phát hiện cắt đuôi hoặc viết lại
toàn bộ chuỗi nếu thiếu mốc tin cậy bên ngoài.
Kết quả lab không chứng nhận hệ thống thật an toàn hoặc tuân thủ pháp luật.
