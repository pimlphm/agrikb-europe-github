# AgriKB 路演 PPT 优化记录（2026-05-25）

## 输出文件
- PPTX：AgriKB_数智新农人经营中枢_路演终版_20260525.pptx
- 后台操作视频：AgriKB_backend_operation_demo_20260525.mp4
- 视频海报：AgriKB_backend_operation_demo_poster_20260525.png
- 预览图：roadshow_ppt_preview_20260525/
- Kimi 实测结果：backend_real_kimi_query_20260525.json

## 本次优化
- 重构为 18 页路演稿：赛道契合、产品闭环、GUI 实测、架构图、Ontology、经验沉淀、RLM 递归推理、真实模型调用、商业化、部署与演示。
- 增加 PowerPoint 演讲者备注：18 张幻灯片均有 speaker notes。
- 增加视频动效位：第 18 页放置后台操作视频海报与演示顺序；MP4 已放在同一材料目录。
- 使用比赛通知 PDF 页面作为赛道与政策依据。
- 引入最新 GUI 功能截图：作物监测、数智中台、质量溯源、资讯聚合、行情农资、天气滑页、政策解读等。

## 实测结果
- 健康检查：active_provider=KimiCliProvider，model=kimi-for-coding，indexed_chunk_count=4635。
- 真实问答：/api/query 返回 llm_used=true、llm_requested=true、model_provider=KimiCliProvider、selected_model=kimi-for-coding。
- 视频文件：ffmpeg 解码检查通过。
- PPTX 检查：18 张幻灯片、18 个演讲备注页、无 API Key、无地区误写、无问号乱码污染。
