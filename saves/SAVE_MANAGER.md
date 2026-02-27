# 标准化存档封存与恢复

本项目提供 `saves/save_manager.py`，用于将“当前运行态”迁移封存，支持后续按快照恢复。

## 1. 目标

- 封存当前局：把角色、日志、会话存档迁移到归档目录，避免影响新开局。
- 标准化交接：每次封存都生成 `manifest.json` + `summary.md`，可追溯、可审计。
- 可恢复：按 `campaign_id/snapshot_id` 将文件放回原路径。

## 2. 运行态范围（默认）

- `characters/active/*.md`
- `logs/session/*.md`
- `logs/combat/*.md`
- `logs/exploration/*.md`
- `logs/system/*.md`
- `saves/save_*.md`（不含 `save_initial_template.md`）

## 3. 归档目录结构

```text
saves/
  archives/
    index.json
    <campaign_id>/
      <snapshot_id>/
        manifest.json
        summary.md
        data/
          characters/active/...
          logs/session/...
          logs/combat/...
          logs/exploration/...
          logs/system/...
          saves/save_*.md
```

## 4. 常用命令

```bash
# 查看当前运行态文件状态
python saves/save_manager.py status

# 查看状态并输出文件明细
python saves/save_manager.py status --verbose

# 迁移封存当前局（推荐，封存后可直接开新局）
python saves/save_manager.py archive -c zhaoyutong --note "Day1 check point"

# 仅复制，不清空当前运行目录
python saves/save_manager.py archive -c zhaoyutong --mode copy

# 列出全部快照
python saves/save_manager.py list

# 列出指定战役快照
python saves/save_manager.py list -c zhaoyutong

# 恢复指定战役最新快照
python saves/save_manager.py restore -c zhaoyutong

# 恢复指定快照
python saves/save_manager.py restore -c zhaoyutong --snapshot 20260227_160000

# 只预览，不实际写入
python saves/save_manager.py archive -c zhaoyutong --dry-run
python saves/save_manager.py restore -c zhaoyutong --dry-run
```

## 5. 冲突处理

- `restore` 默认不覆盖已有文件。
- 若恢复时提示冲突，建议先封存当前局，再执行恢复。
- 若确认要覆盖，可使用 `--force`。

## 6. AI DM 执行职责（建议流程）

1. 会话结束或玩家说“封存当前局”时：
   `python saves/save_manager.py archive -c <campaign_id> --note "<摘要>"`
2. 玩家说“开始新游戏”前：
   `python saves/save_manager.py status`，确认 `new_game_ready: yes`。
3. 玩家说“继续某战役”时：
   `python saves/save_manager.py restore -c <campaign_id> [--snapshot <id>]`
4. 恢复后读取该战役的最新角色卡/日志/存档，继续主持。

## 7. 可选：扩展封存范围

如果你还有额外的运行态文件，可以在封存时追加 glob：

```bash
python saves/save_manager.py archive -c zhaoyutong --extra "story/main_plot/*.md"
```

恢复时会按 `manifest.json` 自动放回对应路径。
