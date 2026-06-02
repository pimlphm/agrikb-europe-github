"""
RLM REPL Engine — 递归语言模型的 Read-Eval-Print Loop 核心
==========================================================
论文核心洞察 (Algorithm 1):
  1. 用户 prompt 不直接塞入 LLM 上下文，而是作为 REPL 环境中的变量
  2. LLM 只接收 prompt 的元数据(长度、前缀摘要)，通过编写代码来操作 prompt
  3. LLM 可以在代码中递归调用自身（sub-RLM），对 prompt 的任意切片进行语义处理
  4. 中间结果存储在 REPL 变量中，不占用根 LLM 的上下文窗口
"""

from __future__ import annotations

import io
import re
import traceback
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from typing import Any, Callable


STDOUT_PREVIEW_LIMIT = 2000
MAX_REPL_ITERATIONS = 15
CODE_FENCE_PATTERN = re.compile(r"```(?:repl|python)\s*\n(.*?)\n```", re.DOTALL)
FINAL_ANSWER_PATTERN = re.compile(r"FINAL\((.+)\)", re.DOTALL)
FINAL_VAR_PATTERN = re.compile(r"FINAL_VAR\((\w+)\)")


@dataclass
class REPLState:
    """REPL 会话的全部持久化状态"""
    variables: dict[str, Any] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    final_answer: str | None = None
    iteration: int = 0
    total_sub_calls: int = 0


