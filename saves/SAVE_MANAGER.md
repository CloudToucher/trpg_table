# 存档系统说明

## 核心概念

- **存档 = 剪切**：运行态文件被移出到归档目录，原位置不保留。
- **读档 = 剪切**：归档文件被移回运行态目录，归档被消费（不保留副本）。
- **不做备份**：没有快照、没有副本，数据始终只存在于一个地方。
- **单槽位**：同一战役只保留最新一份存档，存档时自动清理旧存档。

## 什么时候需要存档/读档

| 场景 | 操作 |
|------|------|
| `characters/active/` 有角色 → 玩家说"继续游戏" | **直接继续**，不需要读档 |
| `characters/active/` 无角色 → 玩家说"继续游戏" | 需要先 `restore` 读档 |
| 玩家说"存档"或会话结束 | 先写存档文件，再 `archive` 剪切到归档 |
| 玩家说"开新游戏" | 先 `archive` 存档当前局（如有），再开始新局 |

## 工具位置

```
tools/save_manager.py    ← 存档管理器（唯一代码文件位置）
```

## 常用命令

```bash
# 查看当前运行态文件状态
python tools/save_manager.py status

# 存档（剪切当前局到归档目录）
python tools/save_manager.py archive -c zhaoyutong --main-roles "赵雨桐+林立" --ai-blip "隧道推进" --note "Day1 文化路站"

# 列出所有存档
python tools/save_manager.py list

# 读档（剪切归档回运行目录）
python tools/save_manager.py restore -c zhaoyutong

# 仅预览，不实际操作
python tools/save_manager.py archive -c zhaoyutong --dry-run
python tools/save_manager.py restore -c zhaoyutong --dry-run
```

## 运行态文件范围

存档/读档操作涉及的文件：

- `characters/active/*.md`（排除 `示例角色*`）
- `logs/session/*.md`
- `logs/combat/*.md`
- `logs/exploration/*.md`
- `logs/system/*.md`
- `saves/save_*.md`（排除模板文件）

## 归档目录结构

```
saves/
  archives/
    index.json
    <campaign_id>/
      <save_id>/
        manifest.json
        summary.md
        data/
          characters/active/...
          logs/...
          saves/save_*.md
```
