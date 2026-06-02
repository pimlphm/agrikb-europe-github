# Software Copyright — Technical Summary

## Software Name

**Industrial Ontology-Based Civil Aircraft Airworthiness Knowledge Graph Intelligent Analysis System**

**Version:** V4.0

**Completion Date:** April 2026

---

## Software Description

This software is an intelligent knowledge graph analysis system designed for the civil aircraft airworthiness certification domain. Built on the IOF/BFO (Industrial Ontologies Foundry / Basic Formal Ontology) three-layer industrial ontology framework, it integrates Large Language Model (LLM) inference capabilities to provide aircraft design teams — such as those at Airbus and Boeing — with a comprehensive toolset spanning requirements analysis, safety assessment, certification traceability, and experience management.

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| GUI Framework | PyQt5 (Dark aerospace theme) |
| Knowledge Graph | RDFLib (Semantic Web) + NetworkX (Graph algorithms) |
| LLM Backend | Ollama (local) / vLLM-Ascend (Huawei Ascend 910B NPU) |
| Document Parsing | PyPDF2, python-docx, openpyxl, python-pptx, BeautifulSoup |
| Visualization | vis-network.js (Force-directed / hierarchical layouts) |
| Standards Database | JSON + Markdown (23 standards across FAA/EASA/CAAC) |

### Core Modules

| Module | Lines of Code | Description |
|--------|--------------|-------------|
| `ontology_engine.py` | ~1,200 | Three-layer ontology management, 74 entity types, 36 relation types, 7-level strength spectrum, graph analysis (clustering, bridging, missing link prediction) |
| `llm_agent.py` | ~830 | Dual-backend LLM client (Ollama + vLLM-Ascend), 6 specialized agent roles, document analysis, safety assessment, traceability checking, change impact analysis |
| `experience_engine.py` | ~600 | Experience extraction, per-program storage, bilingual Markdown generation, human review workflow, audit reporting |
| `standards_library.py` | ~550 | FAA/EASA/CAAC standards database, keyword search, cross-reference lookup, LLM context injection |
| `main_window.py` | ~2,200 | PyQt5 GUI with 7 functional tabs, dark aerospace theme, runtime model switching, interactive knowledge graph |
| `graph_visualizer.py` | ~400 | Interactive HTML knowledge graph generation with vis-network.js |
| `doc_parser.py` | ~300 | 14-format document parser (PDF, DOCX, XLSX, PPTX, MD, HTML, XML, JSON, YAML, CSV, RST, TEX, TXT, ReqIF) |
| `archiver.py` | ~200 | File system monitoring and automatic document classification/archival |
| **Total** | **~6,300** | |

### Key Features

1. **IOF/BFO Three-Layer Ontology** — 74 entity types and 36 relation types aligned with ARP4754A, DO-178C, ARP4761, and Capella/Arcadia standards

2. **Seven-Level Association Strength Spectrum** — Red-Orange-Yellow-Green-Cyan-Blue-Violet color coding quantifies knowledge association closeness from 0 to 1

3. **Six Specialized Agent Roles** — Universal Extractor, Ontology Reasoner, Safety Assessor, V-Model Tracer, Impact Analyzer, Document Organizer

4. **Tri-Authority Standards Library** — 23 core airworthiness standards from FAA (9), EASA (8), and CAAC (6) with full cross-reference tables

5. **Experience Closed-Loop** — Automatic experience distillation, per-aircraft-program management (B787/A320neo/C919...), bilingual Markdown audit files, historical experience injection into future analyses

6. **Dual LLM Backend** — Ollama for general-purpose deployment, vLLM-Ascend for Huawei Ascend 910B NPU domestication deployment

7. **Fully Offline Operation** — No internet connection required, suitable for military/aerospace classified environments

---

## Intellectual Property Protection

This software has been registered for Computer Software Copyright Protection in China under the *Regulations on the Protection of Computer Software* and the *Administrative Measures for Computer Software Copyright Registration*. The registration covers the complete source code and documentation of all modules listed above.

### Open-Source Components

The software utilizes the following open-source libraries under their respective licenses, which do not affect the independent copyright of the proprietary code:

- PyQt5 (GPL v3)
- NetworkX (BSD 3-Clause)
- RDFLib (BSD 3-Clause)
- vis-network.js (Apache 2.0 / MIT)
- PyPDF2, python-docx, openpyxl, python-pptx (various permissive licenses)
