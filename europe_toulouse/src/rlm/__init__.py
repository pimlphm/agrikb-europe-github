"""
Recursive Language Model (RLM) 模块
===================================
基于论文 "Recursive Language Models" (Zhang, Kraska, Khattab, 2026) 的核心思想:
将用户输入的超长文本视为外部环境变量，而非直接填充 LLM 上下文窗口；
通过 REPL 编程环境让 LLM 以符号化方式递归地分解、查看和调用自身，
实现对任意长度输入的高质量处理。

核心组件:
  - REPLEngine: Python REPL 沙箱，管理变量和代码执行
  - RecursiveRetrievalEngine: 将 RLM 范式融入农业知识库的递归检索引擎
  - RLMRetrievalResult: RLM 检索结果数据结构
"""

from src.rlm.repl_engine import REPLEngine, REPLState
from src.rlm.recursive_retrieval import RecursiveRetrievalEngine, RLMRetrievalResult

__all__ = ["REPLEngine", "REPLState", "RecursiveRetrievalEngine", "RLMRetrievalResult"]
