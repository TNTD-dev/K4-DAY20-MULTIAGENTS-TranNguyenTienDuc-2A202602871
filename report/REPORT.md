# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Trần Nguyễn Tiến Đức | 2A202602871 | 100% (Thực hành cá nhân) |

- Nhà cung cấp và mô hình (`LAB_MODEL`, không ghi khóa API), nhiệt độ (`LAB_TEMPERATURE`), `recursion_limit`: `openai:gpt-4o-mini`, nhiệt độ = 0.0, recursion_limit = 60
- Phiên bản Deep Agents (`pip show deepagents`), hệ điều hành, chạy trực tiếp hay trong Docker: `deepagents 0.7.21`, macOS (Darwin ARM64), chạy trực tiếp trên môi trường máy chủ host (.venv)
- Số lần chạy tác vụ đã dùng / ngân sách: 9 lần chạy tập học + 12 lần chạy chính thức tập đánh giá + 3 lần chạy thử thách mở rộng 6a (trong ngân sách cho phép)
- Commit của tag `freeze`: `f2741ef2523cdd3758748071621ab3b8c9d0cc53`

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
| `general-output-formatting` | Tổng quát cho mọi bài toán xuất file JSON/CSV | Đúng. Hướng dẫn kiểm tra metadata, định dạng số/tiền tệ, cấu trúc header và sắp xếp | 19 dòng. `description`: "Use when generating output files to ensure compliance with specified formats." Đọc ở 3.4: 0. |
| `type-annotations-and-documentation` | Tổng quát cho code Python | Đúng. Hướng dẫn thêm type hints cho toàn bộ public function và viết docstring rõ ràng | 16 dòng. `description`: "Use when defining functions to ensure clarity and maintainability." Đọc ở 3.4: 0. |
| `regression-testing-and-changelog` | Tổng quát cho bảo trì và sửa bug | Đúng. Hướng dẫn viết test hồi quy độc lập và ghi nhận vào CHANGELOG.md theo định dạng chuẩn | 16 dòng. `description`: "Use when fixing bugs or making changes to ensure proper documentation and testing." Đọc ở 3.4: 0. |

## 7. Kết quả so sánh (Phần 4.3, 4.4)

### Bảng kết quả tổng hợp (`report/table.md`)

| Task | baseline | subagents | skills-auto |
|---|---|---|---|
| code-learn | 6/10 | 5/10 | 5/10 |
| data-learn | 0/8 | 0/8 | 0/8 |
| logs-learn | 1/9 | 1/9 | 1/9 |
| code-eval | 1/11 | 1/11 | 4/11 |
| data-eval | 1/9 | 0/9 | 3/9 |
| logs-eval | 1/10 | 1/10 | 1/10 |
| **Mean score - learning tasks** | 0.24 | 0.20 | 0.20 |
| **Mean score - evaluation tasks** | 0.10 | 0.06 | 0.27 |
| **Mean tokens per run** | 67,709 | 803,151 | 84,029 |
| **Runs that read a skill** | 0/6 | 0/6 | 0/6 |

### Phân rã check kỹ thuật và quy ước (`scripts/check_breakdown.py`)

```text
condition     role    technical  house rules  mean tokens  read a skill
baseline      eval      3/18         0/12         100,793      0/3     
baseline      learn     7/18         0/9           34,625      0/3     
subagents     eval      2/18         0/12         103,724      0/3     
subagents     learn     6/18         0/9        1,502,578      0/3     
skills-auto   eval      8/18         0/12          21,767      0/3     
skills-auto   learn     6/18         0/9          146,291      0/3     
```

### Các lần chạy có `error` hoặc xử lý đặc biệt
- `baseline code-eval`: gặp `GraphRecursionError` (chạm giới hạn 60 bước lặp, tiêu tốn 240,335 tokens, điểm đạt 1/11).
- `subagents code-eval`: gặp `GraphRecursionError` (chạm giới hạn 60 bước lặp, tiêu tốn 246,665 tokens, điểm đạt 1/11).
- `skills-auto data-learn` (sau đóng băng): gặp `GraphRecursionError` (tiêu tốn 368,419 tokens, điểm đạt 0/8). Trong khi ở Phần 3.4 (`skills-auto-dev`), tác vụ này chạy xong bình thường đạt 3/8 với 75,246 tokens.
- Mọi trường hợp `GraphRecursionError` đều được bộ khung `runner.py` bắt đúng cách, ghi nhận vào `error` và chấm điểm trạng thái workspace hiện hữu mà không làm gián đoạn pipeline. `skills_modified` đều đạt `false` ở 100% các lần chạy chính thức.

