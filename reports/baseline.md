# CP1 — Phân tích baseline

## 1. Agent đã có identity và kiểm quyền mỗi run chưa?

Chưa. `_naive_loop()` chỉ nhận `message` và `llm`, không tạo
`agent_id`, `run_id` hoặc kiểm danh tính người dùng trước khi gọi tool
(agent/loop.py:27).

Mặc dù `run_once()` nhận `principal_id`, nhánh baseline gọi
`_naive_loop(message, llm)` mà không truyền principal
(agent/loop.py:74).

## 2. Ai quyết định cho phép http_post?

Baseline quyết định gửi khi phát hiện chỉ thị injection và đọc được
hồ sơ khách hàng. Không có lời gọi policy để kiểm quyền, mục đích
hoặc phân loại dữ liệu trước POST
(agent/loop.py:34, agent/loop.py:39, agent/loop.py:44).

`tools.http_post()` chỉ kiểm scheme, hostname và port để giới hạn
đích localhost. Nó không kiểm hồ sơ nào được phép gửi
(agent/tools.py:76, agent/tools.py:77).

Lỗi là nội dung ticket không đáng tin được dùng để điều khiển
việc đọc và gửi hồ sơ riêng.

## 3. Bằng chứng dữ liệu đã được gửi nằm ở đâu?

Body POST được tạo dưới dạng `{"records": collected}` tại
agent/loop.py:44, rồi gửi bằng `requests.post()` tại agent/tools.py:84.

Sink ghi đường dẫn và body nhận được vào `reports/sink.log`
(sink/sink.py:37, sink/sink.py:45, sink/sink.py:47).

Ở CP2, tôi sẽ chạy baseline và sao chép log thành
`reports/attack-before.log`. Log chứa hồ sơ synthetic của
`KH-000999` sẽ là bằng chứng dữ liệu thực sự đã tới sink.