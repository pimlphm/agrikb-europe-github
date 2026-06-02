from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement


IP = Path(__file__).resolve().parent
SRC = IP / "发明专利_重构申请文档_知产权综合润色版_附图硬件增强版_第四部分详化版.docx"
OUT = IP / "发明专利_重构申请文档_知产权综合润色版_附图硬件增强版_第四部分深度实施版.docx"
REPORT = IP / "专利文档_附图硬件增强_修改报告.md"


def find_para(doc: Document, prefix: str) -> int:
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip().startswith(prefix):
            return i
    raise RuntimeError(prefix)


def add_after(anchor, text: str):
    new_p = OxmlElement("w:p")
    anchor._p.addnext(new_p)
    p = anchor._parent.add_paragraph()
    p._p = new_p
    r = p.add_run(text)
    r.font.name = "宋体"
    r.font.size = Pt(10.5)
    return p


INSERTIONS = {
    "[0034] DeviceProfile对象至少包括": [
        "[0034A] 设备探测可按以下伪流程执行：首先调用系统级设备查询接口获得CPU核心数、系统内存和操作系统信息；其次尝试调用GPU、NPU、DCU或MLU对应的命令行工具或运行时接口获得设备列表；再次对每个设备执行最小张量分配、矩阵乘或空推理健康检查；最后根据检查结果生成DeviceProfile数组。若某设备能被枚举但不能完成最小张量分配，则不参与生成任务，只可作为候选低优先级设备。该伪流程可表示为：detect_cpu()→detect_accelerators()→probe_runtime()→probe_memory()→build_device_profile()→select_backend()。",
        "[0034B] 后端选择可按模型角色分配。embedding角色优先选择延迟较低且支持批量向量化的设备；rerank角色优先选择单次小批量推理延迟较低的设备；generation角色优先选择可用显存或片上内存较大且支持流式输出的设备；summary角色可与generation角色共用后端。若generation角色无法加载，系统不终止服务，而是保留检索、证据包和保守模板回答能力。"
    ],
    "[0038] EvidenceRecord保存": [
        "[0038A] 对象写入顺序为：DocumentRecord先写入文档注册表；PageRecord和BlockRecord写入解析缓存；ChunkRecord写入chunk目录和SQLite表；EntityRecord和RelationRecord写入图谱存储；EvidenceRecord引用ChunkRecord和标准条款；QueryRecord引用EvidenceBundle；AuditRecord贯穿上述各步骤。任一对象写入失败时，系统回滚当前批次中依赖该对象的下游对象，但不删除已成功注册的原始DocumentRecord，以便后续重新解析。",
        "[0038B] chunk目录中的每个chunk以chunk_id命名保存为JSON文件，SQLite表至少包含chunk_id、doc_name、source、chunk_type、text、entities_json、conditions_json、relations_json和metadata_json字段。这样既可按文件方式人工检查单个chunk，也可按数据库方式进行检索、统计和批量重建索引。"
    ],
    "[0042] PDF解析步骤包括": [
        "[0042A] 对于PDF解析，系统可先采用文本层解析器提取可复制文本；若文本层为空或乱码比例超过阈值，则标记为OCR候选页；若表格提取失败但页面中存在明显竖线或横线结构，则保留页面级文本并将table_meta标记为table_unstructured；若同一页同时出现正文和表格，系统将正文块和表格块分开写入BlockRecord，避免表格列名与正文句子混合造成关系误判。",
        "[0042B] 页眉页脚清理采用重复行检测：若某一短文本行在多个相邻页面的相同位置重复出现，且不包含故障码、标准编号或章节标题，则判定为页眉或页脚并在clean_text中删除；若重复行包含文档版本号、标准编号或机型信息，则保留为metadata字段而不进入正文chunk。"
    ],
    "[0043] 语义分块步骤包括": [
        "[0043A] 分块参数可采用min_chunk_tokens、max_chunk_tokens和semantic_boundary_threshold控制。若当前块tokens小于min_chunk_tokens且下一个块chunk_type相同，则合并；若当前块tokens超过max_chunk_tokens，则按句子边界拆分；若相邻句子的词汇重叠率低于semantic_boundary_threshold且后一句触发故障、原因、规则或动作类型，则建立新的语义块。该处理使故障现象、原因、规则和维修动作不会被混在同一chunk中。",
        "[0043B] 句子切分可同时识别中文句号、分号、问号、感叹号、换行和编号列表。对于维修步骤列表，系统保留步骤序号并写入metadata.step_no；对于表格行，系统保留row_index、column_names和cell_values；对于培训规范中的考核要求，系统保留training_subject和assessment_item字段。"
    ],
    "[0044] chunk_type的判定规则为": [
        "[0044A] 在一种实现中，系统维护TRIGGER_MAP：symptom对应“现象、症状、异常、告警、alarm”等触发词；cause对应“原因、导致、because、failure due to”等触发词；rule对应“如果、当、criteria、判据”等触发词；action对应“建议、检查、replace、inspect、mitigate”等触发词；evidence对应“案例、记录、test、log”等触发词。若一段文本同时命中多个触发类型，系统将最靠近句首或标题的触发类型作为主类型，其余类型写入secondary_types。",
        "[0044B] chunk_type不是最终实体类型，而是后续抽取的上下文提示。例如action类型chunk中仍可出现component或standard_clause实体；symptom类型chunk中仍可出现maintenance_action候选词。实体类型最终由本体约束和上下文共同决定。"
    ],
    "[0047] 关系抽取流程为": [
        "[0047A] 关系触发词表可包括：导致、引起、造成、由于、检查、确认、排除、更换、复位、记录、签署、放行、训练、考核、引用、符合、要求。系统按触发词左右窗口寻找候选头尾实体；若触发词为“导致、引起、造成”，左侧实体优先作为原因，右侧实体优先作为结果；若触发词为“检查、更换、复位”，故障或部件实体优先作为对象，动作词优先作为maintenance_action；若触发词为“引用、符合、要求”，标准条款或规范实体优先作为尾实体。",
        "[0047B] 关联强度计算时，S_type来自关系类别基础权重，S_evidence来自同文档、同章节、同页、同句距离，S_standard来自是否存在直接标准支持，S_graph来自共同邻居和路径距离，S_llm来自模型或规则置信度。默认可采用S=0.25S_type+0.20S_evidence+0.20S_standard+0.20S_graph+0.15S_llm。若强度低于正式阈值但高于候选阈值，则写入候选池；若低于候选阈值，则仅保留在抽取日志中。"
    ],
    "[0048] 标准条款检索采用稀疏检索": [
        "[0048A] 混合检索器构建时分别建立BM25稀疏索引和稠密向量索引。查询时，BM25路径返回sparse_score，稠密路径返回dense_score；系统分别用各自最大值归一化后计算score=sparse_weight·normalized_sparse+dense_weight·normalized_dense。若重排器启用，先取rerank_top_n个候选，再按关键词重叠、文档多样性、长度惩罚和实体类型匹配得到rerank_score，最后截取top_k个结果。",
        "[0048B] 当稠密向量模型不可用时，DenseRetriever可进入fallback模式，以确定性伪向量或词项相似度生成dense_score，保证混合检索接口仍然返回同样结构的结果；当BM25索引为空时，系统只使用稠密路径并将sparse_score置零；当两路均不可用时，查询进入retrieval_unavailable状态并提示重建索引。"
    ],
    "[0051] 六层校验按固定顺序执行": [
        "[0051A] 六层校验输出ValidationReport对象，字段包括object_id、object_type、schema_ok、ontology_ok、standard_ok、span_ok、conflict_ok、confidence_ok、failed_rules、suggested_action和review_required。只有全部布尔字段均为真，且review_required为假时，对象才可从candidate状态提升为official状态；否则保留候选状态并显示失败规则。",
        "[0051B] 人工复核动作包括confirm、reject、merge、split、edit_type、add_standard_ref和add_evidence_span。每次复核均写入AuditRecord，并生成review_revision。若工程人员修改了实体类型或关系方向，系统自动重新执行本体一致性校验和标准引用校验。"
    ],
    "[0056] 对《737典型故障说明R1": [
        "[0056A] 对737故障说明PDF，系统可先按故障主题建立索引表FaultIndex，字段包括fault_id、fault_name、ata_chapter、start_page、end_page、keywords和related_mel。解析时若发现标题包含PACK、BLEED、OIL、FLIGHT CONTROL、TAKEOFF CONFIG等词，系统创建对应FaultIndex记录。后续问答或图谱构建可先定位fault_id，再读取对应页段，减少跨主题误检索。",
        "[0056B] 对每个FaultIndex，系统按“故障现象、可能原因、检查步骤、处置措施、预防提示、相关MEL或记录要求”六类Facet组织文本。若PDF原文未显式给出某类Facet，该类Facet为空，不由模型补造；若某段同时包含检查和处置，系统拆成requires_check和maintenance_action两个FacetPoint。"
    ],
    "[0061] 对《M2-航空器维修": [
        "[0061A] 对M2维修文件，系统可建立MaintenanceRuleIndex，字段包括rule_id、rule_type、chapter、keywords、applicable_fault_types、required_record和human_factor_tags。rule_type可取record、release、tool_control、human_factor、integrity、handover、work_card等。该索引用于把故障案例中的维修动作连接到维修记录、交接复核和人为因素要求。",
        "[0061B] 当故障案例中的维修动作包含“检查、更换、复位、测试、放行、记录”等词时，系统用maintenance_action作为查询，从MaintenanceRuleIndex召回相关规则；若召回规则包含required_record，则在证据包中增加维修记录提示；若召回规则包含human_factor_tags，则在培训提示中增加人为因素复核项。"
    ],
    "[0062] 对《航空器维修基础知识": [
        "[0062A] 对培训规范PDF，系统可建立TrainingRequirementIndex，字段包括training_id、subject、operation_skill、assessment_method、safety_note、related_fault_topics和evidence_span。对于MEL查阅、工卡执行、工具使用、故障隔离、维修记录等训练项目，系统将其与对应故障主题建立training_supports关系。",
        "[0062B] 培训要求不直接改变故障因果关系。系统仅在答案、报告和图谱侧栏中使用training_tip节点提示培训或复盘要点；除非培训规范同时引用具体维修标准或故障处置要求，否则不把training_tip节点作为caused_by或failure_leads_to关系的端点。"
    ],
    "[0068] 基线混合检索路径包括": [
        "[0068A] QueryRouter的路由判定可采用复杂度标记和特征开关共同决定。若查询长度超过预设阈值，或包含“原因、对比、影响、跨文档、全部证据、综合分析”等复杂标记，则complexity设为complex；若ENABLE_RLM开启且命中“全部证据、综合分析、跨文档”等关键词，则路由到rlm；若ENABLE_AGENTIC开启且complexity为complex而未触发rlm，则路由到agentic；否则路由到baseline。",
        "[0068B] baseline路径必须在一次检索中返回足够证据；agentic路径允许多轮改写查询和补证据，但每一步都必须引用上一步的检索结果；rlm路径允许在受控变量空间内对证据分组、过滤和汇总，但只能调用预设检索函数，不得访问任意系统文件或网络。"
    ],
    "[0074] 模型加载策略由ModelPlan对象描述": [
        "[0074A] ModelPlan生成时先计算模型所需内存估计值，再与DeviceProfile.memory_free比较。若memory_free大于估计值和安全余量之和，则允许加载；若不足但设备支持量化，则尝试低比特量化版本；若仍不足，则降低max_model_len或切换fallback_model。加载完成后系统执行一次短提示健康检查，验证模型能返回非空内容并可写入token统计。",
        "[0074B] 嵌入、重排序和生成模型可独立加载。实际部署中，可将embedding和rerank放在CPU/GPU或小显存设备上，将generation放在国产计算卡上；也可在国产计算卡不可用时，将generation切换到本地轻量模型，仍保留证据检索和审计链路。"
    ],
    "[0076] 动态batch的组织规则为": [
        "[0076A] 调度器维护waiting_queue、prefill_queue、decode_batch和finished_queue四个队列。新请求先进入waiting_queue；当检索证据包准备完成后进入prefill_queue；预填充完成后进入decode_batch；生成结束或异常终止后进入finished_queue。调度器每个时间片读取设备剩余内存、活跃请求数和KV页使用率，决定是否接收新请求进入decode_batch。",
        "[0076B] 若decode_batch中某请求提前结束，系统立即释放其非共享KV页，并将共享prefix页的ref_count减一；若ref_count降为零且last_access_time超过缓存保留时间，则该页进入可回收列表。该机制避免长输出请求阻塞短输出请求，也避免已结束会话长期占用计算卡内存。"
    ],
}


