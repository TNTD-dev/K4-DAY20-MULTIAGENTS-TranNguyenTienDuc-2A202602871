# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Trần Nguyễn Tiến Đức | 2A202602871 | 100% (Thực hành cá nhân) |

- Nhà cung cấp và mô hình (`LAB_MODEL`, không ghi khóa API), nhiệt độ (`LAB_TEMPERATURE`), `recursion_limit`: `openai:gpt-4o-mini`, nhiệt độ = 0.0, recursion_limit = 60
- Phiên bản Deep Agents (`pip show deepagents`), hệ điều hành, chạy trực tiếp hay trong Docker: `deepagents 0.7.21`, macOS (Darwin ARM64), chạy trực tiếp trên môi trường máy chủ host (.venv)
- Số lần chạy tác vụ đã dùng / ngân sách: 9 lần chạy tập học + 12 lần chạy chính thức tập đánh giá + thử thách 6a (trong ngân sách cho phép)
- Commit của tag `freeze`: (sẽ cập nhật sau khi tạo tag freeze)

## 2. Giả thuyết (commit TRƯỚC tag `freeze`, Phần 4.0)

- H1 (subagents so với baseline): Điều kiện `subagents` sẽ có điểm số tương đương hoặc chỉ tăng nhẹ so với `baseline` trên tác vụ đánh giá (dự kiến chênh lệch điểm không vượt quá 10%), nhưng chi phí token sẽ tăng đột biến (như đã ghi nhận ở tập học, có tác vụ tiêu tốn trên 4 triệu tokens do subagent lặp nhiều lượt). Căn cứ: nghiên cứu của Anthropic về multi-agent độc lập và quan sát thực nghiệm cho thấy mô hình `gpt-4o-mini` khi giao việc qua subagent bị cô lập ngữ cảnh (context isolation) thường tốn nhiều lượt trao đổi hoặc khó truyền tải toàn vẹn các ràng buộc phức tạp.
- H2 (skills-auto so với baseline): Điều kiện `skills-auto` sẽ đạt điểm cao hơn `baseline` trên tác vụ đánh giá đối với các check quy ước chung mà curator đã khái quát hóa (như cấu trúc đầu ra, type hints, quy trình test hồi quy và changelog), nhưng mức độ cải thiện trên tác vụ đánh giá sẽ thấp hơn so với tác vụ học do hiện tượng quá khớp (overfitting) và do tác vụ đánh giá xuất hiện thêm quy ước tổ chức mới mà curator chưa từng thấy trong phản hồi của tập học. Căn cứ: nghiên cứu SkillsBench và SkillEvolBench chỉ ra rằng skill do mô hình tự sinh có tỷ lệ tổng quát hóa sang tác vụ mới thấp hơn so với skill người biên soạn.
- H3 (tác vụ học so với tác vụ đánh giá): Điểm trung bình của cả ba điều kiện trên tác vụ học sẽ cao hơn tác vụ đánh giá, đặc biệt ở nhóm check quy ước tổ chức (`rule_*`). Căn cứ: tác vụ đánh giá bảo lưu quy ước cũ nhưng bổ sung quy ước Acme mới chưa từng xuất hiện trong phản hồi lỗi của tác vụ học, dẫn đến việc tác tử không thể suy đoán được quy ước ẩn này nếu không có phản hồi trước đó; đồng thời dữ liệu của tác vụ đánh giá mới lạ khiến mô hình dễ gặp trường hợp biên chưa được kiểm thử trong prompt của tập học.

## 3. Làm quen Deep Agents (Phần 0.3)

