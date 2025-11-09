import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# 导入你的核心逻辑
import processor

# --- 1. 定义 API 数据模型 (Pydantic) ---

# API 输入模型
class KeywordRequest(BaseModel):
    keyword: str = Field(..., example="ランニングベスト サロモン 15l")
    language: str = Field(..., example="ja", description="e.g., 'ja', 'de', 'en'")

# 嵌套模型：用于 'tagged_tokens' 列表
class TaggedToken(BaseModel):
    token: str
    tags: List[str]
    confidence: float

# API 输出模型
class KeywordResponse(BaseModel):
    original_keyword: str
    tokens: List[str]
    tagged_tokens: List[TaggedToken]
    tag_summary: Dict[str, List[str]]


# --- 2. 创建 FastAPI 应用 ---
app = FastAPI(
    title="多语言关键词切词与标注 API",
    description="一个用于电商标题的智能切词和标签标注的 Demo",
    version="1.0.0"
)

# --- 3. 定义 API 端点 ---
@app.post("/tokenize-and-tag", response_model=KeywordResponse)
async def api_tokenize_and_tag(request: KeywordRequest):
    """
    接收一个关键词和语言, 返回切词和标签标注结果。
    """
    try:
        # 调用你的核心处理函数
        result = processor.tokenize_and_tag(request.keyword, request.language)
        
        # Pydantic 会自动验证 result 是否符合 KeywordResponse 结构
        return result
        
    except ValueError as ve:
        # 比如传入了不支持的语言
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # 捕获其他意外错误 (实现错误处理机制)
        print(f"发生内部错误: {e}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {e}")


# --- 4. 启动服务器 (用于本地开发) ---
if __name__ == "__main__":
    print("--- 正在启动 FastAPI 服务器 (Uvicorn) ---")
    print("访问 http://127.0.0.1:8000/docs 查看 API 文档")
    # 注意：这里的 'app' 是指上面定义的 app 变量, 而不是字符串
    uvicorn.run(app, host="127.0.0.1", port=8000)