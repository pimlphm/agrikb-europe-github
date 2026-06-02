# Invention Patent — Technical Summary

## Title

**An Intelligent Construction and Analysis Method for Civil Aircraft Airworthiness Knowledge Graphs Based on Industrial Ontology and Large Language Models**

---

## Abstract

This invention discloses an intelligent knowledge graph construction and analysis method for civil aircraft airworthiness certification, combining industrial ontology frameworks with large language model (LLM) technology. The method establishes a three-layer ontology architecture based on BFO (Basic Formal Ontology) at the top layer, IOF (Industrial Ontologies Foundry) at the core layer, and an aviation-specific domain layer, defining 74 entity types and 36 relation types. A seven-level association strength spectrum — Red, Orange, Yellow, Green, Cyan, Blue, Violet (ROYGCBV) — quantifies the closeness of knowledge associations on a continuous 0-to-1 scale. Six specialized LLM agent roles (knowledge extractor, ontology reasoner, safety assessor, V-model tracer, change impact analyzer, and document organizer) automatically extract structured knowledge from multi-format technical documents and construct the knowledge graph. The system integrates the complete standards ecosystem of three major airworthiness authorities — CAAC (China), FAA (USA), and EASA (EU) — and features an experience accumulation engine that forms a closed loop of "analyze → distill → accumulate → inject." The system supports fully offline operation on both general-purpose hardware (via Ollama) and domestically-produced Huawei Ascend 910B NPUs (via vLLM-Ascend).

**Keywords:** Industrial Ontology; Knowledge Graph; Large Language Model; Airworthiness Certification; Safety Assessment; Association Strength Spectrum; Experience Accumulation

---

## Technical Problem

Traditional requirements management and safety assessment methods in civil aviation rely heavily on tools like DOORS/Polarion and manual analysis. They suffer from:

1. **Knowledge Silos** — Cross-document knowledge associations are difficult to discover and visualize automatically
2. **Traceability Gaps** — Requirement-to-code-to-test trace chains are easily broken, especially for derived requirements
3. **Experience Loss** — Engineering analysis experience is lost when personnel transfer or retire
4. **Standards Fragmentation** — Chinese, American, and European airworthiness standards are managed separately with no automated cross-referencing
5. **Incomplete Safety Coverage** — Manual FHA/PSSA/SSA analyses cannot guarantee exhaustive coverage of all functional failure conditions

---

## Core Innovations

### Innovation 1: Three-Layer Industrial Ontology for Airworthiness

A novel fusion of the international IOF/BFO framework with civil aircraft airworthiness standards (ARP4754A / DO-178C / ARP4761), creating 74 domain-specific entity types across five sub-domains:

| Sub-Domain | Example Types | Aligned Standard |
|------------|---------------|------------------|
| Requirements Hierarchy | Aircraft Req, System Req, HLR, LLR, Derived Req | ARP4754A V-Model |
| Safety Assessment | FHA Item, Fault Tree, DAL Assignment, Safety Objective | ARP4761 |
| MBSE Architecture | Operational Analysis, Logical Architecture, Physical Architecture | Capella/Arcadia |
| Verification & Certification | Test Procedure, PSAC, SAS, SOI Review, Compliance Matrix | DO-178C |
| Change Management | Change Request, Problem Report | Configuration Mgmt |

### Innovation 2: Seven-Level Association Strength Spectrum

A first-of-its-kind visual and analytical quantification of knowledge association strength:

| Spectrum | Strength Range | Semantic | Visual |
|----------|---------------|----------|--------|
| Red (赤) | 0.86–1.00 | Mandatory dependency / Direct causation | #FF0000 |
| Orange (橙) | 0.72–0.85 | Strong association / Constraint propagation | #FF6600 |
| Yellow (黄) | 0.58–0.71 | Medium-strong association | #FFCC00 |
| Green (绿) | 0.44–0.57 | Medium association | #33CC33 |
| Cyan (青) | 0.30–0.43 | Weak / Reference | #00CCCC |
| Blue (蓝) | 0.16–0.29 | Indirect association | #3366FF |
| Violet (紫) | 0.00–0.15 | Potential / Speculative | #9933FF |