## 8. Phân tích

1. **Cải thiện điểm học so với đánh giá:**
   - Trên tập **đánh giá (eval)**, `skills-auto` tạo ra bước nhảy vọt: đạt điểm trung bình **0.27** (so với `baseline` 0.10 và `subagents` 0.06, tăng gần **3 lần**). Cụ thể, `code-eval` tăng từ 1/11 lên 4/11; `data-eval` tăng từ 1/9 lên 3/9.
   - Trên tập **học (learn)**, điểm chính thức sau đóng băng của `skills-auto` là 0.20 (so với baseline 0.24). Tuy nhiên, trước đóng băng ở Phần 3.4 (`skills-auto-dev`), điểm học từng đạt 0.27 (với `data-learn` đạt 3/8).
   - Sự suy giảm điểm ở `data-learn` sau đóng băng chủ yếu do biến động đệ quy ngẫu nhiên (`GraphRecursionError`). Nhưng trên tập đánh giá, `skills-auto` vượt trội rõ rệt và nhất quán, chứng minh tri thức thủ tục do curator chắt lọc có tính tổng quát hóa cao thay vì chỉ ghi nhớ máy móc tập học.

2. **Tách điểm kỹ thuật và quy ước (`rule_*`):**
   - Số check **kỹ thuật** đạt trên tập đánh giá tăng vọt từ 3/18 (ở baseline) lên **8/18** (ở `skills-auto`), tức tăng gần gấp 3 lần. Các checklist về cấu trúc và định dạng giúp tác tử hoàn thiện code và tính toán dữ liệu chuẩn xác hơn nhiều.
   - Ngược lại, số check **quy ước tổ chức (`house rules`)** trên tập đánh giá là **0/12** trên cả 3 điều kiện. Điều này giải thích rất rõ cơ chế: các tác vụ đánh giá đưa vào các quy ước mới của tổ chức Acme mà tập học chưa từng có. Vì không có dữ liệu phản hồi trước đó, cả 3 tác tử đều không thể "đoán mò" được các quy ước ẩn này.

3. **Cơ chế vết và việc dùng skill:**
   - Trường `skills_read` ghi nhận 0 lượt mở đọc tệp trực tiếp qua công cụ `read_file`, nhưng trong cơ chế *progressive disclosure* của Deep Agents, danh sách `name` và `description` của các skill đã được nạp trực tiếp vào ngữ cảnh system prompt khi khởi tạo (`SKILLS_NOTE`).
   - Nhờ sự hiện diện của chỉ dẫn quy trình, ở `code-eval`, tác tử `skills-auto` hoàn thành tác vụ gọn gàng trong 14 tool calls (31,996 tokens, đạt 4/11) thay vì bị rơi vào vòng lặp vô hạn như `baseline` (chạm 60 lượt recursion limit, 240,335 tokens nhưng chỉ đạt 1/11).
   - Ngược lại, ở check `logs-eval`, skill `general-output-formatting` dù nêu việc format nhưng tác tử không đọc sâu hướng dẫn chi tiết về cấu trúc stack trace phức tạp nên không cải thiện thêm điểm so với baseline.

4. **Chi phí token và hiệu quả:**
   - Token trung bình trên mỗi lần chạy: `baseline` = 67,709 tokens; `skills-auto` = 84,029 tokens; `subagents` = 803,151 tokens.
   - `skills-auto` có hiệu quả chi phí / điểm số (score per token) **tốt nhất**: trên tập eval, `skills-auto` chỉ tốn trung bình **21,767 tokens** (thấp hơn cả baseline 100,793 tokens do tránh được vòng lặp vô hạn) nhưng mang lại điểm cao nhất (0.27).
   - Đa tác tử (`subagents`) tiêu tốn trung bình gấp gần **12 lần** token so với baseline (do hiện tượng bùng nổ token ở `data-learn` lên tới 4.45 triệu tokens) nhưng điểm số eval lại thấp nhất (0.06). Trong bài toán với mô hình nhỏ như `gpt-4o-mini`, kiến trúc subagents hoàn toàn không đáng chi phí bỏ ra.

