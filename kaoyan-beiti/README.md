# 考研背题 kaoyan-beiti

把考研论述题的参考答案原文，整理成好懂、好背、考场上能直接写的两份 Markdown 背诵稿，需要时再做成手绘风知识卡片。

> Turn essay-question reference answers into an understanding version and an exam version you can memorize.

当前版本：`v1.1.0`（更新记录见 [CHANGELOG](CHANGELOG.md)）

## 它解决什么问题

机构给的论述题答案往往是一整段大白块：逻辑藏在长句里，例子散在各处，同一意思说两遍。直接背，既记不住结构，考场上也写不出层次。

这个 Skill 只做“整理”，不做“加料”：

```text
参考答案原文（文字 / PDF / 照片）
      ↓
逐字转录
      ↓
理解版：拆节、小标题、白话解释，用来读懂
      ↓
答题版：压缩到 ≤1.2 倍原文，用来背和考场作答
      ↓
（可选）知识卡片：一段一张 PNG
```

## 核心原则

- 每段首句原文照录、加粗，硬背。
- 专有名词、人名、作品名、引语、数字一字不改。
- 不加新知识点、新人名、新作品、新观点。
- 理解版字数 1.5–1.9 倍原文；答题版 ≤1.2 倍，宁减勿加但得分点不丢。
- 只算汉字，用脚本统计倍数。
- 排版适配 Obsidian 与任何 Markdown 预览：除连续列表项外每行之间空一行。

## 示例

《西方美学史》第 7 题：论述亚里士多德对柏拉图美学的批判与继承，以及他的美论。

- [原文](examples/第7题_原文.md)
- [理解版](examples/第7题_理解版.md)（1.67 倍）
- [答题版](examples/第7题_答题版.md)（1.01 倍）

## 安装

### 下载 ZIP

1. 在 GitHub 页面选择 **Code → Download ZIP**。
2. 解压后，把其中的 `kaoyan-beiti` 文件夹放进 Codex 或 Claude 的个人 Skills 目录。

### 使用 Git

```powershell
git clone https://github.com/zjun14896-cmd/brooke-skills.git
Copy-Item -Recurse brooke-skills\kaoyan-beiti "$env:USERPROFILE\.codex\skills\kaoyan-beiti"
```

## 使用

把一道论述题的参考答案原文交给 AI，然后说：

```text
请用 $kaoyan-beiti 帮我整理第 N 题。
```

## 它不会做什么

- 不会替你写一份“自己的答案”。没有原文就不开工。
- 不会补原文没有的知识点来“显得更全”。
- 不会自动做卡片，除非你要。

## License

[MIT](../LICENSE)
