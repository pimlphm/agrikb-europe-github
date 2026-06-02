# 00_public_agri_sources_overview

# 农业公开知识源接入说明

生成时间: 2026-05-23 16:39:01

本目录按用户指定链接下载并整理公开农业知识源，用于 AgriKB 农业知识库检索、问答和知识图谱展示。

## 指定来源链接
- ChatGPT 分享页: https://chatgpt.com/share/6a11b7aa-d9b0-83ec-88d4-26e0cc66e50a
- 台湾有机农业开放资料: https://data.gov.tw/en/datasets/49444
- Interoperable Europe AGROVOC: https://interoperable-europe.ec.europa.eu/collection/eu-semantic-interoperability-catalogue/solution/agrovoc-thesaurus
- Crop Ontology: https://cropontology.org/
- Google Earth Engine agriculture tag: https://developers.google.com/earth-engine/datasets/tags/agriculture?hl=zh-cn

## 下载摘要
- 成功文件/派生文件: 53
- 保留失败记录: 2
- manifest: data/raw/public_agriculture_sources/source_manifest.json
- 检索摘要目录: data/raw/public_agriculture_sources/docs_for_ingest
- 原始数据目录: data/raw/public_agriculture_sources

## 知识库接入范围
- AGROVOC: 保存入口页/RDF 导出页/官方 Core RDF ZIP，并抽取概念样例用于本地检索。
- Crop Ontology: 保存首页/API/元数据/统计/重点作物 traits/variables/重点作物 RDF。
- Google Earth Engine: 保存 agriculture 标签页，并抽取数据集目录链接。
- 台湾农业开放数据: 保存有机农业资料 CSV/JSON/XML，并统计经营主体、产品项目、认证字段。
- ChatGPT 分享链接: 保存页面快照或访问失败记录，作为用户来源说明入口。

## 补救说明
- Crop Ontology 全量 traits/variables 端点返回 500；已改用重点作物 traits/variables 接口接入。
- 台湾资料已通过 PowerShell 成功下载 CSV/JSON/XML，并覆盖最初的证书校验失败记录。