### Innovation 3: Standards-Injected Knowledge Extraction

During LLM-based extraction, the system automatically retrieves relevant clauses from a 23-standard database (FAA/EASA/CAAC) and injects them into the prompt context, transforming passive standards consultation into active standards fusion.

### Innovation 4: Experience Closed-Loop Accumulation

```
Document Analysis → LLM Distills Experience → Store by Aircraft Program
        ↑                                              │
        │          Human Review (Approve/Reject)        │
        │                    │                          │
        └──── Inject Historical Experience ←────────────┘
```

Experience is categorized as permanent (reviewed) or temporary (pending), managed per aircraft program (B787, A320neo, C919...), stored as auditable Chinese/English Markdown files, and automatically injected into future analysis prompts.

### Innovation 5: Multi-Role LLM Agent Collaboration

Six specialized agents, each with domain-specific system prompts embedding ontology rules and airworthiness standard requirements:

| Agent Role | Primary Function | Key Standard |
|------------|-----------------|--------------|
| Universal Extractor | Structured knowledge extraction from documents | IOF/BFO Types |
| Ontology Reasoner | Deep reasoning on knowledge graph structure | — |
| Safety Assessor | FHA, PSSA, SSA, CCA, DAL assignment | ARP4761 |
| V-Model Tracer | HLR→LLR→Code→Test traceability checking | DO-178C |
| Impact Analyzer | 5-dimension change impact assessment | — |
| Document Organizer | Automatic document classification and archival | — |

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│         Presentation Layer (PyQt5 GUI)               │
│  Dark aerospace theme · 7 tabs · Force-directed graph│
├─────────────────────────────────────────────────────┤
│         Business Logic Layer (AgentEngine)            │
│  6 Agent Roles · Airworthiness Workflows · Standards  │
├─────────────────────────────────────────────────────┤
│         Knowledge Layer                              │
│  OntologyEngine (RDF + NetworkX)                     │
│  ExperienceEngine (per-program, bilingual .md)       │
│  StandardsLibrary (FAA/EASA/CAAC, 23 standards)     │
├─────────────────────────────────────────────────────┤
│         Infrastructure Layer                         │
│  Ollama (local) │ vLLM-Ascend (Huawei Ascend 910B)  │
│  DocParser (14 formats) │ File I/O                   │
└─────────────────────────────────────────────────────┘
```

---

## Claims Overview

| Claim # | Type | Scope |
|---------|------|-------|
| 1 | Independent (Method) | Complete S1–S6 workflow |
| 2 | Dependent | 74 entity types in 3-layer ontology |
| 3 | Dependent | Seven-level spectrum definition |
| 4 | Dependent | Six agent roles and their functions |
| 5 | Dependent | Tri-authority standards database |
| 6 | Dependent | Experience closed-loop mechanism |
| 7 | Dependent | Graph analysis (missing links, clusters, bridges) |
| 8 | Independent (System) | Six functional modules |
| 9 | Dependent | Dual LLM backend architecture |
| 10 | Dependent | Knowledge graph visualization |

---

## Application Scenarios

1. **Airbus/Boeing Design Teams** — Rapid knowledge framework construction for new programs leveraging historical experience
2. **Airworthiness Certification Reviews** — Automated FHA/DAL allocation, traceability matrices, completeness checks
3. **Change Review Boards** — Five-dimensional change impact analysis to support decision-making
4. **Cross-Regional Certification** — CAAC/FAA/EASA tri-authority standard cross-referencing for bilateral airworthiness projects
5. **Knowledge Preservation** — Systematic retention of engineering analysis experience beyond personnel changes
