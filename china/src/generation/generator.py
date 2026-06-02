from __future__ import annotations

import re
import time
import uuid
import os
from typing import Any


class EvidenceGroundedGenerator:
    def __init__(self, provider=None, config: dict | None = None) -> None:
        self.provider = provider
        self.config = config or {}
        answer_cfg = self.config.get("answer", {})
        self.max_evidence = int(answer_cfg.get("max_evidence", 4))
        self.evidence_chars = int(answer_cfg.get("evidence_excerpt_chars", 220))

    def generate(
        self,
        query: str,
        retrieval_results: list[dict],
        use_llm: bool = True,
        conversation_context: str = "",
        model: str | None = None,
        answer_language: str = "auto",
    ) -> dict:
        if self._is_system_overview_query(query):
            evidence_chain = self._system_evidence_chain()
            answer = self.clean_answer_text(self._system_overview_answer(query, evidence_chain))
            claims = self.build_answer_claims(answer, evidence_chain)
            return {
                "answer": answer,
                "citations": [item["doc_name"] for item in evidence_chain],
                "evidence_chain": evidence_chain,
                "evidence": self.evidence_for_api(evidence_chain),
                "answer_claims": claims,
                "evidence_graph": self.build_evidence_graph(query, evidence_chain, answer, claims),
                "model_prompt": self._display_prompt(query, "系统介绍类问题，使用内置产品说明提示。", answer_language),
            }

        evidence_chain = self._build_evidence_chain(retrieval_results)
        citations = list(dict.fromkeys(item["doc_name"] for item in evidence_chain if item.get("doc_name")))

        answer = self._fallback_answer(query, evidence_chain, answer_language=answer_language)
        prompt = ""
        if use_llm and self.provider and evidence_chain:
            try:
                prompt = self._build_prompt(query, evidence_chain, conversation_context=conversation_context, answer_language=answer_language)
                language_instruction = self._language_instruction(query, answer_language)
                system = (
                    "你是新农人助手，服务江苏句容农业生产、政策、市场和经营判断。"
                    f"{language_instruction}"
                    "只依据给定证据回答；先给可执行结论，再给原因和下一步。"
                    "第一行必须是“一句话建议：……”。"
                    "用中文短标题和短句，不要 Markdown 星号，不要暴露证据编号、后台提示或调试信息。"
                    "普通问答总长控制在 450 到 700 个汉字；紧急生产建议可更短。"
                )
                answer = self.provider.generate(prompt, system=system, model=model)
                answer = self._normalize_answer(answer, evidence_chain)
            except Exception as exc:
                strict_backend = str(self.config.get("backend", "")).lower() in {"openai", "openai_compatible", "api_key", "kimi_cli"}
                answer = self._retry_with_compact_prompt(
                    query,
                    evidence_chain,
                    model=model,
                    answer_language=answer_language,
                    original_error=str(exc),
                    raise_on_error=strict_backend,
                )

        answer = self.clean_answer_text(answer)
        answer_claims = self.build_answer_claims(answer, evidence_chain)
        return {
            "answer": answer,
            "citations": citations,
            "evidence_chain": evidence_chain,
            "evidence": self.evidence_for_api(evidence_chain),
            "answer_claims": answer_claims,
            "evidence_graph": self.build_evidence_graph(query, evidence_chain, answer, answer_claims),
            "model_prompt": prompt or self._display_prompt(query, "未调用模型或证据不足，使用规则兜底回答。", answer_language),
        }

    def _retry_with_compact_prompt(
        self,
        query: str,
        evidence_chain: list[dict[str, Any]],
        model: str | None = None,
        answer_language: str = "auto",
        original_error: str = "",
        raise_on_error: bool = False,
    ) -> str:
        if not self.provider or not evidence_chain:
            return self._fallback_answer(query, evidence_chain, answer_language=answer_language)
        compact_chain = []
        for item in evidence_chain[: min(4, len(evidence_chain))]:
            compact_item = dict(item)
            compact_item["excerpt"] = self._excerpt(str(item.get("excerpt") or ""), 120)
            compact_item["supports"] = self._excerpt(str(item.get("supports") or ""), 80)
            compact_chain.append(compact_item)
        try:
            prompt = self._build_prompt(
                query,
                compact_chain,
                conversation_context="",
                answer_language=answer_language,
            )
            system = (
                "你是新农人助手。上一次回答请求过慢，本次只用精简证据回答。"
                "必须给出可执行建议，短标题分段，不要提到超时、重试、压缩或后台错误。"
            )
            answer = self.provider.generate(prompt, system=system, model=model)
            return self._normalize_answer(answer, compact_chain)
        except Exception as exc:
            if raise_on_error:
                raise RuntimeError(f"新农人助手模型调用失败：{original_error}；压缩重试失败：{exc}") from exc
            return self._fallback_answer(query, evidence_chain, answer_language=answer_language, runtime_note=original_error)

    def _is_system_overview_query(self, query: str) -> bool:
        compact = re.sub(r"\s+", "", query.lower())
        competition_terms = ("比赛", "创业大赛", "第一名", "一等奖", "申报", "福地青年英才", "新农人赛道", "数智信息", "双赛道", "融合赛道", "创业计划书")
        if any(term in compact for term in competition_terms):
            return False
        overview_terms = ("农业知识库", "agrikb", "知识库是什么", "解释知识库", "介绍知识库", "系统介绍", "这个系统", "rag系统")
        return any(term in compact for term in overview_terms)

    def _system_evidence_chain(self) -> list[dict[str, Any]]:
        items = [
            (
                "E1",
                "src/backend/app.py",
                "后端提供健康检查、上传、分块上传、取消上传、检索、生成、RLM和知识树接口",
                "FastAPI后端包含/health、/upload、/upload/chunk、/upload/chunk/cancel、/retrieve、/generate、/rlm、/tree等接口。",
            ),
            (
                "E2",
                "src/retrieval/hybrid.py + config.yaml",
                "检索采用BM25与本地向量融合，默认关闭远程embedding以提升大量文档导入速度",
                "HybridRetriever融合稀疏检索和稠密检索；config.yaml中remote_embeddings=false，支持本地快速索引。",
            ),
            (
                "E3",
                "src/generation/generator.py",
                "回答生成被约束为证据链和专业回答两部分，避免直接展示零散原文片段",
                "EvidenceGroundedGenerator先压缩证据链，再要求模型输出证据编号和专业回答。",
            ),
            (
                "E4",
                "web/app.js + web/index.html",
                "前端提供文件上传、语音交互、动态知识树、图谱视图、树状图、冻结、导出和截图",
                "前端控制台包含上传、语音提问/朗读、知识树、Prezi式图谱和可扩展树状图等交互。",
            ),
        ]
        return [
            {
                "id": evidence_id,
                "doc_name": source,
                "chunk_id": source,
                "chunk_type": "system_design",
                "score": 1.0,
                "source": source,
                "entities": [],
                "excerpt": excerpt,
                "supports": supports,
            }
            for evidence_id, source, supports, excerpt in items
        ]

    def _system_overview_answer(self, query: str, evidence_chain: list[dict[str, Any]]) -> str:
        return (
            "AgriKB 农业知识库不是单纯的文件检索器，而是面向农业公共知识、作物管理、公开资料和用户补充文档的证据锚定型知识系统。它先把资料保存到本地，再进行解析、分块、索引和知识树/图谱构建，最终让用户围绕生产经营、认证主体、数据来源和农业活动进行可追溯问答。\n\n"
            "它的核心工作流可以概括为四层：第一层是资料接入与后台摄取，支持批量上传、分块上传、ZIP 解包和取消上传；第二层是检索层，通过 BM25 和本地向量检索快速召回证据；第三层是生成层，把召回结果整理为独立证据链后再生成专业回答；第四层是交互层，通过农业知识树、图谱视图、可扩展树状图、语音讲解、冻结、导出和截图，帮助用户从全局知识结构钻取到具体证据。\n\n"
            "使用这个系统时应重点看两件事：一是回答结论是否能在下方证据链中找到支撑；二是证据来源、许可、版本和地区适用性是否匹配当前问题。对于经营决策、认证合规、病虫害处置或遥感分析结论，系统回答只能作为资料导航和辅助分析依据，最终仍需要结合当地法规、专家判断和实地情况复核。"
        )

    def _build_evidence_chain(self, retrieval_results: list[dict]) -> list[dict[str, Any]]:
        chain = []
        seen = set()
        for item in retrieval_results:
            key = item.get("chunk_id") or (item.get("doc_name"), item.get("text", "")[:80])
            if key in seen:
                continue
            seen.add(key)
            text = self._clean_text(item.get("text", ""))
            if not text:
                continue
            metadata = item.get("metadata", {}) or {}
            chain.append(
                {
                    "id": f"E{len(chain) + 1}",
                    "doc_name": item.get("doc_name") or metadata.get("doc_name") or item.get("source") or "unknown",
                    "chunk_id": item.get("chunk_id", ""),
                    "chunk_type": item.get("chunk_type", "evidence"),
                    "score": round(float(item.get("score", 0.0) or 0.0), 4),
                    "source": item.get("source", ""),
                    "page": item.get("page") or metadata.get("page"),
                    "metadata": metadata,
                    "entities": item.get("entities", [])[:8],
                    "excerpt": self._excerpt(text, self.evidence_chars),
                    "supports": self._support_hint(item),
                    "source_type": item.get("source_type") or metadata.get("source_type") or ("web_search" if item.get("chunk_type") == "web_search" else "document"),
                }
            )
            if len(chain) >= self.max_evidence:
                break
        return chain

    def _build_prompt(
        self,
        query: str,
        evidence_chain: list[dict[str, Any]],
        conversation_context: str = "",
        answer_language: str = "auto",
    ) -> str:
        evidence_lines = []
        fast_mode = str(os.environ.get("AGRIKB_FAST_MODE", "true")).lower() in {"1", "true", "yes", "on"}
        max_items = min(len(evidence_chain), 3 if fast_mode else len(evidence_chain))
        excerpt_limit = 100 if fast_mode else self.evidence_chars
        for item in evidence_chain[:max_items]:
            evidence_lines.append(
                "\n".join(
                    [
                        f"[{item['id']}] {item['doc_name']} / {item['chunk_type']}",
                        f"摘要：{self._excerpt(str(item.get('excerpt') or ''), excerpt_limit)}",
                        f"支持：{self._excerpt(str(item.get('supports') or ''), 70)}",
                    ]
                )
            )
        evidence_text = "\n\n".join(evidence_lines)
        context_text = ""
        if conversation_context.strip():
            context_text = (
                "会话长期上下文和当前对话临时记忆：\n"
                f"{conversation_context.strip()}\n\n"
                "这些上下文只用于理解代词、省略和追问关系；事实结论仍必须优先由下方证据支持。\n\n"
            )
        return (
            "基于证据回答用户问题；除非问题为空，否则不要要求用户重问。\n\n"
            f"{self._language_instruction(query, answer_language)}\n"
            f"{context_text}"
            f"用户问题：{query}\n"
            "任务：把证据中的政策、天气、市场、作物、渠道信息合成可执行建议；能给动作就直接给动作。\n\n"
            f"证据：\n{evidence_text}\n\n"
            f"{self._answer_format_instruction(query, answer_language)}"
        )

    def _language_instruction(self, query: str, answer_language: str = "auto") -> str:
        mode = str(answer_language or "auto").strip().lower()
        if mode in {"zh", "zh-cn", "chinese", "中文"}:
            return "回答语言：使用简体中文。"
        if mode in {"en", "english", "英文"}:
            return "Answer language: English. Keep Chinese place names or policy names when they are proper nouns."
        return (
            "回答语言：自动判断用户上下文。用户主要用中文提问就用简体中文；用户主要用英文提问就用英文；"
            "如果问题中中英文混用，优先使用用户最后一句主要语言。"
        )

    def _prefers_english(self, query: str, answer_language: str = "auto") -> bool:
        mode = str(answer_language or "auto").strip().lower()
        if mode in {"en", "english", "英文"}:
            return True
        if mode in {"zh", "zh-cn", "chinese", "中文"}:
            return False
        text = str(query or "")
        cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
        latin_words = len(re.findall(r"\b[A-Za-z][A-Za-z-]{2,}\b", text))
        return latin_words >= 5 and latin_words > cjk

    def _answer_format_instruction(self, query: str, answer_language: str = "auto") -> str:
        if self._prefers_english(query, answer_language):
            return (
                "Output only the answer body, not the evidence list.\n"
                "The first line must be: One-sentence recommendation: ... Keep it concise and action-oriented.\n"
                "Then use short plain headings without Markdown symbols:\n"
                "Do first\n"
                "1. The first action.\n"
                "2. The person, goods, place, or timing to confirm.\n"
                "Why this judgment\n"
                "Explain policy, market, weather, or knowledge-base reasons in 1 to 2 short paragraphs.\n"
                "Market and channels\n"
                "Explain sales, procurement, ecommerce, logistics, or enterprise matching; state gaps when evidence is missing.\n"
                "Risk reminder\n"
                "Explain weather, price, compliance, quality, or data freshness risks.\n"
                "Next step\n"
                "Give 1 to 3 actions to click, query, upload, or verify next.\n"
                "Do not include [E1], source id, evidence id, chunk id, filenames, scores, debug words, or Markdown bold markers.\n"
            )
        return (
            "只输出专业回答正文，不要输出证据链列表。\n"
            "第一行写：一句话建议：……，不超过45个汉字，直接说明今天先做什么。\n"
            "随后按需使用这些短标题，标题独占一行，不加 Markdown 符号：\n"
            "今日先做\n"
            "为什么这样判断\n"
            "市场与渠道\n"
            "风险提醒\n"
            "下一步\n"
            "每段不超过90个汉字，每组清单2到3条。"
            "不要出现 [E1]、source id、文件名、score、Primary evidence、retrieval_results 或 **粗体**。"
            "证据不足时先说能判断的部分，再说明缺口；不要编造。"
        )

    def _display_prompt(self, query: str, note: str, answer_language: str = "auto") -> str:
        return "\n".join([
            self._language_instruction(query, answer_language),
            f"用户问题：{query}",
            f"提示说明：{note}",
        ])

    def _fallback_answer(self, query: str, evidence_chain: list[dict[str, Any]], answer_language: str = "auto", runtime_note: str = "") -> str:
        if self._prefers_english(query, answer_language):
            if not evidence_chain:
                return (
                    "One-sentence recommendation: Add local policy, price, weather, or procurement evidence before making the decision.\n\n"
                    "Do first\n"
                    "1. Upload or search the latest local agricultural material related to the crop, market, policy, or weather risk.\n"
                    "2. Then ask the question again with the production place, target market, crop name, and expected sales time.\n\n"
                    "Risk reminder\n"
                    "The current knowledge base did not retrieve enough evidence, so it should not produce a firm business, compliance, plant-protection, or logistics decision yet."
                )
            evidence_brief = self._fallback_evidence_brief(evidence_chain, english=True)
            return (
                "One-sentence recommendation: Make a small evidence-based move first, then verify local policy, weather, and procurement terms.\n\n"
                "Do first\n"
                "1. Identify the crop, sales window, target buyer, and delivery place before committing volume.\n"
                "2. Use the retrieved evidence to check whether policy, market, logistics, or weather conditions fit the current location.\n\n"
                "Why this judgment\n"
                f"{evidence_brief}\n\n"
                "Market and channels\n"
                "Start with a small batch, confirm price, grading, packaging, settlement date, and cold-chain or ordinary delivery requirements with the buyer.\n\n"
                "Next step\n"
                "Refresh live search or upload the latest local notice, quotation, contract, or field record if the decision needs formal execution."
            )
        if not evidence_chain:
            return (
                "一句话建议：先补充本地政策、行情、天气或收购资料，再让系统给经营判断。\n\n"
                "当前农业知识库没有召回足够证据，因此不能给出确定性结论。建议先上传或重新摄取相关作物资料、本体词表、开放数据、认证资料或项目文档后再查询。"
            )

        evidence_brief = self._fallback_evidence_brief(evidence_chain)
        topic = self._fallback_topic(query)
        return (
            f"一句话建议：先围绕{topic}小批量试行，再核对本地政策、天气和收购口径。\n\n"
            "今日先做\n"
            f"1. 把“{topic}”对应的作物、数量、上市时间、目标市场和联系人先确认清楚。\n"
            "2. 若涉及销售，先问清分级、包装、结算和运输要求，再决定是否放量。\n"
            "3. 若涉及补贴或申报，先核对主体资格、材料清单、窗口部门和截止时间。\n\n"
            "为什么这样判断\n"
            f"{evidence_brief}\n\n"
            "市场与渠道\n"
            "先走小批量询价和试单，不要一次性把成熟货全部压到单一渠道。"
            "能对接合作社、批发市场、电商助农或企业收购时，要同时比较到手价、回款速度和损耗风险。\n\n"
            "风险提醒\n"
            "当前结论来自知识库召回和实时聚合材料，仍要核对最新政策原文、当天气象、实际品质和采购方口径。"
            "病虫害、防灾减灾、农资使用和合同条款需要现场专业人员复核。\n\n"
            "下一步\n"
            "1. 点开右侧政策、行情、天气或收购信息继续核验。\n"
            "2. 上传最新通知、报价单、合同或田间记录后再追问一次。\n"
            "3. 需要正式执行时，保留截图、来源链接和沟通记录。"
        )

    def _fallback_topic(self, query: str) -> str:
        text = re.sub(r"^(请|帮我|给我|分析|解释|说明|解读|一下)+", "", str(query or "").strip())
        text = re.split(r"[，,。；;：:\n]", text, 1)[0].strip()
        if 2 <= len(text) <= 16:
            return text
        keywords = [item for item in self._extract_keywords(text or query) if item not in {"请", "分析", "解释"}]
        return keywords[0] if keywords else "当前问题"

    def _fallback_evidence_brief(self, evidence_chain: list[dict[str, Any]], english: bool = False) -> str:
        snippets = []
        for item in evidence_chain[:3]:
            support = str(item.get("supports") or "").strip()
            excerpt = str(item.get("excerpt") or "").strip()
            doc_name = str(item.get("doc_name") or "").strip()
            text = support or excerpt
            text = self._excerpt(text, 110 if not english else 150)
            if text:
                snippets.append((doc_name, text))
        if not snippets:
            return "系统已经召回到相关资料，但有效摘要较少，需要继续补充本地材料。" if not english else "The system retrieved related material, but the useful excerpts are limited."
        if english:
            return "Retrieved evidence points to: " + "; ".join(text for _, text in snippets) + "."
        return "系统已召回到相关资料，主要指向：" + "；".join(text for _, text in snippets) + "。"

    def _normalize_answer(self, answer: str, evidence_chain: list[dict[str, Any]]) -> str:
        text = self._clean_text(answer).replace("Primary evidence:", "").replace("Query:", "")
        return self.clean_answer_text(text)

    def clean_answer_text(self, answer: str) -> str:
        text = self._clean_text(answer)
        answer_match = re.search(r"###\s*专业回答\s*(.*)$", text, flags=re.S)
        if answer_match:
            text = answer_match.group(1).strip()
        text = re.sub(r"###\s*证据链[\s\S]*?(?=###\s*专业回答|$)", "", text).strip()
        text = re.sub(r"\s*\[(?:E|e)\d+\]", "", text)
        text = re.sub(r"\s*【(?:E|e)\d+】", "", text)
        text = re.sub(r"\s*\((?:E|e)\d+\)", "", text)
        text = re.sub(r"\s*evidence\s*[:#]?\s*\d+", "", text, flags=re.I)
        text = re.sub(r"\s*source\s*id\s*[:：]?\s*\S+", "", text, flags=re.I)
        text = re.sub(r"\s*chunk\s*id\s*[:：]?\s*\S+", "", text, flags=re.I)
        text = re.sub(r"score\s*[:：]?\s*\d+(?:\.\d+)?", "", text, flags=re.I)
        text = self._enforce_chinese_answer_layout(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    def _enforce_chinese_answer_layout(self, text: str) -> str:
        value = str(text or "").replace("**", "").strip()
        headings = (
            "今日先做",
            "今日建议",
            "为什么这样判断",
            "市场与渠道",
            "市场渠道",
            "销售渠道",
            "政策机会",
            "政策与产业扶持",
            "天气风险",
            "气象环境提醒",
            "风险提醒",
            "数据依据与缺口",
            "台湾数据依据与缺口",
            "下一步",
            "下一步动作",
        )
        heading_pattern = "|".join(re.escape(item) for item in headings)
        value = re.sub(rf"\s*({heading_pattern})\s*[:：]\s*", r"\n\1\n", value)
        value = re.sub(rf"(?<!^)(?<!\n)({heading_pattern})\s*(?=\n|\d+[.、]|[-*]\s+)", r"\n\1\n", value)
        value = re.sub(rf"(?<=[。！？；;])\s*({heading_pattern})\s+(?=\S)", r"\n\n\1\n", value)
        value = re.sub(r"(?<!\n)(\d{1,2}[.、]\s+)", r"\n\1", value)
        value = re.sub(r"(?<!\n)([-*]\s+)", r"\n\1", value)
        blocks: list[str] = []
        for block in re.split(r"\n{2,}", value):
            lines: list[str] = []
            for raw_line in block.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if re.fullmatch(rf"(?:{heading_pattern})", line):
                    if lines and lines[-1] != "":
                        lines.append("")
                    lines.append(line)
                    lines.append("")
                    continue
                lines.extend(self._split_long_chinese_line(line))
            cleaned = "\n".join(part for part in lines).strip()
            if cleaned:
                blocks.append(cleaned)
        return "\n\n".join(blocks)

    @staticmethod
    def _split_long_chinese_line(line: str, limit: int = 96) -> list[str]:
        if len(line) <= limit or re.match(r"^(\d{1,2}[.、]|[-*])\s+", line):
            return [line]
        sentences = [part for part in re.split(r"(?<=[。！？；;])", line) if part]
        if len(sentences) <= 1:
            return [line]
        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            if current and len(current) + len(sentence) > limit:
                chunks.append(current.strip())
                current = sentence
            else:
                current += sentence
        if current.strip():
            chunks.append(current.strip())
        return chunks or [line]

    def evidence_for_api(self, evidence_chain: list[dict[str, Any]]) -> list[dict[str, Any]]:
        payload = []
        for item in evidence_chain:
            metadata = item.get("metadata", {}) or {}
            payload.append(
                {
                    "evidence_id": item.get("id", ""),
                    "doc_name": item.get("doc_name", ""),
                    "chunk_id": item.get("chunk_id", ""),
                    "page": item.get("page") or metadata.get("page"),
                    "score": item.get("score", 0.0),
                    "evidence_type": item.get("chunk_type", "text"),
                    "snippet": item.get("excerpt", ""),
                    "entities": item.get("entities", []),
                    "source_path": item.get("source", ""),
                    "metadata": metadata,
                    "supports": item.get("supports", ""),
                    "source_type": "model_prior" if item.get("chunk_type") == "system_design" else "document",
                }
            )
        return payload

    def build_answer_claims(self, answer: str, evidence_chain: list[dict[str, Any]]) -> list[dict[str, Any]]:
        clean = self.clean_answer_text(answer)
        sentences = [
            item.strip()
            for item in re.split(r"(?<=[。！？.!?；;])\s*|\n+", clean)
            if item and item.strip()
        ]
        if not sentences and clean:
            sentences = [clean]

        claims: list[dict[str, Any]] = []
        for sentence in sentences[:8]:
            matches = self._match_claim_to_evidence(sentence, evidence_chain)
            matched_source_types = {
                str(item.get("source_type") or "document")
                for item in evidence_chain
                if item.get("id") in matches
            }
            matched_by_documents = matches and matched_source_types <= {"document"}
            if len(matches) >= 2 and matched_by_documents:
                source_type = "inferred"
                confidence = min(0.88, 0.62 + len(matches) * 0.08)
                warning = None
            elif len(matches) == 1 and matched_by_documents:
                source_type = "document"
                confidence = 0.76
                warning = None
            elif matches:
                source_type = "model_prior"
                confidence = 0.48
                warning = "非文档证据：来源不是当前知识库文档 chunk"
            else:
                source_type = "unsupported" if self._looks_unsupported(sentence) else "model_prior"
                confidence = 0.25 if source_type == "unsupported" else 0.42
                warning = (
                    "未在当前知识库证据中找到可靠支撑"
                    if source_type == "unsupported"
                    else "非文档证据：来自模型内置知识或通用推理"
                )
            claims.append(
                {
                    "id": f"claim_{uuid.uuid4().hex[:10]}",
                    "text": sentence,
                    "source_type": source_type,
                    "supporting_evidence_ids": matches,
                    "confidence": round(confidence, 3),
                    "warning": warning,
                    "provenance": {
                        "source_type": source_type,
                        "source_id": ",".join(matches) if matches else source_type,
                        "confidence": round(confidence, 3),
                        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    },
                }
            )
        if not claims:
            claims.append(
                {
                    "id": f"claim_{uuid.uuid4().hex[:10]}",
                    "text": "当前没有生成可拆分的回答结论。",
                    "source_type": "unsupported",
                    "supporting_evidence_ids": [],
                    "confidence": 0.0,
                    "warning": "没有可验证的回答结论",
                    "provenance": {
                        "source_type": "unsupported",
                        "source_id": "unsupported",
                        "confidence": 0.0,
                        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    },
                }
            )
        return claims

    def build_evidence_graph(
        self,
        query: str,
        evidence_chain: list[dict[str, Any]],
        answer: str,
        claims: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        claims = claims or self.build_answer_claims(answer, evidence_chain)
        nodes: list[dict[str, Any]] = [
            {"id": "q", "type": "query", "label": "用户问题", "detail": query, "source_type": "query"},
        ]
        edges: list[dict[str, str]] = []
        entity_ids: dict[str, str] = {}
        fallback_entities = self._extract_keywords(query)
        for entity in fallback_entities[:3]:
            ent_id = f"ent_{len(entity_ids) + 1}"
            entity_ids[entity] = ent_id
            nodes.append({"id": ent_id, "type": "entity", "label": entity, "detail": "来自问题关键词", "source_type": "entity"})
            edges.append({"source": "q", "target": ent_id, "type": "mentions"})

        for index, item in enumerate(evidence_chain, start=1):
            ev_id = f"ev_{index}"
            item_source_type = item.get("source_type") or "document"
            doc_id = str((item.get("metadata") or {}).get("doc_id") or item.get("doc_name") or "")
            doc_node_id = f"doc_{index}"
            nodes.append(
                {
                    "id": doc_node_id,
                    "type": "document",
                    "label": item.get("doc_name", "document"),
                    "detail": item.get("source", ""),
                    "source_type": item_source_type,
                    "doc_id": doc_id,
                    "file_name": item.get("doc_name", ""),
                }
            )
            evidence_entities = [str(value) for value in item.get("entities", [])[:3] if str(value).strip()]
            if not evidence_entities:
                evidence_entities = fallback_entities[:1]
            for entity in evidence_entities[:3]:
                if entity not in entity_ids:
                    ent_id = f"ent_{len(entity_ids) + 1}"
                    entity_ids[entity] = ent_id
                    nodes.append({"id": ent_id, "type": "entity", "label": entity[:48], "detail": "来自证据实体", "source_type": "entity"})
                    edges.append({"source": "q", "target": ent_id, "type": "mentions"})
            nodes.append(
                {
                    "id": ev_id,
                    "type": "retrieved_chunk",
                    "label": item.get("doc_name") or item.get("chunk_id") or item.get("id", f"E{index}"),
                    "detail": item.get("excerpt", ""),
                    "evidence_id": item.get("id", f"E{index}"),
                    "doc_name": item.get("doc_name", ""),
                    "file_name": item.get("doc_name", ""),
                    "doc_id": doc_id,
                    "chunk_id": item.get("chunk_id", ""),
                    "title": item.get("chunk_type", ""),
                    "section": (item.get("metadata") or {}).get("section") or item.get("chunk_type", ""),
                    "page": item.get("page") or (item.get("metadata") or {}).get("page"),
                    "raw_text": item.get("excerpt", ""),
                    "score": item.get("score", 0.0),
                    "source_type": item_source_type,
                    "entities": evidence_entities,
                    "snippet": item.get("excerpt", ""),
                    "supports": item.get("supports", ""),
                    "provenance": self._evidence_provenance(item),
                }
            )
            edges.append({"source": doc_node_id, "target": ev_id, "type": "contains"})
            linked = False
            for entity in evidence_entities[:3]:
                ent_id = entity_ids.get(entity)
                if ent_id:
                    edges.append({"source": ent_id, "target": ev_id, "type": "retrieves"})
                    linked = True
            if not linked:
                edges.append({"source": "q", "target": ev_id, "type": "retrieves"})

        claim_nodes = []
        for index, claim in enumerate(claims, start=1):
            claim_id = claim.get("id") or f"claim_{index}"
            claim_nodes.append(claim_id)
            nodes.append(
                {
                    "id": claim_id,
                    "type": "answer_claim",
                    "label": f"Claim {index}",
                    "detail": claim.get("text", ""),
                    "text": claim.get("text", ""),
                    "source_type": claim.get("source_type", "unsupported"),
                    "confidence": claim.get("confidence", 0.0),
                    "warning": claim.get("warning"),
                    "supporting_evidence_ids": claim.get("supporting_evidence_ids", []),
                    "provenance": claim.get("provenance", {}),
                }
            )
            matched = claim.get("supporting_evidence_ids", [])
            for evidence_id in matched:
                ev_index = self._evidence_index(evidence_id)
                if ev_index:
                    edges.append({"source": f"ev_{ev_index}", "target": claim_id, "type": "supports"})
            if not matched:
                prior_id = f"{claim_id}_prior"
                nodes.append(
                    {
                        "id": prior_id,
                        "type": claim.get("source_type", "model_prior"),
                        "label": "非文档证据" if claim.get("source_type") == "model_prior" else "未支撑",
                        "detail": claim.get("warning") or "此结论未找到文档证据。",
                        "source_type": claim.get("source_type", "model_prior"),
                    }
                )
                edges.append({"source": prior_id, "target": claim_id, "type": "qualifies"})
            edges.append({"source": "q", "target": claim_id, "type": "answers"})
        return {"nodes": nodes, "edges": edges}

    def _match_claim_to_evidence(self, claim: str, evidence_chain: list[dict[str, Any]]) -> list[str]:
        claim_tokens = self._token_set(claim)
        matched: list[str] = []
        for item in evidence_chain:
            evidence_text = f"{item.get('excerpt', '')} {item.get('supports', '')} {' '.join(item.get('entities', []))}"
            evidence_tokens = self._token_set(evidence_text)
            if not claim_tokens or not evidence_tokens:
                continue
            overlap = len(claim_tokens & evidence_tokens) / max(1, min(len(claim_tokens), len(evidence_tokens)))
            entity_hit = any(str(entity).lower() in claim.lower() for entity in item.get("entities", []))
            if overlap >= 0.16 or entity_hit:
                matched.append(item.get("id", ""))
        return [item for item in matched if item][:4]

    def _evidence_index(self, evidence_id: str) -> int | None:
        match = re.search(r"(\d+)$", str(evidence_id or ""))
        return int(match.group(1)) if match else None

    def _looks_unsupported(self, sentence: str) -> bool:
        text = sentence.lower()
        markers = ("证据不足", "没有召回", "无法确认", "不能给出", "unsupported", "insufficient")
        return any(marker in text for marker in markers)

    def _evidence_provenance(self, item: dict[str, Any]) -> dict[str, Any]:
        metadata = item.get("metadata", {}) or {}
        source_type = item.get("source_type") or "document"
        return {
            "source_type": source_type,
            "source_id": item.get("chunk_id") or item.get("id") or "",
            "doc_id": metadata.get("doc_id") or item.get("doc_name") or "",
            "chunk_id": item.get("chunk_id", ""),
            "file_name": item.get("doc_name", ""),
            "page": item.get("page") or metadata.get("page"),
            "url": None,
            "model": None,
            "retrieval_score": item.get("score", 0.0),
            "confidence": item.get("score", 0.0),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    def _token_set(self, text: str) -> set[str]:
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9][A-Za-z0-9_/-]{1,}", str(text or "").lower())
        stop = {"当前", "建议", "回答", "证据", "可以", "the", "and", "with", "that", "this"}
        return {token for token in tokens if token not in stop}

    def _extract_keywords(self, text: str) -> list[str]:
        candidates = re.findall(r"[\u4e00-\u9fffA-Za-z0-9][\u4e00-\u9fffA-Za-z0-9_/-]{1,24}", text or "")
        stop = {"请", "解释", "一下", "什么", "如何", "the", "and", "with", "about"}
        seen = set()
        keywords = []
        for candidate in candidates:
            if candidate.lower() in stop or candidate in seen:
                continue
            seen.add(candidate)
            keywords.append(candidate)
            if len(keywords) >= 5:
                break
        return keywords or ["问题关键词"]

    def _support_hint(self, item: dict) -> str:
        chunk_type = item.get("chunk_type", "evidence")
        entities = item.get("entities") or []
        if entities:
            return f"涉及{chunk_type}信息，关联实体包括{self._join_short(entities[:4])}"
        return f"提供{chunk_type}类证据，可用于支撑回答中的事实依据"

    def _excerpt(self, text: str, limit: int) -> str:
        cleaned = self._clean_text(text)
        if len(cleaned) <= limit:
            return cleaned
        sentence_end = max(cleaned.rfind("。", 0, limit), cleaned.rfind("；", 0, limit), cleaned.rfind(".", 0, limit))
        if sentence_end > limit * 0.45:
            return cleaned[: sentence_end + 1]
        return cleaned[:limit].rstrip() + "..."

    def _clean_text(self, value: str) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        return text.replace("{{SSISTANT", "").replace("ASSISTANT", "").strip()

    def _join_short(self, values: list[Any]) -> str:
        return "、".join(str(value)[:32] for value in values if value)
