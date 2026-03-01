#!/usr/bin/env python3
# Check for hidden Unicode characters in playground.md
with open(r'd:\trpg_table\playground.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

found = 0
for i, line in enumerate(lines):
    for j, c in enumerate(line):
        cp = ord(c)
        # Flag: NBSP, other invisible/control chars, zero-width chars
        if cp == 0xA0:
            print(f"  Line {i+1}, Col {j+1}: NO-BREAK SPACE (U+00A0)")
            found += 1
        elif cp in (0x200B, 0x200C, 0x200D, 0xFEFF, 0x2060):
            print(f"  Line {i+1}, Col {j+1}: ZERO-WIDTH U+{cp:04X}")
            found += 1
        elif cp == 0x3000:
            print(f"  Line {i+1}, Col {j+1}: IDEOGRAPHIC SPACE (U+3000)")
            found += 1

print(f"\nTotal hidden chars found: {found}")
if found == 0:
    print("File is clean! No NBSP or hidden Unicode detected.")
    print("\nThe edit tool failure was likely due to a string matching issue,")
    print("not a Unicode encoding problem.")
