# AgriKB 竞品对标与资讯聚合实测说明

## 实测范围

- 本地服务：`http://127.0.0.1:8010/ui/`
- 实测模型：`moonshot-v1-8k`（Kimi / Moonshot 默认后台）
- 知识库状态：已整理 145 条农业知识块
- 实测能力：17 个可点击功能入口，包括数智信息、新农人经营、农业局治理、农业企业、今天怎么干、东西卖给谁、能领啥补贴、天气有没有风险、新农人政策、数智中台、资讯聚合、竞品对标、创业大赛、农产品行情、农业气象、质量溯源、作物本体。
- 自动化验证：每个入口均触发 `/api/query`，并携带 `web_search=true`、`regional_intelligence=true`、`top_k=7`，问答区返回对应场景信息。

## 竞品对标对象

- FieldView：农场数据、地块监测、作物表现和作业决策。
- John Deere Operations Center：农机数据、作业协同、农场运营管理。
- CropX、Agworld：农艺管理、作业记录、投入品与咨询服务。
- OneSoil、EOSDA：卫星遥感、NDVI、地块监测、长势分析。
- 惠农网、一亩田：农产品供需撮合、批发交易、渠道流量。
- 农技耘/农技推广类工具：农技咨询、培训推广、专家服务。

## AgriKB 的强化方向

1. 资讯聚合：把政策、农业局通知、气象预警、市场行情、收购渠道、电商助农、农技咨询统一整理成可操作判断。
2. 县域适配：以江苏句容为应用场景，把本地作物、主体、政策、渠道和市场判断放在同一条问答链路里。
3. 三类用户闭环：农民看今日经营，农业局看治理台账和扶持筛选，企业看采购窗口和质量溯源。
4. 证据可展开：前台默认隐藏证据链，答辩、审计和汇报时可展开来源、知识树和会话证据图。
5. 商业交付：支持 PWA、本地运行、局域网访问、材料包、PPT、软著/专利文本和功能讲解录制。

## 输出文件

- 商业增强 PPT：`AgriKB_数智新农人经营中枢_商业增强路演PPT_含功能测试截图_最新版.pptx`
- 功能讲解录制：`AgriKB_function_demo_recording.webm`
- 功能截图：`outputs/manual-20260523-agrikb-function-screenshots/presentations/agrikb-function-screenshots/assets/function-screenshots/`
- 后端实测结果：`outputs/manual-20260523-agrikb-function-screenshots/real_benchmark_test_result.json`

## 参考来源

- FieldView: https://climate.com/
- John Deere Operations Center: https://www.deere.com/en/technology-products/precision-ag-technology/operations-center/
- CropX: https://cropx.com/
- Agworld: https://www.agworld.com/
- OneSoil: https://onesoil.ai/en/
- EOSDA Crop Monitoring: https://eos.com/products/crop-monitoring/
- 惠农网: https://www.cnhnb.com/
- 一亩田: https://www.ymt.com/
