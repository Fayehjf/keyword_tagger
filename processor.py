import spacy
from spacy.matcher import PhraseMatcher
from spacy.tokens import Span
import spacy.util
from pathlib import Path
from typing import Dict, Set, List, Any
import os
import openai

# --- OpenAI 客户端初始化 ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("警告：未找到 OPENAI_API_KEY 环境变量。AI 标注功能将无法使用。")
    print("请在终端运行: export OPENAI_API_KEY='YOUR_API_KEY'")
    client = None
else:
    client = openai.OpenAI(api_key=api_key)


# --- 全局缓存 ---
NLP_MODELS: Dict[str, spacy.Language] = {}
DICTIONARIES: Dict[str, Dict[str, Set[str]]] = {}
MATCHERS: Dict[str, PhraseMatcher] = {}

# 词典文件名到真实标签的映射
TAG_MAPPING = {
    "brands": "品牌词",
    "products": "商品词",
    "people": "人群词",
    "scene": "场景词",
    "colors": "颜色词",
    "sizes": "尺寸词",
    "selling_points": "卖点词",
    "attributes": "属性词",
}

# spaCy 模型映射
MODEL_MAP = {
    "ja": "ja_core_news_sm", # 日语
    "de": "de_core_news_sm", # 德语
    "fr": "fr_core_news_sm", # 法语
    "en": "en_core_web_sm",  # 英语
    "es": "es_core_news_sm", # 西班牙语

    # 如需添加新语言 (例如 意大利语 'it'):
    # 1. 在终端运行: python3 -m spacy download it_core_news_sm
    # 2. 在下方添加一行: "it": "it_core_news_sm"
}

# AI 调用
def classify_unknown_token(token_text: str, original_keyword: str) -> str | None:
    """
    使用 AI 模型 (LLM) 来分类一个未知的 token。
    """
    # 如果客户端未初始化 (因为没有Key)，则跳过
    if not client: 
        return None

    # 定义8个标签
    tag_list = "品牌词, 商品词, 人群词, 场景词, 颜色词, 尺寸词, 卖点词, 属性词"
    
    # Prompt
    prompt = (
        f"你是一个电商关键词分析师。\n"
        f"在商品标题 “{original_keyword}” 中, \n"
        f"词语 “{token_text}” 最符合以下哪个类别？\n"
        f"类别: [{tag_list}, 或 'None']\n"
        f"请只回答一个类别名称，如果都不符合则回答 'None'。"
    )
    
    try:
        # --- 在此调用 AI API (真实的 OpenAI 调用) ---
        response = client.chat.completions.create(
             model="gpt-3.5-turbo", 
             messages=[{"role": "user", "content": prompt}],
             temperature=0
        )
        ai_result = response.choices[0].message.content.strip()
        
        if ai_result in tag_list:
            print(f"--- AI 标注成功: '{token_text}' -> '{ai_result}' ---")
            return ai_result
        else:
            return None
            
    except Exception as e:
        print(f"AI 调用失败: {e}")
        return None


def load_dictionaries(lang: str) -> Dict[str, Set[str]]:
    """从 dictionaries/ 文件夹加载所有词典到内存"""

    # 此函数会根据语言代码自动加载词典。
    # 如需为新语言 (例如 'it') 添加词典, 只需在 'dictionaries/' 文件夹中
    # 添加 'it_brands.txt', 'it_products.txt' 等文件即可。
    # 此处无需修改代码。

    if lang in DICTIONARIES:
        return DICTIONARIES[lang]

    print(f"--- 正在加载 {lang} 词典... ---")
    dict_path = Path("dictionaries")
    lang_dicts: Dict[str, Set[str]] = {}
    
    # 查找所有以 "ja_", "de_" 等开头的文件
    for f in dict_path.glob(f"{lang}_*.txt"):
        tag_key = f.stem.split('_', 1)[-1]
        pdf_tag_name = TAG_MAPPING.get(tag_key)
        
        if pdf_tag_name:
            try:
                with f.open('r', encoding='utf-8') as file:
                    # 读取、去重、转小写
                    terms = set(line.strip().lower() for line in file if line.strip())
                    lang_dicts[pdf_tag_name] = terms
                    print(f"  - 加载 {f.name}: {len(terms)} 个词条")
            except Exception as e:
                print(f"  - 无法加载 {f.name}: {e}")
        else:
            print(f"  - 跳过 {f.name}: 在 TAG_MAPPING 中未定义")

    DICTIONARIES[lang] = lang_dicts
    return lang_dicts

