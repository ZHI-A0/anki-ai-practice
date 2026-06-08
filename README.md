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

适合：

- 英语单词填空
- 概念辨析
- 根据已有例句挖空
- 不想消耗 API token 的场景

Local-first 会优先使用已经构建好的本地图谱，从图谱中选择与正确答案最相似的 3 个节点作为混淆项。

### 3. LLM-first 大模型优先模式

LLM-first 模式会调用 OpenAI-compatible API，让大模型根据笔记内容生成题干、解释或问答。

适合：

- 需要更自然的题干
- 需要根据知识点生成开放式问题
- 需要更详细解释
- 不局限于词汇场景的知识卡片

配置中可以设置：

- Base URL
- API Key
- Model
- Temperature
- 调用模式

### 4. 双知识图谱

插件现在会为牌组构建两种本地图谱：

#### Spelling Graph / 拼写图

基于英文词条本身计算相似度。当前主要参考：

- 字符 2-gram 重合度
- 字符 3-gram 重合度
- 单词长度相近度
- 前缀相似度

它更适合做词形辨析、拼写相近干扰项、英文填空题。

#### Meaning Graph / 释义图

基于释义字段计算相似度。当前主要参考：

- 中文释义 / 英文释义中的 token overlap
- 字符 2-gram 重合度

它更适合做语义相近干扰项，例如近义词、相关概念辨析。

注意：当前 meaning graph 仍是轻量本地算法，不是 embedding 语义向量。如果后续接入 embedding 模型，语义相似度会更准确。

### 5. 图谱可视化

插件提供一个 3D-like 的图谱查看器：

- 点击节点：切换中心节点
- 拖动画布空白处或连线：旋转图谱
- 鼠标滚轮：缩放
- 悬停节点：查看释义和例句
- 中心节点、一阶节点、二阶节点使用不同颜色区分
- 节点远近根据当前邻居集合中的相对相似度决定
- 节点之间有最小间隔，避免完全重叠

图谱查看入口：

```text
Tools → AI Practice → View Knowledge Graph
```

## 安装方式

### 开发安装

进入 Anki 的 add-ons 目录，把仓库 clone 到 `addons21` 下。

Windows 常见路径：

```text
C:\Users\你的用户名\AppData\Roaming\Anki2\addons21
```

然后执行：

```bash
git clone https://github.com/ZHI-A0/anki-ai-practice.git
```

重启 Anki。

### 更新插件

如果已经 clone 过，进入插件目录：

```bash
cd C:\Users\你的用户名\AppData\Roaming\Anki2\addons21\anki-ai-practice
git pull
```

然后重启 Anki。

## 使用流程

### 1. 构建知识图谱

先为你的牌组构建图谱：

```text
Tools → AI Practice → Build Knowledge Graph
```

选择一个牌组，然后点击：

```text
Build Dual Graphs from Deck
```

插件会扫描该牌组，生成：

- spelling graph
- meaning graph

图谱文件会保存到本地：

```text
C:\Users\你的用户名\.anki_ai_practice_graphs
```

### 2. 查看知识图谱

打开：

```text
Tools → AI Practice → View Knowledge Graph
```

选择牌组和图谱类型：

- Spelling graph
- Meaning graph

然后点击 `View Graph`。

### 3. 从 Browse 中生成练习

打开 Anki 的 Browse / 浏览 页面。

选中一些笔记或卡片。

右键菜单：

```text
AI Practice: Generate from Selection
```

然后在弹出的练习窗口中点击生成。

在 Local-first 模式下，插件会优先使用本地图谱，选择相似度最高的 3 个节点作为混淆项。

### 4. 设置

入口：

```text
Tools → AI Practice → Settings
```

当前可以配置：

- 生成模式：local-first / llm-first
- 图谱字段
- 题干字段
- 答案字段
- 解释字段
- 本地选项来源
- 使用 spelling graph 还是 meaning graph
- OpenAI-compatible API 配置

## 推荐配置示例：六级英语单词

如果你的笔记字段类似：

```text
英语单词
中文释义
英语例句
中文例句
```

可以使用默认配置。

推荐流程：

1. 先构建整个六级词汇牌组的知识图谱。
2. 做英文填空题时使用 spelling graph。
3. 做词义辨析题时使用 meaning graph。
4. 解释中包含中文释义和中文例句。

## 当前状态

这个插件仍处于开发阶段，功能正在快速变化。

已经实现：

- Browse 右键生成练习
- 主菜单 AI Practice 入口
- Local-first 生成
- LLM-first 生成
- OpenAI-compatible API 配置
- 双图谱构建
- 本地图谱保存
- 3D-like 图谱查看器
- 基于图谱相似度选择混淆项

仍在改进：

- 真正的 WebGL/three.js 3D 图谱
- embedding 语义图谱
- 更完善的设置页面
- 将生成练习保存成正式 Anki notes/cards
- 最近复习卡片自动读取
- 建图进度条和异步构建

## 技术说明

Anki 插件主要使用：

- Python
- Anki add-on API
- Qt / PyQt
- 本地 JSON 图谱存储
- OpenAI-compatible chat completions API，可选

本地知识图谱目前存储在用户目录下：

```text
~/.anki_ai_practice_graphs
```

## License

MIT License
