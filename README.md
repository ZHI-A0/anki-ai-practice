# anki-ai-practice

`anki-ai-practice` 是一个面向 Anki 桌面端的练习生成插件。它可以从你已有的 Anki 笔记/卡片中读取学习材料，构建本地知识图谱，并基于这些内容生成选择题、填空题等练习，用来测试和加深记忆。

这个项目的目标不是替代 Anki 的复习系统，而是在复习之外提供一种“反向练习”能力：你已经背过一些词汇、概念或知识点后，插件可以根据这些已学内容生成新的问题，让你主动回忆和辨析。

## 当前能做什么

### 1. 从选中的 Anki 笔记生成临时练习

在 Anki 的 Browse / 浏览 页面中选中一些 notes/cards 后，可以通过右键菜单生成练习。

当前支持的主要形式是选择题 / 填空题。插件会读取配置中的字段，例如：

- 答案字段：如 `英语单词`、`Front`、`正面`、`Term`
- 题干字段：如 `英语例句`、`Example`、`Sentence`
- 解释字段：如 `中文释义`、`中文例句`、`Meaning`、`Back`

### 2. Local-first 本地优先模式

Local-first 模式不会调用大模型 API。它主要依赖你牌组内已有字段和本地知识图谱生成练习。

Local-first 会优先使用已经构建好的本地图谱，从图谱中选择与正确答案最相似的 3 个节点作为混淆项。

### 3. LLM-first 大模型优先模式

LLM-first 模式会调用 OpenAI-compatible API，让大模型根据笔记内容生成题干、解释或问答。

### 4. 双知识图谱

插件现在会为牌组构建两种本地图谱：
- Spelling graph / 拼写图
- Meaning graph / 释义图

### 5. 图谱可视化

提供 3D-like 的图谱查看器：
- 点击节点：切换中心节点
- 拖动画布空白处或连线：旋转图谱
- 鼠标滚轮：缩放
- 悬停节点：查看释义和例句
- 中心节点、一阶节点、二阶节点使用不同颜色区分
- 节点远近根据当前邻居集合中的相对相似度决定
- 节点之间有最小间隔，避免完全重叠

### 6. 从最近复习卡片生成练习

新增菜单入口：
```text
Tools → AI Practice → Generate from Recently Reviewed
```
插件会读取最近复习的卡片对应的 notes 并生成练习题。

### 7. 保存生成的练习为 Anki 卡片

新增菜单入口：
```text
Tools → AI Practice → Save Generated Practice as Cards
```
可以把最近一次生成的练习题保存成新的 Anki 牌组/笔记。

## 安装方式

- 将插件 clone 到 `addons21` 目录
- 重启 Anki

## 使用流程

1. 构建知识图谱
2. 查看知识图谱
3. 从 Browse 或最近复习生成练习
4. 使用新菜单保存练习为正式卡片

## 配置

可通过 `Tools → AI Practice → Settings` 配置：
- 生成模式：local-first / llm-first
- 图谱字段
- 题干/答案/解释字段
- 最近复习扫描量和生成数量限制
- LLM API 配置

## License

MIT License