def get_spacy_model(lang: str) -> spacy.Language:
    """获取一个 spaCy 模型实例"""
    if lang in NLP_MODELS:
        return NLP_MODELS[lang]
    
    model_name = MODEL_MAP.get(lang)
    if not model_name:
        raise ValueError(f"不支持的语言: {lang}")

    print(f"--- 正在加载 spaCy 模型: {model_name} ---")
    try:
        nlp = spacy.load(model_name)
        NLP_MODELS[lang] = nlp
        return nlp
    except OSError:
        print(f"错误: 找不到 spaCy 模型 '{model_name}'。")
        print(f"请运行: python -m spacy download {model_name}")
        raise

def get_matcher(lang: str, nlp: spacy.Language) -> PhraseMatcher:
    """
    创建或获取一个 PhraseMatcher, 用于识别固定搭配 [cite: 18]
    """
    if lang in MATCHERS:
        return MATCHERS[lang]

    print(f"--- 正在为 {lang} 构建固定搭配匹配器... ---")
    lang_dicts = load_dictionaries(lang)
    
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    
    # 存储 "term" -> "tag" 的反向映射
    term_tag_map = {}

    for tag_name, terms in lang_dicts.items():
        patterns = [nlp.make_doc(text) for text in terms]
        matcher.add(tag_name, patterns) 
        
        for term in terms:
            term_tag_map[term.lower()] = tag_name
    
    MATCHERS[lang] = matcher
    # 顺便将 term_tag_map 存入词典缓存
    DICTIONARIES[lang]["_term_tag_map"] = term_tag_map

    return matcher


def tokenize_and_tag(keyword: str, language: str) -> Dict[str, Any]:
    """
    核心处理函数
    """
    
    # 1. 加载模型和匹配器
    nlp = get_spacy_model(language)
    matcher = get_matcher(language, nlp)

    doc = nlp(keyword)
    matches = matcher(doc)

    # 2. 优先处理匹配到的固定搭配
    raw_spans = []
    for match_id, start, end in matches:
        tag_name = nlp.vocab.strings[match_id] 
        raw_spans.append(Span(doc, start, end, label=tag_name))

    spans = spacy.util.filter_spans(raw_spans)

    final_tokens = []
    tagged_tokens_list = []
    tag_summary: Dict[str, List[str]] = {}
    seen_token_indices = set()

    # 循环1: 处理所有匹配到的固定搭配 (如 "15l" "salomon")
    for span in spans:
        token_text = span.text.lower()
        tag_name = span.label_ 
        
        final_tokens.append(token_text)
        tagged_token = {
            "token": token_text,
            "tags": [tag_name],
            "confidence": 0.99 # 来自词典, 高置信度
        }
        tagged_tokens_list.append(tagged_token)
        
        if tag_name not in tag_summary:
            tag_summary[tag_name] = []
        tag_summary[tag_name].append(token_text)
        
        # 记录已处理的 token 索引
        for i in range(span.start, span.end):
            seen_token_indices.add(i)

    # 循环2: 处理所有剩余的、未被固定搭配占用的 token
    for token in doc:
        if token.i in seen_token_indices or token.is_punct or token.is_space:
            continue
        
        token_text = token.text.lower()
        
        # AI 标注逻辑 
        ai_tag = classify_unknown_token(token_text, keyword)
        
        if ai_tag:
            # AI 成功识别
            final_tokens.append(token_text)
            tagged_token = {
                "token": token_text,
                "tags": [ai_tag], # 使用 AI 的结果
                "confidence": 0.80 # 置信度 0.8 (低于词典的 0.99)
            }
            tagged_tokens_list.append(tagged_token)
            
            # (更新 tag_summary 的逻辑)
            if ai_tag not in tag_summary:
                tag_summary[ai_tag] = []
            tag_summary[ai_tag].append(token_text)
        
        else:
            # AI 失败或返回 'None'
            final_tokens.append(token_text)
            tagged_token = {
                "token": token_text,
                "tags": [],
                "confidence": 0.50 # 仍然未知
            }
            tagged_tokens_list.append(tagged_token)


    # 3. 格式化为最终输出
    response = {
        "original_keyword": keyword,
        "tokens": final_tokens,
        "tagged_tokens": tagged_tokens_list,
        "tag_summary": tag_summary
    }

    return response