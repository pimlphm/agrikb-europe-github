# Data Manifest

This manifest documents both runtime data inside the portable project and original source materials stored beside the project.

## Runtime Data Inside This Project

| Path | Type | Purpose | Notes |
| --- | --- | --- | --- |
| `data/raw/` | Directory | Local uploaded source files | Empty in clean package except `.gitkeep`; do not publish private uploads |
| `data/processed/` | Directory | Intermediate processed artifacts | Empty in clean package except `.gitkeep` |
| `knowledge/chunks.db` | SQLite database | Main document chunk index used by retrieval and dynamic tree APIs | May contain extracted text from source documents |
| `knowledge/chunks/` | Directory | Optional JSON chunk output | Disabled by default for speed |
| `knowledge/wiki/` | Directory | Generated wiki-style summaries per document | May contain document-derived text |
| `knowledge/graph/graph.graphml` | GraphML | Knowledge graph artifact | Safe only if underlying data is publishable |
| `knowledge/agent_memory/gbrain_rules.json` | JSON | Refined rule memory | Derived from document evidence and user queries |
| `knowledge/sessions/` | Directory | Conversation history and session evidence graph | Private by default |

## Original Source Materials

Original IP and project materials are stored outside the portable runtime:

```text
../知识产权/
```

These files should be treated as project source data, not ordinary generated cache.

### Patent and Copyright Documents

| Asset | Purpose |
| --- | --- |
| `发明专利_完整申请文档.md` | Full invention patent application draft in Markdown |
| `发明专利_重构申请文档.docx` | Reconstructed patent application |
| `发明专利_重构申请文档_润色申请版_约5万字.docx` | Polished long application version |
| `发明专利_重构申请文档_知产权综合润色版.docx` | Comprehensive IP-polished version |
| `发明专利_重构申请文档_知产权综合润色版_附图硬件增强版.docx` | Hardware-diagram enhanced version |
| `发明专利_重构申请文档_知产权综合润色版_附图硬件增强版_第四部分详化版.docx` | Detailed fourth-section version |
| `发明专利_重构申请文档_知产权综合润色版_附图硬件增强版_第四部分详化版_技术架构实现增强版_20260511.docx` | Technical-architecture implementation enhanced version |
| `发明专利_重构申请文档_知产权综合润色版_附图硬件增强版_第四部分详化版_技术架构实现增强版_20260511_1比1复现增强版_20260513.docx` | 1:1 reproducibility enhanced patent version |
| `发明专利_重构申请文档_知产权综合润色版_附图硬件增强版_第四部分详化版_技术架构实现增强版_20260511_1比1复现增强版_20260513_权利要求实施例合并版_20260513.docx` | Merged claims and embodiment version |
| `软件著作权_完整申请文档.md` | Complete software copyright application draft |
| `专利文档_附图硬件增强_修改报告.md` | Modification report for patent and hardware figures |

### Patent Subfolders

| Directory | Contents |
| --- | --- |
| `发明专利/` | Request form, claims, specification, drawings description, abstract and disclosure supplements |
| `软件著作权/` | Software copyright form, design specification, user guide and source-code document |
| `专利附图/` | Original patent figure PNG files |
| `专利附图_可编辑导出/` | Exported editable/redrawn figure PNG files |
| `专利附图备份/` | Backup of original patent figures |
| `English_Publication/` | English summary, README, LinkedIn posts, FAQ and architecture HTML |

### Patent Figures

The figure folders include diagrams such as:

```text
图01_系统整体架构图.png
图02_BFO_IOF三层本体架构.png
图03_多因子关联强度计算流程图.png
图04_混合标准条款检索算法.png
图05_六层输出一致性校验流程图.png
图06_知识图谱可视化效果图.png
图07_737_PACK_OFF子图.png
图08_故障树自动生成结果图.png
图09_因果树自动生成结果图.png
图10_跨文档关联网络图.png
图11_检索性能对比柱状图.png
图12_定量评估指标雷达图.png
图13_经验闭环流程图.png
图14_安全审计与权限管理架构图.png
图15_GUI界面效果图.png
```

### Original Data Scripts

The original data folder also contains document-generation and patent-editing scripts:

```text
create_editable_patent_figures.py
deepen_implementation_from_project.py
enhance_patent_hardware_figures.py
generate_docx.py
restructure_patent_implementation.py
rewrite_implementation_four_detailed.py
rewrite_implementation_six_embodiments.py
```

These scripts are documented in `docs/SCRIPTS_REFERENCE.md`.

## Publication Policy

For a private GitHub repository, the original data folder may be added if collaborators are allowed to access the material.

For a public GitHub repository:

- Do not publish `.docx` patent drafts unless cleared.
- Do not publish source documents that include confidential technical details.
- Prefer publishing summaries and redacted examples.
- Keep generated `knowledge/chunks.db` out of public releases unless it was built from publishable demo data.
