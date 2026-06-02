# Elevator Pitch & FAQ

> Quick reference for networking, conferences, and LinkedIn conversations.

---

## 30-Second Elevator Pitch

"I built an AI system that automatically reads aerospace technical documents and constructs an intelligent knowledge graph — think of it as a brain that understands how requirements, safety hazards, design decisions, and test cases are all connected. It uses industrial ontology standards and large language models to do what used to take senior engineers weeks in hours. It covers FAA, EASA, and Chinese CAAC standards, runs fully offline for classified environments, and actually gets smarter with every analysis because it accumulates engineering experience. I've filed a Chinese invention patent with 10 claims for the method."

---

## 60-Second Technical Pitch

"AeroKG is a knowledge graph system for civil aircraft airworthiness certification. It's built on a three-layer industrial ontology — BFO at the top for universal concepts, IOF in the middle for engineering primitives, and a custom aviation layer with 74 entity types aligned to ARP4754A, DO-178C, and ARP4761.

What makes it unique is the seven-color strength spectrum — every relationship in the graph is quantified from 0 to 1 and visualized as Red through Violet, so engineers can instantly see critical safety paths versus speculative connections. Six specialized LLM agents handle everything from knowledge extraction to safety assessment to change impact analysis.

The system integrates 23 standards from FAA, EASA, and CAAC with automatic cross-referencing and prompt injection. It also has an experience accumulation engine that distills lessons from every analysis, organizes them by aircraft program, and feeds them back into future analyses.

Fully offline, supports Huawei Ascend NPU for domestic deployment, and I've filed a 10-claim invention patent covering both the method and the system architecture."

---

## Frequently Asked Questions

### Q: How is this different from DOORS or Polarion?

**A:** DOORS and Polarion are requirements management tools — they store and link requirements, but they don't *understand* the content. AeroKG reads the actual documents, extracts knowledge entities and relationships using LLM agents, quantifies association strength, and can perform automated safety assessments and traceability checks. Think of DOORS as a structured database; AeroKG is an intelligent analyst that builds and reasons over a knowledge graph.

### Q: Why not use a general-purpose knowledge graph tool like Neo4j?

**A:** General-purpose graph databases don't have domain-specific ontology. AeroKG's 74 entity types and 36 relation types are specifically designed for airworthiness certification — they distinguish between "FHA Items" and "Fault Trees," between "satisfies" and "failure_leads_to" relationships. The seven-level strength spectrum is also unique to this system. You could use Neo4j as a backend, but you'd still need everything AeroKG provides on top.

### Q: What LLM does it use?

**A:** It's model-agnostic. The system supports any model available through Ollama (Qwen, Llama, Mistral, etc.) or vLLM-Ascend for Huawei NPU deployment. Models can be switched at runtime from the GUI. The intelligence comes from the domain-specific system prompts and ontology rules, not from any particular model.

### Q: Can it work without an LLM (offline with no GPU)?

**A:** The knowledge graph engine, standards library, experience browser, and visualization all work without an LLM. LLM inference is needed for automatic knowledge extraction, safety assessment, and experience distillation. For CPU-only environments, smaller quantized models (e.g., Qwen2.5-1.5B) work reasonably well through Ollama.

### Q: Is this open source?

**A:** The system has a registered software copyright and a filed invention patent. Current status is proprietary. Open to licensing discussions and research collaborations.

### Q: Which standards does it cover?

**A:** 23 core standards across three authorities:
- **FAA (9):** 14 CFR 25, DO-178C, DO-254, ARP4754A, ARP4761, DO-160G, ARINC 653, DO-297, DO-326A
- **EASA (8):** CS-25, ED-12C, ED-80, ED-79A, ED-135, ED-14G, ED-124, ED-202A
- **CAAC (6):** CCAR-25, CTSO-C153, MH/T 0028, AC-25.1309, AC-25-19, AC-21-AA-2018-58

With automatic cross-reference tables (e.g., DO-178C ↔ ED-12C ↔ CTSO-C153).

### Q: What's the Huawei Ascend support about?

**A:** For Chinese aerospace organizations that need domestically-produced AI hardware (avoiding reliance on NVIDIA GPUs due to export controls), AeroKG supports deployment on Huawei Ascend 910B NPUs via the vLLM-Ascend Docker framework. This provides an OpenAI-compatible API backed by domestic AI chips.

### Q: How does the experience engine work?

**A:** After each document analysis or safety assessment, the LLM automatically distills reusable lessons into structured experience entries. These are:
1. Categorized as permanent (high-confidence, reviewed) or temporary (initial, pending review)
2. Organized by aircraft program (B787, A320neo, C919...)
3. Stored as Markdown files in Chinese and English for human audit
4. Automatically loaded and injected into future LLM prompts as reference context
5. Tracked by usage count for relevance ranking

### Q: What programming languages/frameworks are used?

**A:** Pure Python 3.10+. Key libraries:
- **GUI:** PyQt5 with custom dark aerospace CSS theme
- **Knowledge Graph:** RDFLib (semantic web / RDF triples) + NetworkX (graph algorithms)
- **LLM:** HTTP clients for Ollama REST API and OpenAI-compatible API
- **Documents:** PyPDF2, python-docx, openpyxl, python-pptx, BeautifulSoup
- **Visualization:** vis-network.js (JavaScript, embedded in HTML output)

### Q: Can it handle languages other than English/Chinese?

**A:** The ontology types, relation types, and standards are defined in both Chinese and English. The LLM-based extraction works in whatever language the underlying model supports. The GUI is currently in Chinese, but the architecture supports localization.

### Q: What's next?

**A:** Exploring:
- Integration with Capella/Arcadia for direct MBSE model import
- DOORS Next Generation API connector for bi-directional requirement sync
- Expanding the standards library to include DO-278A (ground-based software), AS9100 (quality management), and ISO 26262 (automotive safety) for cross-domain applications
- Multi-user collaborative mode for large program teams

---

## Key Numbers (for posts and conversations)

| Metric | Value |
|--------|-------|
| Entity types | 74 |
| Relation types | 36 |
| Strength spectrum levels | 7 (ROYGCBV) |
| LLM agent roles | 6 |
| Airworthiness standards | 23 |
| Airworthiness authorities | 3 (FAA/EASA/CAAC) |
| Document formats supported | 14 |
| Patent claims | 10 (method + system) |
| Source code | ~6,300 lines Python |
| GUI tabs | 7 |
| Demo documents | 10 (Boeing + Airbus) |
