#!/usr/bin/env python3
# Clear R33 player inputs in playground.md
import re

with open(r'd:\trpg_table\playground.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Liu's input line
content = re.sub(
    r'\[刘流柳\]巢母这个想法.*?丧尸。',
    '[刘流柳]',
    content,
    flags=re.DOTALL
)

# Replace Sang's input line
content = re.sub(
    r'\[老桑\]向刘老师询问.*?over',
    '[老桑]',
    content,
    flags=re.DOTALL
)

with open(r'd:\trpg_table\playground.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done. Verifying...")
with open(r'd:\trpg_table\playground.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(13, 22):
        print(f"Line {i+1}: {lines[i].rstrip()}")
