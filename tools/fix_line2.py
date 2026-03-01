filepath = r'd:\trpg_table\playground.md'

with open(filepath, 'rb') as f:
    data = f.read()

# Find the R29-E line - locate the start and end
marker = 'R29-E'.encode('utf-8')
idx = data.find(marker)
if idx == -1:
    print('R29-E not found!')
else:
    # Find the start of this line (go back to previous newline)
    line_start = data.rfind(b'\n', 0, idx)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1  # skip the newline itself
    
    # Find the end of this line
    line_end = data.find(b'\n', idx)
    if line_end == -1:
        line_end = len(data)
    
    old_line = data[line_start:line_end]
    print(f'Found line at bytes {line_start}-{line_end}')
    print(f'Old line length: {len(old_line)} bytes')
    
    new_line = '| R29-E | - | \u5168\u961f | \u8fdb\u5165MT-7\u7ef4\u4fee\u901a\u9053 | 19:30 | - | \u2705 | \u6851\u524d/\u9646\u4e2d(\u80cc\u9c7c)/\u5927\u9ec4\u5de6\u7ffc/\u5218\u6bbf\u540e |'.encode('utf-8')
    
    new_data = data[:line_start] + new_line + data[line_end:]
    
    with open(filepath, 'wb') as f:
        f.write(new_data)
    
    print('Fixed!')
