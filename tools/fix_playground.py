import pathlib

p = pathlib.Path(r'd:\trpg_table\playground.md')
c = p.read_text(encoding='utf-8')

# Find the header section end and the execution instructions section
header_end = c.index('> 规则：') 
header_end = c.index('\n', header_end) + 1

# Find "## 执行指令示例" or the --- before it
exec_section = c.index('## 执行指令示例')
# Find the --- before it
dash_before = c.rfind('---', 0, exec_section)

# Build new content: keep header, add separator, keep everything from 执行指令示例 onward
new_content = c[:header_end] + '\n---\n\n' + c[exec_section:]

p.write_text(new_content, encoding='utf-8')
print('Done. File updated.')