def main():
    if not SRC.exists():
        raise FileNotFoundError(SRC)
    shutil.copy2(SRC, OUT)
    doc = Document(OUT)
    # Insert in reverse document order to keep anchors stable.
    for anchor_prefix, paras in reversed(list(INSERTIONS.items())):
        idx = find_para(doc, anchor_prefix)
        anchor = doc.paragraphs[idx]
        for para in reversed(paras):
            add_after(anchor, para)
    doc.save(OUT)
    note = f"""

## 第四部分深度实施版

补充时间：{datetime.now():%Y-%m-%d %H:%M:%S}

已在“第四部分详化版”基础上继续细化，并结合项目中的doc_parser、IngestPipeline、segmenter、extractor、HybridRetriever、QueryRouter、LLM双后端和三PDF全流程测试内容，补充对象写入顺序、SQLite chunk表、分块参数、触发词映射、关系触发词、强度公式、ValidationReport、ConflictRecord、FaultIndex、MaintenanceRuleIndex、TrainingRequirementIndex、QueryRouter路由规则、ModelPlan、动态batch队列和KV页回收流程。输出文件：{OUT}
"""
    REPORT.write_text(REPORT.read_text(encoding="utf-8") + note, encoding="utf-8")
    print(checks())


def checks():
    doc = Document(OUT)
    txt = "\n".join(p.text for p in doc.paragraphs)
    bad = ["综合实施例", "软件设计说明书", "第九部分", "第十部分", "待补充", "TODO", "占位图", "示意图占位"]
    with zipfile.ZipFile(OUT) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/")]
    return {
        "bad_terms": [b for b in bad if b in txt],
        "embodiments": sum(1 for p in doc.paragraphs if p.text.strip().startswith("实施例")),
        "paragraphs": len(doc.paragraphs),
        "media": len(media),
        "out": str(OUT),
    }


if __name__ == "__main__":
    main()
