#!/usr/bin/env python3
"""Kiểm tra dấu vết chatbot và văn phong công thức trong văn bản tiếng Việt."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ERROR_PATTERNS = [
    (r"[—–]", "DASH", "Có gạch ngang dài hoặc gạch ngang vừa."),
    (r"…|\.\.\.", "ELLIPSIS", "Có dấu ba chấm hoặc dấu bỏ lửng."),
    (r"[→⇒➜➡↔↑↓]", "ARROW", "Có ký hiệu mũi tên trong văn bản."),
    (r"[✅✓✔❌✗⚠ℹ💡📌🚀🎯]", "ICON", "Có emoji hoặc biểu tượng trang trí."),
    (r"(?m)^\s{0,3}#{1,6}\s+", "MD_HEADING", "Có tiêu đề Markdown còn nguyên."),
    (r"```|~~~|`[^`]+`", "MD_CODE", "Có backtick hoặc hàng rào mã còn nguyên."),
    (r"(?m)^\s*(?:---|\*\*\*)\s*$", "MD_RULE", "Có đường phân cách Markdown."),
    (r"(?m)^\s*\|.*\|\s*$", "MD_TABLE", "Có hàng của bảng Markdown."),
    (r"\*\*[^*]+\*\*|__[^_]+__", "MD_EMPHASIS", "Có dấu tạo chữ đậm Markdown."),
    (r"【\d+】", "UI_CITATION", "Có ký hiệu trích dẫn giao diện không chuẩn."),
    (r"\\(?:frac|sum|text|begin|end)\b|\\[\[(]", "RAW_LATEX", "Có mã LaTeX chưa hiển thị."),
    (r"\[(?:tên|thêm|điền|nguồn|ngày|nội dung|insert|your)[^\]]*\]", "PLACEHOLDER", "Có chỗ giữ nội dung trong ngoặc vuông."),
    (r"<(?:tên|thêm|điền|nguồn|ngày|nội dung|insert|your)[^>]*>", "PLACEHOLDER", "Có chỗ giữ nội dung trong ngoặc nhọn."),
]

FORBIDDEN_PHRASES = [
    "dưới đây là", "tất nhiên", "hy vọng nội dung này hữu ích",
    "bạn có muốn tôi", "nếu bạn cần thêm", "trong bối cảnh hiện nay",
    "trong thời đại ngày nay", "trong thế giới ngày càng kết nối",
    "với sự phát triển không ngừng của", "không thể phủ nhận rằng",
    "có thể thấy rằng", "đóng vai trò vô cùng quan trọng",
    "một phần không thể thiếu", "mang lại nhiều lợi ích đáng kể",
    "mở ra nhiều cơ hội mới", "đặt ra nhiều cơ hội và thách thức",
    "góp phần thúc đẩy sự phát triển", "đáp ứng nhu cầu ngày càng cao",
    "tạo tiền đề cho", "cần có một cách tiếp cận toàn diện",
    "tiềm năng to lớn", "nếu được triển khai hợp lý",
    "nhiều nghiên cứu cho thấy", "các chuyên gia nhận định",
    "theo các báo cáo gần đây",
]

WARN_PATTERNS = [
    (r";", "SEMICOLON", "Có dấu chấm phẩy; cân nhắc tách câu."),
    (r":", "COLON", "Có dấu hai chấm; kiểm tra xem có thật sự cần."),
    (r"\([^)]{45,}\)", "LONG_PAREN", "Có nội dung dài trong ngoặc đơn."),
    (r"\b(?:và|hoặc)/(?:và|hoặc)\b|\b\w+/\w+\b", "SLASH", "Có dấu gạch chéo trong cụm từ."),
    (r"(?mi)^\s*(?:bên cạnh đó|ngoài ra|hơn nữa|tuy nhiên|do đó|vì vậy)[, ]", "LINKER", "Đoạn hoặc dòng mở bằng từ nối công thức."),
    (r"\b(?:thứ nhất|thứ hai|thứ ba|cuối cùng)\b", "ENUMERATION", "Có từ đánh số ý; kiểm tra thứ tự có cần thiết."),
]


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def scan(text: str) -> list[tuple[str, str, int, str]]:
    issues: list[tuple[str, str, int, str]] = []
    lowered = text.casefold()
    for pattern, code, message in ERROR_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            issues.append(("ERROR", code, line_number(text, match.start()), message))
    for phrase in FORBIDDEN_PHRASES:
        start = 0
        while True:
            index = lowered.find(phrase.casefold(), start)
            if index < 0:
                break
            issues.append(("ERROR", "PHRASE", line_number(text, index), f"Cụm từ bị cấm: {phrase!r}."))
            start = index + len(phrase)
    for pattern, code, message in WARN_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            issues.append(("WARN", code, line_number(text, match.start()), message))
    return sorted(issues, key=lambda item: (item[2], item[0] != "ERROR", item[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="Tệp UTF-8 cần kiểm tra. Bỏ trống để đọc stdin.")
    parser.add_argument("--text", help="Kiểm tra trực tiếp chuỗi được truyền vào.")
    args = parser.parse_args()

    if args.text is not None:
        text = args.text
    elif args.file:
        text = Path(args.file).read_text(encoding="utf-8-sig")
    else:
        text = sys.stdin.read()

    issues = scan(text)
    if not issues:
        print("PASS: Không phát hiện mẫu bị cấm hoặc cần xem xét.")
        return 0

    for severity, code, line, message in issues:
        print(f"{severity} {code} line {line}: {message}")
    errors = sum(1 for item in issues if item[0] == "ERROR")
    warnings = len(issues) - errors
    print(f"SUMMARY: {errors} error(s), {warnings} warning(s).")
    return 1 if errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
