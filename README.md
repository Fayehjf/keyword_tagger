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
├── run_batch.py            # 脚本1: 批量运行 CSV 并调用 API，生成 'batch_results.json'
├── update_dictionaries.py  # 脚本2: 读取 results, 自动更新 dictionaries 文件夹
├── dictionaries/           # 所有语言的自定义词典 (.txt)
├── keywords.csv            # 需求方提供的测试数据
└── requirements.txt        # Python 依赖
```

---

## 🚀 安装 & 启动

### A 本地安装（仅需一次）

#### 1️. 创建虚拟环境并激活

```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2️. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3️. 安装对应语言的 spaCy 模型

项目依赖 keywords.csv 中出现的语言模型（ja / de / en / fr / es）：

```bash
python3 -m spacy download ja_core_news_sm
python3 -m spacy download de_core_news_sm
python3 -m spacy download en_core_web_sm
python3 -m spacy download fr_core_news_sm
python3 -m spacy download es_core_news_sm
```

### B 运行服务（每次运行时执行）

1. 设置AI密匙

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

2. 启动API服务

    设置好密钥后，在同一个终端中运行：

    ```bash
    uvicorn app:app --reload
    ```
---

## 🧪 测试方法一：手动API测试

此方法用于快速测试单个关键词。

1. 启动服务：确保成功运行了 uvicorn

2. 访问文档: 在浏览器中打开自动生成的 Swagger 文档

    👉 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

3. 展开接口: 点击绿色的 POST /tokenize-and-tag 栏，将其展开。

4. 点击 "Try it out": 使请求体 (Request body) 变为可编辑状态。

5. 粘贴请求: 在 "Request body" 中粘贴以下 JSON。

    这个例子包含了：

        测试词典：reloj inteligente (商品词(智能手表), 在 es_products.txt 中)

        测试AI：mujer (人群词(女士), 不在 es_people.txt 中)

    ```json
    {
    "keyword": "reloj inteligente mujer",
    "language": "es"
    }
    ```

6. 执行：点击蓝色的 "Execute" 按钮。

7. 查看结果: 向下滚动到 "Responses" -> "Response body"。

    返回结果：

    ```json
    {
        "original_keyword": "reloj inteligente mujer",
        "tokens": [
            "reloj inteligente",
            "mujer"
        ],
        "tagged_tokens": [
            {
            "token": "reloj inteligente",
            "tags": [
                "商品词"
            ],
            "confidence": 0.99
            },
            {
            "token": "mujer",
            "tags": [
                "人群词"
            ],
            "confidence": 0.8
            }
        ],
        "tag_summary": {
            "商品词": [
            "reloj inteligente"
            ],
            "人群词": [
            "mujer"
            ]
        }
    }
    ```

    0.99 置信度: 代表由词典 (.txt 文件) 高速匹配。

    0.80 置信度: 代表由 AI 标注。

---

## 🤖 测试方法二：批量测试与词典更新 (核心工作流)

**此方法是项目的核心，它实现了“AI 标注 -> 自动更新词典”的完整闭环。**

1. 运行批量测试 (run_batch.py)

    此脚本会读取 keywords.csv ，逐行调用 API，并（在需要时）触发 AI，最后将所有结果保存到 batch_results.json。

    1. 确保 API 正在运行 (在终端 1 中, 且已设置 OPENAI_API_KEY)。

    2. 打开第二个终端 (在 (venv) 环境中)。

    3. 运行 run_batch.py:

    ```bash
    python3 run_batch.py
    ```

    4. 脚本会显示一个进度条。完成后，会得到一个含有 AI 标注结果 (0.80) 的 batch_results.json 文件。

2. 运行词典更新 (update_dictionaries.py)

    此脚本会读取 batch_results.json，找到所有被 AI 标注的新词，并自动将它们追加到 dictionaries/ 文件夹下对应的 .txt 文件中。

    1. 在第二个终端中 (等 run_batch.py 运行完毕后)。

    2. 运行 run_batch.py:

    ```bash
    python3 update_dictionaries.py
    ```

    3. 会看到成功的日志。

3. 重启 API 以加载新词典

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

* 本项目通过 run_batch.py 和 update_dictionaries.py 实现了生产级的“读写分离”工作流。

    * “读” (API): app.py 负责高速响应。它只从内存中读取词典。

    * “写” (离线脚本):

        1. run_batch.py 负责离线批量调用 AI 分析未知词汇。

        2. update_dictionaries.py 负责将 AI 结果安全地写入 .txt 词典文件。


* 优势: 保证了 API 的高速响应（所有词都来自内存词典），并极大降低了 AI 成本，符合“利用 AI 构建词典 + 可动态更新”的需求 。

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

    4. 结论: 对于当前的 Demo，我采用了更简单、直接的独立词典方案，因为它已完全满足需求文档。但“实体链接”是系统未来进行深度数据分析和扩展的关键。


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
