"""
骰池生成器 - 《末日地铁：无限》TRPG 工具

用法：
  python dice_pool.py          # 生成标准骰池并输出到控制台
  python dice_pool.py -o       # 生成并写入 dice_pool.md 文件
  python dice_pool.py -o FILE  # 生成并写入指定文件
  python dice_pool.py -a       # 追加模式（不覆盖已有内容）
  python dice_pool.py -l       # 大号骰池（数量翻倍）

组合用法：
  python dice_pool.py -o -l    # 大号骰池写入文件
  python dice_pool.py -o -a    # 追加到已有骰池文件
"""

import random
import sys
import os
from datetime import datetime

STANDARD_POOL = {
    "d100": 50,
    "d10": 15,
    "d8": 12,
    "d6": 15,
    "d4": 10,
}

LARGE_POOL = {k: v * 2 for k, v in STANDARD_POOL.items()}

DICE_MAX = {
    "d100": 100,
    "d10": 10,
    "d8": 8,
    "d6": 6,
    "d4": 4,
}


def roll_pool(pool_sizes: dict) -> dict:
    result = {}
    for dice, count in pool_sizes.items():
        max_val = DICE_MAX[dice]
        result[dice] = [random.randint(1, max_val) for _ in range(count)]
    return result


def format_pool(pool: dict) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"【骰池补充】 生成时间：{timestamp}", ""]
    
    for dice, values in pool.items():
        lines.append(f"{dice}:")
        # 每5个一行
        for i in range(0, len(values), 5):
            chunk = values[i:i+5]
            nums = ", ".join(str(v).rjust(2 if dice == "d100" else 1) for v in chunk)
            lines.append(f"  {nums}")
        lines.append("")  # 空行分隔不同骰子类型
    
    lines.append(f"共 {sum(len(v) for v in pool.values())} 个骰子。复制以上内容发送给DM即可。")
    return "\n".join(lines)


def main():
    args = sys.argv[1:]
    large = "-l" in args
    write_file = "-o" in args
    append = "-a" in args

    pool_sizes = LARGE_POOL if large else STANDARD_POOL
    pool = roll_pool(pool_sizes)
    output = format_pool(pool)

    print(output)
    print()

    if write_file:
        custom_path = None
        for i, a in enumerate(args):
            if a == "-o" and i + 1 < len(args) and not args[i + 1].startswith("-"):
                custom_path = args[i + 1]
                break

        filepath = custom_path or os.path.join(os.path.dirname(__file__), "dice_pool.md")
        mode = "a" if append else "w"
        with open(filepath, mode, encoding="utf-8") as f:
            if append:
                f.write("\n---\n\n")
            f.write(output + "\n")
        print(f"已{'追加' if append else '写入'}到: {filepath}")


if __name__ == "__main__":
    main()
