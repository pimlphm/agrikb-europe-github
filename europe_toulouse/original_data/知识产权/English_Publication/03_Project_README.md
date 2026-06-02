# AeroKG — Civil Aircraft Airworthiness Knowledge Graph System

> **An Industrial Ontology-Powered, LLM-Driven Knowledge Graph for Airworthiness Certification**

---

## Overview

AeroKG is an intelligent knowledge graph system purpose-built for civil aircraft airworthiness certification. It transforms unstructured aerospace technical documents into structured, queryable, and reasoned knowledge graphs using a three-layer industrial ontology (BFO/IOF) architecture and multi-role Large Language Model agents.

Designed for integration into the workflows of aircraft design teams at organizations like Airbus, Boeing, COMAC, and their Tier-1 suppliers, AeroKG addresses the full spectrum of airworthiness certification activities — from requirements decomposition and safety assessment to traceability verification and change impact analysis.

### Why AeroKG?

| Challenge | Traditional Approach | AeroKG Solution |
|-----------|---------------------|-----------------|
| Knowledge scattered across 100s of documents | Manual search & reading | Automatic knowledge extraction into unified graph |
| Traceability gaps (Req → Code → Test) | Spreadsheet-based matrices | LLM-powered completeness checking per DO-178C |
| Safety assessment coverage | Manual FHA/PSSA/SSA | Agent-assisted ARP4761 assessment |
| Cross-authority standard lookup | Separate document sets | Integrated FAA/EASA/CAAC database with cross-references |
| Engineering experience lost on staff turnover | Undocumented tribal knowledge | Automatic experience distillation with auditable Markdown files |
| Export control / classification constraints | Cloud-dependent tools | Fully offline, supports domestic Huawei Ascend NPU |

---

## Architecture

```
                    ┌────────────────────────────┐
                    │    PyQt5 Desktop GUI        │
                    │  Dark Aerospace Theme       │
                    │  7 Functional Tabs           │
                    └─────────┬──────────────────┘
                              │
                    ┌─────────┴──────────────────┐
                    │      Agent Engine           │
                    │  6 Specialized LLM Roles    │
                    │  ┌──────────┬──────────┐    │
                    │  │Extractor │ Safety   │    │
                    │  │Reasoner  │ Assessor │    │
                    │  │Organizer │ Tracer   │    │
                    │  │          │ Analyzer │    │
                    │  └──────────┴──────────┘    │
                    └──┬──────────┬──────────┬────┘
                       │          │          │
              ┌────────┴┐   ┌────┴────┐  ┌──┴─────────┐
              │Ontology  │   │Experience│  │Standards   │
              │Engine    │   │Engine    │  │Library     │
              │RDF+NX    │   │Per-prog  │  │FAA/EASA/   │
              │74T/36R/7S│   │Bilingual │  │CAAC (23)   │
              └────────┬─┘   └────┬────┘  └──┬─────────┘
                       │          │           │
              ┌────────┴──────────┴───────────┴────┐
              │        LLM Inference Backend        │
              │  Ollama (x86/ARM) │ vLLM-Ascend     │
              │                   │ (Huawei 910B)   │
              └────────────────────────────────────┘
```

**74T / 36R / 7S** = 74 Entity Types / 36 Relation Types / 7-Level Strength Spectrum

---

## Key Features

### 1. Industrial Ontology (IOF/BFO)

Three-layer knowledge modeling aligned with international standards:

- **BFO Top Layer** (6 types): Entity, Process, Function, Quality, Role, Disposition
- **IOF Core Layer** (18 types): Requirement, Design, Verification, Interface, Constraint, Specification, Component, System, Test, Risk, Standard, Document, Plan, Report, Decision, Metric, Tool, Agent
- **Aviation Domain Layer** (50 types): Aircraft-level through LLR requirements, FHA/FMEA/FTA safety items, Capella/Arcadia architecture layers, DO-178C lifecycle artifacts, change management objects

### 2. Seven-Level Association Strength Spectrum

Every knowledge relationship carries a quantified strength (0–1) mapped to a distinctive color:

