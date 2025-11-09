import pandas as pd
import requests
import json
from tqdm import tqdm
import time
import sys

API_URL = "http://127.0.0.1:8000/tokenize-and-tag"
CSV_PATH = "keywords.csv"
OUTPUT_PATH = "batch_results.json"

# 只测试前 100 行。
ROWS_TO_TEST = 100

# 简化的语言映射
LANGUAGE_MAP = {
    "日语": "ja",
    "德语": "de",
    "英语": "en",
    "法语": "fr",
    "西班牙语": "es"
}

def run_batch_test():
    # 1. 检查 API
    try:
        requests.get("http://127.0.0.1:8000/docs", timeout=3)
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到 API。请在另一个终端运行: uvicorn app:app --reload")
        sys.exit(1)
        
    print(f"--- 成功连接到 API。即将开始批量测试... ---")
    
    # 2. 读取 CSV 
    print(f"--- 正在从 {CSV_PATH} 加载关键词... ---")
    try:
        # 优先尝试 'gb18030' (中文 Excel 导出的常见编码)
        df = pd.read_csv(CSV_PATH, encoding="gb18030")
        
    except UnicodeDecodeError:
        # 如果 'gb18030' 失败, 尝试 'utf-8-sig' (BOM)
        print(f"警告: 'gb18030' 解码失败。尝试 'utf-8-sig'...")
        try:
            df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        except Exception as e:
            print(f"错误: 无法读取 {CSV_PATH}。尝试了 'gb18030' 和 'utf-8-sig'。 {e}")
            sys.exit(1)
    except Exception as e:
         print(f"错误: 无法读取 {CSV_PATH}。 {e}")
         sys.exit(1)

    # 3. 截取测试行数
    if len(df) > ROWS_TO_TEST:
        print(f"文件包含 {len(df)} 行，将只测试前 {ROWS_TO_TEST} 行。")
        df_to_test = df.head(ROWS_TO_TEST)
    else:
        df_to_test = df

    all_results = []
    
    print(f"--- 开始批量测试 {len(df_to_test)} 个关键词 ---")
    
    # 4. 循环处理
    for index, row in tqdm(df_to_test.iterrows(), total=df_to_test.shape[0], desc="处理中"):
        term = row.get('search_term')
        lang_name = row.get('language')
        
        # 检查是否成功读取了列名
        if term is None or lang_name is None:
            print(f"\n错误: 无法在 CSV 第 {index} 行中找到 'search_term' 或 'language' 列。")
            print("这可能是因为解码器仍然是错误的，导致表头乱码。")
            print(f"读取到的列: {df.columns.to_list()}")
            break # 停止脚本，因为文件读取显然是错误的

        lang_code = LANGUAGE_MAP.get(lang_name) # 查找语言代码

        if not term or not lang_code:
            tqdm.write(f"跳过第 {index} 行: 缺少 search_term 或 language (值: {lang_name})")
            continue

        payload = {
            "keyword": str(term),
            "language": lang_code
        }

        # 5. 调用 API
        try:
            response = requests.post(API_URL, json=payload, timeout=30) 
            if response.status_code == 200:
                result_data = response.json()
                result_data["language_code"] = lang_code # 把 "ja" 或 "de" 也存进去
                all_results.append(result_data)
            else:
                tqdm.write(f"\n错误 (行 {index}): API 返回 {response.status_code}。关键词: {term}")
        
        except requests.exceptions.Timeout:
            tqdm.write(f"\n错误 (行 {index}): AI 调用超时。关键词: {term}")
        except Exception as e:
            tqdm.write(f"\n错误 (行 {index}): {e}")
        
        time.sleep(0.1) # 保持一个小的限速

    # 6. 保存结果
    try:
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"\n--- 批量测试完成！ ---")
        print(f"成功！{len(all_results)} 条结果已保存到: {OUTPUT_PATH}")
    except Exception as e:
        print(f"\n错误: 无法写入 {OUTPUT_PATH}。 {e}")

if __name__ == "__main__":
    run_batch_test()
