import sys

filepath = r'd:\trpg_table\playground.md'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'R29-E' in line:
        new_lines.append('| R29-E | - | \u5168\u961f | \u8fdb\u5165MT-7\u7ef4\u4fee\u901a\u9053 | 19:30 | - | \u2705 | \u6851\u524d/\u9646\u4e2d(\u80cc\u9c7c)/\u5927\u9ec4\u5de6\u7ffc/\u5218\u6bbf\u540e |\n')
    else:
        new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Done. Fixed R29-E line.')
