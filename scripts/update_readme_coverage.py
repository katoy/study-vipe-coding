#!/usr/bin/env python3
"""Update README.md coverage section from coverage XML.
Usage: scripts/update_readme_coverage.py [coverage.xml] [README.md]
If arguments omitted defaults to coverage.xml and README.md at repo root.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

cov_xml = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("coverage.xml")
readme = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("README.md")

if not cov_xml.exists():
    print(f"Coverage XML not found: {cov_xml}")
    sys.exit(1)
if not readme.exists():
    print(f"README not found: {readme}")
    sys.exit(1)

root = ET.fromstring(cov_xml.read_text())
# coverage.xml root has attribute line-rate as fraction 0..1
line_rate = float(root.get("line-rate", "0"))
line_percent = round(line_rate * 100)

# gather file level stats for app/ files
files = []
for package in root.findall("packages/package"):
    for clazz in package.findall("classes/class"):
        filename = clazz.get("filename", "")
        if not filename.startswith("app/"):
            continue
        lr = float(clazz.get("line-rate", "0"))
        # try to get lines-valid and lines-covered
        lines_valid = int(clazz.get("lines-valid", "0")) if clazz.get("lines-valid") else 0
        lines_covered = int(clazz.get("lines-covered", "0")) if clazz.get("lines-covered") else 0
        files.append((filename, lr * 100, lines_valid, lines_covered))

# sort by filename
files.sort()

# build replacement text
lines = []
lines.append("### 現在のカバレッジ結果（自動更新）")
lines.append(f"- 総合行カバレッジ: {line_percent}%")
lines.append("")
lines.append("ファイル別（抜粋）:")
for fn, pct, valid, covered in files:
    pct_int = round(pct)
    lines.append(f"- {fn}: {pct_int}% ({covered} / {valid} 行)")

replacement = "\n".join(lines) + "\n"

text = readme.read_text()
start_marker = "### 現在のカバレッジ結果（ローカル実行: pytest --cov=app 実行結果）"
# If old exact header not found, try an alternate header
if start_marker in text:
    start = text.index(start_marker)
else:
    # fallback: search for any line starting with '### 現在のカバレッジ結果'
    import re
    m = re.search(r"^### 現在のカバレッジ結果.*$", text, flags=re.M)
    if m:
        start = m.start()
    else:
        # prepend replacement near Tests and Coverage section if not found
        insert_after = "## テストとカバレッジ"
        i = text.find(insert_after)
        if i != -1:
            # insert after that section heading
            parts = text.split('\n')
            # find location of the section heading line
            for idx, line in enumerate(parts):
                if line.strip() == insert_after:
                    insert_at = idx + 1
                    break
            head = "\n".join(parts[:insert_at])
            tail = "\n".join(parts[insert_at:])
            new_text = head + "\n\n" + replacement + "\n" + tail
            readme.write_text(new_text)
            print("README updated (inserted coverage block)")
            sys.exit(0)
        else:
            print("Could not find insertion point for coverage block")
            sys.exit(1)

# find end marker as next '---' separator after start
end = text.find("---", start)
if end == -1:
    # fallback: replace until next top-level heading '## '
    import re
    m2 = re.search(r"^## ", text[start:], flags=re.M)
    if m2:
        end = start + m2.start()
    else:
        end = len(text)

new_text = text[:start] + replacement + text[end:]
readme.write_text(new_text)
print("README updated with coverage results")