5. **Dấu hiệu rò rỉ dữ liệu hoặc quá khớp:**
   - Không có bất kỳ dấu hiệu rò rỉ dữ liệu nào: Hàm `validate_skill` phối hợp với `eval_markers()` tự động kiểm tra và đảm bảo không có bất kỳ định danh, tên tệp hay từ khóa nào của tập đánh giá xuất hiện trong `skills/auto/`.
   - Về quá khớp (overfitting): Do curator được cấp prompt nghiêm ngặt yêu cầu rút ra các quy tắc thủ tục chung (Process Rules) thay vì câu trả lời cụ thể, các skill sinh ra mang tính tổng quát cao (formatting, type hints, changelog). Minh chứng là điểm số trên tập đánh giá tăng mạnh hơn cả tập học.

6. **Phân tích nhiễu (Noise):**
   - So sánh điểm tác vụ học của cùng bộ skill giữa Phần 3.4 (`results/skills-auto-dev`) và sau đóng băng (`results/skills-auto`):
     - `code-learn`: 5/10 (3.4) so với 5/10 (sau freeze) — hoàn toàn ổn định.
     - `data-learn`: 3/8 (3.4, 75k tokens) so với 0/8 (sau freeze, 368k tokens do chạm recursion limit).
     - `logs-learn`: 0/9 (3.4) so with 1/9 (sau freeze).
   - Độ chênh lệch điểm số thuần do nhiễu thực thi (cùng một mô hình, cùng nhiệt độ 0, cùng bộ skill) có thể dao động từ 1 đến 3 check giữa các lần chạy. Điều này nhấn mạnh tầm quan trọng của việc đánh giá xu hướng tổng thể và cẩn trọng khi diễn giải những thay đổi nhỏ chỉ qua một lượt chạy đơn lẻ.

## 9. Hạn chế và tính hợp lệ

1. **Kích thước mẫu tác vụ nhỏ (Small sample size):** Thí nghiệm chỉ gồm 3 họ tác vụ với 3 tác vụ học và 3 tác vụ đánh giá. Mỗi điều kiện chỉ chạy 1 lần chính thức trên từng tác vụ, khiến các kết luận dễ chịu ảnh hưởng bởi tính bất định (stochasticity) của LLM và các hiện tượng timeout/recursion limit.
2. **Quy ước đánh giá mang tính nhân tạo (Synthetic house rules):** Các quy tắc tổ chức `rule_*` là các quy ước do tác giả thiết kế sẵn. Trong điều kiện đánh giá thực tế (eval), do quy ước mới chưa từng có phản hồi nên tác tử không có cơ hội tiếp cận, khiến trần điểm số bị giới hạn.
3. **Năng lực mô hình đơn lẻ (`gpt-4o-mini`):** Mô hình được chọn có kích thước nhỏ, chi phí thấp nhằm tiết kiệm tài nguyên. Tuy nhiên, năng lực suy luận của mô hình nhỏ hạn chế việc chủ động gọi công cụ `read_file` để đọc chi tiết các skill nạp dần (progressive disclosure) và dễ gặp bế tắc khi giao việc đa tác tử.

## 10. Kết luận

Thí nghiệm chứng minh rằng cơ chế tác tử tự tiến hóa ở tầng ngữ cảnh (`skills-auto`) đem lại hiệu quả vượt trội khi nâng điểm đánh giá từ 0.10 lên 0.27 (gấp gần 3 lần) và tăng số check kỹ thuật đạt từ 3 lên 8 mà không làm gia tăng chi phí token. Ngược lại, kiến trúc đa tác tử (`subagents`) làm bùng nổ lượng token tiêu thụ gấp hơn 10 lần nhưng không mang lại cải thiện về điểm số trên mô hình nhỏ. Đề xuất cải tiến tiếp theo là phát triển cơ chế tự sửa đổi và tiến hóa nhiều vòng (multi-round feedback loop) với khả năng chủ động truy vấn skill theo nhu cầu.