1. Tác tử mặc định có 9 công cụ: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`, `execute`, `task`. Công cụ duy nhất cho phép chạy lệnh là `execute`.
2. Mô tả của công cụ `task` nêu: subagent `general-purpose` được dùng để nghiên cứu câu hỏi phức tạp, tìm kiếm file/nội dung khi chưa chắc chắn kết quả, và thực thi chuỗi tác vụ nhiều bước. Về ngữ cảnh: subagent hoạt động phi trạng thái (stateless by default), chỉ nhìn thấy nội dung prompt được tác tử chính giao cho nó và trả về một báo cáo cuối cùng; nó không nhìn thấy toàn bộ lịch sử hội thoại trước đó của tác tử chính.
3. Trích dẫn câu hướng dẫn hành vi:
   - Từ mô tả công cụ `task`: *"Put full detail in the prompt and state exactly what it should return — unless an agent type below says it inherits your conversation instead."*
   - Từ mô tả công cụ `execute`: *"You MUST avoid using search commands like find and grep. Instead use the grep, glob tools to search. Use read_file rather than cat/head/tail."*

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

| Tác vụ | Check thất bại | Nhóm lỗi (A-G) | Bằng chứng (trích ngắn từ `detail` hoặc vết) |
|---|---|---|---|
| `code-learn` | `csv_quoting_follows_docstring` | A | `to_csv_row returned 'Desk, large "oak",10.00,2'` (bỏ qua quy tắc RFC 4180 trong docstring: bọc ngoặc kép khi có dấu phẩy/ngoặc kép và nhân đôi ngoặc kép bên trong) |
| `code-learn` | `rule_type_hints` | E | `RULE: every public function (name not starting with '_') in the package has type annotations on all parameters and on the return value.` |
| `code-learn` | `rule_regression_tests` | E | `RULE: add tests/test_regressions.py with one test function per bug you fixed (at least 3); the file must pass.` |
| `code-learn` | `rule_changelog` | E | `RULE: record each fix in CHANGELOG.md under the heading '## Unreleased' as a bullet '- fix(<function name>): <short description>' (at least 3 bullets).` |
| `data-learn` | `north_q1_revenue` | D | `north_q1_revenue: wrong value (got 0.0)` (bỏ sót xử lý đa định dạng ngày YYYY-MM-DD, DD/MM/YYYY, ISO-8601 offset và giá trị khuyết -999) |
| `data-learn` | `north_q1_orders` | D | `north_q1_orders: wrong value (got 0)` (lọc ngày sai dẫn đến số đơn hàng Q1 tính ra 0) |
| `data-learn` | `top_region` | D | `top_region: wrong value (got 'West')` (không chuẩn hóa khoảng trắng và viết hoa trước khi gom nhóm doanh thu theo vùng) |
| `data-learn` | `missing_amount_orders` | D | `missing_amount_orders: wrong value (got 0)` (không nhận diện giá trị sentinel -999 là missing amount) |
| `data-learn` | `duplicate_rows_removed` | D | `duplicate_rows_removed: wrong value (got 0)` (không loại bỏ dòng trùng order_id) |
| `data-learn` | `rule_money_in_cents` | E | `RULE: money values in answer.json are integer cents (1606.67 USD is written 160667).` |
| `data-learn` | `rule_meta_block` | E | `RULE: answer.json has an object meta = {"source": <input file name>, "rows_in": ..., "rows_used": ...}` |
| `data-learn` | `rule_clean_csv` | E | `RULE: write workspace/clean.csv with the header order_id,timestamp_utc,region,amount_cents; one row per distinct order with a known amount...` |
| `logs-learn` | `entry_count` | D | `wrong number of entries (got 14)` (bỏ sót việc bóc tách toàn bộ log nhiều dòng và lọc cấp độ ERROR/CRITICAL) |
| `logs-learn` | `timestamps_utc` | D | `0/25 timestamps match` (không chuyển đổi định dạng thời gian về chuẩn ISO-8601 UTC) |
| `logs-learn` | `exception_fields` | A | `25 wrong exception values` (không trích xuất đúng dòng cuối cùng của stack trace theo đặc tả) |
| `logs-learn` | `repeat_counts` | A | `25 wrong repeat_count values` (không cộng dồn mẫu dòng '-- last message repeated N times --') |
| `logs-learn` | `counts_by_service` | D | `counts_by_service: wrong values` (tính sai tổng số lỗi do repeat_count sai) |
| `logs-learn` | `rule_service_names` | E | `RULE: service names in the output are lower-case with '-' replaced by '_' (payment-service -> payment_service).` |
| `logs-learn` | `rule_sorted_errors` | E | `RULE: errors is sorted by service, then by timestamp_utc, ascending.` |
| `logs-learn` | `rule_schema_header` | E | `RULE: the top-level object has "schema_version": 2 and "generated_by": "log-triage".` |

Nhận xét:
- Nhóm lỗi E (Vi phạm quy ước tổ chức) chiếm đa số áp đảo trên cả 3 tác vụ. Đây là các quy tắc ẩn của "Acme" mà đề bài ban đầu không nêu. Skill do curator sinh hoàn toàn có khả năng phòng ngừa nhóm này vì curator đã trích xuất được các yêu cầu về metadata, định dạng cents, header, quy ước đặt tên và yêu cầu changelog vào các checklist mệnh lệnh.
- Nhóm lỗi A và D xuất hiện ở `data-learn` và `logs-learn` do mô hình `gpt-4o-mini` xử lý dữ liệu bẩn và chuỗi phức tạp chưa triệt để.
- Bằng chứng phủ định: ở `code-learn`, 6/6 check kỹ thuật chức năng đều đạt 100% (`visible_suite_passes`, `tests_not_modified`, `parse_price_all_formats`, `other_caller_fixed`, `discount_rounds_half_up`, `low_stock_follows_docstring`), chứng minh tác tử giải quyết rất tốt logic lập trình cốt lõi nhưng thất bại ở các quy ước bổ trợ không có trong đề.

## 5. Điều kiện `subagents` (Phần 2.3)

- Các subagent đã định nghĩa:
  1. `explorer`: Chuyên đọc và trích xuất đặc tả từ README, docstrings, changelog, dữ liệu mẫu mà không làm thay đổi file.
  2. `implementer`: Chuyên thực hiện các chỉnh sửa code/data cụ thể và chạy kiểm thử tự động xác nhận.
  3. `reviewer`: Rà soát độc lập kết quả đầu ra theo đề bài và kiểm tra các trường hợp biên.
- `subagent_calls` ở từng tác vụ:
  - `code-learn`: 0 lần. Tác tử chính tự nhận diện các file lỗi và dùng trực tiếp các file tools (`read_file`, `write_file`, `execute`) để sửa.
  - `data-learn`: 2 lần. Tác tử chính đã gọi subagent để khám phá và thực thi việc làm sạch dữ liệu.
  - `logs-learn`: 0 lần. Tác tử chính tự phân tích file `app.log`.
- Thông tin thiếu hoặc thừa khi giao việc: Ở `data-learn`, prompt giao việc của tác tử chính tóm tắt tương đối đầy đủ nhưng subagent chạy độc lập trong sandbox dẫn đến việc thực thi nhiều vòng lặp khám phá.
- Ảnh hưởng đến token và thời gian: Khi không gọi subagent (`code-learn`, `logs-learn`), số token và thời gian tương đương `baseline` (khoảng 26k-29k tokens, 16-30 giây). Khi gọi subagent (`data-learn`), chi phí token tăng vọt lên 4,451,699 tokens (so với baseline 25,744 tokens, tăng hơn 170 lần) và thời gian thực thi kéo dài đến 717 giây.

## 6. Self-evolving: skill do curator sinh (Phần 3)

- Số lần chạy curator: 1 lần. Số skill bị xóa: 0. Cả 3 skill được mô hình sinh ra đều vượt qua bộ kiểm tra an toàn `validate_skill` (đúng format frontmatter, độ dài ≤ 40 dòng, không rò rỉ eval markers).

| Skill | Tổng quát hay riêng cho tác vụ học? | Đúng hay sai (nêu chỗ sai nếu có) | Độ dài, `description` và `skills_read` ở Phần 3.4 |
|---|---|---|---|
| `general-output-formatting` | Tổng quát cho mọi bài toán xuất file JSON/CSV | Đúng. Hướng dẫn kiểm tra metadata, định dạng số/tiền tệ, cấu trúc header và sắp xếp | 19 dòng. `description`: "Use when generating output files to ensure compliance with specified formats." Đọc ở 3.4: 0 (tác tử giải quyết dựa trên prompt). |
| `type-annotations-and-documentation` | Tổng quát cho code Python | Đúng. Hướng dẫn thêm type hints cho toàn bộ public function và viết docstring rõ ràng | 16 dòng. `description`: "Use when defining functions to ensure clarity and maintainability." Đọc ở 3.4: 0. |
| `regression-testing-and-changelog` | Tổng quát cho bảo trì và sửa bug | Đúng. Hướng dẫn viết test hồi quy độc lập và ghi nhận vào CHANGELOG.md theo định dạng chuẩn | 16 dòng. `description`: "Use when fixing bugs or making changes to ensure proper documentation and testing." Đọc ở 3.4: 0. |

## 7. Kết quả so sánh (Phần 4.3, 4.4)

(Sẽ cập nhật sau khi hoàn thành chạy đánh giá ở Phần 4)

## 8. Phân tích

(Sẽ hoàn thiện sau khi có số liệu bảng ở Phần 7)

## 9. Hạn chế và tính hợp lệ

(Sẽ hoàn thiện sau khi có số liệu bảng ở Phần 7)

## 10. Kết luận

(Sẽ hoàn thiện sau khi có số liệu bảng ở Phần 7)

## Phụ lục

- Lệnh đã chạy (theo thứ tự):
- Thử thách mở rộng (nếu có): Hướng 6a (tiến hóa tại thời điểm chạy - hot-path)
- Ghi chú khác:
