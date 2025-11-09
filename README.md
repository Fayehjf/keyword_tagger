# 多语言关键词分析服务 (Multi-language Keyword Analysis Service)

本项目是 **《关键词切词与标签标注需求文档》** 的一个工程实现 Demo，目标是在多语言电商搜索/营销场景中，解析商品标题或关键词，提取**关键组成词（token）**并进行**标签标注（tagging）**。

---

## ✅ 核心能力

| 功能                     | 描述                                                       |
| ---------------------- | -------------------------------------------------------- |
| **API 驱动**             | 基于 FastAPI，提供 `/tokenize-and-tag` HTTP 接口（POST）。         |
| **智能切词（Tokenization）** | 支持多语言 spaCy + 固定搭配优先策略，避免错误拆词。                           |
| **标签标注（Tagging）**      | 标注为 8 类标签：品牌词 / 商品词 / 人群词 / 颜色词 / 尺寸词 / 材质词 / 型号词 / 属性词。 |
| **多语言支持**              | 支持 `keywords.csv` 中出现的语言：日语、德语、英语、法语、西班牙语（可扩展）。          |
| **词典优先**               | Python 加载词典 `.txt` 文件，通过 spaCy PhraseMatcher 实现固定搭配识别。   |

> 方案符合需求文档要求：固定搭配优先、可扩展词典、支持多语言。

---

## 📌 项目结构

```
simple_tagger/
├── app.py                  # FastAPI 服务器（接口入口）
├── processor.py            # 核心处理逻辑：切词 + 标签标注
├── dictionaries/           # 所有语言的自定义词典 (.txt)
├── keywords.csv            # 需求方提供的测试数据
└── requirements.txt        # Python 依赖
```

词典命名方式示例：

```
# dictionaries/
ja_brands.txt        # 品牌（日语）
ja_products.txt      # 商品词（日语）
ja_sizes.txt         # 尺寸（日语）
...
de_brands.txt        # 品牌（德语）
```

---

## 🚀 安装 & 启动

### 1️. 创建虚拟环境并激活

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2️. 安装依赖

```bash
pip install -r requirements.txt
```

### 3️. 安装对应语言的 spaCy 模型

项目依赖 keywords.csv 中出现的语言模型（ja / de / en / fr / es）：

```bash
python3 -m spacy download ja_core_news_sm
python3 -m spacy download de_core_news_sm
python3 -m spacy download en_core_web_sm
python3 -m spacy download fr_core_news_sm
python3 -m spacy download es_core_news_sm
```

### 4️. 运行服务

* 设置AI密匙

    在启动服务的同一个终端窗口中，运行以下命令：

    **Mac / Linux (Zsh / Bash):**

    ```bash
    # 将 YOUR_API_KEY 替换为从 OpenAI 网站获取的密钥
    export OPENAI_API_KEY="YOUR_API_KEY"
    ```

    **Windows (CMD):**

    ```bash
    set OPENAI_API_KEY="YOUR_API_KEY"
    ```
    processor.py 会自动从这个环境变量中读取密钥。

* 启动API服务

    设置好密钥后，在同一个终端中运行：

    ```bash
    uvicorn app:app --reload
    ```
---

## 🧪 API 使用示例

1. 启动服务：确保成功运行了 uvicorn

2. 访问文档: 在浏览器中打开自动生成的 Swagger 文档

    👉 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

3. 展开接口: 点击绿色的 POST /tokenize-and-tag 栏，将其展开。

4. 点击 "Try it out": 点击右上角的 "Try it out"（试一试）按钮，使请求体 (Request body) 变为可编辑状态。

5. 粘贴请求: 在 "Request body" 中粘贴以下 JSON。

    这个例子包含了：

        * haimont (品牌词, 假设它不在你的词典中, 将由 AI 标注)

        * ランニングベスト (商品词, 假设它在你的 ja_products.txt 中)

        * レディース (人群词, 假设它在你的 ja_people.txt 中)

    ```json
    {
    "keyword": "haimont ランニングベスト レディース 15l",
    "language": "ja"
    }
    ```

6. 执行：点击蓝色的 "Execute" 按钮。

7. 查看结果: 向下滚动到 "Responses" -> "Response body"。

    你将看到 AI 标注（haimont）会花费几秒钟时间，然后返回最终结果。

    返回结果：

    ```json
    {
    "original_keyword": "haimont ランニングベスト レディース 15l",
    "tokens": ["haimont", "ランニングベスト", "レディース", "15l"],
    "tagged_tokens": [
        {"token": "haimont", "tags": ["品牌词"], "confidence": 0.95},
        {"token": "ランニングベスト", "tags": ["商品词"], "confidence": 0.90},
        {"token": "レディース", "tags": ["人群词"], "confidence": 0.95},
        {"token": "15l", "tags": ["尺寸词"], "confidence": 0.99}
    ],
    "tag_summary": {
        "品牌词": ["haimont"],
        "商品词": ["ランニングベスト"],
        "人群词": ["レディース"],
        "尺寸词": ["15l"]
    }
    }
    ```

    0.99 置信度: 代表由词典 (.txt 文件) 高速匹配。

    0.80 置信度: 代表由 AI 标注（结果较慢，成本较高）。

---

## 🧠 关键实现策略与架构思考

### 策略一：词典优先 (固定搭配)

* 使用 spaCy PhraseMatcher 优先识别词典短语（如 "15l"）。

* 如果词典中能命中，则不会被 spaCy 的默认分词器拆分。

---

### 策略二：AI 备选 (处理未知词)

* 对于PhraseMatcher未命中的词（如新品牌 "haimont"），API 会进入“循环2”。

* 在这里，classify_unknown_token 函数 会被调用，它向 OpenAI API 发送一个上下文提示，以获取该词的标签。

* 这样就解决了词典无法穷举所有新词的“冷启动”问题。

---

### 策略三：多语言设计 (不做自动检测)

* 调用者必须在 API 请求中传递 language 参数。

* 优势: 避免语言检测错误；避免加载无关模型；极大提升 API 速度。

* processor.py 会根据 language 参数动态加载对应的 MODEL_MAP 模型和 dictionaries/ 词典。

---

### 策略四：词典管理（AI与动态更新）

* Demo 策略（API 实时调用 AI）：

    1. 为保证 Demo 能立即展示 AI 效果，本项目在 API 运行时实时调用 AI。

    2. 缺点: 速度慢，成本高（每次都调用）。

* Production 策略（读写分离）：

    1. 需求文档提示“利用 AI 构建词典 + 可动态更新”。

    2. 一个生产级系统应增加一个管理工具（如 run_batch.py 脚本）。

    3. 该工具负责离线调用 AI 分析未知词汇，并将结果安全地写入 .txt 词典文件。

    4. 写入后，通知主 API 重新加载词典。

    5. 优势：这样既实现了“动态更新”，保证了 API 的高速响应（所有词都来自内存词典），又避免了 API 在高并发下写入文件导致I/O阻塞或数据损坏的风险，并极大降低了 AI 成本。

---

## 🧱 架构权衡：独立词典 vs. 统一实体 (Phase 2 思考)

* 当前架构 (独立词典):

    1. ja_brands.txt 和 de_brands.txt 是完全独立的。

    2. 优势: 100% 满足了 PDF 的需求（只要求输出标签 tags: ["品牌词"]）；架构简单；内存高效（API 只加载请求语言的词典）。

    3. 局限: 系统并不知道 Adidas (en) 和 アディダス (ja) 是同一个品牌实体。

* 统一 架构 (实体链接):

    1. 这是一个关键的架构优化点。

    2. 我们可以用一个统一的数据库（例如 brand_database.json）来取代独立的 .txt 文件。

    3. 这个数据库会存储一个规范名称（Canonical Name，如 "Adidas"）以及它在所有语言中的变体（Variants，如 "アディダス"），API 的返回结果将更加丰富  

    4. 结论: 对于当前的 Demo，我们采用了更简单、直接的独立词典方案，因为它已完全满足需求文档。但“实体链接”是系统未来进行深度数据分析和扩展的关键。


## ➕ 如何扩展支持新的语言 (如：意大利语 it)

只需 3 步：

1. **安装 spaCy 模型**

    ```bash
    python3 -m spacy download it_core_news_sm
    ```

2. **更新 processor.py 中的MODEL_MAP**

    ```bash
    "it": "it_core_news_sm",
    ```

3. **新建词典文件**

    dictionaries/it_brands.txt
    dictionaries/it_products.txt

    API 重启后即可自动支持，无需修改核心代码。