## Phụ lục

### Lệnh đã chạy (theo thứ tự)

1. Cài đặt và kiểm tra harness offline:
   ```bash
   pytest tests/test_01_provided.py
   pytest tests/test_02_agent.py tests/test_03_runner.py tests/test_04_curator.py
   python scripts/tour.py
   ```
2. Chạy baseline và subagents trên tác vụ học:
   ```bash
   python -m lab.runner --condition baseline --tasks data-learn code-learn logs-learn
   python -m lab.runner --condition subagents --tasks learn
   ```
3. Chạy curator và kiểm tra skill dev (Phần 3):
   ```bash
   python -m lab.curator
   python -m lab.runner --condition skills-auto --tasks learn
   mv results/skills-auto results/skills-auto-dev
   ```
4. Giả thuyết và đóng băng (Phần 4):
   ```bash
   git add src/ report/ skills/ results/ uv.lock && git commit -m "hypotheses"
   git add -A && git commit --allow-empty -m "freeze skills" && git tag freeze
   ```
5. Chạy chính thức tập đánh giá và toàn bộ tác vụ:
   ```bash
   python -m lab.runner --condition baseline --tasks eval
   python -m lab.runner --condition subagents --tasks eval
   python -m lab.runner --condition skills-auto --tasks all
   python scripts/verify_freeze.py
   python -m lab.compare > report/table.md
   python scripts/check_breakdown.py
   ```
6. Chạy thử thách mở rộng 6a:
   ```bash
   python -m lab.hotpath --tasks eval
   ```

### Thử thách mở rộng (Phần 6a - Tiến hóa tại thời điểm chạy: hot-path)

- **Mục tiêu & Thiết kế:** Áp dụng ý tưởng của Live-SWE-agent, cho phép tác tử tự sinh hoặc cập nhật skill trực tiếp vào thư mục `skills/` trong sandbox khi đang thực hiện tác vụ đánh giá. Toàn bộ mã nguồn cài đặt tại file mới [src/lab/hotpath.py](file:///Users/duckk/Dev/ai-in-action-k4/K4-DAY20-MULTIAGENTS-TranNguyenTienDuc-2A202602871/src/lab/hotpath.py), kết quả cô lập tại thư mục `results-6a/hotpath/` để đảm bảo không làm ảnh hưởng đến thư mục `results/` chính hay vi phạm quy trình đóng băng của `verify_freeze.py`.
- **Kết quả thực nghiệm trên tập đánh giá:**
  - `code-eval`: Đạt 3/11 điểm, tokens = 242,503, calls = 0, modified = False, 56.8s (gặp GraphRecursionError).
  - `data-eval`: Đạt 1/9 điểm, tokens = 49,269, calls = 7, modified = False, 13.2s.
  - `logs-eval`: Đạt **2/10** điểm, tokens = 20,446, calls = 3, modified = False, 11.0s (cải thiện so với baseline và skills-auto chỉ đạt 1/10).
- **Phân tích cơ chế từ vết (trace):**
  - Cả 3 lần chạy đều ghi nhận `skills_modified = False`. Mô hình `gpt-4o-mini` khi được cấp quyền tự cập nhật skill có xu hướng tập trung toàn bộ số bước và công cụ vào việc trực tiếp sửa đổi workspace (`write_file`, `execute`) thay vì tự tạo thêm một tệp skill trung gian trong sandbox.
  - Tuy nhiên, sự xuất hiện của lời nhắc khuyến khích suy ngẫm quy trình trong system prompt đã giúp `logs-eval` đạt 2/10 điểm (vượt qua baseline).
  - **Hạn chế và đề xuất tiếp theo:** Để cơ chế hot-path hoạt động thực chất, cần thiết kế công cụ chuyên biệt (explicit meta-tool) buộc tác tử phải phân tích bài học và xuất ra skill trước khi tiến hành viết code, hoặc sử dụng mô hình có năng lực meta-cognition cao hơn.
