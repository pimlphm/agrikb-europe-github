"""
RLM 递归检索引擎 — 将 RLM 范式融入农业知识库 RAG 管线
=====================================================
设计理念 (来自论文的三个核心 design choices):

1. Prompt-as-Environment: 将所有检索到的证据块拼接为一个超长字符串，
   作为 REPL 变量加载，而非直接塞入 LLM 上下文窗口。

2. Symbolic Recursion: LLM 通过编写代码调用 llm_query() 对证据的任意
   切片进行语义分析，支持循环、分支、聚合等复杂操作。

3. Variable-based Output: 最终答案通过 REPL 变量返回，支持远超上下文
   窗口限制的输出长度。

在农业知识库场景中的特殊适配:
  - 子 LLM 调用自动注入农业本体、作物性状和开放数据上下文
  - 支持对多文档证据的跨文档推理 (如术语对齐、数据源追溯、地区资料对比)
  - 保留完整的推理轨迹用于审计
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from src.rlm.repl_engine import REPLEngine


@dataclass
class RLMRetrievalResult:
    """RLM 递归检索的完整返回结构"""
    query: str
    answer: str
    citations: list[str]
    evidence_chunks: list[dict]
    rlm_trace: dict
    total_iterations: int
    total_sub_calls: int
    elapsed_seconds: float
    mode: str = "rlm"

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "answer": self.answer,
            "citations": self.citations,
            "evidence_chunks": [
                {k: v for k, v in chunk.items() if not k.startswith("_")}
                for chunk in self.evidence_chunks
            ],
            "rlm_trace": self.rlm_trace,
            "total_iterations": self.total_iterations,
            "total_sub_calls": self.total_sub_calls,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "mode": self.mode,
        }


class RecursiveRetrievalEngine:
    """
    将 RLM 范式与农业知识库 RAG 管线融合的递归检索引擎。

    工作流程:
      1. 接收查询 → 混合检索 → 获取 top-N 证据块
      2. 将所有证据块序列化为结构化文本（context 变量）
      3. 启动 REPL 引擎，LLM 通过代码分析证据
      4. 子 LLM 调用自动注入农业领域 system prompt
      5. 收集最终答案、引用和审计轨迹
    """

    def __init__(self, service: Any, config: dict | None = None) -> None:
        self.service = service
        self.config = config or {}
        rlm_cfg = self.config.get("rlm", {})
        self.max_iterations = rlm_cfg.get("max_iterations", 10)
        self.max_sub_calls = rlm_cfg.get("max_sub_calls", 30)
        self.evidence_top_k = rlm_cfg.get("evidence_top_k", 20)
        self.chunk_chars_per_sub_call = rlm_cfg.get("chunk_chars_per_sub_call", 3000)
        self.enabled = bool(
            self.config.get("feature_flags", {}).get("ENABLE_RLM", False)
        )

    def run(self, query: str, top_k: int | None = None) -> RLMRetrievalResult:
        """执行 RLM 递归检索"""
        t0 = time.time()
        top_k = top_k or self.evidence_top_k

        retrieval = self.service.retrieve(query, top_k=top_k)
        evidence_chunks = retrieval.get("retrieval_results", [])

        context_str = self._serialize_evidence(query, evidence_chunks)

        llm_fn = self._make_root_llm_fn()
        sub_llm_fn = self._make_sub_llm_fn(query)

        stdout_limit = self.config.get("rlm", {}).get("stdout_preview_limit", 2000)
        repl = REPLEngine(
            llm_fn=llm_fn,
            sub_llm_fn=sub_llm_fn,
            max_iterations=self.max_iterations,
            stdout_limit=stdout_limit,
        )

        system_prompt = self._build_rlm_system_prompt(query, evidence_chunks)
        rlm_result = repl.run(context_str, system_prompt=system_prompt)

        citations = self._extract_citations(rlm_result["answer"], evidence_chunks)
        elapsed = time.time() - t0

        return RLMRetrievalResult(
            query=query,
            answer=rlm_result["answer"],
            citations=citations,
            evidence_chunks=evidence_chunks,
            rlm_trace={
                "history": rlm_result["history"],
                "iterations": rlm_result["iterations"],
                "sub_calls": rlm_result["sub_calls"],
            },
            total_iterations=rlm_result["iterations"],
            total_sub_calls=rlm_result["sub_calls"],
            elapsed_seconds=elapsed,
        )

    def _serialize_evidence(self, query: str, chunks: list[dict]) -> str:
        """将检索到的证据块序列化为 REPL 可操作的结构化文本"""
        parts = [f"# 查询: {query}\n# 检索到 {len(chunks)} 个证据块\n"]
        for i, chunk in enumerate(chunks):
            doc_name = chunk.get("doc_name", chunk.get("source", "unknown"))
            chunk_type = chunk.get("chunk_type", "evidence")
            entities = ", ".join(chunk.get("entities", [])[:5])
            score = chunk.get("score", 0.0)
            text = chunk.get("text", "")

            parts.append(
                f"\n--- 证据块 {i} ---\n"
                f"来源: {doc_name}\n"
                f"类型: {chunk_type}\n"
                f"实体: {entities}\n"
                f"分数: {score}\n"
                f"内容:\n{text}\n"
            )
        return "\n".join(parts)

    def _make_root_llm_fn(self):
        """创建根 LLM 调用函数"""
        provider = self.service.provider

        def root_llm(prompt: str, system: str | None = None) -> str:
            return provider.generate(prompt, system=system)

        return root_llm

    def _make_sub_llm_fn(self, original_query: str):
        """
        创建子 LLM 调用函数。

        论文关键设计: 子 LLM 是普通的 LLM 调用（不再递归），
        但自动注入领域上下文以提升农业知识库场景的质量。
        """
        provider = self.service.provider

        sub_system = (
            "你是农业知识库的子分析引擎。你的任务是精确回答关于作物管理、"
            "农业开放数据、认证资料、遥感农业目录和术语互操作的问题。请基于提供的证据给出准确、简洁的回答，"
            "并在回答中引用来源文档名（用方括号标注）。\n"
            f"原始查询上下文: {original_query[:200]}"
        )

        def sub_llm(prompt: str) -> str:
            return provider.generate(prompt, system=sub_system)

        return sub_llm

    def _build_rlm_system_prompt(self, query: str, chunks: list[dict]) -> str:
        """构建 RLM 专用的系统提示"""
        doc_names = list(dict.fromkeys(
            chunk.get("doc_name", chunk.get("source", ""))
            for chunk in chunks
            if chunk.get("doc_name") or chunk.get("source")
        ))
        doc_summary = ", ".join(doc_names[:10])

        return (
            "你是农业知识库的递归语言模型 (RLM) 引擎，专精于作物管理、农业开放数据、农业场景资料和证据追溯推理。\n\n"
            f"当前查询: {query}\n"
            f"证据来源文档: {doc_summary}\n"
            f"证据块总数: {len(chunks)}\n\n"
            "你的任务上下文（所有检索到的证据）已加载到 REPL 的 `context` 变量中。\n\n"
            "操作指南:\n"
            "1. 先用代码查看 context 结构（如行数、文档分布），了解证据全貌\n"
            "2. 如果证据不多（<5个块），直接将全部证据传给 llm_query 分析\n"
            "3. 如果证据较多，按来源文档分组，对每组调用 llm_query 提取关键信息\n"
            "4. 将各组分析结果存入变量，最后汇总生成包含引用的最终答案\n"
            "5. 在最终答案中用 [文档名] 格式标注引用来源\n\n"
            "代码编写规范:\n"
            "- 代码用 ```repl ... ``` 包裹\n"
            "- 用 print() 输出中间结果\n"
            "- 用 llm_query(prompt) 调用子 LLM 进行语义分析\n"
            "- 将重要中间结果存入变量（如 findings, summary）\n\n"
            "完成后必须用 FINAL(你的答案) 或 FINAL_VAR(变量名) 返回最终结果。\n"
            "最终答案必须包含引用来源。"
        )

    def _extract_citations(self, answer: str, chunks: list[dict]) -> list[str]:
        """从答案文本中提取引用的文档名"""
        all_doc_names = set()
        for chunk in chunks:
            name = chunk.get("doc_name", chunk.get("source", ""))
            if name:
                all_doc_names.add(name)

        cited = []
        for name in all_doc_names:
            if name in answer:
                cited.append(name)

        if not cited and all_doc_names:
            cited = list(all_doc_names)[:3]
        return cited