```
 Red     Orange   Yellow   Green    Cyan     Blue    Violet
 0.86    0.72     0.58     0.44     0.30     0.16    0.00
  │        │        │        │        │        │        │
  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
  Mandatory ─────────────────────────────── Speculative
```

### 3. Airworthiness Certification Workflows

- **ARP4761 Safety Assessment**: FHA, PSSA, SSA, CCA, DAL allocation
- **DO-178C Traceability**: HLR → LLR → Source Code → Test Cases, MC/DC coverage, derived requirements detection
- **ARP4754A V-Model**: Aircraft → System → Subsystem decomposition and verification
- **Change Impact Analysis**: Upstream, downstream, lateral, safety, and certification dimensions

### 4. Tri-Authority Standards Library

23 core standards with full-text indexing:

| Authority | Standards | Examples |
|-----------|-----------|----------|
| FAA (USA) | 9 | 14 CFR 25, DO-178C, DO-254, ARP4754A, ARP4761, DO-160G, ARINC 653, DO-297, DO-326A |
| EASA (EU) | 8 | CS-25, ED-12C, ED-80, ED-79A, ED-135, ED-14G, ED-124, ED-202A |
| CAAC (China) | 6 | CCAR-25, CTSO-C153, MH/T 0028, AC-25.1309, AC-25-19, AC-21-AA-2018-58 |

Automatic cross-reference table generation. Standards clauses are injected into LLM prompts during analysis.

### 5. Experience Accumulation Engine

- Automatic distillation of permanent and temporary experience from each analysis
- Per-aircraft-program directories (B787, A320neo, C919, A350, B777X...)
- Bilingual Markdown files (Chinese + English) for human audit
- Historical experience injection into future LLM prompts
- Cross-program audit summary reports

### 6. Multi-Format Document Support

PDF, DOCX, XLSX, PPTX, TXT, Markdown, HTML, XML, JSON, YAML, CSV, RST, TeX, ReqIF — 14 formats with automatic encoding detection.

---

## Deployment Options

| Platform | Backend | Hardware | Command |
|----------|---------|----------|---------|
| General Purpose | Ollama | x86_64 / Apple Silicon | `ollama serve && python main.py` |
| Domestication | vLLM-Ascend | Huawei Ascend 910B NPU | `deploy_ascend.sh start && python main.py` |

Both modes operate **fully offline** — no internet connection required.

---

## Demo Documents Included

| Manufacturer | Document | Focus |
|-------------|----------|-------|
| Boeing | B787 ECS Safety Assessment FHA/PSSA | ARP4761 safety workflow |
| Boeing | B787 Electrical Power System Requirements | Requirements decomposition |
| Boeing | B787 Digital Thread Ontology Framework | Knowledge engineering |
| Boeing | B777X FCS MBSE Capella Model | Capella/Arcadia architecture |
| Boeing | B777X Composite Wing Structure Analysis | Structural engineering |
| Airbus | A320neo FBW DO-178C Certification | Software certification |
| Airbus | A320neo Engine Control Software Spec | Software requirements |
| Airbus | A350 EWIS Certification ARP4754A | Wiring systems V-model |
| Airbus | A350 Flight Control System Design | System design |
| Airbus | A350 MBSE Knowledge Engineering | Knowledge modeling |

---

## Intellectual Property

- **Chinese Software Copyright** registered (V4.0, ~6,300 lines of code)
- **Chinese Invention Patent** filed — "An Intelligent Construction and Analysis Method for Civil Aircraft Airworthiness Knowledge Graphs Based on Industrial Ontology and Large Language Models" (10 claims: method + system)

---

## Technology Background

This work builds upon and integrates concepts from:

- **IOF/BFO Ontology Framework** — Industrial Ontologies Foundry & Basic Formal Ontology for standardized industrial knowledge modeling
- **Hedi Karray / UTTOP-Toulouse INP** — Research on industrial ontology applications
- **Dr. Zhengyu Liu** — Technical concepts in aerospace knowledge engineering
- **SAE ARP4754A/ARP4761, RTCA DO-178C/DO-254** — Civil aircraft airworthiness certification standards
- **Capella/Arcadia** — MBSE methodology for systems architecture

---

## Contact

*(Please add your contact information here)*