class REPLEngine:
    """
    Python REPL 沙箱环境。

    按论文 Algorithm 1 实现:
      - InitREPL: 将 prompt 加载为 context 变量，注入 llm_query 函数
      - 主循环: LLM 生成代码 → REPL 执行 → 截取 stdout 元数据 → 追加到 hist
      - 终止: 当 LLM 输出 FINAL(answer) 或 FINAL_VAR(var_name) 时停止
    """

    def __init__(
        self,
        llm_fn: Callable[[str, str | None], str],
        sub_llm_fn: Callable[[str], str] | None = None,
        max_iterations: int = MAX_REPL_ITERATIONS,
        stdout_limit: int = STDOUT_PREVIEW_LIMIT,
    ) -> None:
        self.llm_fn = llm_fn
        self.sub_llm_fn = sub_llm_fn
        self.max_iterations = max_iterations
        self.stdout_limit = stdout_limit

    def run(self, prompt: str, system_prompt: str | None = None) -> dict:
        """执行 RLM 主循环 (Algorithm 1)"""
        state = REPLState()
        self._init_repl(state, prompt)

        metadata = self._build_prompt_metadata(prompt)
        if system_prompt is None:
            system_prompt = self._default_system_prompt()

        hist_messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": metadata},
        ]

        while state.iteration < self.max_iterations:
            state.iteration += 1

            llm_output = self.llm_fn(
                self._format_messages(hist_messages),
                system_prompt,
            )

            final_match = FINAL_ANSWER_PATTERN.search(llm_output)
            final_var_match = FINAL_VAR_PATTERN.search(llm_output)

            if final_var_match:
                var_name = final_var_match.group(1).strip()
                state.final_answer = str(state.variables.get(var_name, f"[变量 {var_name} 未找到]"))
                state.history.append({
                    "iteration": state.iteration,
                    "type": "final_var",
                    "variable": var_name,
                    "answer": state.final_answer,
                })
                break

            if final_match:
                state.final_answer = final_match.group(1).strip()
                state.history.append({
                    "iteration": state.iteration,
                    "type": "final",
                    "answer": state.final_answer,
                })
                break

            code_blocks = CODE_FENCE_PATTERN.findall(llm_output)
            if code_blocks:
                for code in code_blocks:
                    stdout, error = self._exec_in_repl(state, code)
                    truncated = self._truncate_stdout(stdout)
                    state.history.append({
                        "iteration": state.iteration,
                        "type": "exec",
                        "code_preview": code[:300],
                        "stdout_preview": truncated,
                        "error": error,
                    })

                    turn_summary = f"[REPL 执行结果] stdout长度={len(stdout)}字符"
                    if truncated:
                        turn_summary += f", 前{self.stdout_limit}字符:\n{truncated}"
                    if error:
                        turn_summary += f"\n错误: {error}"

                    hist_messages.append({"role": "assistant", "content": llm_output})
                    hist_messages.append({"role": "user", "content": turn_summary})
            else:
                hist_messages.append({"role": "assistant", "content": llm_output})
                hist_messages.append({
                    "role": "user",
                    "content": "请继续。在 REPL 中编写代码处理 context 变量，或用 FINAL(answer)/FINAL_VAR(var) 给出最终答案。",
                })

        if state.final_answer is None:
            state.final_answer = self._extract_best_effort_answer(state)

        return {
            "answer": state.final_answer,
            "iterations": state.iteration,
            "sub_calls": state.total_sub_calls,
            "history": state.history,
        }

    def _init_repl(self, state: REPLState, prompt: str) -> None:
        """InitREPL: 将 prompt 加载到 REPL 变量中"""
        state.variables["context"] = prompt
        state.variables["context_length"] = len(prompt)

        def llm_query(sub_prompt: str) -> str:
            """在 REPL 中可调用的子 LLM 查询函数"""
            state.total_sub_calls += 1
            if self.sub_llm_fn:
                return self.sub_llm_fn(sub_prompt)
            return self.llm_fn(sub_prompt, None)

        state.variables["llm_query"] = llm_query

    def _exec_in_repl(self, state: REPLState, code: str) -> tuple[str, str | None]:
        """在 REPL 沙箱中执行代码，返回 (stdout, error)"""
        stdout_buf = io.StringIO()
        error = None
        try:
            with redirect_stdout(stdout_buf):
                exec(code, state.variables)  # noqa: S102
        except Exception:
            error = traceback.format_exc()[-500:]
        return stdout_buf.getvalue(), error

    def _build_prompt_metadata(self, prompt: str) -> str:
        """构建 prompt 的元数据描述（不包含原始内容）"""
        char_count = len(prompt)
        line_count = prompt.count("\n") + 1
        preview = prompt[:500] + ("..." if len(prompt) > 500 else "")
        return (
            f"你的任务上下文已加载到 REPL 环境中的 `context` 变量里。\n\n"
            f"上下文元数据:\n"
            f"  - 总字符数: {char_count:,}\n"
            f"  - 总行数: {line_count:,}\n"
            f"  - 前500字符预览:\n{preview}\n\n"
            f"可用工具:\n"
            f"  - `context`: 包含完整上下文的字符串变量\n"
            f"  - `llm_query(prompt)`: 递归调用子 LLM 进行语义分析\n"
            f"  - `print()`: 输出中间结果\n\n"
            f"请编写代码分析 context，使用 llm_query 进行语义处理。"
        )

    def _truncate_stdout(self, stdout: str) -> str:
        if len(stdout) <= self.stdout_limit:
            return stdout
        return stdout[: self.stdout_limit] + f"\n... (共 {len(stdout)} 字符, 已截断)"

    def _format_messages(self, messages: list[dict]) -> str:
        """将消息历史格式化为单一 prompt（适配简单 LLM 接口）"""
        parts = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            parts.append(msg["content"])
        return "\n\n---\n\n".join(parts)

    def _extract_best_effort_answer(self, state: REPLState) -> str:
        """循环结束未给出 FINAL 时，从变量中寻找最佳结果"""
        for name in ("final_answer", "answer", "result", "output", "summary"):
            if name in state.variables and isinstance(state.variables[name], str):
                return state.variables[name]
        last_stdout = ""
        for entry in reversed(state.history):
            if entry.get("stdout_preview"):
                last_stdout = entry["stdout_preview"]
                break
        return last_stdout or "RLM 未能在迭代次数内产生最终答案。"

    @staticmethod
    def _default_system_prompt() -> str:
        return (
            "你是农业知识库的递归语言模型 (RLM) 引擎。你的任务上下文已加载到 REPL 环境变量中，"
            "你需要通过编写 Python 代码来分析、分块和理解这些内容。\n\n"
            "核心能力:\n"
            "1. 通过 `context` 变量访问完整输入（可能非常长）\n"
            "2. 通过 `llm_query(prompt)` 递归调用子 LLM 进行语义分析\n"
            "3. 使用 `print()` 查看中间结果\n"
            "4. 将结果存储在 REPL 变量中（不占用你的上下文窗口）\n\n"
            "推荐策略:\n"
            "- 先查看 context 的结构和长度\n"
            "- 将 context 按逻辑分块（按段落、章节或固定大小）\n"
            "- 对每个分块调用 llm_query 提取关键信息\n"
            "- 将结果汇总后，用 llm_query 生成最终答案\n"
            "- 用 FINAL(答案) 或 FINAL_VAR(变量名) 返回最终结果\n\n"
            "代码用 ```repl 包裹。处理完成后用 FINAL(your answer) 或 FINAL_VAR(var_name) 返回。"
        )
