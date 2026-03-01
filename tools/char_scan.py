# -*- coding: utf-8 -*-
"""
Clean playground.md: replace risky 4-byte emoji with safe 2-3 byte alternatives.
Also strips Variation Selector U+FE0F.

Safe chars (keep as-is):
  - All CJK characters
  - Basic markdown symbols
  - These specific symbols: * (asterisk for bold)

Replacement map (risky -> safe):
  U+1F4A5  -> [!!]     (was explosion emoji)
  U+2620   -> [KILL]   (was skull)
  U+1F6A9  -> [FLAG]   (was flag)
  U+1F512  -> [LOCK]   (was lock)
  U+1F9E0  -> [PSI]    (was brain/psychic)
  U+1F489  -> [MED]    (was syringe)
  U+1F3B2  -> [DICE]   (was dice)
  U+FE0F   -> (strip)  (variation selector, invisible but causes matching issues)
"""
import sys

TARGET = r'd:\trpg_table\playground.md'

REPLACEMENTS = {
    '\U0001F4A5': '[!!]',      # explosion
    '\u2620': '[KILL]',         # skull
    '\U0001F6A9': '[FLAG]',    # flag
    '\U0001F512': '[LOCK]',    # lock
    '\U0001F9E0': '[PSI]',     # brain
    '\U0001F489': '[MED]',     # syringe
    '\U0001F3B2': '[DICE]',    # dice
    '\uFE0F': '',              # variation selector - strip
}

with open(TARGET, 'r', encoding='utf-8') as f:
    text = f.read()

count = 0
for old, new in REPLACEMENTS.items():
    n = text.count(old)
    if n > 0:
        text = text.replace(old, new)
        count += n

with open(TARGET, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)

# Write a small marker file to confirm execution
with open(TARGET + '.cleaned', 'w') as f:
    f.write('replaced %d chars' % count)
