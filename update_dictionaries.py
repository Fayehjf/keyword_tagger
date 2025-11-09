import json
from pathlib import Path
from collections import defaultdict

# 这个映射和 processor.py 中的TAG_MAPPING 变量【完全相反】
REVERSE_TAG_MAPPING = {
    "品牌词": "brands",
    "商品词": "products",
    "人群词": "people",
    "场景词": "scene",
    "颜色词": "colors",
    "尺寸词": "sizes",
    "卖点词": "selling_points",
    "属性词": "attributes",
}

# AI 标注的置信度 (来自 processor.py)
AI_CONFIDENCE_SCORE = 0.80

INPUT_FILE = "batch_results.json"
DICTIONARY_DIR = Path("dictionaries")

def update_dictionaries():
    print(f"--- 正在从 {INPUT_FILE} 加载 AI 标注结果... ---")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            results = json.load(f)
    except FileNotFoundError:
        print(f"错误: 找不到 {INPUT_FILE}。")
        print("请先运行 'python3 run_batch.py' 来生成该文件。")
        return
    except json.JSONDecodeError:
        print(f"错误: {INPUT_FILE} 文件内容不是有效的 JSON。")
        return

    # 1. 收集所有 AI 发现的新词
    words_to_add = defaultdict(set)
    ai_token_count = 0

    for item in results:
        lang_code = item.get("language_code")
        if not lang_code:
            print(f"警告: 跳过一个条目，缺少 'language_code' 字段。")
            continue
            
        for token in item.get("tagged_tokens", []):
            # 检查这个词是否由 AI 标注
            if token.get("confidence") == AI_CONFIDENCE_SCORE:
                ai_token_count += 1
                token_text = token.get("token")
                tag_name = token.get("tags", [])[0]
                
                # 转换回文件名 e.g., "brands"
                tag_key = REVERSE_TAG_MAPPING.get(tag_name)
                
                if token_text and tag_key:
                    # 构造文件名 e.g., "ja_brands"
                    dict_key = f"{lang_code}_{tag_key}"
                    words_to_add[dict_key].add(token_text)

    if ai_token_count == 0:
        print("--- 在结果中没有找到 AI 标注的词 (confidence == 0.80)。 ---")
        print("--- 请确保你的 API 密钥已设置并且 AI 标注已开启。 ---")
        return

    print(f"--- AI 共标注了 {ai_token_count} 个词。准备更新词典文件... ---")

    # 2. 将新词写入对应的 .txt 文件
    updated_files = 0
    total_new_words = 0

    for dict_key, new_terms_set in words_to_add.items():
        file_path = DICTIONARY_DIR / f"{dict_key}.txt"
        
        # 加载已有的词，防止重复添加
        existing_terms = set()
        if file_path.exists():
            try:
                with file_path.open('r', encoding='utf-8') as f:
                    existing_terms = {line.strip().lower() for line in f if line.strip()}
            except Exception as e:
                print(f"警告: 无法读取现有的 {file_path}。 {e}")
                
        # 找出真正需要添加的新词
        truly_new_words = new_terms_set - existing_terms
        
        if not truly_new_words:
            continue

        # 以“追加”模式 ('a') 写入新词
        try:
            with file_path.open('a', encoding='utf-8') as f:
                for term in sorted(list(truly_new_words)):
                    f.write(f"\n{term}") # 在文件末尾追加
            
            print(f"成功: 向 {file_path.name} 添加了 {len(truly_new_words)} 个新词。")
            updated_files += 1
            total_new_words += len(truly_new_words)
            
        except Exception as e:
            print(f"错误: 无法写入 {file_path}。 {e}")

    print("\n--- 词典更新完成！ ---")
    print(f"总共 {updated_files} 个文件被更新，添加了 {total_new_words} 个新词条。")
    print("请重启 `uvicorn` API 服务器来加载新词典。")

if __name__ == "__main__":
    update_dictionaries()