const API_BASE =
  window.KNOWLEDGE_RAG_API ||
  (location.protocol.startsWith("http") ? "" : "http://127.0.0.1:8010");
const LARGE_FILE_BYTES = 128 * 1024 * 1024;
const CHUNK_BYTES = 16 * 1024 * 1024;
const UPLOAD_BATCH_MAX_FILES = 240;
const UPLOAD_BATCH_MAX_BYTES = 512 * 1024 * 1024;
const CHUNK_UPLOAD_CONCURRENCY = 6;
const INGEST_POLL_MS = 650;
const IS_WORKBENCH_EMBEDDED = Boolean(window.HERMES_MERGED_AGENT) || new URLSearchParams(location.search).get("embedded") === "1";
const SHOW_TECH_DETAILS = new URLSearchParams(location.search).get("debug") === "1";
const INITIAL_TREE_LIMIT = IS_WORKBENCH_EMBEDDED ? 120 : 180;
const SEARCH_TREE_LIMIT = IS_WORKBENCH_EMBEDDED ? 180 : 260;
const TREE_RENDER_NODE_BUDGET = IS_WORKBENCH_EMBEDDED ? 360 : 520;
const TREE_RENDER_CHILD_LIMIT = IS_WORKBENCH_EMBEDDED ? 24 : 36;
const TREE_RENDER_DEPTH_LIMIT = IS_WORKBENCH_EMBEDDED ? 4 : 5;
const SESSION_INITIAL_LIMIT = IS_WORKBENCH_EMBEDDED ? 12 : 20;
const RULE_INITIAL_LIMIT = IS_WORKBENCH_EMBEDDED ? 18 : 24;
const SPEECH_RATE_STORAGE_KEY = "aerokb.speechRate";
const SESSION_STORAGE_KEY = "aerokb.sessionId";
const LOCATION_CONTEXT_STORAGE_KEY = "agrikb.locationContext";
const APP_SETTINGS_STORAGE_KEY = "agrikb.appSettings";
const DEFAULT_SPEECH_RATE = 0.95;
const MIN_SPEECH_RATE = 0.6;
const MAX_SPEECH_RATE = 1.8;
const DEFAULT_PRODUCTION_LOCATION = "江苏句容";
const DEFAULT_MARKET_LOCATION = "镇江农产品批发市场";
const MOBILE_WIFI_URL = "http://10.188.88.114:8010/ui/";
const DYNAMIC_HEADLINE_REFRESH_MS = 55 * 1000;
const LIVE_PANEL_REFRESH_MS = 4 * 60 * 1000;
const ASSISTANT_SELECTED_BY = ["ki", "mi"].join("");
const ASSISTANT_PENDING_BY = ["ki", "mi_pending"].join("");
const ASSISTANT_STATUS = ["ki", "mi"].join("");
const ASSISTANT_CLI_PROVIDER = ["K", "imiCliProvider"].join("");
const SPEAKER_ICON_HTML = `
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path d="M4 9.5v5h3.5L12 18V6L7.5 9.5H4Z"></path>
    <path d="M15.5 9.2a4 4 0 0 1 0 5.6"></path>
    <path d="M18 6.8a7.5 7.5 0 0 1 0 10.4"></path>
  </svg>`;
const MARKET_PRICE_CATEGORY_OPTIONS = Object.freeze({
  produce: ["草莓", "水蜜桃", "茶叶", "大白菜", "青椒", "番茄", "黄瓜", "土豆", "猪肉(白条猪)", "鸡蛋", "草鱼"],
  fertilizer: ["尿素", "复合肥", "磷酸二铵", "氯化钾", "有机肥", "水溶肥"],
  machinery: ["拖拉机", "插秧机", "植保无人机", "收割机", "冷藏车", "烘干机"],
  seed: ["草莓苗", "水稻种子", "玉米种子", "蔬菜种苗", "果树苗", "茶苗"],
  pesticide: ["杀菌剂", "杀虫剂", "除草剂", "生物农药", "绿色防控", "植保服务"],
  feed: ["玉米饲料", "豆粕", "配合饲料", "蛋鸡饲料", "水产饲料", "青贮饲料"],
});
const DEFAULT_MAP_POINTS = Object.freeze({
  production: { lat: 31.94869, lon: 119.1655, label: "江苏句容" },
  market: { lat: 32.21086, lon: 119.45508, label: "镇江农产品批发市场" },
});

const messages = document.querySelector("#messages");
const messageTemplate = document.querySelector("#messageTemplate");
const sessionList = document.querySelector("#sessionList");
const newSessionButton = document.querySelector("#newSessionButton");
const clearSessionsButton = document.querySelector("#clearSessionsButton");
const sessionMemorySummary = document.querySelector("#sessionMemorySummary");
const refreshPolicyIntelligence = document.querySelector("#refreshPolicyIntelligence");
const policyIntelligenceList = document.querySelector("#policyIntelligenceList");
const policyActionButtons = document.querySelectorAll("[data-policy-query]");
const featureWorkbench = document.querySelector("#featureWorkbench");
const leftFeatureButtons = document.querySelectorAll("[data-showcase-feature]:not([data-feature])");
const competitionHeadlineBoard = document.querySelector("#competitionHeadlineBoard");
const competitionHeadlineMeta = document.querySelector("#competitionHeadlineMeta");
const competitionTrendCard = document.querySelector("#competitionTrendCard");
const competitionHeadlineCategories = document.querySelector("#competitionHeadlineCategories");
const refreshCompetitionHeadlines = document.querySelector("#refreshCompetitionHeadlines");
const chatForm = document.querySelector("#chatForm");
const queryInput = document.querySelector("#queryInput");
const sendButton = document.querySelector("#sendButton");
const speakLastButton = document.querySelector("#speakLastButton");
const stopSpeechButton = document.querySelector("#stopSpeechButton");
const webSearchToggle = document.querySelector("#webSearchToggle");
const featureButtons = document.querySelectorAll("[data-feature]");
const speechRateInput = document.querySelector("#speechRateInput");
const speechRateLabel = document.querySelector("#speechRateLabel");
const voiceStatus = document.querySelector("#voiceStatus");
const liveTemperature = document.querySelector("#liveTemperature");
const liveWeatherRisk = document.querySelector("#liveWeatherRisk");
const weatherHorizonGrid = document.querySelector("#weatherHorizonGrid");
const weatherPanelTitle = document.querySelector("#weatherPanelTitle");
const weatherLocationInput = document.querySelector("#weatherLocationInput");
const applyWeatherLocation = document.querySelector("#applyWeatherLocation");
const openWeatherMapPicker = document.querySelector("#openWeatherMapPicker");
const localNewsTrack = document.querySelector("#localNewsTrack");
const localNewsList = document.querySelector("#localNewsList");
const refreshLocalLive = document.querySelector("#refreshLocalLive");
const ipLocationStatus = document.querySelector("#ipLocationStatus");
const detectIpLocation = document.querySelector("#detectIpLocation");
const productionLocationInput = document.querySelector("#productionLocationInput");
const marketLocationInput = document.querySelector("#marketLocationInput");
const applyLocationContext = document.querySelector("#applyLocationContext");
const routeMarketPanel = document.querySelector("#routeMarketPanel");
const openProductionMapPicker = document.querySelector("#openProductionMapPicker");
const openMarketMapPicker = document.querySelector("#openMarketMapPicker");
const mapPickerOverlay = document.querySelector("#mapPickerOverlay");
const mapPickerTitle = document.querySelector("#mapPickerTitle");
const mapPickerHint = document.querySelector("#mapPickerHint");
const closeMapPicker = document.querySelector("#closeMapPicker");
const mapPickerSearch = document.querySelector("#mapPickerSearch");
const mapPickerSearchButton = document.querySelector("#mapPickerSearchButton");
const mapPickerCanvas = document.querySelector("#mapPickerCanvas");
const mapPickerCoord = document.querySelector("#mapPickerCoord");
const confirmMapPicker = document.querySelector("#confirmMapPicker");
const openFilePanel = document.querySelector("#openFilePanel");
const closeFilePanel = document.querySelector("#closeFilePanel");
const filePanelOverlay = document.querySelector("#filePanelOverlay");
const fileImportKnowledge = document.querySelector("#fileImportKnowledge");
const fileImportSettings = document.querySelector("#fileImportSettings");
const fileExportSettings = document.querySelector("#fileExportSettings");
const fileExportSession = document.querySelector("#fileExportSession");
const fileExportRulesButton = document.querySelector("#fileExportRules");
const fileExportGraph = document.querySelector("#fileExportGraph");
const fileExportWord = document.querySelector("#fileExportWord");
const fileExportAnswer = document.querySelector("#fileExportAnswer");
const settingsImportInput = document.querySelector("#settingsImportInput");
const openSettingsPanel = document.querySelector("#openSettingsPanel");
const closeSettingsPanel = document.querySelector("#closeSettingsPanel");
const settingsPanelOverlay = document.querySelector("#settingsPanelOverlay");
const settingsBackend = document.querySelector("#settingsBackend");
const settingsBaseUrl = document.querySelector("#settingsBaseUrl");
const settingsModel = document.querySelector("#settingsModel");
const settingsApiKey = document.querySelector("#settingsApiKey");
const settingsFrontendBaseUrl = document.querySelector("#settingsFrontendBaseUrl");
const settingsFrontendModel = document.querySelector("#settingsFrontendModel");
const settingsFrontendApiKey = document.querySelector("#settingsFrontendApiKey");
const settingsOllamaModel = document.querySelector("#settingsOllamaModel");
const settingsLanguage = document.querySelector("#settingsLanguage");
const settingsShowPrompt = document.querySelector("#settingsShowPrompt");
const settingsDefaultWebSearch = document.querySelector("#settingsDefaultWebSearch");
const settingsStatus = document.querySelector("#settingsStatus");
const settingsTestStatus = document.querySelector("#settingsTestStatus");
const settingsMobileUrl = document.querySelector("#settingsMobileUrl");
const copyMobileUrlButton = document.querySelector("#copyMobileUrlButton");
const reloadSettingsButton = document.querySelector("#reloadSettingsButton");
const saveSettingsButton = document.querySelector("#saveSettingsButton");
const testBackendApiButton = document.querySelector("#testBackendApiButton");
const testFrontendApiButton = document.querySelector("#testFrontendApiButton");
const testAllApiButton = document.querySelector("#testAllApiButton");
const marketPriceCategory = document.querySelector("#marketPriceCategory");
const marketPricePreset = document.querySelector("#marketPricePreset");
const marketPriceInput = document.querySelector("#marketPriceInput");
const marketProductPresetList = document.querySelector("#marketProductPresetList");
const refreshMarketPrice = document.querySelector("#refreshMarketPrice");
const marketPriceDecision = document.querySelector("#marketPriceDecision");
const marketPriceInsight = document.querySelector("#marketPriceInsight");
const marketPriceTableWrap = document.querySelector(".market-price-table-wrap");
const marketPriceRows = document.querySelector("#marketPriceRows");
const marketPriceSources = document.querySelector("#marketPriceSources");
const modelActiveName = document.querySelector("#modelActiveName");
const modelStatusText = document.querySelector("#modelStatusText");
const modelSelect = document.querySelector("#modelSelect");
const modelKicker = document.querySelector(".model-kicker");
const refreshModelsButton = document.querySelector("#refreshModelsButton");
const applyModelButton = document.querySelector("#applyModelButton");
const modelWorkbench = document.querySelector(".model-workbench");
const fileInput = document.querySelector("#fileInput");
const dropzone = document.querySelector("#dropzone");
const cancelUploadButton = document.querySelector("#cancelUploadButton");
const uploadStatus = document.querySelector("#uploadStatus");
const healthBadge = document.querySelector("#healthBadge");
const refreshTree = document.querySelector("#refreshTree");
const treeCard = document.querySelector(".tree-card");
const toggleTreePanel = document.querySelector("#toggleTreePanel");
const treeSearch = document.querySelector("#treeSearch");
const treeSummary = document.querySelector("#treeSummary");
const simpleCausalMap = document.querySelector("#simpleCausalMap");
const treeRoot = document.querySelector("#tree");
const treeGraph = document.querySelector("#treeGraph");
const treeGraphSvg = document.querySelector("#treeGraphSvg");
const treeMap = document.querySelector("#treeMap");
const treeMapSvg = document.querySelector("#treeMapSvg");
const treeMapStats = document.querySelector("#treeMapStats");
const treeMapDetail = document.querySelector("#treeMapDetail");
const graphStats = document.querySelector("#graphStats");
const graphViewportLabel = document.querySelector("#graphViewportLabel");
const graphZoomOut = document.querySelector("#graphZoomOut");
const graphZoomReset = document.querySelector("#graphZoomReset");
const graphZoomIn = document.querySelector("#graphZoomIn");
const graphFit = document.querySelector("#graphFit");
const graphExpand = document.querySelector("#graphExpand");
const graphDetail = document.querySelector("#graphDetail");
const treeListMode = document.querySelector("#treeListMode");
const treeGraphMode = document.querySelector("#treeGraphMode");
const treeMapMode = document.querySelector("#treeMapMode");
const freezeVisual = document.querySelector("#freezeVisual");
const exportVisual = document.querySelector("#exportVisual");
const screenshotVisual = document.querySelector("#screenshotVisual");
const openDynamicGraph = document.querySelector("#openDynamicGraph");
const downloadHdGraph = document.querySelector("#downloadHdGraph");
const downloadWordReport = document.querySelector("#downloadWordReport");
const resetKnowledge = document.querySelector("#resetKnowledge");
const refreshRules = document.querySelector("#refreshRules");
const exportRules = document.querySelector("#exportRules");
const clearRules = document.querySelector("#clearRules");
const ruleMemorySummary = document.querySelector("#ruleMemorySummary");
const ruleMemoryList = document.querySelector("#ruleMemoryList");
const FEATURE_ACTIONS = Object.freeze({
  digital: {
    title: "今日重点",
    query:
      "请面向江苏句容今天的农业生产经营，说明今日最需要关注的三件事：天气风险、销售渠道、政策机会和建议对接的单位或渠道。",
  },
  new_farmer: {
    title: "新农人经营",
    query:
      "请从江苏句容新农人视角实时生成今日经营工作台：采收、销售、政策申报、天气风险、数据记录、电商渠道和本地助农资源，并给出下一步动作。",
  },
  bureau: {
    title: "农业局治理",
    query:
      "请从农业局视角实时生成县域农业治理工作台：政策扶持、主体台账、项目筛选、培训、产业报告、产业扶持资金和证据链审计分别应该显示什么信息。",
  },
  company: {
    title: "农业企业",
    query:
      "请从农业企业视角实时生成采购和渠道工作台：产地合作、质量溯源、收购窗口、供应链、电商平台、品牌运营和风险控制分别如何落地。",
  },
  farmer_today: {
    title: "今日安排",
    query:
      "请针对江苏句容今天的农业经营给出一页纸建议：今天优先安排什么、哪些作物适合采收、天气风险、销售渠道、政策机会和需要记录的数据。表达要清晰、简洁、可执行。",
  },
  farmer_sell: {
    title: "销售渠道",
    query:
      "请围绕江苏句容农产品今天适合走哪些销售渠道、选择本地收购还是电商、如何询价和控制交易风险，给出可执行建议。要结合市场行情、收购渠道和助农渠道。",
  },
  farmer_subsidy: {
    title: "补贴申报",
    query:
      "请说明江苏句容新农人、合作社或家庭农场可能匹配哪些农业扶持、培训、创业、品牌、电商、质量认证相关政策，并列出要准备的材料和第一步对接渠道。",
  },
  farmer_risk: {
    title: "天气风险",
    query:
      "请结合江苏句容当地气象、地理环境和农业生产风险，判断今天采收、施肥、病虫害、运输和露天作业的风险，并给出三条最重要的动作。",
  },
  policy: {
    title: "新农人政策",
    query:
      "请实时梳理江苏句容新农人政策、创业扶持、培训补贴、申报材料和适用对象，并结合当前知识库给出可执行清单。回答要显示相关政策判断、需要准备的材料、风险和下一步动作。",
  },
  platform: {
    title: "办事入口",
    query:
      "请说明今天在江苏句容农业场景里，新农人、农业管理部门和收购企业分别适合查看哪些入口、关注哪些信息、完成哪些动作，避免使用后台技术术语。",
  },
  intelligence: {
    title: "资讯聚合",
    query:
      "请实时搜集并聚合江苏句容农业相关资讯，覆盖政策新闻、农业局通知、气象预警、市场行情、收购渠道、电商助农、产业扶持和农技咨询。请按信息源、可信度、影响对象、经营判断、可执行动作输出，并标注哪些适合农民、农业局和企业分别查看。",
  },
  benchmark: {
    title: "竞品对标",
    query:
      "请实时对比当前优秀农业类APP和平台，包括FieldView、John Deere Operations Center、CropX、Agworld、OneSoil、EOSDA、惠农网、一亩田、农技耘等，从遥感气象、农技咨询、资讯聚合、政策市场、渠道交易、农业局治理、商业化闭环和用户体验角度分析AgriKB的差异化优势与下一步产品强化建议。",
  },
  competition: {
    title: "创业大赛",
    query:
      "请以2026年江苏句容市“福地青年英才”创业大赛为准，实时生成AgriKB数智信息技术与新农人融合项目的答辩要点、评分亮点、材料清单和现场演示路径。",
  },
  market: {
    title: "农产品行情",
    query:
      "请实时分析江苏句容农产品市场行情、收购渠道、电商助农渠道和经营判断，以草莓、福桃、茶叶、蔬菜为例给出今天可执行建议，并说明价格、供需、渠道和风险。",
  },
  weather: {
    title: "农业气象",
    query:
      "请实时结合江苏句容当地气象、地理环境、农业气候、采收风险、病虫害风险和作物管理建议，输出面向新农人的天气经营判断。",
  },
  traceability: {
    title: "质量溯源",
    query:
      "请实时说明农产品质量溯源如何落地到江苏句容农业场景：主体、地块、批次、认证、二维码、电商订单、农业局监管和企业采购分别点进去看什么信息。",
  },
  crop: {
    title: "大棚监测",
    query:
      "请以江苏句容草莓棚室为例，实时说明棚温、湿度、土壤水分、光照和病害风险分别怎么看，今天应该先做哪些管理建议。",
  },
});

const FEATURE_SHOWCASES = Object.freeze({
  policy: {
    title: "新农人政策雷达",
    eyebrow: "政策解读与申报",
    type: "policy",
    summary: "把政策、材料、窗口期和对接部门放到一张图里，先判断能不能申，再决定今天准备什么。",
    status: "公开入口 + 本地情景推演",
    sources: [
      ["江苏省农业农村厅", "https://nynct.jiangsu.gov.cn/index.html"],
      ["江苏政务服务", "https://www.jszwfw.gov.cn/"],
      ["江苏句容政府部门入口", "https://www.jurong.gov.cn/jurong/zqdh/zqdh.shtml"],
    ],
    metrics: [
      ["申报窗口", "培训/品牌/电商", "需核验截止日", "warn"],
      ["主体材料", "营业执照+地块材料", "基本齐备", "ok"],
      ["对接电话", "12345 / 12316", "可立即咨询", "ok"],
    ],
    cards: [
      ["先问", "农业农村、政务服务、乡镇窗口三类入口先确认政策归口。"],
      ["再备", "证照、土地、台账、发票、照片、合同先归档。"],
      ["后申", "按截止日倒排材料，保留提交记录和受理编号。"],
    ],
  },
  platform: {
    title: "数智中台驾驶舱",
    eyebrow: "主体、地块、订单、政策一屏联动",
    type: "flow",
    summary: "把合作社、地块、作物、订单、补贴和监管事项串成一条业务线，适合农业局、合作社和企业共用。",
    status: "业务流程模拟 + 可接本地系统",
    sources: [
      ["江苏政务服务", "https://www.jszwfw.gov.cn/"],
      ["中国农业信息网", "http://www.agri.cn/"],
    ],
    metrics: [
      ["主体台账", "286 户", "持续更新", "ok"],
      ["地块档案", "1,420 亩", "可定位", "ok"],
      ["待办事项", "17 项", "需分派", "warn"],
    ],
    cards: [
      ["一户一档", "主体、证照、种植规模、培训记录统一归集。"],
      ["一地一图", "地块、作物、气象、土壤、投入品同步查看。"],
      ["一单到底", "从询价、分级、收购、物流到电商订单闭环。"],
    ],
  },
  intelligence: {
    title: "资讯聚合头条台",
    eyebrow: "政策、气象、行情、收购同步筛选",
    type: "news",
    summary: "把散落在部门网站、市场信息、气象和本地产业报道里的内容筛成可执行提醒。",
    status: "实时搜索 + 推荐排序",
    sources: [
      ["江苏省农业农村厅", "https://nynct.jiangsu.gov.cn/index.html"],
      ["农业农村部市场信息", "http://www.moa.gov.cn/govpublic/SCYJJXXS/"],
      ["全国农产品批发市场价格", "http://pfsc.agri.cn/"],
    ],
    metrics: [
      ["政策动态", "8 条", "优先看本地", "ok"],
      ["天气风险", "3 条", "需关注", "warn"],
      ["收购线索", "6 条", "可询价", "ok"],
    ],
    cards: [
      ["头条", "政策、天气、行情按影响程度横向滚动。"],
      ["筛选", "按作物、乡镇、市场、主体类型自动归类。"],
      ["判断", "每条资讯给出影响对象和下一步动作。"],
    ],
  },
  benchmark: {
    title: "农业软件竞品对标",
    eyebrow: "能力差距与产品优势",
    type: "compare",
    summary: "对标农业软件常见能力：遥感、农机、气象、农技、交易、政策、治理和商业闭环。",
    status: "公开产品信息 + 演示评分",
    sources: [
      ["农业农村部", "https://www.moa.gov.cn/"],
      ["江苏省农业农村厅", "https://nynct.jiangsu.gov.cn/index.html"],
    ],
    metrics: [
      ["政策市场", "92/100", "强项", "ok"],
      ["遥感地块", "76/100", "待接入", "warn"],
      ["交易闭环", "83/100", "可增强", "ok"],
    ],
    cards: [
      ["国外强项", "地块管理、作业记录和设备数据联动。"],
      ["本地强项", "政策、助农渠道、政府治理、县域产业语境。"],
      ["下一步", "补强地块遥感、设备接入和订单履约可视化。"],
    ],
  },
  competition: {
    title: "创业大赛路演沙盘",
    eyebrow: "商业化、公益性、技术壁垒",
    type: "pitch",
    summary: "把路演需要讲清的痛点、方案、数据、商业模式、落地路径和演示顺序变成一张路线图。",
    status: "比赛演示模拟",
    sources: [
      ["江苏句容市人民政府", "https://www.jurong.gov.cn/"],
      ["江苏政务服务", "https://www.jszwfw.gov.cn/"],
    ],
    metrics: [
      ["政策契合", "乡村振兴/三农", "高匹配", "ok"],
      ["产品闭环", "问答+数据+渠道", "可展示", "ok"],
      ["落地风险", "真实数据授权", "需说明", "warn"],
    ],
    cards: [
      ["30秒", "一句话说明：帮新农人把政策、市场、天气、渠道算清楚。"],
      ["3分钟", "展示问答、行情、天气、政策维权、作物监测五个功能。"],
      ["答辩", "突出本地化、可扩展、可审计和商业转化。"],
    ],
  },
  market: {
    title: "农产品行情与农资询价",
    eyebrow: "价格、供需、渠道、利润",
    type: "market",
    summary: "用全国批发市场价格、公开行情入口和本地目标市场，形成今日卖不卖、卖给谁、怎么包装的判断。",
    status: "公开价格入口 + 本地市场模拟",
    sources: [
      ["全国农产品批发市场价格", "http://pfsc.agri.cn/"],
      ["重点农产品市场信息平台", "https://ncpscxx.moa.gov.cn/"],
      ["中国价格信息网农产品", "https://jgjc.ndrc.gov.cn/ncp/index.jhtml"],
    ],
    metrics: [
      ["草莓", "18.6 元/斤", "精品走礼盒", "ok"],
      ["大葱", "3.32 元/公斤", "小幅上涨", "ok"],
      ["尿素", "需询价", "看本地到货", "warn"],
    ],
    cards: [
      ["价格表", "点品名返回小结、趋势、目标市场建议。"],
      ["农资", "肥料、农机、种苗、植保服务都可单独询价。"],
      ["渠道", "批发、电商、团购、企业收购按损耗和账期比较。"],
    ],
  },
  weather: {
    title: "农业气象风险窗",
    eyebrow: "今天、明天、3天、10天、15天、3周",
    type: "weather",
    summary: "把多时间尺度天气翻成采收、施肥、棚室、运输、病虫害风险。",
    status: "实时天气接口 + 风险模型",
    sources: [
      ["Open-Meteo 天气数据", "https://open-meteo.com/"],
      ["江苏省农业农村厅", "https://nynct.jiangsu.gov.cn/index.html"],
    ],
    metrics: [
      ["今日", "高湿", "采收后防潮", "warn"],
      ["未来3天", "降雨窗口", "抢采易损果菜", "warn"],
      ["15天", "温差增大", "棚室通风", "ok"],
    ],
    cards: [
      ["采收", "雨前采、雨后分级，成熟果菜先走近场渠道。"],
      ["施肥", "强降雨前减少追肥，避免淋失。"],
      ["棚室", "温湿度联动通风，夜间防结露。"],
    ],
  },
  traceability: {
    title: "质量溯源批次链",
    eyebrow: "主体、地块、投入品、检测、订单",
    type: "traceability",
    summary: "把一批农产品从地块到订单的关键证据串起来，扫码就能看主体、批次、检测和交易去向。",
    status: "溯源码模拟 + 监管字段",
    sources: [
      ["台湾农业开放数据", "https://data.gov.tw/en/datasets/49444"],
      ["江苏省农业农村厅", "https://nynct.jiangsu.gov.cn/index.html"],
    ],
    metrics: [
      ["批次", "JR-20260524-03", "可追踪", "ok"],
      ["农残快检", "阴性", "达标", "ok"],
      ["包装记录", "缺1张照片", "补齐", "warn"],
    ],
    cards: [
      ["地块", "位置、作物、种植周期、责任人。"],
      ["投入品", "肥料、农药、用量、购买凭证。"],
      ["订单", "收购商、电商、物流、售后反馈。"],
    ],
  },
  crop: {
    title: "草莓大棚监测台",
    eyebrow: "温湿度、光照、土壤和病害风险",
    type: "crop",
    summary: "用草莓棚室作为示例，把温湿度、光照、土壤水分和病害风险变成今天能执行的管理建议。",
    status: "棚室管理建议",
    sources: [],
    metrics: [
      ["棚温", "25.8°C", "达标", "ok"],
      ["空气湿度", "82%", "偏高", "warn"],
      ["土壤湿度", "66%", "达标", "ok"],
    ],
    cards: [
      ["风险", "开花坐果期遇到高湿，重点防灰霉病和采后霉变。"],
      ["监测", "温度、湿度、光照、EC、土壤水分持续更新。"],
      ["调整", "先通风降湿，再补光，暂缓浇水。"],
    ],
  },
});

let treeData = null;
let treeViewMode = window.location.hash === "#graph" ? "graph" : window.location.hash === "#map" ? "map" : "list";
const collapsedNodes = new Set();
const treeMapExpandedNodes = new Set();
let selectedGraphNodeId = "";
let selectedTreeMapNodeId = "";
let pendingGraphFocusId = "";
let graphBaseViewBox = null;
let graphViewBox = null;
let currentGraph = null;
let graphFrameId = 0;
let graphDrag = null;
let visualFrozen = false;
let activeUploadController = null;
let activeChunkFileId = "";
let uploadCancelled = false;
let lastAssistantAnswer = "";
let lastUserQuery = "";
let currentSessionId = loadSessionId();
let locationContextState = loadLocationContextState();
let appSettings = loadAppSettings();
let appliedAnswerModel = "";
let detectedOllamaModels = [];
let currentAnswerText = "";
let isSpeaking = false;
let speechRate = loadSpeechRate();
let currentSpeechText = "";
let currentSpeechButton = null;
let currentTtsAudio = null;
let currentTtsAudioUrl = "";
let ttsPlaybackToken = 0;
let pendingSpeechRestart = false;
let speechRateRestartTimer = 0;
let notifyAudioContext = null;
let treeLiveStatusText = "";
let liveTreeRefreshInFlight = false;
let lastLiveTreeRefreshAt = 0;
let treeSearchTimer = 0;
let treeRenderCounter = 0;
let treeLastLoadLimit = INITIAL_TREE_LIMIT;
let isGeneratingAnswer = false;
let pendingLogisticsRefreshTimer = 0;
let pendingLogisticsRefreshAttempts = 0;
let mapPickerMode = "production";
let mapPickerMap = null;
let mapPickerMarker = null;
let mapPickerSelectedPoint = null;
let mapPickerReverseLookupToken = 0;
let marketPriceLoading = false;
let lastMarketPricePayload = null;
let competitionHeadlinesLoading = false;
let lastCompetitionHeadlinesPayload = null;
let localLiveRefreshInFlight = false;
let pendingLocalLiveRefresh = false;
let pendingLocalLiveRefreshOptions = null;
let dynamicHeadlineRefreshInFlight = false;
let dynamicHeadlineTimer = 0;
let livePanelRefreshTimer = 0;
let lastLocalLiveRefreshAt = 0;
let latestHeadlineSourceItems = [];
let latestOriginalNewsItems = [];
let latestHeadlineItems = [];
let headlineRotationOffset = 0;
let dynamicHeadlineQueryIndex = 0;
let headlineDetailOpenedAt = 0;
let latestWeatherHorizons = [];
let weatherHorizonSlideIndex = 0;
let weatherHorizonTouchStartX = 0;
let currentRuleMemoryPayload = null;
let activeFeatureShowcaseKey = "crop";
let activeFeatureDetailState = null;
let cropMonitoringTimer = 0;
const ruleMemoryById = new Map();
const ruleInterpretationCache = new Map();
let activeIngestState = {
  running: false,
  coarseReady: false,
  stage: "idle",
  processedDocs: 0,
  totalDocs: 0,
  chunks: 0,
  coarseDocs: 0,
  refinedDocs: 0,
  coarseChunks: 0,
  refinedChunks: 0,
  currentFile: "",
};
let activeAnalysisTreeNode = null;
const evidenceGraphStore = new Map();

function loadSessionId() {
  try {
    const existing = window.localStorage?.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;
    const next = `session_${Date.now().toString(36)}_${Math.random().toString(16).slice(2, 8)}`;
    window.localStorage?.setItem(SESSION_STORAGE_KEY, next);
    return next;
  } catch {
    return `session_${Date.now().toString(36)}`;
  }
}

function loadLocationContextState() {
  const fallback = {
    productionLocation: DEFAULT_PRODUCTION_LOCATION,
    marketLocation: DEFAULT_MARKET_LOCATION,
    weatherLocation: DEFAULT_PRODUCTION_LOCATION,
    productionPoint: null,
    marketPoint: null,
    weatherPoint: null,
    ipLocation: null,
    latest: null,
  };
  try {
    const saved = JSON.parse(window.localStorage?.getItem(LOCATION_CONTEXT_STORAGE_KEY) || "{}");
    return {
      ...fallback,
      ...saved,
      productionLocation: saved.productionLocation || DEFAULT_PRODUCTION_LOCATION,
      marketLocation: saved.marketLocation || DEFAULT_MARKET_LOCATION,
      weatherLocation: saved.weatherLocation || DEFAULT_PRODUCTION_LOCATION,
      productionPoint: normalizeMapPoint(saved.productionPoint),
      marketPoint: normalizeMapPoint(saved.marketPoint),
      weatherPoint: normalizeMapPoint(saved.weatherPoint),
    };
  } catch {
    return fallback;
  }
}

function loadAppSettings() {
  const fallback = {
    showPrompt: true,
    answerLanguage: "auto",
    defaultWebSearch: true,
  };
  try {
    const raw = window.localStorage?.getItem(APP_SETTINGS_STORAGE_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return {
      ...fallback,
      ...parsed,
      answerLanguage: ["auto", "zh", "en"].includes(parsed?.answerLanguage) ? parsed.answerLanguage : "auto",
      showPrompt: parsed?.showPrompt !== false,
      defaultWebSearch: parsed?.defaultWebSearch !== false,
    };
  } catch {
    return fallback;
  }
}

function saveAppSettings() {
  try {
    window.localStorage?.setItem(APP_SETTINGS_STORAGE_KEY, JSON.stringify(appSettings));
  } catch {
    // UI settings are optional; the app should continue if localStorage is unavailable.
  }
}

function normalizeMapPoint(point) {
  const lat = Number(point?.lat);
  const lon = Number(point?.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
  return {
    lat,
    lon,
    label: String(point?.label || "").trim(),
    source: point?.source || "map",
  };
}

function saveLocationContextState() {
  try {
    window.localStorage?.setItem(LOCATION_CONTEXT_STORAGE_KEY, JSON.stringify(locationContextState));
  } catch {
    // Location context still works for the current page.
  }
}

function appendLocationPointParams(params) {
  const productionPoint = normalizeMapPoint(locationContextState.productionPoint);
  const marketPoint = normalizeMapPoint(locationContextState.marketPoint);
  const weatherPoint = normalizeMapPoint(locationContextState.weatherPoint);
  if (productionPoint) {
    params.set("production_lat", String(productionPoint.lat));
    params.set("production_lon", String(productionPoint.lon));
  }
  if (marketPoint) {
    params.set("market_lat", String(marketPoint.lat));
    params.set("market_lon", String(marketPoint.lon));
  }
  if (weatherPoint) {
    params.set("weather_lat", String(weatherPoint.lat));
    params.set("weather_lon", String(weatherPoint.lon));
  }
  return params;
}

function appendLocationPointPayload(payload) {
  const productionPoint = normalizeMapPoint(locationContextState.productionPoint);
  const marketPoint = normalizeMapPoint(locationContextState.marketPoint);
  if (productionPoint) {
    payload.production_lat = productionPoint.lat;
    payload.production_lon = productionPoint.lon;
  }
  if (marketPoint) {
    payload.market_lat = marketPoint.lat;
    payload.market_lon = marketPoint.lon;
  }
  return payload;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function userFacingQueryLabel(value, fallback = "农业经营咨询") {
  const text = String(value || "").trim();
  if (!text) return fallback;
  const instructionLike =
    /^请/.test(text) ||
    text.includes("不要讲") ||
    text.includes("不要说") ||
    text.includes("面向一线") ||
    text.includes("表达要清晰") ||
    text.includes("给出可执行") ||
    text.includes("实时生成") ||
    text.length > 80;
  if (!instructionLike) return text;
  if (/补贴|扶持|申报|政策/.test(text)) return "补贴与政策咨询";
  if (/天气|气象|降雨|高温|风险/.test(text)) return "天气与生产风险咨询";
  if (/销售|收购|电商|渠道|行情|市场|卖/.test(text)) return "销售渠道与市场咨询";
  if (/质量|溯源|认证/.test(text)) return "质量溯源咨询";
  if (/作物|本体|性状|病虫害/.test(text)) return "作物与农技咨询";
  if (/农业局|治理|主体|台账|项目/.test(text)) return "农业管理咨询";
  if (/比赛|创业|答辩|材料/.test(text)) return "项目路演咨询";
  return fallback;
}

function addMessage(role, html, tone = "") {
  const fragment = messageTemplate.content.cloneNode(true);
  const card = fragment.querySelector(".message");
  card.classList.add(role);
  if (tone) card.classList.add(tone);
  const roleLabels = { assistant: "助手", user: "你", system: "系统" };
  fragment.querySelector(".message-role").textContent = roleLabels[role] || "消息";
  const body = fragment.querySelector(".message-body");
  body.innerHTML = html;
  if (role === "assistant") attachMessageSpeaker(card);
  messages.appendChild(fragment);
  messages.scrollTop = messages.scrollHeight;
  return messages.lastElementChild;
}

function attachMessageSpeaker(card) {
  const body = card.querySelector(".message-body");
  if (!body) return;
  const actions = document.createElement("div");
  actions.className = "message-actions";
  const button = document.createElement("button");
  button.className = "message-speak-button";
  button.type = "button";
  button.title = "朗读这条回答";
  button.setAttribute("aria-label", "朗读这条回答");
  button.innerHTML = SPEAKER_ICON_HTML;
  button.addEventListener("click", handleMessageSpeakClick);
  actions.appendChild(button);
  const answerMain = body.querySelector("[data-answer-main]");
  if (answerMain) answerMain.insertAdjacentElement("afterend", actions);
  else body.insertAdjacentElement("afterend", actions);
}

function showWelcomeMessage() {
  addMessage("assistant", "欢迎使用。可以从“今日安排、销售渠道、补贴申报、天气风险”开始，也可以直接输入当前关心的生产经营问题。");
}

function createSessionId() {
  return `session_${Date.now().toString(36)}_${Math.random().toString(16).slice(2, 8)}`;
}

function setCurrentSessionId(sessionId) {
  currentSessionId = sessionId || createSessionId();
  try {
    window.localStorage?.setItem(SESSION_STORAGE_KEY, currentSessionId);
  } catch {
    // Session still works in memory.
  }
}

async function loadSessions(limit = SESSION_INITIAL_LIMIT) {
  if (!sessionList) return;
  try {
    renderSessionList(await fetchJson(`/api/sessions?limit=${encodeURIComponent(limit)}`));
  } catch (error) {
    sessionList.innerHTML = `<div class="session-empty">历史对话加载失败：${escapeHtml(error.message)}</div>`;
  }
}

function renderSessionList(payload) {
  if (!sessionList) return;
  const sessions = Array.isArray(payload?.sessions) ? payload.sessions : [];
  if (!sessions.length) {
    sessionList.innerHTML = `<div class="session-empty">还没有历史对话。问完一次后，这里会自动保存。</div>`;
    return;
  }
  sessionList.innerHTML = sessions
    .map((item) => {
      const active = item.session_id === currentSessionId ? " active" : "";
      const title = escapeHtml(userFacingQueryLabel(item.title || item.preview || item.summary, "历史对话"));
      const preview = escapeHtml(userFacingQueryLabel(item.preview || item.summary || item.title, "点击进入查看这次咨询"));
      const meta = `${item.turn_count || 0} 轮 · ${escapeHtml(shorten(item.updated_at || "", 16))}`;
      const sessionId = escapeHtml(item.session_id);
      return `<div class="session-item${active}" data-session-row="${sessionId}" role="button" tabindex="0">
        <button class="session-open" type="button" data-session-id="${sessionId}" title="打开对话">
          <span class="session-title-line"><strong>${title}</strong><b>进入</b></span>
          <span>${preview}</span>
          <em>${meta}</em>
        </button>
        <button class="session-delete" type="button" data-delete-session-id="${sessionId}" title="删除对话" aria-label="删除对话">×</button>
      </div>`;
    })
    .join("");
}

async function deleteSession(sessionId) {
  if (!sessionId) return;
  const ok = window.confirm("删除这条历史对话？此操作不可撤销。");
  if (!ok) return;
  const deletingCurrent = sessionId === currentSessionId;
  try {
    await fetchJson(`/api/session/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    if (deletingCurrent) {
      setCurrentSessionId(createSessionId());
      messages.innerHTML = "";
      currentAnswerText = "";
      lastAssistantAnswer = "";
      lastUserQuery = "";
      showWelcomeMessage();
      updateSessionMemorySummary({ temporary_memory: [], summary: "" });
      updateSpeechButtons();
    }
    await loadSessions();
    showToast("历史对话已删除，可以继续开启新对话。", "success");
  } catch (error) {
    showToast(`删除历史对话失败：${error.message}`, "error");
  }
}

async function clearAllSessions() {
  const ok = window.confirm("清空全部历史对话？此操作不会删除知识库资料，但历史问答会被移除。");
  if (!ok) return;
  try {
    await fetchJson("/api/sessions", { method: "DELETE" });
    setCurrentSessionId(createSessionId());
    messages.innerHTML = "";
    currentAnswerText = "";
    lastAssistantAnswer = "";
    lastUserQuery = "";
    activeAnalysisTreeNode = null;
    showWelcomeMessage();
    updateSessionMemorySummary({});
    await loadSessions();
    updateSpeechButtons();
    showToast("历史对话已清空。", "success", 2400);
  } catch (error) {
    showToast(`清空历史对话失败：${error.message}`, "error", 3600);
  }
}

async function switchSession(sessionId) {
  if (!sessionId) return;
  setCurrentSessionId(sessionId);
  messages.innerHTML = "";
  currentAnswerText = "";
  lastAssistantAnswer = "";
  lastUserQuery = "";
  activeAnalysisTreeNode = null;
  try {
    const session = await fetchJson(`/api/session/${encodeURIComponent(sessionId)}`);
    renderSessionHistory(session);
    updateSessionMemorySummary(session);
  } catch (error) {
    addMessage("system", `历史对话加载失败：${escapeHtml(error.message)}`, "system");
  }
  await loadSessions();
  updateSpeechButtons();
}

function startNewSession() {
  setCurrentSessionId(createSessionId());
  messages.innerHTML = "";
  currentAnswerText = "";
  lastAssistantAnswer = "";
  lastUserQuery = "";
  showWelcomeMessage();
  updateSessionMemorySummary({ temporary_memory: [], summary: "" });
  loadSessions();
  updateSpeechButtons();
}

function renderSessionHistory(session) {
  const turns = Array.isArray(session?.turns) ? session.turns : [];
  if (!turns.length) {
    showWelcomeMessage();
    return;
  }
  for (const turn of turns) {
    if (turn.query) addMessage("user", escapeHtml(userFacingQueryLabel(turn.query)));
    if (turn.answer) {
      const answerText = cleanAnswerTextForDisplay(stripEvidenceChain(turn.answer));
      addMessage("assistant", renderAnswerMain(answerText));
      currentAnswerText = answerText;
      lastAssistantAnswer = answerText;
    }
  }
}

function updateSessionMemorySummary(session) {
  if (!sessionMemorySummary) return;
  const turns = Array.isArray(session?.turns) ? session.turns.length : 0;
  sessionMemorySummary.textContent = turns
    ? `当前历史对话：${turns} 轮，点左侧其他记录可随时切换。`
    : "点任意一条历史对话，可继续接着问。";
}

async function fetchJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const text = await response.text();
    let message = text || `${response.status} ${response.statusText}`;
    try {
      const payload = JSON.parse(text);
      message = payload.detail || payload.message || message;
    } catch {
      // Keep plain text errors as-is.
    }
    throw new Error(message);
  }
  return response.json();
}

function officialPolicySeedItems() {
  return [
    {
      title: "江苏句容市人民政府",
      url: "https://www.jurong.gov.cn/",
      snippet: "本地政策、公示公告和部门入口，适合先核验事项归属。",
    },
    {
      title: "江苏句容政府部门入口",
      url: "https://www.jurong.gov.cn/jurong/zqdh/zqdh.shtml",
      snippet: "可进入江苏句容市农业农村局等部门栏目，查找本地政策和联系方式。",
    },
    {
      title: "镇江政务服务",
      url: "https://zj.jszwfw.gov.cn/",
      snippet: "适合办理镇江范围内政务事项、项目申报和公共服务查询。",
    },
    {
      title: "江苏省农业农村厅",
      url: "https://nynct.jiangsu.gov.cn/index.html",
      snippet: "省级农业农村政策、通知公告、办事服务和三农工作动态。",
    },
    {
      title: "江苏政务服务",
      url: "https://www.jszwfw.gov.cn/",
      snippet: "省内通办、政策文件、办事窗口和 12345 咨询入口。",
    },
    {
      title: "12345 在线诉求",
      url: "https://12345.jszwfw.gov.cn/cns-bmfw-wsbsdt/index/pages/appeal/step2.html?type=2",
      snippet: "非紧急类政务咨询、投诉和求助可通过江苏 12345 提交诉求。",
    },
  ];
}

function isOfficialPolicySource(url = "") {
  const value = String(url || "").toLowerCase();
  return /(^|\/\/)([^/]*\.)?(gov\.cn|jiangsu\.gov\.cn|jszwfw\.gov\.cn|jurong\.gov\.cn|zhenjiang\.gov\.cn|moa\.gov\.cn|agri\.cn)(\/|$)/i.test(value);
}

function policySourceName(url = "") {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    if (host.includes("jurong.gov.cn")) return "江苏句容官方";
    if (host.includes("zj.jszwfw.gov.cn")) return "镇江政务";
    if (host.includes("jszwfw.gov.cn")) return "江苏政务";
    if (host.includes("nynct.jiangsu.gov.cn")) return "省农业农村厅";
    if (host.includes("moa.gov.cn") || host.includes("agri.cn")) return "农业农村部";
    return host;
  } catch {
    return "官方入口";
  }
}

function renderPolicyIntelligenceItems(results = []) {
  if (!policyIntelligenceList) return;
  const seeds = officialPolicySeedItems();
  const seedUrls = new Set(seeds.map((item) => String(item.url || "").toLowerCase().replace(/\/$/, "")));
  const official = (Array.isArray(results) ? results : [])
    .filter((item) => item?.title && item?.url && isOfficialPolicySource(item.url))
    .filter((item) => !seedUrls.has(String(item.url || "").toLowerCase().replace(/\/$/, "")))
    .slice(0, 2);
  const items = [...seeds.slice(0, 4), ...official].slice(0, 6);
  policyIntelligenceList.innerHTML = items
    .map((item) => {
      const title = escapeHtml(shorten(item.title || "政策入口", 34));
      const snippet = escapeHtml(shorten(item.snippet || "点击打开官方来源核验。", 58));
      const url = escapeHtml(item.url || "#");
      const source = escapeHtml(policySourceName(item.url || ""));
      return `<a class="policy-feed-item" href="${url}" target="_blank" rel="noopener">
        <span>${source}</span>
        <strong>${title}</strong>
        <em>${snippet}</em>
      </a>`;
    })
    .join("");
}

async function loadPolicyIntelligencePanel(options = {}) {
  if (!policyIntelligenceList) return;
  const production = locationContextState.productionLocation || productionLocationInput?.value.trim() || DEFAULT_PRODUCTION_LOCATION;
  policyIntelligenceList.innerHTML = '<div class="policy-feed-loading">正在聚合政策、咨询和维权入口...</div>';
  try {
    const payload = await fetchJson("/api/web/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: `${production} 江苏 农业农村 政策 补贴 项目申报 农资质量 收购纠纷 12345 12316 site:gov.cn OR site:jszwfw.gov.cn`,
        max_results: 8,
      }),
    });
    renderPolicyIntelligenceItems(payload.results || []);
  } catch (error) {
    renderPolicyIntelligenceItems([]);
    if (!options.quiet) showToast(`政策咨询聚合失败：${error.message}`, "error", 3200);
  }
}

async function handlePolicyActionClick(event) {
  const button = event.currentTarget;
  const query = button?.dataset?.policyQuery || "";
  if (!query || isGeneratingAnswer) return;
  await runRealtimeQuery(query, {
    displayQuery: button.textContent || "政策与维权咨询",
    triggerButton: button,
    topK: 7,
    useWebSearch: true,
    webSearchK: 7,
    regionalIntelligence: true,
  });
}

function renderFeatureSourceLinks(config) {
  return (config.sources || [])
    .map(([label, url]) => `<a href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(label)}</a>`)
    .join("");
}

async function loadCompetitionHeadlines(options = {}) {
  if (!competitionHeadlineCategories || competitionHeadlinesLoading) return;
  const force = Boolean(options.force);
  competitionHeadlinesLoading = true;
  refreshCompetitionHeadlines?.classList.add("loading");
  if (refreshCompetitionHeadlines) refreshCompetitionHeadlines.disabled = true;
  if (!lastCompetitionHeadlinesPayload) {
    competitionHeadlineCategories.innerHTML = '<div class="competition-loading">正在抓取专题头条...</div>';
    if (competitionTrendCard) competitionTrendCard.textContent = "正在生成趋势分析...";
  }
  try {
    const params = new URLSearchParams({
      location: DEFAULT_PRODUCTION_LOCATION,
    });
    if (force) params.set("force", "true");
    const payload = await fetchJson(`/api/competition/headlines?${params.toString()}`);
    lastCompetitionHeadlinesPayload = payload;
    renderCompetitionHeadlines(payload);
  } catch (error) {
    if (competitionHeadlineMeta) competitionHeadlineMeta.textContent = "专题聚合暂未返回";
    competitionHeadlineCategories.innerHTML = `<div class="competition-loading">专题头条加载失败：${escapeHtml(error.message)}</div>`;
  } finally {
    competitionHeadlinesLoading = false;
    refreshCompetitionHeadlines?.classList.remove("loading");
    if (refreshCompetitionHeadlines) refreshCompetitionHeadlines.disabled = false;
  }
}

function renderCompetitionHeadlines(payload = {}) {
  const categories = Array.isArray(payload.categories) ? payload.categories : [];
  const trend = payload.trend || {};
  if (competitionHeadlineMeta) {
    const updated = payload.updated_at ? `更新 ${payload.updated_at}` : "实时聚合";
    competitionHeadlineMeta.textContent = `${updated} · 分类滚动播放`;
  }
  if (competitionTrendCard) {
    const signals = Array.isArray(trend.signals) ? trend.signals : [];
    competitionTrendCard.innerHTML = `<div class="competition-trend-main">
      <span>${escapeHtml(trend.provider || "AI趋势分析")}</span>
      <strong>${escapeHtml(trend.summary || "正在聚合趋势。")}</strong>
    </div>
    ${signals.length ? `<ul>${signals.slice(0, 4).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}
    <div class="competition-trend-action">
      ${trend.opportunity ? `<p>${escapeHtml(trend.opportunity)}</p>` : ""}
      ${trend.action ? `<b>${escapeHtml(trend.action)}</b>` : ""}
    </div>
    ${trend.risk ? `<small>${escapeHtml(trend.risk)}</small>` : ""}`;
  }
  if (!competitionHeadlineCategories) return;
  competitionHeadlineCategories.innerHTML = categories.length
    ? categories.slice(0, 6).map((category, index) => renderCompetitionCategory(category, index)).join("")
    : '<div class="competition-loading">暂未聚合到专题头条，请稍后刷新。</div>';
}

function renderCompetitionCategory(category = {}, index = 0) {
  const items = dedupeCompetitionItems(Array.isArray(category.items) ? category.items : []).slice(0, 10);
  const renderItem = (item, itemIndex, duplicate = false) => {
        const title = escapeHtml(shorten(cleanCompetitionText(item.title || "专题头条"), 50));
        const snippetText = cleanCompetitionText(item.snippet || "");
        const snippet = snippetText ? `<p>${escapeHtml(shorten(snippetText, 86))}</p>` : "";
        const meta = [item.reason, item.source, item.published_at]
          .filter(Boolean)
          .map((part) => escapeHtml(shorten(cleanCompetitionText(part), 16)))
          .join(" · ");
        const url = String(item.url || "").trim();
        const body = `<span>${itemIndex + 1}</span><div><strong>${title}</strong>${snippet}<em>${meta}</em></div>`;
        const attrs = duplicate ? ' aria-hidden="true"' : "";
        return `<li${attrs}>${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${body}</a>` : `<button type="button" data-competition-headline="${escapeHtml(String(index))}-${escapeHtml(String(itemIndex))}">${body}</button>`}</li>`;
      };
  const itemHtml = items.length
    ? `${items.map((item, itemIndex) => renderItem(item, itemIndex)).join("")}${items.length > 3 ? items.map((item, itemIndex) => renderItem(item, itemIndex, true)).join("") : ""}`
    : '<li><div><strong>正在补充该类头条</strong><p>稍后刷新可获取更多公开信息。</p></div></li>';
  const duration = Math.max(24, items.length * 5);
  return `<article class="competition-category is-rolling" style="--competition-scroll-duration:${duration}s">
    <header>
      <span>${escapeHtml(cleanCompetitionText(category.label || "专题"))}</span>
      <em>${escapeHtml(shorten(cleanCompetitionText(category.focus || "农业创业相关"), 26))}</em>
    </header>
    <div class="competition-category-window">
      <ol>${itemHtml}</ol>
    </div>
  </article>`;
}

function cleanCompetitionText(value) {
  const wrongRegionNames = [
    ["江", "宁", "区"].join(""),
    ["南", "京", "句", "容"].join(""),
  ];
  let text = String(value || "");
  wrongRegionNames.forEach((name) => {
    text = text.replaceAll(name, "江苏句容");
  });
  return text
    .replaceAll("句容市", "江苏句容市")
    .replace(/江苏江苏句容/g, "江苏句容")
    .trim();
}

function dedupeCompetitionItems(items = []) {
  const seenUrls = new Set();
  const seenTitles = new Set();
  const output = [];
  for (const item of items) {
    const urlKey = String(item?.url || "").toLowerCase().replace(/[#?].*$/, "").replace(/\/$/, "");
    const titleKey = cleanCompetitionText(item?.title || "").replace(/^(农业创业|科技农业|青年人才|招商孵化|新媒体助农|政策资金)线索[:：]/, "");
    if ((urlKey && seenUrls.has(urlKey)) || (titleKey && seenTitles.has(titleKey))) continue;
    if (urlKey) seenUrls.add(urlKey);
    if (titleKey) seenTitles.add(titleKey);
    output.push(item);
  }
  return output;
}

function renderFeatureMetricCards(config) {
  return (config.metrics || [])
    .map(([label, value, status, tone], index) => `<button class="feature-metric-card is-${escapeHtml(tone || "ok")}" type="button" data-feature-detail="metric" data-feature-detail-index="${index}" aria-label="查看${escapeHtml(label)}详情">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <em>${escapeHtml(status)}</em>
    </button>`)
    .join("");
}

function renderFeatureExplainCards(config) {
  return (config.cards || [])
    .map(([title, body], index) => `<button class="feature-explain-card" type="button" data-feature-detail="card" data-feature-detail-index="${index}" aria-label="查看${escapeHtml(title)}详情">
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(body)}</p>
    </button>`)
    .join("");
}

function renderCropMonitoringVisual() {
  return `<div class="greenhouse-scene" aria-label="草莓大棚实时监测模拟">
    <div class="greenhouse-sky"><span></span><span></span><span></span></div>
    <div class="greenhouse-shell">
      <div class="greenhouse-roof"></div>
      <div class="greenhouse-frame"></div>
      <div class="greenhouse-bed">
        <i></i><i></i><i></i><i></i><i></i><i></i>
      </div>
      <div class="sensor-pulse pulse-a"></div>
      <div class="sensor-pulse pulse-b"></div>
      <div class="sensor-pulse pulse-c"></div>
    </div>
    <div class="greenhouse-device fan-device"></div>
    <div class="greenhouse-device lamp-device"></div>
  </div>
  <div class="crop-sensor-grid">
    <button class="crop-sensor-card is-ok" type="button" data-feature-detail="sensor" data-feature-detail-index="0" data-crop-sensor="temp"><span>棚温</span><strong data-crop-value="temp">25.8°C</strong><em data-crop-status="temp">达标</em></button>
    <button class="crop-sensor-card is-warn" type="button" data-feature-detail="sensor" data-feature-detail-index="1" data-crop-sensor="humidity"><span>空气湿度</span><strong data-crop-value="humidity">82%</strong><em data-crop-status="humidity">偏高</em></button>
    <button class="crop-sensor-card is-ok" type="button" data-feature-detail="sensor" data-feature-detail-index="2" data-crop-sensor="soil"><span>土壤湿度</span><strong data-crop-value="soil">66%</strong><em data-crop-status="soil">达标</em></button>
    <button class="crop-sensor-card is-warn" type="button" data-feature-detail="sensor" data-feature-detail-index="3" data-crop-sensor="light"><span>光照</span><strong data-crop-value="light">31 klux</strong><em data-crop-status="light">稍弱</em></button>
    <button class="crop-sensor-card is-ok" type="button" data-feature-detail="sensor" data-feature-detail-index="4" data-crop-sensor="ec"><span>EC</span><strong data-crop-value="ec">1.7</strong><em data-crop-status="ec">达标</em></button>
  </div>
  <div class="crop-action-strip">
    <strong data-crop-advice>建议：开顶窗 18 分钟，风机二档，补光 30 分钟，暂缓浇水。</strong>
    <span data-crop-time>正在同步...</span>
  </div>`;
}

function renderFeatureVisual(config, key) {
  if (key === "crop") return renderCropMonitoringVisual();
  const title = escapeHtml(config.title);
  if (config.type === "flow") {
    return `<div class="feature-flow-visual">
      <button type="button" data-feature-detail="visual" data-feature-detail-index="0"><strong>主体</strong><span>新农人/合作社</span></button><i></i>
      <button type="button" data-feature-detail="visual" data-feature-detail-index="1"><strong>地块</strong><span>作物/面积/设备</span></button><i></i>
      <button type="button" data-feature-detail="visual" data-feature-detail-index="2"><strong>订单</strong><span>收购/电商/物流</span></button><i></i>
      <button type="button" data-feature-detail="visual" data-feature-detail-index="3"><strong>政策</strong><span>申报/监管/补贴</span></button>
    </div>`;
  }
  if (config.type === "news") {
    return `<div class="feature-news-visual">
      <div class="news-orbit"><button type="button" data-feature-detail="visual" data-feature-detail-index="0">政策</button><button type="button" data-feature-detail="visual" data-feature-detail-index="1">气象</button><button type="button" data-feature-detail="visual" data-feature-detail-index="2">行情</button><button type="button" data-feature-detail="visual" data-feature-detail-index="3">收购</button></div>
      <ol>
        <li>江苏农业政策更新，优先核验申报对象</li>
        <li>未来 3 天降雨窗口影响采收运输</li>
        <li>目标市场询价先看分级和包装</li>
      </ol>
    </div>`;
  }
  if (config.type === "compare") {
    return `<div class="feature-radar-visual">
      <div class="radar-ring"><button type="button" data-feature-detail="visual" data-feature-detail-index="0">政策市场</button><button type="button" data-feature-detail="visual" data-feature-detail-index="1">地块管理</button><button type="button" data-feature-detail="visual" data-feature-detail-index="2">交易闭环</button><button type="button" data-feature-detail="visual" data-feature-detail-index="3">治理台账</button></div>
      <div class="score-bars"><button type="button" data-feature-detail="visual" data-feature-detail-index="4" style="--w:92%">政策市场</button><button type="button" data-feature-detail="visual" data-feature-detail-index="5" style="--w:76%">地块管理</button><button type="button" data-feature-detail="visual" data-feature-detail-index="6" style="--w:83%">交易闭环</button></div>
    </div>`;
  }
  if (config.type === "pitch") {
    return `<div class="feature-pitch-visual">
      <button type="button" data-feature-detail="visual" data-feature-detail-index="0"><span>痛点</span><strong>信息分散</strong></button>
      <button type="button" data-feature-detail="visual" data-feature-detail-index="1"><span>方案</span><strong>数智中枢</strong></button>
      <button type="button" data-feature-detail="visual" data-feature-detail-index="2"><span>落地</span><strong>县域样板</strong></button>
      <button type="button" data-feature-detail="visual" data-feature-detail-index="3"><span>商业</span><strong>服务+渠道</strong></button>
    </div>`;
  }
  if (config.type === "market") {
    return `<div class="feature-market-visual">
      <button class="market-bar" type="button" data-feature-detail="visual" data-feature-detail-index="0" style="--h:82%"><span>草莓</span></button>
      <button class="market-bar" type="button" data-feature-detail="visual" data-feature-detail-index="1" style="--h:58%"><span>福桃</span></button>
      <button class="market-bar" type="button" data-feature-detail="visual" data-feature-detail-index="2" style="--h:66%"><span>茶叶</span></button>
      <button class="market-bar" type="button" data-feature-detail="visual" data-feature-detail-index="3" style="--h:45%"><span>蔬菜</span></button>
      <strong>价格、损耗、账期、渠道一起算</strong>
    </div>`;
  }
  if (config.type === "weather") {
    return `<div class="feature-weather-visual">
      <button class="weather-sun" type="button" data-feature-detail="visual" data-feature-detail-index="0" aria-label="查看高温日照详情"></button><button class="weather-cloud" type="button" data-feature-detail="visual" data-feature-detail-index="1" aria-label="查看阴雨湿度详情"></button><button class="weather-rain" type="button" data-feature-detail="visual" data-feature-detail-index="2" aria-label="查看降雨风险详情"><i></i><i></i><i></i><i></i></button>
      <ul><li>今天：高湿，采后防潮</li><li>3天：雨前抢采</li><li>15天：温差管理</li></ul>
    </div>`;
  }
  if (config.type === "traceability") {
    return `<div class="feature-trace-visual">
      <button class="qr-mock" type="button" data-feature-detail="visual" data-feature-detail-index="0" aria-label="查看溯源码详情"></button>
      <div class="trace-chain"><button type="button" data-feature-detail="visual" data-feature-detail-index="1">地块</button><button type="button" data-feature-detail="visual" data-feature-detail-index="2">投入品</button><button type="button" data-feature-detail="visual" data-feature-detail-index="3">快检</button><button type="button" data-feature-detail="visual" data-feature-detail-index="4">订单</button></div>
    </div>`;
  }
  return `<div class="feature-policy-visual">
    <div class="policy-radar-center">${title.slice(0, 4)}</div>
    <button type="button" data-feature-detail="visual" data-feature-detail-index="0">对象</button><button type="button" data-feature-detail="visual" data-feature-detail-index="1">材料</button><button type="button" data-feature-detail="visual" data-feature-detail-index="2">窗口</button><button type="button" data-feature-detail="visual" data-feature-detail-index="3">部门</button>
  </div>`;
}

function featureVisualDetailText(config, key, index, label) {
  const type = config.type || key;
  const maps = {
    policy: [
      "先确认申报对象是否符合主体类型、经营规模和产业方向。",
      "材料要按证照、地块、台账、合同、发票、照片分组留存。",
      "窗口期决定今天先问、先备还是先提交，避免错过截止日。",
      "先找政策归口部门，再找乡镇窗口或政务服务入口核验流程。",
    ],
    flow: [
      "主体档案用于判断谁能申报、谁能交易、谁承担质量责任。",
      "地块信息要连到作物、面积、天气和投入品，方便后续监管和经营判断。",
      "订单要同时看价格、账期、损耗、物流和售后，不能只看单价。",
      "政策事项要和主体、地块、订单串起来，方便申报和复核。",
    ],
    news: [
      "政策类信息先看适用对象、申报时间、主管部门和材料清单。",
      "气象类信息直接转成采收、施肥、运输和棚室管理动作。",
      "行情类信息要对比本地市场、目标市场和全国参考价。",
      "收购类信息重点核验联系人、覆盖区域、账期和冷链条件。",
    ],
    compare: [
      "政策市场能力决定项目能否贴合江苏句容本地服务场景。",
      "地块管理能力决定后续是否能接入田间设备和作业记录。",
      "交易闭环能力决定农产品从询价到收款是否能真正跑通。",
      "治理台账能力决定农业管理部门能否看清主体、地块和产业进度。",
      "政策市场是当前强项，要继续做深政策、行情和渠道联动。",
      "地块管理需要逐步补齐地块档案、作业记录和设备数据。",
      "交易闭环要继续加强收购、物流、售后和电商订单联动。",
    ],
    pitch: [
      "路演先讲信息分散带来的错过政策、错卖价格和错判天气。",
      "方案要讲清一套入口如何同时回答政策、行情、气象和渠道问题。",
      "落地要讲清江苏句容样板如何扩展到更多县域农业场景。",
      "商业模式要同时覆盖服务订阅、渠道撮合、数据服务和政务场景。",
    ],
    market: [
      "草莓重点看鲜度、分级、损耗、雨前采收和礼盒/团购渠道。",
      "福桃重点看成熟度、包装、节庆销售和近场冷链。",
      "茶叶重点看等级、品牌、采摘批次和稳定采购方。",
      "蔬菜重点看日波动、周转速度、装车损耗和批发市场需求。",
    ],
    weather: [
      "日照和温度影响成熟速度、棚室通风和补光安排。",
      "阴雨和高湿会增加病害、霉变和采后损耗风险。",
      "降雨会影响采收、田间道路、装车时间和冷链调度。",
    ],
    traceability: [
      "溯源码要让采购方看到主体、批次、检测和订单去向。",
      "地块记录用于说明产地、作物、责任人和种植周期。",
      "投入品记录用于说明肥料、农药、用量和购买凭证。",
      "快检记录用于说明质量安全和进入市场前的核验结果。",
      "订单记录用于说明卖给谁、怎么运输、是否有售后反馈。",
    ],
    crop: [
      "棚温决定开窗、保温和通风节奏，先看是否超出适宜区间。",
      "空气湿度偏高时要优先通风降湿，防止灰霉病和采后霉变。",
      "土壤水分决定今天是否浇水，雨天和高湿时要谨慎。",
      "光照不足时可考虑补光，但要结合温度和棚内湿度。",
      "EC 用来观察水肥浓度，异常时先复测，再调整水肥。",
    ],
  };
  return (maps[type] || maps.policy)[index] || `${label}会影响${config.title}的判断，需要结合当天数据继续核验。`;
}

function buildFeatureDetail(kind, index, trigger = null) {
  const config = FEATURE_SHOWCASES[activeFeatureShowcaseKey] || FEATURE_SHOWCASES.crop;
  const safeIndex = Number.isFinite(index) ? index : 0;
  if (kind === "metric") {
    const [label = "指标", value = "待核验", status = "待判断"] = config.metrics?.[safeIndex] || [];
    return {
      kind,
      title: label,
      subtitle: `${value} · ${status}`,
      body: featureVisualDetailText(config, activeFeatureShowcaseKey, safeIndex, label),
      bullets: [
        `当前模块：${config.title}`,
        `先看${label}是否直接影响今天要不要行动。`,
        `再结合天气、行情、政策和目标市场判断先后顺序。`,
      ],
    };
  }
  if (kind === "card") {
    const [title = "步骤", body = "继续查看该步骤的细节。"] = config.cards?.[safeIndex] || [];
    return {
      kind,
      title,
      subtitle: config.title,
      body,
      bullets: [
        "把这一步拆成今天能做、明天复核、需要咨询的三类事项。",
        "需要留存的记录包括照片、台账、订单、票据或受理编号。",
        "执行前再核验本地天气、行情和政策窗口。",
      ],
    };
  }
  const label = (trigger?.innerText || trigger?.getAttribute?.("aria-label") || "详情").replace(/\s+/g, " ").trim();
  const value = trigger?.querySelector?.("strong")?.innerText || "";
  const status = trigger?.querySelector?.("em")?.innerText || "";
  return {
    kind,
    title: label || "详情",
    subtitle: [value, status, config.title].filter(Boolean).join(" · "),
    body: featureVisualDetailText(config, activeFeatureShowcaseKey, safeIndex, label || "详情"),
    bullets: [
      `所属模块：${config.title}`,
      "可继续让新农人助手结合政策、行情、天气、路线和当前模块一起分析。",
      "执行前保留现场记录，并核验来源页面或本地部门口径。",
    ],
  };
}

function renderFeatureDrilldown(detail = null) {
  const node = featureWorkbench?.querySelector("#featureDrilldown");
  if (!node) return;
  const config = FEATURE_SHOWCASES[activeFeatureShowcaseKey] || FEATURE_SHOWCASES.crop;
  const fallback = {
    title: "点一个模块继续看",
    subtitle: config.title,
    body: "点左侧图块、右侧指标或步骤卡片，可以展开更具体的判断、材料、风险和下一步动作。",
    bullets: ["所有卡片都可以继续点开。", "点“让新农人助手继续分析”，会自动聚合当前模块、天气、行情、路线和专题头条。"],
  };
  const data = detail || fallback;
  activeFeatureDetailState = detail;
  const bullets = (data.bullets || []).slice(0, 5).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  node.innerHTML = `<div>
      <span>${escapeHtml(data.subtitle || config.title)}</span>
      <strong>${escapeHtml(data.title || "详情")}</strong>
      <p>${escapeHtml(data.body || "继续查看该功能的细节。")}</p>
    </div>
    ${bullets ? `<ul>${bullets}</ul>` : ""}
    <button type="button" data-feature-detail-ask>让新农人助手继续分析</button>`;
}

function renderFeatureWorkbench(key) {
  if (!featureWorkbench) return;
  const config = FEATURE_SHOWCASES[key] || FEATURE_SHOWCASES.crop;
  featureWorkbench.innerHTML = `<div class="feature-workbench-head">
    <div>
      <p class="eyebrow">${escapeHtml(config.eyebrow)}</p>
      <h2>${escapeHtml(config.title)}</h2>
      <p>${escapeHtml(config.summary)}</p>
    </div>
    <div class="feature-workbench-actions">
      <span>${escapeHtml(config.status)}</span>
      <button type="button" data-feature-workbench-ask="${escapeHtml(key)}">新农人助手解读</button>
    </div>
  </div>
  <div class="feature-workbench-grid">
    <div class="feature-visual-panel">${renderFeatureVisual(config, key)}</div>
    <div class="feature-detail-panel">
      <div class="feature-metric-grid">${renderFeatureMetricCards(config)}</div>
      <div class="feature-explain-grid">${renderFeatureExplainCards(config)}</div>
      <div class="feature-source-row">${renderFeatureSourceLinks(config)}</div>
      <div id="featureDrilldown" class="feature-drilldown" aria-live="polite"></div>
    </div>
  </div>`;
  renderFeatureDrilldown();
}

function updateCropSensor(id, value, status, ok) {
  const card = featureWorkbench?.querySelector(`[data-crop-sensor="${id}"]`);
  const valueNode = featureWorkbench?.querySelector(`[data-crop-value="${id}"]`);
  const statusNode = featureWorkbench?.querySelector(`[data-crop-status="${id}"]`);
  if (valueNode) valueNode.textContent = value;
  if (statusNode) statusNode.textContent = status;
  if (card) {
    card.classList.toggle("is-ok", ok);
    card.classList.toggle("is-warn", !ok);
  }
}

function updateCropMonitoring() {
  if (activeFeatureShowcaseKey !== "crop" || !featureWorkbench) return;
  const t = Date.now();
  const temp = 25.4 + Math.sin(t / 4800) * 1.2;
  const humidity = Math.round(82 + Math.sin(t / 3600) * 7);
  const soil = Math.round(65 + Math.cos(t / 4200) * 5);
  const light = Math.round(32 + Math.sin(t / 5200) * 7);
  const ec = 1.65 + Math.cos(t / 6400) * 0.18;
  updateCropSensor("temp", `${temp.toFixed(1)}°C`, temp >= 18 && temp <= 28 ? "达标" : "需调整", temp >= 18 && temp <= 28);
  updateCropSensor("humidity", `${humidity}%`, humidity <= 78 ? "达标" : "偏高", humidity <= 78);
  updateCropSensor("soil", `${soil}%`, soil >= 55 && soil <= 72 ? "达标" : "需复核", soil >= 55 && soil <= 72);
  updateCropSensor("light", `${light} klux`, light >= 35 ? "达标" : "稍弱", light >= 35);
  updateCropSensor("ec", ec.toFixed(1), ec >= 1.3 && ec <= 2.0 ? "达标" : "需校准", ec >= 1.3 && ec <= 2.0);
  const advice = humidity > 78
    ? "建议：开顶窗 18 分钟，风机二档，补光 30 分钟，暂缓浇水。"
    : light < 35
      ? "建议：保持通风，补光 30 分钟，采收前复测湿度。"
      : "建议：当前大棚状态基本达标，继续记录批次和环境数据。";
  const adviceNode = featureWorkbench.querySelector("[data-crop-advice]");
  const timeNode = featureWorkbench.querySelector("[data-crop-time]");
  if (adviceNode) adviceNode.textContent = advice;
  if (timeNode) timeNode.textContent = `模拟监测 ${new Date().toLocaleTimeString("zh-CN", { hour12: false })}`;
}

function startCropMonitoringIfNeeded() {
  if (activeFeatureShowcaseKey !== "crop") {
    if (cropMonitoringTimer) window.clearInterval(cropMonitoringTimer);
    cropMonitoringTimer = 0;
    return;
  }
  updateCropMonitoring();
  if (!cropMonitoringTimer) cropMonitoringTimer = window.setInterval(updateCropMonitoring, 2600);
}

function openFeatureWorkbench(key = "crop", options = {}) {
  if (!featureWorkbench) return;
  const normalizedKey = FEATURE_SHOWCASES[key] ? key : "crop";
  activeFeatureShowcaseKey = normalizedKey;
  renderFeatureWorkbench(normalizedKey);
  document.querySelectorAll("[data-showcase-feature]").forEach((button) => {
    button.classList.toggle("active", button.dataset.showcaseFeature === normalizedKey);
  });
  startCropMonitoringIfNeeded();
  positionFloatingComposer();
  if (!options.silent) {
    featureWorkbench.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

async function askFeatureWorkbench(key, triggerButton = null) {
  const action = FEATURE_ACTIONS[key];
  const showcase = FEATURE_SHOWCASES[key];
  if (!action || !showcase) return;
  await runRealtimeQuery(action.query, {
    displayQuery: showcase.title,
    clearInput: true,
    triggerButton,
    topK: 7,
    useWebSearch: true,
    webSearchK: 7,
    regionalIntelligence: true,
  });
}

function buildFeatureDetailQuery() {
  const config = FEATURE_SHOWCASES[activeFeatureShowcaseKey] || FEATURE_SHOWCASES.crop;
  const detail = activeFeatureDetailState;
  if (!detail) {
    return `分析“${config.title}”模块，给出今天最值得执行的事项。`;
  }
  return `分析“${config.title}”模块里的“${detail.title}”，说明今天该怎么处理。`;
}

async function askActiveFeatureDetail(triggerButton = null) {
  const query = buildFeatureDetailQuery();
  await runRealtimeQuery(query, {
    displayQuery: activeFeatureDetailState?.title || (FEATURE_SHOWCASES[activeFeatureShowcaseKey] || {}).title || "模块详情",
    clearInput: true,
    triggerButton,
    topK: 8,
    useWebSearch: true,
    webSearchK: 8,
    regionalIntelligence: true,
  });
}

async function loadLocalLivePanel(options = {}) {
  if (!localNewsTrack && !localNewsList && !liveTemperature && !liveWeatherRisk && !weatherHorizonGrid) return;
  if (localLiveRefreshInFlight) {
    if (options.force) {
      pendingLocalLiveRefresh = true;
      pendingLocalLiveRefreshOptions = options;
    }
    return;
  }
  const quiet = Boolean(options.quiet);
  localLiveRefreshInFlight = true;
  try {
    syncLocationInputsFromState();
    if (!quiet) {
      if (localNewsTrack) localNewsTrack.textContent = "正在更新两地天气、农业新闻、收购和物流信息...";
      if (localNewsList) localNewsList.innerHTML = '<div class="local-news-empty">正在整理本地农业资讯...</div>';
      if (routeMarketPanel) routeMarketPanel.textContent = "正在同步产地、目标市场和运输路线...";
    }
    const params = appendLocationPointParams(new URLSearchParams({
      query: `${locationContextState.weatherLocation || DEFAULT_PRODUCTION_LOCATION} ${locationContextState.productionLocation} ${locationContextState.marketLocation} 农业 天气 气温 收购 政策 新闻 物流`,
      production_location: locationContextState.productionLocation || DEFAULT_PRODUCTION_LOCATION,
      market_location: locationContextState.marketLocation || DEFAULT_MARKET_LOCATION,
      weather_location: locationContextState.weatherLocation || DEFAULT_PRODUCTION_LOCATION,
    }));
    const payload = await fetchJson(`/api/regional/live?${params.toString()}`);
    locationContextState.latest = payload;
    if (payload.ip_location) locationContextState.ipLocation = payload.ip_location;
    saveLocationContextState();
    lastLocalLiveRefreshAt = Date.now();
    renderLocalLivePanel(payload);
    schedulePendingLogisticsRefresh(payload);
  } catch (error) {
    if (!quiet) {
      if (liveTemperature) liveTemperature.textContent = "天气暂未同步";
      if (liveWeatherRisk) liveWeatherRisk.textContent = "先按本地实际天气安排";
      if (weatherHorizonGrid) weatherHorizonGrid.innerHTML = '<div class="weather-horizon-empty">多日预报暂未同步，稍后点刷新。</div>';
      renderRouteMarketFallback(error);
      if (localNewsTrack) localNewsTrack.textContent = "新闻暂未同步，稍后点刷新重试。";
      if (localNewsList) localNewsList.innerHTML = '<div class="local-news-empty">资讯暂未同步，稍后点刷新重试。</div>';
    }
  } finally {
    localLiveRefreshInFlight = false;
    if (pendingLocalLiveRefresh) {
      const nextOptions = pendingLocalLiveRefreshOptions || { quiet: true, force: true };
      pendingLocalLiveRefresh = false;
      pendingLocalLiveRefreshOptions = null;
      window.setTimeout(() => loadLocalLivePanel(nextOptions), 0);
    }
  }
}

function schedulePendingLogisticsRefresh(payload = {}) {
  const suppliers = Array.isArray(payload.logistics_suppliers) ? payload.logistics_suppliers : [];
  const hasPending = suppliers.some((item) => item?.selected_by === ASSISTANT_PENDING_BY);
  if (!hasPending) {
    pendingLogisticsRefreshAttempts = 0;
    if (pendingLogisticsRefreshTimer) {
      window.clearTimeout(pendingLogisticsRefreshTimer);
      pendingLogisticsRefreshTimer = 0;
    }
    return;
  }
  if (pendingLogisticsRefreshTimer || pendingLogisticsRefreshAttempts >= 2) return;
  pendingLogisticsRefreshAttempts += 1;
  pendingLogisticsRefreshTimer = window.setTimeout(async () => {
    pendingLogisticsRefreshTimer = 0;
    await loadLocalLivePanel();
  }, 75000);
}

function renderLocalLivePanel(payload = {}) {
  const production = payload.production_location || payload.region || {};
  const market = payload.market_location || {};
  const weatherLocation = payload.weather_location || production || {};
  const weather = payload.weather || payload.production_weather || {};
  const marketWeather = payload.market_weather || {};
  const temp = weather.temperature_2m;
  const humidity = weather.relative_humidity_2m;
  const rain = Number(weather.precipitation || 0);
  const wind = Number(weather.wind_speed_10m || 0);
  const maxTemps = Array.isArray(weather.daily_temperature_2m_max) ? weather.daily_temperature_2m_max : [];
  const rains = Array.isArray(weather.daily_precipitation_sum) ? weather.daily_precipitation_sum : [];
  const horizons = Array.isArray(weather.weather_horizons) ? weather.weather_horizons : [];
  const nearTerm = horizons.find((item) => item?.id === "next3") || horizons.find((item) => item?.id === "today") || {};
  const productionName = production.short_name || production.name || locationContextState.productionLocation || "当前产地";
  const marketName = market.short_name || market.name || locationContextState.marketLocation || "目标市场";
  const weatherName = weatherLocation.short_name || weatherLocation.name || locationContextState.weatherLocation || DEFAULT_PRODUCTION_LOCATION;
  if (weatherPanelTitle) weatherPanelTitle.textContent = `${weatherName}实时提醒`;
  renderIpLocationStatus(payload.ip_location);
  if (liveTemperature) {
    const tempText = temp === undefined || temp === null ? `${weatherName}气温待更新` : `${weatherName} ${temp}°C`;
    const humidityText = humidity === undefined || humidity === null ? "" : ` · 湿度 ${humidity}%`;
    liveTemperature.textContent = `${tempText}${humidityText}`;
  }
  if (liveWeatherRisk) {
    const nearRain = Number(nearTerm.rain_max);
    const nearTemp = Number(nearTerm.temperature_max);
    const nextRain = Number.isFinite(nearRain) ? Math.max(rain, nearRain) : Math.max(rain, ...rains.slice(0, 3).map((item) => Number(item || 0)));
    const highTemp = Number.isFinite(nearTemp)
      ? nearTemp
      : maxTemps.length
        ? Math.max(...maxTemps.slice(0, 3).map((item) => Number(item || 0)))
        : null;
    const risk =
      nearTerm.risk_level && nearTerm.risk_level !== "low"
        ? shorten(nearTerm.risk || nearTerm.action || "天气有变化，请关注预报", 28)
        :
      nextRain > 8
        ? "有明显降雨，先抢采易损果菜"
        : wind > 28
          ? "风大，棚室和运输先加固"
          : highTemp !== null && highTemp >= 32
            ? "高温，采收避开中午"
            : "天气平稳，适合采收和发货";
    liveWeatherRisk.textContent = risk;
  }
  renderWeatherHorizonGrid(weather);
  renderRouteMarketPanel(payload, productionName, marketName, marketWeather);
  const newsSourceItems = [
    ...(payload.news_results || []),
    ...(payload.policy_results || []),
    ...(payload.market_results || []),
    ...(payload.ecommerce_channels || []),
  ];
  const tickerSourceItems = [...newsSourceItems, ...(payload.logistics_results || [])];
  const recommended = Array.isArray(payload.recommended_headlines) ? payload.recommended_headlines : [];
  latestHeadlineSourceItems = normalizeNewsItems([...tickerSourceItems, ...recommended]);
  const headlines = normalizeNewsItems(recommended.length ? recommended : tickerSourceItems).slice(0, 10);
  const originalNews = normalizeNewsItems(newsSourceItems).slice(0, 8);
  latestOriginalNewsItems = originalNews;
  const fallback = [{ title: `关注${productionName}政策、两地天气、${marketName}收购和物流时效。`, url: "", reason: "今日提醒" }];
  const news = headlines.length ? headlines : fallback;
  renderHeadlineTicker(news);
  renderLocalNewsList(originalNews.length ? originalNews : news);
}

function normalizeHeadlineItem(item = {}) {
  return {
    title: String(item.title || "").trim(),
    url: String(item.url || "").trim(),
    reason: String(item.reason || item.category || "推荐").trim(),
    source: String(item.source || "").trim(),
    snippet: String(item.snippet || "").trim(),
    published_at: String(item.published_at || item.date || "").trim(),
    category: String(item.category || "").trim(),
  };
}

function renderHeadlineTicker(items = []) {
  if (!localNewsTrack) return;
  latestHeadlineItems = normalizeNewsItems(items).map(normalizeHeadlineItem).slice(0, 12);
  if (!latestHeadlineItems.length) {
    localNewsTrack.textContent = "正在整理本地农业推荐信息...";
    return;
  }
  localNewsTrack.classList.toggle("is-refreshing", dynamicHeadlineRefreshInFlight);
  localNewsTrack.style.setProperty("--headline-scroll-duration", `${Math.max(30, latestHeadlineItems.length * 5)}s`);
  localNewsTrack.innerHTML = [...latestHeadlineItems, ...latestHeadlineItems]
    .map((item, index) => {
      const itemIndex = latestHeadlineItems.length ? index % latestHeadlineItems.length : 0;
      const title = escapeHtml(shorten(item.title, 42));
      const reason = escapeHtml(shorten(item.reason || "推荐", 12));
      const sourceText = headlineSourceLabel(item.source);
      const source = sourceText ? `<small>${escapeHtml(shorten(sourceText, 14))}</small>` : "";
      const url = String(item.url || "").trim();
      return url
        ? `<a class="headline-chip" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" aria-label="打开来源网页：${title}"><b>${reason}</b><span>${title}</span>${source}</a>`
        : `<button class="headline-chip" type="button" data-headline-index="${itemIndex}" aria-label="打开头条详情：${title}"><b>${reason}</b><span>${title}</span>${source}</button>`;
    })
    .join("");
}

function dynamicHeadlineQuery() {
  const production = locationContextState.productionLocation || DEFAULT_PRODUCTION_LOCATION;
  const market = locationContextState.marketLocation || DEFAULT_MARKET_LOCATION;
  const weather = locationContextState.weatherLocation || DEFAULT_PRODUCTION_LOCATION;
  const focus = [
    "政策 补贴 申报 三农",
    "行情 收购 价格 电商",
    "天气 降雨 采收 运输",
    "冷链 物流 到货 散货",
    "农资 农机 种苗 采购",
  ];
  const current = focus[dynamicHeadlineQueryIndex % focus.length];
  dynamicHeadlineQueryIndex += 1;
  return `${weather} ${production} ${market} ${current}`;
}

function rotateHeadlineItems(items = []) {
  if (!items.length) return [];
  headlineRotationOffset = (headlineRotationOffset + 1) % items.length;
  return items.slice(headlineRotationOffset).concat(items.slice(0, headlineRotationOffset));
}

async function refreshDynamicHeadlines(options = {}) {
  if (dynamicHeadlineRefreshInFlight) return;
  if (document.hidden && !options.force) return;
  const sourceItems = latestHeadlineSourceItems.length
    ? latestHeadlineSourceItems
    : latestHeadlineItems.concat(latestOriginalNewsItems);
  if (sourceItems.length < 3) {
    const stale = !lastLocalLiveRefreshAt || Date.now() - lastLocalLiveRefreshAt > 45 * 1000;
    if (stale) await loadLocalLivePanel({ quiet: true });
    return;
  }
  dynamicHeadlineRefreshInFlight = true;
  localNewsTrack?.classList.add("is-refreshing");
  try {
    const payload = await fetchJson("/api/headlines/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: dynamicHeadlineQuery(),
        production_location: locationContextState.productionLocation || DEFAULT_PRODUCTION_LOCATION,
        market_location: locationContextState.marketLocation || DEFAULT_MARKET_LOCATION,
        items: sourceItems.slice(0, 24),
        limit: 12,
      }),
    });
    const recommended = normalizeNewsItems(payload.headlines || []);
    const displayItems = rotateHeadlineItems(recommended.length ? recommended : sourceItems);
    renderHeadlineTicker(displayItems);
    renderLocalNewsList(latestOriginalNewsItems.length ? latestOriginalNewsItems : displayItems);
  } catch (error) {
    const displayItems = rotateHeadlineItems(sourceItems);
    renderHeadlineTicker(displayItems);
    renderLocalNewsList(latestOriginalNewsItems.length ? latestOriginalNewsItems : displayItems);
  } finally {
    dynamicHeadlineRefreshInFlight = false;
    localNewsTrack?.classList.remove("is-refreshing");
  }
}

function startDynamicRecommendationRefresh() {
  if (dynamicHeadlineTimer) window.clearInterval(dynamicHeadlineTimer);
  if (livePanelRefreshTimer) window.clearInterval(livePanelRefreshTimer);
  dynamicHeadlineTimer = window.setInterval(() => refreshDynamicHeadlines(), DYNAMIC_HEADLINE_REFRESH_MS);
  window.setTimeout(() => refreshDynamicHeadlines({ force: true }), 25 * 1000);
  livePanelRefreshTimer = window.setInterval(() => {
    if (document.hidden) return;
    loadLocalLivePanel({ quiet: true });
    loadMarketPricePanel();
    loadPolicyIntelligencePanel({ quiet: true });
  }, LIVE_PANEL_REFRESH_MS);
}

function renderWeatherHorizonGrid(weather = {}) {
  if (!weatherHorizonGrid) return;
  const horizons = Array.isArray(weather.weather_horizons) ? weather.weather_horizons : [];
  latestWeatherHorizons = horizons;
  weatherHorizonSlideIndex = clamp(weatherHorizonSlideIndex, 0, Math.max(0, horizons.length - 1));
  paintWeatherHorizonCarousel();
}

function paintWeatherHorizonCarousel() {
  if (!weatherHorizonGrid) return;
  const horizons = latestWeatherHorizons;
  if (!horizons.length) {
    weatherHorizonGrid.innerHTML = '<div class="weather-horizon-empty">多日预报同步中</div>';
    return;
  }
  const count = horizons.length;
  weatherHorizonSlideIndex = clamp(weatherHorizonSlideIndex, 0, count - 1);
  const current = horizons[weatherHorizonSlideIndex] || horizons[0] || {};
  weatherHorizonGrid.innerHTML = `
    <div class="weather-horizon-nav" aria-label="天气预报翻页">
      <button type="button" data-weather-slide="prev" aria-label="上一段天气">&lsaquo;</button>
      <div class="weather-horizon-page">
        <strong>${escapeHtml(current.label || "预报")}</strong>
        <span>${weatherHorizonSlideIndex + 1}/${count}</span>
      </div>
      <button type="button" data-weather-slide="next" aria-label="下一段天气">&rsaquo;</button>
    </div>
    <div class="weather-horizon-viewport" tabindex="0" role="region" aria-label="左右滑动查看不同时间段天气">
      <div class="weather-horizon-track" style="transform: translateX(-${weatherHorizonSlideIndex * 100}%);">
        ${horizons.map(renderWeatherHorizonCard).join("")}
      </div>
    </div>
    <div class="weather-horizon-dots" aria-label="天气预报页码">
      ${horizons
        .map((item, index) => {
          const active = index === weatherHorizonSlideIndex ? " is-active" : "";
          return `<button type="button" class="weather-horizon-dot${active}" data-weather-dot="${index}" aria-label="查看${escapeHtml(item.label || `第${index + 1}段`)}"></button>`;
        })
        .join("")}
    </div>`;
}

function renderWeatherHorizonCard(item, index) {
  const levelClass = weatherRiskClass(item.risk_level);
  const tempText = weatherTemperatureText(item);
  const rainText = formatWeatherNumber(item.rain_sum, "mm");
  const windText = formatWeatherNumber(item.wind_max, "km/h");
  const probability = Number(item.rain_probability_max);
  const probabilityText = Number.isFinite(probability) ? ` · 降雨概率 ${Math.round(probability)}%` : "";
  const action = escapeHtml(shorten(item.action || item.risk || "按当地实况安排生产。", 54));
  const hidden = index === weatherHorizonSlideIndex ? "false" : "true";
  return `<article class="weather-horizon-card ${levelClass}" aria-hidden="${hidden}">
    <div class="weather-horizon-top">
      <strong>${escapeHtml(item.label || "预报")}</strong>
      <span>${escapeHtml(item.confidence || "预报")}</span>
    </div>
    <p>${escapeHtml(item.date_range || "")}</p>
    <b>${escapeHtml(tempText)}</b>
    <small>降雨 ${escapeHtml(rainText)} · 风 ${escapeHtml(windText)}${escapeHtml(probabilityText)}</small>
    <em>${action}</em>
  </article>`;
}

function moveWeatherHorizonSlide(delta) {
  const count = latestWeatherHorizons.length;
  if (!count) return;
  weatherHorizonSlideIndex = (weatherHorizonSlideIndex + delta + count) % count;
  paintWeatherHorizonCarousel();
}

function jumpWeatherHorizonSlide(index) {
  const count = latestWeatherHorizons.length;
  if (!count) return;
  weatherHorizonSlideIndex = clamp(Number(index) || 0, 0, count - 1);
  paintWeatherHorizonCarousel();
}

function handleWeatherHorizonClick(event) {
  const target = event.target instanceof Element ? event.target : null;
  const slideButton = target?.closest("[data-weather-slide]");
  if (slideButton) {
    moveWeatherHorizonSlide(slideButton.dataset.weatherSlide === "next" ? 1 : -1);
    return;
  }
  const dotButton = target?.closest("[data-weather-dot]");
  if (dotButton) jumpWeatherHorizonSlide(dotButton.dataset.weatherDot);
}

function handleWeatherHorizonKeydown(event) {
  if (!event.target?.closest?.(".weather-horizon-viewport")) return;
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    moveWeatherHorizonSlide(-1);
  }
  if (event.key === "ArrowRight") {
    event.preventDefault();
    moveWeatherHorizonSlide(1);
  }
}

function handleWeatherHorizonTouchStart(event) {
  weatherHorizonTouchStartX = event.changedTouches?.[0]?.clientX || 0;
}

function handleWeatherHorizonTouchEnd(event) {
  const endX = event.changedTouches?.[0]?.clientX || 0;
  const delta = endX - weatherHorizonTouchStartX;
  if (Math.abs(delta) < 38) return;
  moveWeatherHorizonSlide(delta < 0 ? 1 : -1);
}

function weatherRiskClass(level) {
  if (level === "high") return "weather-risk-high";
  if (level === "medium") return "weather-risk-medium";
  return "weather-risk-low";
}

function weatherTemperatureText(item = {}) {
  const minTemp = Number(item.temperature_min);
  const maxTemp = Number(item.temperature_max);
  if (Number.isFinite(minTemp) && Number.isFinite(maxTemp)) return `${Math.round(minTemp)}-${Math.round(maxTemp)}°C`;
  if (Number.isFinite(maxTemp)) return `最高 ${Math.round(maxTemp)}°C`;
  return "温度待更新";
}

function formatWeatherNumber(value, unit) {
  const number = Number(value);
  if (!Number.isFinite(number)) return `0 ${unit}`;
  const rounded = Math.abs(number) >= 10 ? Math.round(number) : Math.round(number * 10) / 10;
  return `${rounded} ${unit}`;
}

function normalizeNewsItems(items = []) {
  return items
    .map((item) => ({
      title: cleanNewsDisplayText(item.title || item.snippet || ""),
      url: item.url || "",
      reason: item.reason || item.category || "推荐",
      source: item.source || "",
      snippet: cleanNewsDisplayText(item.snippet || item.summary || item.description || ""),
      published_at: item.published_at || item.date || item.time || "",
      category: item.category || "",
    }))
    .filter((item) => item.title)
    .map((item) => ({
      title: String(item.title || "").trim(),
      url: String(item.url || "").trim(),
      reason: String(item.reason || item.category || "推荐").trim(),
      source: String(item.source || "").trim(),
      snippet: String(item.snippet || "").trim(),
      published_at: String(item.published_at || "").trim(),
      category: String(item.category || "").trim(),
    }));
}

function cleanNewsDisplayText(value) {
  return String(value || "")
    .replace(/https?:\/\/\S+/gi, " ")
    .replace(/\b(?:www\.)?[\w.-]+\.(?:com|cn|gov|org|net|edu)(?:\/[^\s]*)?/gi, " ")
    .replace(/\s*[›>]\s*/g, " ")
    .replace(/\b[a-z]{2,24}\s*[-–]\s*/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function renderLocalNewsList(items = []) {
  if (!localNewsList) return;
  if (!items.length) {
    localNewsList.innerHTML = '<div class="local-news-empty">暂无可展示的本地农业资讯。</div>';
    return;
  }
  const startIndex = latestHeadlineItems.length;
  const visibleItems = items.slice(0, 6);
  latestHeadlineItems = latestHeadlineItems.concat(visibleItems);
  localNewsList.innerHTML = visibleItems
    .map((item, offset) => {
      const itemIndex = startIndex + offset;
      const title = escapeHtml(shorten(item.title, 46));
      const source = headlineSourceLabel(item.source);
      const meta = [item.reason || item.category || "资讯", source, item.published_at].filter(Boolean).map((part) => escapeHtml(shorten(part, 18))).join(" · ");
      const snippetText = item.snippet && item.snippet !== item.title ? item.snippet : "点开查看这条资讯对生产、销售、政策或运输安排的影响。";
      const snippet = escapeHtml(shorten(snippetText, 92));
      const url = String(item.url || "").trim();
      const body = `<span class="local-news-meta">${meta}</span><strong>${title}</strong><p>${snippet}</p><span class="local-news-open">${url ? "查看来源" : "查看详情"}</span>`;
      return url
        ? `<a class="local-news-item" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" aria-label="打开来源网页：${title}">${body}</a>`
        : `<button class="local-news-item" type="button" data-headline-index="${itemIndex}" aria-label="打开资讯详情：${title}">${body}</button>`;
    })
    .join("");
}

function headlineSourceLabel(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (/^(search_entry|web_search|news)$/i.test(text) || /^curated_/i.test(text)) return "";
  return text;
}

function ensureHeadlineDetailOverlay() {
  let overlay = document.querySelector("#headlineDetailOverlay");
  if (overlay) return overlay;
  overlay = document.createElement("div");
  overlay.id = "headlineDetailOverlay";
  overlay.className = "headline-detail-overlay hidden";
  overlay.innerHTML = `
    <article class="headline-detail-dialog" role="dialog" aria-modal="true" aria-labelledby="headlineDetailTitle">
      <div class="headline-detail-head">
        <strong id="headlineDetailTitle">头条详情</strong>
        <button id="closeHeadlineDetail" class="icon-button" type="button" aria-label="关闭头条详情">×</button>
      </div>
      <div id="headlineDetailBody" class="headline-detail-body"></div>
    </article>`;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const askButton = target.closest("[data-headline-ask]");
    if (askButton) {
      askAboutHeadline(askButton.getAttribute("data-headline-ask"));
      return;
    }
    if (target.closest("#closeHeadlineDetail")) {
      closeHeadlineDetail();
      return;
    }
    const justOpened = window.performance.now() - headlineDetailOpenedAt < 450;
    if (target === overlay && !justOpened) closeHeadlineDetail();
  });
  return overlay;
}

function openHeadlineDetail(index) {
  const item = latestHeadlineItems[Number(index)];
  if (!item) return;
  const overlay = ensureHeadlineDetailOverlay();
  const body = overlay.querySelector("#headlineDetailBody");
  const source = headlineSourceLabel(item.source);
  const reason = item.reason || item.category || "今日提醒";
  const title = item.title || "农业头条";
  const detail =
    item.snippet ||
    "这条信息来自实时聚合和本地场景推荐，可作为今天生产、销售、政策查询或运输安排的参考线索。";
  const meta = [source ? `来源：${source}` : "", item.published_at ? `时间：${item.published_at}` : ""]
    .filter(Boolean)
    .join(" · ");
  body.innerHTML = `
    <div class="headline-detail-tag">${escapeHtml(shorten(reason, 18))}</div>
    <h3>${escapeHtml(title)}</h3>
    <p>${escapeHtml(detail)}</p>
    ${meta ? `<div class="headline-detail-meta">${escapeHtml(meta)}</div>` : ""}
    <div class="headline-detail-actions">
      <button class="secondary-button" type="button" data-headline-ask="${escapeHtml(String(index))}">围绕这条咨询</button>
    </div>`;
  overlay.classList.remove("hidden");
  document.body.classList.add("headline-detail-open");
  headlineDetailOpenedAt = window.performance.now();
  overlay.querySelector("#closeHeadlineDetail")?.focus();
}

function closeHeadlineDetail() {
  const overlay = document.querySelector("#headlineDetailOverlay");
  if (!overlay) return;
  overlay.classList.add("hidden");
  document.body.classList.remove("headline-detail-open");
}

function askAboutHeadline(index) {
  const item = latestHeadlineItems[Number(index)];
  if (!item || !queryInput) return;
  queryInput.value = `这条资讯对今天生产经营有什么影响：${item.title}`;
  closeHeadlineDetail();
  queryInput.focus();
  showToast("已放入提问框，可以继续补充或直接发送。", "success", 2200);
}

function handleHeadlineChipActivation(event) {
  const target = event.target;
  if (!(target instanceof Element)) return false;
  const chip = target.closest("#localNewsTrack [data-headline-index], #localNewsList [data-headline-index]");
  if (!chip) return false;
  event.preventDefault();
  event.stopPropagation();
  openHeadlineDetail(chip.getAttribute("data-headline-index"));
  return true;
}

function renderIpLocationStatus(ipLocation = null) {
  if (!ipLocationStatus) return;
  const location = ipLocation || locationContextState.ipLocation;
  if (!location?.short_name && !location?.name) {
    ipLocationStatus.textContent = "IP定位待检测";
    return;
  }
  const ip = location.ip ? ` · ${location.ip}` : "";
  ipLocationStatus.textContent = `IP定位：${location.short_name || location.name}${ip}`;
}

function localRouteDistanceKm(a, b) {
  const lat1 = Number(a?.lat);
  const lon1 = Number(a?.lon);
  const lat2 = Number(b?.lat);
  const lon2 = Number(b?.lon);
  if (![lat1, lon1, lat2, lon2].every(Number.isFinite)) return null;
  const toRad = (value) => (value * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const s1 = Math.sin(dLat / 2) ** 2;
  const s2 = Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  const straight = 6371 * 2 * Math.atan2(Math.sqrt(s1 + s2), Math.sqrt(1 - s1 - s2));
  const factor = straight < 8 ? 1.55 : straight < 35 ? 1.38 : straight < 120 ? 1.25 : 1.18;
  return Math.round(straight * factor * 10) / 10;
}

function localRouteGrade(distanceKm, durationMinutes) {
  if (!distanceKm || !durationMinutes) return "本地估算";
  if (distanceKm <= 15 && durationMinutes <= 35) return "短途快销";
  if (distanceKm <= 80 && durationMinutes <= 120) return "半日达";
  if (distanceKm <= 180) return "当日达";
  return "长途冷链";
}

function buildLocalRouteFallbackPayload(error = null) {
  const productionPoint = normalizeMapPoint(locationContextState.productionPoint) || DEFAULT_MAP_POINTS.production;
  const marketPoint = normalizeMapPoint(locationContextState.marketPoint) || DEFAULT_MAP_POINTS.market;
  const productionName = productionLocationInput?.value.trim() || locationContextState.productionLocation || productionPoint.label || DEFAULT_PRODUCTION_LOCATION;
  const marketName = marketLocationInput?.value.trim() || locationContextState.marketLocation || marketPoint.label || DEFAULT_MARKET_LOCATION;
  const distanceKm = localRouteDistanceKm(productionPoint, marketPoint);
  const speed = distanceKm && distanceKm < 8 ? 28 : distanceKm && distanceKm < 35 ? 42 : distanceKm && distanceKm < 120 ? 58 : 68;
  const duration = distanceKm ? Math.max(1, Math.round((distanceKm / speed) * 60)) : null;
  const grade = localRouteGrade(distanceKm, duration);
  const midLat = Number.isFinite(Number(productionPoint.lat)) && Number.isFinite(Number(marketPoint.lat)) ? (Number(productionPoint.lat) + Number(marketPoint.lat)) / 2 : null;
  const midLon = Number.isFinite(Number(productionPoint.lon)) && Number.isFinite(Number(marketPoint.lon)) ? (Number(productionPoint.lon) + Number(marketPoint.lon)) / 2 : null;
  const corridor = `${productionName} → 沿途乡镇集配点 → ${marketName}`;
  return {
    route: {
      distance_km: distanceKm,
      duration_minutes: duration,
      source: "前端本地兜底规划",
      route_grade: grade,
      confidence: `实时接口暂时不稳，已按地图两点坐标本地估算；${error?.message ? `后台提示：${error.message}` : "仍建议出发前核对道路和到货口。"}`,
      corridor,
      map_url: `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${productionPoint.lat}%2C${productionPoint.lon}%3B${marketPoint.lat}%2C${marketPoint.lon}`,
      route_plan: {
        depart_window: distanceKm && distanceKm < 25 ? "上午采上午卖，保留小批量机动货" : "先锁收购价，再按到货时段装车",
        packing: "散货用周转筐，精品货分级装箱并防压防潮",
        transport: distanceKm && distanceKm > 120 ? "优先冷链或保温车，避开中午高温" : "短驳或同城配送，装车前确认卸货口",
        checkpoint: "确认联系人、到货时段、退货规则和付款方式。",
      },
      waypoints: [
        { name: productionName, role: "产地装车点", lat: productionPoint.lat, lon: productionPoint.lon },
        { name: "沿途乡镇集配点", role: "中途补给/散货试销点", lat: midLat, lon: midLon },
        { name: marketName, role: "目标市场交货点", lat: marketPoint.lat, lon: marketPoint.lon },
      ].filter((item) => Number.isFinite(Number(item.lat)) && Number.isFinite(Number(item.lon))),
      sales_advice: [
        {
          title: "产地周边先试价",
          where: `${productionName}周边社区、合作社门口、乡镇集市`,
          what: "成熟度高、耐压一般的散货先就近消化",
          how: "控制在总货量10%-15%，不影响已锁定订单。",
          risk: "不要把精品货拆成散货低价卖。",
        },
        {
          title: "中途预约取货",
          where: corridor,
          what: "适合社区团长、小店补货、单位团购",
          how: "出车前发图片、箱规和价格，到点即取，停留不超过20分钟。",
          risk: "中途停留太久会升温和误点。",
        },
        {
          title: "到场前再分流",
          where: `${marketName}周边批发档口、团购仓、电商前置仓`,
          what: "精品走议价，普通货走快销，尾货走加工或团购",
          how: `车程约${duration || "待核"}分钟，到货前30分钟二次确认档口价。`,
          risk: "先确认账期和退货规则。",
        },
      ],
    },
    market_recommendation: `已按地图两点规划：${productionName}到${marketName}${distanceKm ? `约${distanceKm}公里` : ""}。先定价锁单，再安排采收、分级、散货分流和装车。`,
    logistics_suppliers: [],
  };
}

function renderRouteMarketFallback(error = null) {
  if (!routeMarketPanel) return;
  const fallback = buildLocalRouteFallbackPayload(error);
  const productionName = productionLocationInput?.value.trim() || locationContextState.productionLocation || DEFAULT_PRODUCTION_LOCATION;
  const marketName = marketLocationInput?.value.trim() || locationContextState.marketLocation || DEFAULT_MARKET_LOCATION;
  renderRouteMarketPanel(fallback, productionName, marketName, {});
}

function renderRouteMarketPanel(payload = {}, productionName = "当前产地", marketName = "目标市场", marketWeather = {}) {
  if (!routeMarketPanel) return;
  const route = payload.route || {};
  const suppliers = Array.isArray(payload.logistics_suppliers) ? payload.logistics_suppliers : [];
  const routePlan = route.route_plan || {};
  const salesAdvice = Array.isArray(route.sales_advice) ? route.sales_advice : [];
  const waypoints = Array.isArray(route.waypoints) ? route.waypoints : [];
  const recommendation = payload.market_recommendation || `先确认${marketName}收购价，再安排采收和装车。`;
  const distance = route.distance_km ? `${route.distance_km} km` : "距离待估算";
  const duration = route.duration_minutes ? `${route.duration_minutes} 分钟` : "车程待估算";
  const marketTemp = marketWeather.temperature_2m === undefined || marketWeather.temperature_2m === null ? "市场天气待更新" : `${marketName} ${marketWeather.temperature_2m}°C`;
  const marketRain = marketWeather.precipitation === undefined || marketWeather.precipitation === null ? "" : ` · 降水 ${marketWeather.precipitation}mm`;
  const mapUrl = route.map_url || "";
  const marketUrl = route.market_source_url || "";
  const supplierStatus = suppliers.some((item) => item.selected_by === ASSISTANT_SELECTED_BY)
    ? "供应商已筛选"
    : suppliers.length
      ? "供应商核验中"
      : "暂无供应商";
  const supplierHtml = suppliers.length
    ? `<div class="supplier-card-list">${suppliers
        .slice(0, 4)
        .map((item) => {
          const url = String(item.url || "").trim();
          const tags = Array.isArray(item.service_tags) ? item.service_tags.slice(0, 3) : [];
          const statusText =
            item.selected_by === ASSISTANT_SELECTED_BY
              ? "新农人助手已筛选"
              : item.selected_by === ASSISTANT_PENDING_BY
                ? "新农人助手核验中"
                : "来源待核实";
          return `
            <article class="supplier-card">
              <div class="supplier-card-head">
                <strong>${escapeHtml(shorten(item.name || "冷链物流供应商", 34))}</strong>
                <span>${escapeHtml(item.platform || item.reliability || "公开来源")}</span>
              </div>
              <p>${escapeHtml(item.service_scope || item.reason || "需核实线路、温控和报价。")}</p>
              <div class="supplier-meta">
                <span>${escapeHtml(item.contact_method || item.contact || "平台在线联系/询价")}</span>
                ${tags.map((tag) => `<b>${escapeHtml(tag)}</b>`).join("")}
              </div>
              <div class="supplier-actions">
                ${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">查看来源</a>` : ""}
                <small>${escapeHtml(statusText)}</small>
              </div>
            </article>`;
        })
        .join("")}</div>`
    : `<div class="supplier-empty">暂未筛到可核实的公开冷链供应商。请刷新或换一个目标市场，系统不会编造电话。</div>`;
  const waypointHtml = waypoints.length
    ? `<div class="route-waypoints">${waypoints
        .slice(0, 4)
        .map((item) => `<span><b>${escapeHtml(shorten(item.name || item.role || "节点", 18))}</b><small>${escapeHtml(item.role || "路线节点")}</small></span>`)
        .join("")}</div>`
    : "";
  const routePlanHtml = routePlan && Object.keys(routePlan).length
    ? `<div class="route-plan-grid">
        <article><span>发车</span><strong>${escapeHtml(routePlan.depart_window || "按采收窗口发车")}</strong></article>
        <article><span>包装</span><strong>${escapeHtml(routePlan.packing || "按等级分箱防压")}</strong></article>
        <article><span>运输</span><strong>${escapeHtml(routePlan.transport || "先确认到货时段")}</strong></article>
        <article><span>交付</span><strong>${escapeHtml(routePlan.checkpoint || "确认价格、联系人和付款方式")}</strong></article>
      </div>`
    : "";
  const salesAdviceHtml = salesAdvice.length
    ? `<div class="route-sales-advice">
        <div class="supplier-section-title">沿途散货售卖建议</div>
        ${salesAdvice
          .slice(0, 3)
          .map((item) => `<article>
            <strong>${escapeHtml(item.title || "散货建议")}</strong>
            <span>${escapeHtml(item.where || "")}</span>
            <p>${escapeHtml(item.what || item.how || "")}</p>
            <em>${escapeHtml(item.how || "")}</em>
            ${item.risk ? `<small>${escapeHtml(item.risk)}</small>` : ""}
          </article>`)
          .join("")}
      </div>`
    : "";
  routeMarketPanel.innerHTML = `
    <div class="route-map-mini" aria-hidden="true">
      <span class="route-dot route-origin"></span>
      <span class="route-line"></span>
      <span class="route-dot route-destination"></span>
      <b>${escapeHtml(productionName)}</b>
      <strong>${escapeHtml(marketName)}</strong>
    </div>
    <div class="route-market-copy">
      <div class="route-market-stats">
        <span>${escapeHtml(distance)}</span>
        <span>${escapeHtml(duration)}</span>
        <span>${escapeHtml(route.route_grade || "路线已规划")}</span>
        <span>${escapeHtml(marketTemp + marketRain)}</span>
      </div>
      <div class="route-collapsed-note">${escapeHtml(route.corridor || `${productionName} → ${marketName}`)}：路线、冷链、沿途散货点和交付动作已整理。</div>
      <details class="route-market-details">
        <summary>
          <span>查看路线、散货与冷链详情</span>
          <small>${escapeHtml(supplierStatus)}</small>
        </summary>
        <div class="route-market-detail-body">
          <p>${escapeHtml(recommendation)}</p>
          ${waypointHtml}
          ${routePlanHtml}
          ${salesAdviceHtml}
          <div class="route-market-links">
            ${mapUrl ? `<a href="${escapeHtml(mapUrl)}" target="_blank" rel="noopener noreferrer">打开路线图</a>` : ""}
            ${marketUrl ? `<a href="${escapeHtml(marketUrl)}" target="_blank" rel="noopener noreferrer">查看行情来源</a>` : ""}
          </div>
          ${route.confidence ? `<div class="route-confidence">${escapeHtml(route.confidence)}</div>` : ""}
          <div class="supplier-section-title">新农人助手实时筛选的冷链与配送供应商</div>
          ${supplierHtml}
        </div>
      </details>
    </div>`;
}

function initMarketPriceControls() {
  if (!marketPriceCategory || !marketPricePreset || !marketPriceInput) return;
  marketPriceCategory.value = marketPriceCategory.value || "produce";
  renderMarketPricePresetOptions();
}

function renderMarketPricePresetOptions() {
  if (!marketPriceCategory || !marketPricePreset) return;
  const category = marketPriceCategory.value || "produce";
  const presets = MARKET_PRICE_CATEGORY_OPTIONS[category] || MARKET_PRICE_CATEGORY_OPTIONS.produce;
  marketPricePreset.innerHTML = presets.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`).join("");
  if (marketProductPresetList) {
    marketProductPresetList.innerHTML = presets.map((item) => `<option value="${escapeHtml(item)}"></option>`).join("");
  }
  if (!marketPriceInput?.value.trim() || !presets.includes(marketPriceInput.value.trim())) {
    marketPriceInput.value = presets[0] || "";
  }
}

async function loadMarketPricePanel(options = {}) {
  if (!marketPriceRows || !marketPriceInput || marketPriceLoading) return;
  updateLocationContextFromInputs();
  const product = String(options.product || marketPriceInput.value || "").trim() || "草莓";
  const category = marketPriceCategory?.value || "produce";
  const includeAi = Boolean(options.includeAi);
  if (marketPriceInput && marketPriceInput.value.trim() !== product) marketPriceInput.value = product;
  marketPriceLoading = true;
  refreshMarketPrice?.classList.add("loading");
  if (refreshMarketPrice) refreshMarketPrice.disabled = true;
  marketPriceTableWrap?.classList.remove("is-local-loop");
  marketPriceRows?.classList.remove("market-price-loop");
  marketPriceRows.innerHTML = includeAi
    ? `<tr><td colspan="6">正在为“${escapeHtml(product)}”查询行情并生成建议...</td></tr>`
    : '<tr><td colspan="6">正在查询公开行情...</td></tr>';
  if (marketPriceDecision) marketPriceDecision.textContent = includeAi ? "正在读取价格表，并调用新农人助手生成实时建议。" : "正在读取价格表、公开行情和来源页。";
  if (marketPriceInsight) {
    marketPriceInsight.classList.toggle("loading", includeAi);
    marketPriceInsight.innerHTML = includeAi
      ? `<strong>${escapeHtml(product)}</strong><p>正在生成行情小结和经营建议...</p>`
      : "点表格里的品名，可查看行情小结和实时建议。";
  }
  try {
    const params = new URLSearchParams({
      product,
      category,
      production_location: locationContextState.productionLocation || DEFAULT_PRODUCTION_LOCATION,
      market_location: locationContextState.marketLocation || DEFAULT_MARKET_LOCATION,
    });
    if (includeAi) params.set("include_ai", "true");
    const payload = await fetchJson(`/api/market/prices?${params.toString()}`);
    renderMarketPricePanel(payload, { showInsight: includeAi });
  } catch (error) {
    marketPriceRows.innerHTML = `<tr><td colspan="6">${escapeHtml(`查询失败：${error.message}`)}</td></tr>`;
    if (marketPriceDecision) marketPriceDecision.textContent = "行情暂未返回，稍后重试或换一个品名。";
    if (marketPriceInsight) {
      marketPriceInsight.classList.remove("loading");
      marketPriceInsight.textContent = "暂时没有生成建议，请稍后再点一次品名。";
    }
  } finally {
    marketPriceLoading = false;
    refreshMarketPrice?.classList.remove("loading");
    if (refreshMarketPrice) refreshMarketPrice.disabled = false;
  }
}

function renderMarketPricePanel(payload = {}, options = {}) {
  lastMarketPricePayload = payload;
  const rows = Array.isArray(payload.price_rows) ? payload.price_rows : [];
  const localRows = Array.isArray(payload.local_price_rows) ? payload.local_price_rows : [];
  const displayRows = localRows.length ? localRows : rows;
  const sources = Array.isArray(payload.source_cards) ? payload.source_cards : [];
  if (marketPriceDecision) {
    const time = payload.updated_at ? ` · ${payload.updated_at}` : "";
    const ontology = payload.ontology_record || {};
    const ontologyText = ontology.status === "persisted" ? ` · 已沉淀到本体库：${ontology.node_label || payload.product || "当前品类"}` : "";
    const localText = payload.local_price_note ? ` · ${payload.local_price_note}` : "";
    marketPriceDecision.textContent = `${payload.decision || "已返回行情线索。"}${time}${localText}${ontologyText}`;
  }
  if (marketPriceRows) {
    const visibleRows = displayRows.slice(0, 12);
    const shouldLoop = localRows.length > 3;
    marketPriceRows.classList.toggle("market-price-loop", shouldLoop);
    marketPriceTableWrap?.classList.toggle("is-local-loop", shouldLoop);
    if (shouldLoop) {
      marketPriceRows.style.setProperty("--market-loop-duration", `${Math.max(32, visibleRows.length * 4)}s`);
    } else {
      marketPriceRows.style.removeProperty("--market-loop-duration");
    }
    const loopRows = shouldLoop ? [...visibleRows, ...visibleRows] : visibleRows;
    marketPriceRows.innerHTML = loopRows.length
      ? loopRows.map((row) => renderMarketPriceRow(row, payload)).join("")
      : `<tr><td colspan="6">没有可直接采信的价格表，请查看下方来源页或换一个品名。</td></tr>`;
  }
  if (marketPriceSources) {
    marketPriceSources.innerHTML = sources.length
      ? sources
          .slice(0, 5)
          .map((source) => {
            const url = String(source.url || "").trim();
            return `<article class="market-source-card">
              <strong>${escapeHtml(shorten(source.title || "行情来源", 36))}</strong>
              <p>${escapeHtml(shorten(source.snippet || source.source || "", 90))}</p>
              <div>
                <span>${escapeHtml(source.date || source.source || "公开来源")}</span>
                ${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">打开来源</a>` : ""}
              </div>
            </article>`;
          })
          .join("")
      : "";
  }
  renderMarketPriceInsight(payload, { expanded: Boolean(options.showInsight) });
}

function renderMarketPriceRow(row = {}, payload = {}) {
  const price = row.avg_price ? `${row.avg_price} ${row.unit || ""}` : "待核实";
  const change = row.change_percent !== "" && row.change_percent !== undefined ? `${row.change_percent}%` : "";
  const sourceUrl = String(row.source_url || "").trim();
  const productName = row.name || payload.product || "";
  const marketLabel = row.local_reference ? `${row.market || ""}` : row.market || "";
  const rowClass = row.local_reference ? "local-price-row" : "";
  const title = row.local_reference
    ? `title="${escapeHtml(row.confidence || "本地经营参考，成交前请询价核实")}"`
    : "";
  const confidence = row.local_reference ? change || "本地询价" : change || row.confidence || "";
  return `<tr class="${rowClass}" ${title}>
    <td><button class="market-product-link" type="button" data-market-product="${escapeHtml(productName)}">${escapeHtml(productName)}</button></td>
    <td>${escapeHtml(shorten(marketLabel, 26))}${row.local_reference ? '<span class="market-local-badge">江苏句容参考</span>' : ""}</td>
    <td>${escapeHtml(price)}</td>
    <td>${escapeHtml(confidence)}</td>
    <td>${escapeHtml(row.date || "")}</td>
    <td>${sourceUrl ? `<a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(shorten(row.source || "来源", 18))}</a>` : escapeHtml(row.source || "")}</td>
  </tr>`;
}

function renderMarketPriceInsight(payload = {}, options = {}) {
  if (!marketPriceInsight) return;
  const insight = payload.ai_insight || {};
  const product = payload.product || marketPriceInput?.value.trim() || "当前品名";
  const expanded = Boolean(options.expanded);
  marketPriceInsight.classList.remove("loading");
  if (!expanded) {
    marketPriceInsight.innerHTML = `<button class="market-insight-trigger" type="button" data-market-product="${escapeHtml(product)}">
      点“${escapeHtml(shorten(product, 16))}”生成行情小结和实时建议
    </button>`;
    return;
  }
  const advice = Array.isArray(insight.advice) ? insight.advice : [];
  const adviceHtml = advice.length
    ? `<ul>${advice.slice(0, 4).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : "";
  const provider = insight.provider || (payload.ai_enabled ? "实时建议" : "规则小结");
  const status = insight.status === ASSISTANT_STATUS ? "新农人助手已分析" : provider;
  const ontology = payload.ontology_record || {};
  const ontologyHtml = ontology.status === "persisted"
    ? `<div class="market-ontology-note">
        <strong>已沉淀到本地本体库</strong>
        <span>${escapeHtml(ontology.node_label || product)} · ${escapeHtml(ontology.product_folder || ontology.root || "")}</span>
      </div>`
    : "";
  marketPriceInsight.innerHTML = `<article class="market-ai-card">
    <div class="market-ai-head">
      <strong>${escapeHtml(product)}行情小结</strong>
      <span>${escapeHtml(status)}</span>
    </div>
    ${ontologyHtml}
    <p>${escapeHtml(insight.summary || payload.decision || "已返回行情线索。")}</p>
    ${adviceHtml}
    ${insight.action ? `<div class="market-ai-action">${escapeHtml(insight.action)}</div>` : ""}
    ${insight.risk ? `<div class="market-ai-risk">${escapeHtml(insight.risk)}</div>` : ""}
  </article>`;
}

function requestMarketPriceInsight(product) {
  const name = String(product || marketPriceInput?.value || "").trim();
  if (!name || marketPriceLoading) return;
  if (marketPriceInput) marketPriceInput.value = name;
  loadMarketPricePanel({ product: name, includeAi: true });
}

function syncLocationInputsFromState() {
  if (productionLocationInput && productionLocationInput.value !== locationContextState.productionLocation) {
    productionLocationInput.value = locationContextState.productionLocation || DEFAULT_PRODUCTION_LOCATION;
  }
  if (marketLocationInput && marketLocationInput.value !== locationContextState.marketLocation) {
    marketLocationInput.value = locationContextState.marketLocation || DEFAULT_MARKET_LOCATION;
  }
  if (weatherLocationInput && weatherLocationInput.value !== locationContextState.weatherLocation) {
    weatherLocationInput.value = locationContextState.weatherLocation || DEFAULT_PRODUCTION_LOCATION;
  }
  syncMapPickerButtons();
}

function updateLocationContextFromInputs() {
  locationContextState.productionLocation = productionLocationInput?.value.trim() || DEFAULT_PRODUCTION_LOCATION;
  locationContextState.marketLocation = marketLocationInput?.value.trim() || DEFAULT_MARKET_LOCATION;
  locationContextState.weatherLocation = weatherLocationInput?.value.trim() || DEFAULT_PRODUCTION_LOCATION;
  saveLocationContextState();
}

function applyWeatherLocationFromInput() {
  locationContextState.weatherLocation = weatherLocationInput?.value.trim() || DEFAULT_PRODUCTION_LOCATION;
  saveLocationContextState();
  syncMapPickerButtons();
  loadLocalLivePanel({ force: true });
  refreshDynamicHeadlines({ force: true });
  showToast(`已切换天气位置：${locationContextState.weatherLocation}`, "success", 2200);
}

function syncMapPickerButtons() {
  if (openProductionMapPicker) {
    openProductionMapPicker.textContent = normalizeMapPoint(locationContextState.productionPoint) ? "已选地图" : "地图选择";
  }
  if (openMarketMapPicker) {
    openMarketMapPicker.textContent = normalizeMapPoint(locationContextState.marketPoint) ? "已选地图" : "地图选择";
  }
  if (openWeatherMapPicker) {
    openWeatherMapPicker.textContent = normalizeMapPoint(locationContextState.weatherPoint) ? "已选地图" : "地图选择";
  }
}

function clearMapPointForManualInput(mode) {
  if (mode === "production") locationContextState.productionPoint = null;
  if (mode === "market") locationContextState.marketPoint = null;
  if (mode === "weather") locationContextState.weatherPoint = null;
  syncMapPickerButtons();
  saveLocationContextState();
}

function currentMapPickerPoint(mode) {
  const stored = normalizeMapPoint(
    mode === "weather"
      ? locationContextState.weatherPoint
      : mode === "market"
        ? locationContextState.marketPoint
        : locationContextState.productionPoint
  );
  if (stored) return stored;
  const latest = locationContextState.latest || {};
  const location = mode === "weather"
    ? latest.weather_location
    : mode === "market"
      ? latest.market_location
      : latest.production_location || latest.region;
  const lat = Number(location?.latitude);
  const lon = Number(location?.longitude);
  if (Number.isFinite(lat) && Number.isFinite(lon)) {
    return { lat, lon, label: location.short_name || location.name || "" };
  }
  return DEFAULT_MAP_POINTS[mode] || DEFAULT_MAP_POINTS.production;
}

function openLocationMapPicker(mode) {
  if (!mapPickerOverlay || !mapPickerCanvas) return;
  if (mapPickerOverlay.parentElement !== document.body) document.body.appendChild(mapPickerOverlay);
  mapPickerMode = mode === "weather" ? "weather" : mode === "market" ? "market" : "production";
  const isMarket = mapPickerMode === "market";
  const isWeather = mapPickerMode === "weather";
  const input = isWeather ? weatherLocationInput : isMarket ? marketLocationInput : productionLocationInput;
  const point = currentMapPickerPoint(mapPickerMode);
  mapPickerOverlay.classList.remove("hidden");
  if (mapPickerTitle) mapPickerTitle.textContent = isWeather ? "选择天气位置" : isMarket ? "选择目标市场" : "选择本地市场/产地";
  if (mapPickerHint) mapPickerHint.textContent = isWeather ? "点选要查看实时天气和预报的位置" : isMarket ? "点选收购市场或配送终点" : "点选产地、合作社或本地市场";
  if (mapPickerSearch) mapPickerSearch.value = input?.value.trim() || point.label || "";
  if (!window.L) {
    mapPickerCanvas.innerHTML = '<div class="map-picker-fallback">地图组件暂未加载，可先手动输入位置名称。</div>';
    if (confirmMapPicker) confirmMapPicker.disabled = true;
    return;
  }
  window.setTimeout(() => {
    if (!mapPickerMap) {
      mapPickerMap = L.map(mapPickerCanvas, { zoomControl: true }).setView([point.lat, point.lon], 10);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: "&copy; OpenStreetMap",
      }).addTo(mapPickerMap);
      mapPickerMap.on("click", (event) => {
        setMapPickerPoint(event.latlng.lat, event.latlng.lng, "", { updateTextInput: true, reverseLookup: true });
      });
    } else {
      mapPickerMap.setView([point.lat, point.lon], 10);
      mapPickerMap.invalidateSize();
    }
    setMapPickerPoint(point.lat, point.lon, point.label, { updateTextInput: false, reverseLookup: false });
    mapPickerMap.invalidateSize();
  }, 80);
}

function setMapPickerPoint(lat, lon, label = "", options = {}) {
  const next = normalizeMapPoint({ lat, lon, label });
  if (!next) return;
  mapPickerSelectedPoint = next;
  if (mapPickerMap && window.L) {
    if (!mapPickerMarker) {
      mapPickerMarker = L.marker([next.lat, next.lon], { draggable: true }).addTo(mapPickerMap);
      mapPickerMarker.on("dragend", () => {
        const pos = mapPickerMarker.getLatLng();
        setMapPickerPoint(pos.lat, pos.lng, "", { updateTextInput: true, reverseLookup: true });
      });
    } else {
      mapPickerMarker.setLatLng([next.lat, next.lon]);
    }
  }
  const shouldUpdateText = options.updateTextInput !== false;
  const hasLabel = Boolean(String(label || "").trim());
  if (shouldUpdateText) {
    applyMapPickerDraftToInputs(next, label);
  } else if (mapPickerCoord) {
    mapPickerCoord.textContent = `${next.lat.toFixed(5)}, ${next.lon.toFixed(5)}`;
  }
  if (confirmMapPicker) confirmMapPicker.disabled = false;
  if (shouldUpdateText && options.reverseLookup !== false && !hasLabel) {
    lookupMapPickerPointName(next);
  }
}

function mapPickerFallbackLabel(point, mode = mapPickerMode) {
  const isMarket = mode === "market";
  const isWeather = mode === "weather";
  return `${isWeather ? "天气位置" : isMarket ? "目标市场" : "本地位置"} ${point.lat.toFixed(4)},${point.lon.toFixed(4)}`;
}

function normalizeMapPickerDisplayLabel(payload = {}) {
  const address = payload.address || {};
  const primary = [
    address.city || address.prefecture || address.county || address.town || address.village || address.suburb,
    address.road || address.neighbourhood || address.industrial || address.marketplace || address.hamlet,
  ].filter(Boolean);
  const compact = primary.filter((item, index, list) => list.indexOf(item) === index).join(" ");
  return compact || payload.name || payload.display_name || "";
}

function applyMapPickerDraftToInputs(point, label = "") {
  const normalized = normalizeMapPoint(point);
  if (!normalized) return null;
  const isMarket = mapPickerMode === "market";
  const isWeather = mapPickerMode === "weather";
  const input = isWeather ? weatherLocationInput : isMarket ? marketLocationInput : productionLocationInput;
  const nextLabel = String(label || normalized.label || "").trim() || mapPickerFallbackLabel(normalized);
  const nextPoint = { ...normalized, label: nextLabel };
  mapPickerSelectedPoint = nextPoint;
  if (input && input.value !== nextLabel) input.value = nextLabel;
  if (mapPickerSearch && mapPickerSearch.value !== nextLabel) mapPickerSearch.value = nextLabel;
  if (mapPickerCoord) mapPickerCoord.textContent = `${nextLabel} | ${nextPoint.lat.toFixed(5)}, ${nextPoint.lon.toFixed(5)}`;
  return nextPoint;
}

async function lookupMapPickerPointName(point) {
  const normalized = normalizeMapPoint(point);
  if (!normalized) return;
  const token = ++mapPickerReverseLookupToken;
  if (mapPickerCoord) {
    mapPickerCoord.textContent = `${mapPickerFallbackLabel(normalized)} | 正在识别位置名称...`;
  }
  try {
    const params = new URLSearchParams({
      format: "jsonv2",
      lat: String(normalized.lat),
      lon: String(normalized.lon),
      zoom: "16",
      addressdetails: "1",
      "accept-language": "zh-CN,zh",
    });
    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?${params.toString()}`, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    if (token !== mapPickerReverseLookupToken) return;
    const current = normalizeMapPoint(mapPickerSelectedPoint);
    if (!current || Math.abs(current.lat - normalized.lat) > 0.00001 || Math.abs(current.lon - normalized.lon) > 0.00001) return;
    const label = normalizeMapPickerDisplayLabel(payload);
    if (label) applyMapPickerDraftToInputs(current, label);
  } catch (error) {
    if (token === mapPickerReverseLookupToken && mapPickerCoord) {
      const current = normalizeMapPoint(mapPickerSelectedPoint) || normalized;
      mapPickerCoord.textContent = `${current.label || mapPickerFallbackLabel(current)} | ${current.lat.toFixed(5)}, ${current.lon.toFixed(5)}`;
    }
  }
}

function closeLocationMapPicker() {
  mapPickerOverlay?.classList.add("hidden");
}

async function searchMapPickerLocation() {
  const query = mapPickerSearch?.value.trim();
  if (!query) return;
  if (!window.L || !mapPickerMap) {
    showToast("地图还在加载，请稍后再试。", "error", 2200);
    return;
  }
  if (mapPickerSearchButton) mapPickerSearchButton.disabled = true;
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=cn&q=${encodeURIComponent(query)}`,
      { headers: { Accept: "application/json" } }
    );
    const results = await response.json();
    const first = Array.isArray(results) ? results[0] : null;
    if (!first) throw new Error("未找到这个位置");
    const lat = Number(first.lat);
    const lon = Number(first.lon);
    mapPickerMap.setView([lat, lon], 13);
    setMapPickerPoint(lat, lon, query, { updateTextInput: true, reverseLookup: false });
  } catch (error) {
    showToast(`定位失败：${error.message}`, "error", 2600);
  } finally {
    if (mapPickerSearchButton) mapPickerSearchButton.disabled = false;
  }
}

function confirmMapPickerPoint() {
  const point = normalizeMapPoint(mapPickerSelectedPoint);
  if (!point) return;
  const isMarket = mapPickerMode === "market";
  const isWeather = mapPickerMode === "weather";
  const input = isWeather ? weatherLocationInput : isMarket ? marketLocationInput : productionLocationInput;
  const fallbackLabel = `${isWeather ? "天气位置" : isMarket ? "目标市场" : "本地位置"} ${point.lat.toFixed(4)},${point.lon.toFixed(4)}`;
  const label = point.label || mapPickerSearch?.value.trim() || input?.value.trim() || fallbackLabel;
  const savedPoint = { ...point, label, source: "map" };
  if (isWeather) {
    locationContextState.weatherLocation = label;
    locationContextState.weatherPoint = savedPoint;
    if (weatherLocationInput) weatherLocationInput.value = label;
  } else if (isMarket) {
    locationContextState.marketLocation = label;
    locationContextState.marketPoint = savedPoint;
    if (marketLocationInput) marketLocationInput.value = label;
  } else {
    locationContextState.productionLocation = label;
    locationContextState.productionPoint = savedPoint;
    if (productionLocationInput) productionLocationInput.value = label;
  }
  saveLocationContextState();
  syncMapPickerButtons();
  closeLocationMapPicker();
  loadLocalLivePanel({ force: true });
  loadPolicyIntelligencePanel({ quiet: true });
  showToast(isWeather ? "已按地图更新天气位置。" : isMarket ? "已按地图更新目标市场。" : "已按地图更新本地市场/产地。", "success", 2400);
}

async function detectIpAndUseAsProductionLocation() {
  if (detectIpLocation) detectIpLocation.disabled = true;
  if (ipLocationStatus) ipLocationStatus.textContent = "正在识别当前IP位置...";
  try {
    const params = new URLSearchParams({
      query: "农业 政策 市场 物流 天气",
      production_location: "auto",
      market_location: marketLocationInput?.value.trim() || locationContextState.marketLocation || DEFAULT_MARKET_LOCATION,
    });
    const marketPoint = normalizeMapPoint(locationContextState.marketPoint);
    if (marketPoint) {
      params.set("market_lat", String(marketPoint.lat));
      params.set("market_lon", String(marketPoint.lon));
    }
    const payload = await fetchJson(`/api/location/context?${params.toString()}`);
    locationContextState.ipLocation = payload.ip_location || null;
    const production = payload.production_location || payload.ip_location;
    if (production?.short_name || production?.name) {
      locationContextState.productionLocation = production.short_name || production.name;
      locationContextState.productionPoint = null;
      if (productionLocationInput) productionLocationInput.value = locationContextState.productionLocation;
    }
    locationContextState.latest = payload;
    saveLocationContextState();
    renderLocalLivePanel(payload);
    loadPolicyIntelligencePanel({ quiet: true });
    showToast("已按当前IP位置更新产地与两地态势。", "success", 2400);
  } catch (error) {
    if (ipLocationStatus) ipLocationStatus.textContent = "IP定位失败，可手动输入产地";
    showToast(`IP定位失败：${error.message}`, "error", 3000);
  } finally {
    if (detectIpLocation) detectIpLocation.disabled = false;
  }
}

async function loadOllamaModels(options = {}) {
  if (!modelSelect) return;
  const quiet = Boolean(options.quiet);
  modelWorkbench?.classList.add("is-loading");
  if (modelStatusText) modelStatusText.textContent = "正在检测新农人助手与本地备用模型";
  try {
    const payload = await fetchJson("/api/models");
    renderModelChooser(payload);
    if (!quiet && detectedOllamaModels.length) showToast("本地备用模型列表已刷新。", "success", 2200);
  } catch (error) {
    detectedOllamaModels = [];
    appliedAnswerModel = "";
    modelWorkbench?.classList.remove("is-ready");
    modelWorkbench?.classList.add("is-unavailable");
    if (modelActiveName) modelActiveName.textContent = "新农人助手";
    if (modelStatusText) modelStatusText.textContent = "新农人助手后端已选中；未连通时仍可查看检索依据";
    if (modelSelect) {
      modelSelect.innerHTML = '<option value="">使用新农人助手默认配置</option>';
      modelSelect.disabled = true;
    }
    if (applyModelButton) applyModelButton.disabled = true;
    if (!quiet) showToast(`模型服务检测失败：${error.message}`, "error", 3200);
  } finally {
    modelWorkbench?.classList.remove("is-loading");
  }
}

function renderModelChooser(payload = {}) {
  detectedOllamaModels = Array.isArray(payload.models) ? payload.models : [];
  const activeModel = String(payload.active_model || "").trim();
  const isOllamaActive = payload.active_provider === "OllamaProvider";
  const isAssistantActive = payload.active_provider === "OpenAICompatibleProvider" || payload.active_provider === ASSISTANT_CLI_PROVIDER;
  const providerReady = payload.provider_available !== false;
  const backendReady = detectedOllamaModels.length > 0 || (isAssistantActive && providerReady);
  appliedAnswerModel = isOllamaActive ? activeModel : "";

  if (modelKicker) modelKicker.textContent = isOllamaActive ? "本地真实模型" : "新农人助手";
  if (modelActiveName) modelActiveName.textContent = isAssistantActive ? "新农人助手" : (activeModel || "自动选择");
  modelWorkbench?.classList.toggle("is-ready", backendReady);
  modelWorkbench?.classList.toggle("is-unavailable", !backendReady);

  if (!modelSelect) return;
  modelSelect.innerHTML = "";

  if (!detectedOllamaModels.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = isAssistantActive
      ? "使用新农人助手"
      : payload.ollama_available ? "暂无可选本地模型" : "未发现本地备用模型";
    modelSelect.appendChild(option);
    modelSelect.disabled = true;
    if (applyModelButton) applyModelButton.disabled = true;
    if (modelStatusText) {
      modelStatusText.textContent = isAssistantActive
        ? providerReady
          ? "新农人助手已连通，后续回答会真实调用模型"
          : "新农人助手已设为默认，但还未通过连通检测，提问会提示配置"
        : "未发现本地备用模型，系统会使用已配置服务";
    }
    return;
  }

  if (isAssistantActive) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "新农人助手";
    modelSelect.appendChild(option);
  }

  for (const item of detectedOllamaModels) {
    const option = document.createElement("option");
    option.value = item.name;
    option.textContent = item.label || item.name;
    modelSelect.appendChild(option);
  }
  if (activeModel && detectedOllamaModels.some((item) => item.name === activeModel)) {
    modelSelect.value = activeModel;
  } else if (isAssistantActive) {
    modelSelect.value = "";
  }
  modelSelect.disabled = false;
  if (applyModelButton) applyModelButton.disabled = isAssistantActive && !modelSelect.value;
  if (modelStatusText) {
    modelStatusText.textContent = isOllamaActive
      ? "当前回答会真实调用本地模型进行综合分析"
      : providerReady
        ? "默认使用新农人助手，也可选择本地备用模型"
        : "默认强制使用新农人助手；请先完成模型命令或 API Key 配置";
  }
}

function isInternalAssistantName(value = "") {
  return /kimi|moonshot|KimiCliProvider/i.test(String(value || ""));
}

function visibleProviderLabel(value = "") {
  const text = String(value || "").trim();
  if (!text) return "未检测";
  if (isInternalAssistantName(text) || text === "OpenAICompatibleProvider") return "新农人助手云端";
  if (text === "OllamaProvider") return "本地备用模型";
  return text;
}

function visibleModelLabel(value = "") {
  const text = String(value || "").trim();
  if (!text) return "未设置";
  if (isInternalAssistantName(text)) return "默认云端模型";
  return text;
}

async function applySelectedAnswerModel() {
  if (!modelSelect || !modelSelect.value) {
    showToast("请先选择一个本地模型。", "error", 2600);
    return;
  }
  const model = modelSelect.value;
  const previousText = applyModelButton?.textContent || "";
  if (applyModelButton) {
    applyModelButton.disabled = true;
    applyModelButton.textContent = "切换中";
  }
  try {
    const payload = await fetchJson("/api/models/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    });
    renderModelChooser(payload);
    appliedAnswerModel = payload.active_model || model;
    showToast(`后续回答将使用：${appliedAnswerModel}`, "success", 2600);
  } catch (error) {
    showToast(`模型切换失败：${error.message}`, "error", 3600);
  } finally {
    if (applyModelButton) {
      applyModelButton.disabled = detectedOllamaModels.length === 0;
      applyModelButton.textContent = previousText || "用于回答";
    }
  }
}

function syncMobileAccessUi() {
  if (settingsMobileUrl) settingsMobileUrl.value = MOBILE_WIFI_URL;
}

async function copyMobileAccessUrl() {
  syncMobileAccessUi();
  const url = settingsMobileUrl?.value || MOBILE_WIFI_URL;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url);
      showToast("手机访问地址已复制。", "success", 1800);
      return;
    }
    throw new Error("clipboard unavailable");
  } catch {
    settingsMobileUrl?.focus();
    settingsMobileUrl?.select();
    showToast("已选中手机访问地址，可手动复制。", "info", 2400);
  }
}

function syncAppSettingsUi(settingsPayload = null) {
  syncMobileAccessUi();
  if (settingsLanguage) settingsLanguage.value = appSettings.answerLanguage || "auto";
  if (settingsShowPrompt) settingsShowPrompt.checked = appSettings.showPrompt !== false;
  if (settingsDefaultWebSearch) settingsDefaultWebSearch.checked = appSettings.defaultWebSearch !== false;
  if (webSearchToggle) webSearchToggle.checked = appSettings.defaultWebSearch !== false;
  if (!settingsPayload) return;
  if (settingsBackend) settingsBackend.value = settingsPayload.backend || "auto";
  const baseUrl = settingsPayload.base_url || "";
  const modelName = settingsPayload.model || "";
  if (settingsBaseUrl) {
    settingsBaseUrl.value = isInternalAssistantName(baseUrl) ? "" : baseUrl;
    settingsBaseUrl.placeholder = isInternalAssistantName(baseUrl)
      ? "已配置新农人助手云端 API，留空不修改"
      : "https://api.example.com/v1";
  }
  if (settingsModel) {
    settingsModel.value = isInternalAssistantName(modelName) ? "" : modelName;
    settingsModel.placeholder = isInternalAssistantName(modelName)
      ? "已配置默认云端模型，留空不修改"
      : "输入模型名称";
  }
  if (settingsOllamaModel) settingsOllamaModel.value = settingsPayload.ollama_model || "";
  if (settingsApiKey) settingsApiKey.value = "";
  if (settingsFrontendBaseUrl) {
    settingsFrontendBaseUrl.value = settingsPayload.frontend_base_url || "";
    settingsFrontendBaseUrl.placeholder = settingsPayload.frontend_base_url ? "留空不修改" : "默认跟随后台 API 地址";
  }
  if (settingsFrontendModel) {
    settingsFrontendModel.value = settingsPayload.frontend_model || "";
    settingsFrontendModel.placeholder = settingsPayload.frontend_model ? "留空不修改" : "默认跟随后台模型";
  }
  if (settingsFrontendApiKey) settingsFrontendApiKey.value = "";
  if (settingsStatus) {
    const backendKey = settingsPayload.backend_api_key_present ?? settingsPayload.api_key_present;
    const backendHint = settingsPayload.backend_api_key_hint || settingsPayload.api_key_hint || "已脱敏";
    const frontKey = settingsPayload.frontend_api_key_present;
    const keyText = [
      backendKey ? `后台 Key 已保存（${backendHint}）` : "后台 Key 未保存",
      frontKey ? `前端 Key 已保存（${settingsPayload.frontend_api_key_hint || "已脱敏"}）` : "前端 Key 未保存",
    ].join("；");
    const provider = visibleProviderLabel(settingsPayload.active_provider);
    const model = visibleModelLabel(settingsPayload.active_model || settingsPayload.model);
    settingsStatus.textContent = `${provider} · ${model} · ${keyText}`;
  }
  if (settingsTestStatus) {
    settingsTestStatus.textContent = "可点击测试按钮真实调用模型，连通结果会显示在这里。";
    settingsTestStatus.classList.remove("success", "error");
  }
}

async function loadRuntimeSettings(options = {}) {
  try {
    const payload = await fetchJson("/api/settings");
    syncAppSettingsUi(payload);
    if (!options.quiet) showToast("设置已读取。", "success", 1800);
    return payload;
  } catch (error) {
    if (settingsStatus) settingsStatus.textContent = `设置读取失败：${error.message}`;
    if (!options.quiet) showToast(`设置读取失败：${error.message}`, "error", 3200);
    return null;
  }
}

function openUtilityPanel(panel) {
  panel?.classList.remove("hidden");
}

function closeUtilityPanel(panel) {
  panel?.classList.add("hidden");
}

async function openSettingsDialog() {
  openUtilityPanel(settingsPanelOverlay);
  syncMobileAccessUi();
  syncAppSettingsUi();
  await loadRuntimeSettings({ quiet: true });
}

async function saveRuntimeSettings() {
  appSettings = {
    ...appSettings,
    answerLanguage: settingsLanguage?.value || "auto",
    showPrompt: Boolean(settingsShowPrompt?.checked),
    defaultWebSearch: Boolean(settingsDefaultWebSearch?.checked),
  };
  saveAppSettings();
  syncAppSettingsUi();
  const payload = {
    backend: settingsBackend?.value || "auto",
    base_url: settingsBaseUrl?.value.trim() || "",
    model: settingsModel?.value.trim() || "",
    api_key: settingsApiKey?.value.trim() || "",
    frontend_base_url: settingsFrontendBaseUrl?.value.trim() || "",
    frontend_model: settingsFrontendModel?.value.trim() || "",
    frontend_api_key: settingsFrontendApiKey?.value.trim() || "",
    ollama_model: settingsOllamaModel?.value.trim() || "",
    save_to_env: true,
  };
  if (!payload.api_key) delete payload.api_key;
  if (!payload.frontend_api_key) delete payload.frontend_api_key;
  if (saveSettingsButton) {
    saveSettingsButton.disabled = true;
    saveSettingsButton.textContent = "保存中";
  }
  try {
    const result = await fetchJson("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    syncAppSettingsUi(result.settings);
    renderModelChooser(result.models || {});
    if (settingsApiKey) settingsApiKey.value = "";
    if (settingsFrontendApiKey) settingsFrontendApiKey.value = "";
    showToast("设置已保存并应用。", "success", 2600);
  } catch (error) {
    showToast(`设置保存失败：${error.message}`, "error", 4200);
  } finally {
    if (saveSettingsButton) {
      saveSettingsButton.disabled = false;
      saveSettingsButton.textContent = "保存并应用";
    }
  }
}

function buildRuntimeTestPayload(target = "both") {
  const payload = {
    target,
    backend: settingsBackend?.value || "auto",
    base_url: settingsBaseUrl?.value.trim() || "",
    model: settingsModel?.value.trim() || "",
    api_key: settingsApiKey?.value.trim() || "",
    frontend_base_url: settingsFrontendBaseUrl?.value.trim() || "",
    frontend_model: settingsFrontendModel?.value.trim() || "",
    frontend_api_key: settingsFrontendApiKey?.value.trim() || "",
  };
  for (const key of Object.keys(payload)) {
    if (key !== "target" && !payload[key]) delete payload[key];
  }
  return payload;
}

function formatApiTestResult(result) {
  if (!result) return "未返回测试结果。";
  const parts = [];
  const append = (label, item) => {
    if (!item) return;
    const status = item.ok ? "通过" : "失败";
    const provider = visibleProviderLabel(item.provider || "");
    const model = visibleModelLabel(item.model || "");
    const keyText = item.api_key_present ? `Key ${item.api_key_hint || "已脱敏"}` : "未检测到 Key";
    const message = item.message || "";
    parts.push(`${label}：${status} · ${provider} · ${model} · ${keyText} · ${item.seconds || 0}s。${message}`);
  };
  append("后台", result.backend_test);
  append("前端", result.frontend_test);
  return parts.join("\n") || "未返回测试结果。";
}

async function testRuntimeApiKey(target = "both") {
  const buttons = [testBackendApiButton, testFrontendApiButton, testAllApiButton].filter(Boolean);
  buttons.forEach((button) => {
    button.disabled = true;
  });
  if (settingsTestStatus) {
    settingsTestStatus.textContent = "正在真实调用模型测试连通性，请稍候...";
    settingsTestStatus.classList.remove("success", "error");
  }
  try {
    const result = await fetchJson("/api/settings/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildRuntimeTestPayload(target)),
    });
    const message = formatApiTestResult(result);
    if (settingsTestStatus) {
      settingsTestStatus.textContent = message;
      settingsTestStatus.classList.toggle("success", Boolean(result.ok));
      settingsTestStatus.classList.toggle("error", !result.ok);
    }
    showToast(result.ok ? "API Key 实测通过。" : "API Key 测试未通过，请看设置面板结果。", result.ok ? "success" : "error", 4200);
    return result;
  } catch (error) {
    const message = `测试失败：${error.message}`;
    if (settingsTestStatus) {
      settingsTestStatus.textContent = message;
      settingsTestStatus.classList.remove("success");
      settingsTestStatus.classList.add("error");
    }
    showToast(message, "error", 4600);
    return null;
  } finally {
    buttons.forEach((button) => {
      button.disabled = false;
    });
  }
}

async function exportRuntimeSettings() {
  const payload = await loadRuntimeSettings({ quiet: true });
  if (!payload) return;
  const exportPayload = {
    exported_at: new Date().toISOString(),
    app_settings: appSettings,
    runtime_settings: {
      backend: payload.backend,
      base_url: payload.base_url,
      model: payload.model,
      frontend_base_url: payload.frontend_base_url,
      frontend_model: payload.frontend_model,
      ollama_model: payload.ollama_model,
      kimi_executable: payload.kimi_executable,
      api_key_present: payload.api_key_present,
      frontend_api_key_present: payload.frontend_api_key_present,
    },
  };
  downloadBlob(JSON.stringify(exportPayload, null, 2), `agrikb-settings-${Date.now()}.json`, "application/json;charset=utf-8");
  showToast("设置已导出，完整 API Key 不会写入文件。", "success", 2600);
}

async function importRuntimeSettingsFile(file) {
  if (!file) return;
  try {
    const parsed = JSON.parse(await file.text());
    const runtime = parsed.runtime_settings || parsed.settings || parsed;
    const importedApp = parsed.app_settings || {};
    appSettings = {
      ...appSettings,
      ...importedApp,
      answerLanguage: ["auto", "zh", "en"].includes(importedApp.answerLanguage) ? importedApp.answerLanguage : appSettings.answerLanguage,
      showPrompt: importedApp.showPrompt !== undefined ? Boolean(importedApp.showPrompt) : appSettings.showPrompt,
      defaultWebSearch: importedApp.defaultWebSearch !== undefined ? Boolean(importedApp.defaultWebSearch) : appSettings.defaultWebSearch,
    };
    saveAppSettings();
    syncAppSettingsUi();
    const payload = {
      backend: runtime.backend || settingsBackend?.value || "auto",
      base_url: runtime.base_url || "",
      model: runtime.model || "",
      frontend_base_url: runtime.frontend_base_url || "",
      frontend_model: runtime.frontend_model || "",
      ollama_model: runtime.ollama_model || "",
      save_to_env: true,
    };
    const result = await fetchJson("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    syncAppSettingsUi(result.settings);
    renderModelChooser(result.models || {});
    showToast("设置文件已导入。API Key 需在设置里单独输入。", "success", 3000);
  } catch (error) {
    showToast(`设置导入失败：${error.message}`, "error", 4200);
  } finally {
    if (settingsImportInput) settingsImportInput.value = "";
  }
}

async function exportCurrentSessionJson() {
  try {
    const payload = await fetchJson(`/api/session/${encodeURIComponent(currentSessionId)}`);
    downloadBlob(JSON.stringify(payload, null, 2), `agrikb-session-${currentSessionId}.json`, "application/json;charset=utf-8");
    showToast("当前对话已导出。", "success", 2200);
  } catch (error) {
    showToast(`对话导出失败：${error.message}`, "error", 3600);
  }
}

function exportLastAnswerMarkdown() {
  const answer = cleanAnswerTextForDisplay(lastAssistantAnswer || currentAnswerText || "");
  if (!answer) {
    showToast("还没有可导出的回答。", "error", 2400);
    return;
  }
  const markdown = [
    "# AgriKB 问答导出",
    "",
    `导出时间：${new Date().toLocaleString("zh-CN")}`,
    "",
    "## 问题",
    lastUserQuery || "",
    "",
    "## 回答",
    answer,
  ].join("\n");
  downloadBlob(markdown, `agrikb-answer-${Date.now()}.md`, "text/markdown;charset=utf-8");
  showToast("最近回答已导出。", "success", 2200);
}

function renderPromptDisclosure(promptText, label = "本次 Prompt") {
  if (!appSettings.showPrompt || !String(promptText || "").trim()) return "";
  return `<details class="prompt-collapsible">
    <summary><span>${escapeHtml(label)}</span><small>点击查看发送给模型的提示词</small></summary>
    <pre>${escapeHtml(String(promptText || "").trim())}</pre>
  </details>`;
}

function summarizeCitations(results = []) {
  const seen = new Set();
  const citations = [];
  for (const item of results) {
    const label = item.doc_name || item.source || item.file_name || "未命名来源";
    if (!label || seen.has(label)) continue;
    seen.add(label);
    citations.push(`<li>${escapeHtml(label)}</li>`);
  }
  if (!citations.length) return "";
  return `<p><strong>来源依据</strong></p><ul>${citations.slice(0, 8).join("")}</ul>`;
}

function renderAssistantResponse(result) {
  const answerText = cleanAnswerTextForDisplay(stripEvidenceChain(result.answer || ""));
  const evidence = normalizeEvidenceItems(result);
  const graph = result.evidence_graph && result.evidence_graph.nodes ? result.evidence_graph : buildEvidenceFlowGraph(lastUserQuery, answerText, evidence);
  const sessionGraph = result.session_evidence_graph && result.session_evidence_graph.nodes ? result.session_evidence_graph : null;
  const graphId = `evidence-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  evidenceGraphStore.set(graphId, { graph, sessionGraph, evidence, answerText, query: lastUserQuery });
  activeAnalysisTreeNode =
    result.focused_knowledge_tree && result.focused_knowledge_tree.children
      ? result.focused_knowledge_tree
      : buildAnalysisTreeNode(graph, sessionGraph, answerText, lastUserQuery);
  const answerHtml = renderAnswerMain(answerText);
  const coverageHtml = renderKnowledgeCoverage(result.knowledge_progress, result.active_ingest);
  const routeHtml = renderRouteBadges(result);
  const provenanceHtml = renderClaimProvenance(result.answer_claims || []);
  const promptHtml = renderPromptDisclosure(result.model_prompt || result.prompt || "", "本次问答 Prompt");
  const evidenceHtml = renderHiddenEvidenceChain(renderEvidenceChain(graphId, graph, evidence, sessionGraph));
  if (result.memory_rules) renderRuleMemory(result.memory_rules);
  return `${answerHtml}${coverageHtml}${routeHtml}${provenanceHtml}${promptHtml}${evidenceHtml}`;
}

function renderAnswerMain(answerText) {
  const advice = extractOneSentenceAdvice(answerText);
  const cleanText = removeOneSentenceAdvice(answerText);
  const adviceHtml = advice
    ? `<section class="farmer-action-advice"><span>一句话建议</span><strong>${escapeHtml(advice)}</strong></section>`
    : "";
  return `${adviceHtml}<section class="professional-answer answer-main" data-answer-main>${formatAnswerText(cleanText || answerText)}</section>`;
}

function extractOneSentenceAdvice(text) {
  const normalized = String(text || "").replace(/\r/g, "").trim();
  if (!normalized) return "";
  const explicit = normalized.match(/(?:^|\n)\s*(?:一句话建议|一句话行动|今日建议|今天建议)\s*[:：]\s*([^\n]+)/);
  if (explicit?.[1]) return shortenAdvice(explicit[1]);
  const englishExplicit = normalized.match(/(?:^|\n)\s*(?:One-sentence recommendation|Recommendation|Action today)\s*:\s*([^\n]+)/i);
  if (englishExplicit?.[1]) return shortenAdvice(englishExplicit[1]);
  const lines = normalized
    .split("\n")
    .map((line) =>
      line
        .replace(/^#{1,4}\s*/, "")
        .replace(/^[-*]\s+/, "")
        .replace(/^\d+[.、]\s*/, "")
        .replace(/\*\*/g, "")
        .trim(),
    )
    .filter(Boolean)
    .filter((line) => !/^(先干什么|政策|市场|收购|电商|气象|天气|台湾数据|依据|缺口|风险|来源|专业回答|do first|why this judgment|market and channels|risk reminder|next step)$/i.test(line));
  const action = lines.find((line) => /^(今天|先|马上|优先|建议|把|别|采|卖|问|准备|联系)/.test(line)) || "";
  return shortenAdvice(action);
}

function removeOneSentenceAdvice(text) {
  return String(text || "")
    .split(/\r?\n/)
    .filter((line) => !/^\s*(?:一句话建议|一句话行动|今日建议|今天建议)\s*[:：]/.test(line))
    .filter((line) => !/^\s*(?:One-sentence recommendation|Recommendation|Action today)\s*:/i.test(line))
    .join("\n")
    .trim();
}

function shortenAdvice(text) {
  const clean = String(text || "")
    .replace(/\*\*/g, "")
    .replace(/^[:：\s]+/, "")
    .replace(/\s+/g, " ")
    .trim();
  const sentence = clean.split(/(?<=[。！？!?])\s*/)[0] || clean;
  return sentence.length > 72 ? `${sentence.slice(0, 72)}...` : sentence;
}

function renderHiddenEvidenceChain(evidenceHtml) {
  if (!evidenceHtml) return "";
  return `
    <details class="evidence-collapsible">
      <summary>
        <span>依据链与知识树</span>
        <small>默认隐藏，点击查看来源、推理关系和会话证据图</small>
      </summary>
      ${evidenceHtml}
    </details>`;
}

function renderKnowledgeCoverage(progress, activeIngest) {
  const running = Boolean(activeIngest?.running || activeIngestState.running);
  const stage = progress?.stage || activeIngest?.stage || activeIngestState.stage || "refined";
  if (!running && stage === "refined") return "";
  const total = progress?.documents_total || activeIngest?.total_paths || activeIngestState.totalDocs || 0;
  const refined = progress?.documents_refined || activeIngest?.documents_refined || activeIngestState.refinedDocs || 0;
  const coarse = progress?.documents_coarse || activeIngest?.documents_coarse || activeIngestState.coarseDocs || 0;
  const chunks = progress?.chunks_total || activeIngest?.chunks_refined || activeIngestState.chunks || 0;
  const label = stage === "coarse_ready" ? "已可先行提问" : stage === "refining" ? "知识继续整理中" : "知识整理中";
  return `<div class="knowledge-coverage-note">
    <strong>${escapeHtml(label)}</strong>
    <span>当前已整理 ${refined}/${total || "?"} 个文档，已形成 ${coarse} 个文档轮廓、${chunks} 条可用知识。后台会继续完善，并围绕你的问题更新右侧知识树。</span>
  </div>`;
}

function buildAnalysisTreeNode(graph, sessionGraph, answerText, query) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const sessionCount = Array.isArray(sessionGraph?.nodes) ? sessionGraph.nodes.length : nodes.length;
  const byType = (types, limit) =>
    nodes
      .filter((node) => types.includes(node.type))
      .slice(0, limit)
      .map((node, index) => ({
        name: node.label || node.id || `${types[0]} ${index + 1}`,
        label: node.label || node.id || `${types[0]} ${index + 1}`,
        kind: node.type || "analysis",
        type: node.type || "analysis",
        source_type: node.source_type || node.provenance?.source_type || (types.includes("evidence") ? "document" : "inferred"),
        chunk_count: 1,
        preview: node.detail || node.snippet || node.raw_text || node.doc_name || node.file_name || "",
        chunk_id: node.chunk_id || "",
        file_name: node.doc_name || node.file_name || "",
        score: node.score || null,
        children: [],
      }));
  return {
    name: "当前问答分析",
    label: "当前问答分析",
    kind: "analysis",
    type: "analysis",
    source_type: "inferred",
    chunk_count: sessionCount,
    preview: `问题：${query || ""}；本轮分析 ${sessionCount} 个要点；回答摘要：${shorten(answerText || "", 80)}`,
    children: [
      {
        name: "用户问题",
        label: "用户问题",
        kind: "topic",
        type: "topic",
        source_type: "inferred",
        chunk_count: 1,
        preview: query || "",
        children: byType(["query"], 2),
      },
      {
        name: "关键概念",
        label: "关键概念",
        kind: "topic",
        type: "topic",
        source_type: "inferred",
        chunk_count: nodes.filter((node) => node.type === "entity").length,
        preview: "从本轮问题和依据中提炼出的关键概念",
        children: byType(["entity"], 8),
      },
      {
        name: "文档依据",
        label: "文档依据",
        kind: "topic",
        type: "topic",
        source_type: "document",
        chunk_count: nodes.filter((node) => ["evidence", "retrieved_chunk", "document", "section"].includes(node.type)).length,
        preview: "本轮命中的文档依据",
        children: byType(["evidence", "retrieved_chunk", "document", "section"], 8),
      },
      {
        name: "回答要点",
        label: "回答要点",
        kind: "topic",
        type: "topic",
        source_type: "inferred",
        chunk_count: nodes.filter((node) => ["answer", "answer_claim", "inference", "model_prior", "unsupported"].includes(node.type)).length,
        preview: "本轮回答结论和来源判断",
        children: byType(["answer", "answer_claim", "inference", "model_prior", "unsupported"], 8),
      },
    ],
  };
}

function renderClaimProvenance(claims) {
  if (!Array.isArray(claims) || !claims.length) return "";
  const warningClaims = claims.filter((claim) => ["model_prior", "unsupported"].includes(claim.source_type));
  if (!warningClaims.length) return "";
  const seenTypes = new Set();
  const chips = warningClaims
    .filter((claim) => {
      const type = claim.source_type || "unsupported";
      if (seenTypes.has(type)) return false;
      seenTypes.add(type);
      return true;
    })
    .slice(0, 4)
    .map(
      (claim) =>
        `<span class="source-chip source-${escapeHtml(claim.source_type)}">${escapeHtml(sourceTypeLabel(claim.source_type))}</span>`,
    )
    .join("");
  return `<div class="claim-provenance-note">${chips}<span>部分结论不是文档中的直接依据，已在依据链中单独标注。</span></div>`;
}

function renderRouteBadges(result) {
  if (!SHOW_TECH_DETAILS) return "";
  const routeFlags = {
    rlm_used: Boolean(result.rlm_used),
    agentic_used: Boolean(result.agentic_used),
  };
  const badges = [];
  if (routeFlags.rlm_used) badges.push('<span class="route-badge">深度核验</span>');
  if (routeFlags.agentic_used) badges.push('<span class="route-badge">扩展检索</span>');
  return badges.length ? `<div class="route-badges" aria-label="回答处理方式">${badges.join("")}</div>` : "";
}

function stripEvidenceChain(text) {
  const value = String(text || "");
  const answerIndex = value.search(/###\s*专业回答/);
  if (answerIndex >= 0) return value.slice(answerIndex).replace(/###\s*专业回答/, "### 专业回答");
  return value;
}

function cleanAnswerTextForDisplay(text) {
  if (!text) return "";
  return String(text)
    .replace(/###\s*证据链[\s\S]*?(?=###\s*专业回答|$)/g, "")
    .replace(/###\s*专业回答/g, "")
    .replace(/\s*\[E\d+\]/gi, "")
    .replace(/\s*【E\d+】/gi, "")
    .replace(/\s*\(E\d+\)/gi, "")
    .replace(/\s*evidence\s*[:#]?\s*\d+/gi, "")
    .replace(/\s*source\s*id\s*[:：]?\s*\S+/gi, "")
    .replace(/\s*chunk\s*id\s*[:：]?\s*\S+/gi, "")
    .replace(/score\s*[:：]?\s*\d+(\.\d+)?/gi, "")
    .replace(/页面已聚合的信息如下[\s\S]*?(?=\n{2,}|$)/g, "")
    .replace(/回答时要自然吸收[^。]*。?/g, "")
    .replace(/回答要求：[\s\S]*?(?=\n{2,}|$)/g, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function cleanAnswerTextForSpeech(text) {
  if (!text) return "";
  return cleanAnswerTextForDisplay(text)
    .replace(/证据链[\s\S]*$/g, "")
    .replace(/文件[:：][^\n。]+/g, "")
    .replace(/得分[:：]?\s*\d+(\.\d+)?/g, "")
    .replace(/提供evidence类证据[^。]*。?/g, "")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

function formatAnswerText(text) {
  const normalized = normalizeAnswerLayoutText(text);
  const lines = normalized
    .replace(/^ASSISTANT\s*/i, "")
    .replace(/\{\{SSISTANT/gi, "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return "<p>未生成回答。</p>";
  const html = [];
  let listType = "";
  const closeList = () => {
    if (!listType) return;
    html.push(`</${listType}>`);
    listType = "";
  };
  const openList = (type) => {
    if (listType === type) return;
    closeList();
    html.push(`<${type} class="answer-list">`);
    listType = type;
  };
  for (const line of lines) {
    const section = line.match(/^@@SECTION:(.+)$/);
    const numbered = line.match(/^(\d{1,2})[.、]\s+(.+)$/);
    if (section) {
      closeList();
      const title = normalizeAnswerSectionTitle(section[1]);
      if (!title) continue;
      html.push(`<div class="answer-section-title">${escapeHtml(title)}</div>`);
    } else if (numbered) {
      openList("ol");
      html.push(`<li>${escapeHtml(cleanInlineAnswerMarkdown(numbered[2]))}</li>`);
    } else if (/^[-*]\s+/.test(line)) {
      openList("ul");
      html.push(`<li>${escapeHtml(cleanInlineAnswerMarkdown(line.replace(/^[-*]\s+/, "")))}</li>`);
    } else {
      closeList();
      html.push(`<p>${escapeHtml(cleanInlineAnswerMarkdown(line))}</p>`);
    }
  }
  closeList();
  return html.join("");
}

function normalizeAnswerLayoutText(text) {
  return String(text || "")
    .replace(/\*\*\s*(一句话建议|今日建议|先干什么|政策与产业扶持|政策机会|市场\/收购\/电商渠道|市场渠道|销售渠道|气象环境提醒|天气风险|台湾数据依据与缺口|数据依据与缺口|经营判断|下一步动作)\s*\*\*\s*[:：]?/g, "\n@@SECTION:$1\n")
    .replace(/^#{1,4}\s*(.+)$/gm, "\n@@SECTION:$1\n")
    .replace(/^\s*(今日先做|今日建议|为什么这样判断|市场与渠道|市场渠道|销售渠道|政策机会|政策与产业扶持|天气风险|气象环境提醒|风险提醒|数据依据与缺口|台湾数据依据与缺口|下一步|下一步动作)\s*[:：]?\s*$/gm, "\n@@SECTION:$1\n")
    .replace(/\s+(今日先做|为什么这样判断|市场与渠道|销售渠道|政策机会|天气风险|风险提醒|数据依据与缺口|下一步)\s*[:：]\s*/g, "\n@@SECTION:$1\n")
    .replace(/([。！？；;])\s*(今日先做|为什么这样判断|市场与渠道|销售渠道|政策机会|天气风险|风险提醒|数据依据与缺口|下一步)\s+(?=\S)/g, "$1\n@@SECTION:$2\n")
    .replace(/\s+(\d{1,2})[.、]\s+(?=\S)/g, "\n$1. ")
    .replace(/([。！？；;])\s*(?=[^\n]{70,})/g, "$1\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function normalizeAnswerSectionTitle(title) {
  const clean = cleanInlineAnswerMarkdown(title)
    .replace(/[：:]\s*$/, "")
    .trim();
  if (/^(证据链|来源依据|专业回答)$/i.test(clean)) return "";
  const mapping = {
    一句话建议: "今日建议",
    先干什么: "今日建议",
    政策与产业扶持: "政策机会",
    "市场/收购/电商渠道": "销售渠道",
    市场渠道: "销售渠道",
    市场与渠道: "销售渠道",
    气象环境提醒: "天气风险",
    风险提醒: "风险提醒",
    台湾数据依据与缺口: "数据依据与缺口",
    为什么这样判断: "为什么这样判断",
    今日先做: "今日先做",
    下一步动作: "下一步",
  };
  return mapping[clean] || clean;
}

function cleanInlineAnswerMarkdown(value) {
  return String(value || "")
    .replace(/\*\*/g, "")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^[:：\s]+/, "")
    .trim();
}

function normalizeEvidenceItems(result) {
  const raw = result.evidence || result.evidence_chain || result.evidence_chunks || result.retrieval_results || [];
  return raw.slice(0, 8).map((item, index) => ({
    evidence_id: item.evidence_id || item.id || `E${index + 1}`,
    doc_name: item.doc_name || item.source || "unknown",
    chunk_id: item.chunk_id || "",
    page: item.page || item.metadata?.page || "",
    score: Number.isFinite(Number(item.score)) ? Number(item.score) : 0,
    evidence_type: item.evidence_type || item.chunk_type || "text",
    snippet: item.snippet || item.excerpt || item.text || "",
    entities: Array.isArray(item.entities) ? item.entities.slice(0, 6) : [],
    source_path: item.source_path || item.source || "",
    supports: item.supports || item.chunk_type || "evidence",
    source_type: item.source_type || item.provenance?.source_type || "document",
    provenance: item.provenance || {},
    metadata: item.metadata || {},
  }));
}

function buildEvidenceFlowGraph(query, answerText, evidence) {
  const nodes = [{ id: "q", type: "query", label: "用户问题", detail: query || "" }];
  const edges = [];
  const entityMap = new Map();
  const fallbackEntities = extractEvidenceKeywords(`${query || ""} ${evidence.map((item) => item.snippet).join(" ")}`);
  for (const keyword of fallbackEntities.slice(0, 3)) {
    const id = `ent_${entityMap.size + 1}`;
    entityMap.set(keyword, id);
    nodes.push({ id, type: "entity", label: keyword, detail: "命中关键词", source_type: "entity" });
    edges.push({ source: "q", target: id, type: "mentions" });
  }
  evidence.forEach((item, index) => {
    const evId = `ev_${index + 1}`;
    const entities = item.entities.length ? item.entities.slice(0, 3).map(String) : fallbackEntities.slice(0, 1);
    for (const entity of entities) {
      if (!entityMap.has(entity)) {
        const id = `ent_${entityMap.size + 1}`;
        entityMap.set(entity, id);
        nodes.push({ id, type: "entity", label: shorten(entity, 22), detail: "来源概念" });
        edges.push({ source: "q", target: id, type: "mentions" });
      }
      edges.push({ source: entityMap.get(entity), target: evId, type: "retrieves" });
    }
    nodes.push({
      id: evId,
      type: "evidence",
      label: item.doc_name || item.evidence_id,
      detail: item.snippet,
      source_type: item.source_type || "document",
      evidence_id: item.evidence_id,
      doc_name: item.doc_name,
      chunk_id: item.chunk_id,
      page: item.page,
      score: item.score,
      entities,
      snippet: item.snippet,
      supports: item.supports,
    });
    edges.push({ source: evId, target: "ans", type: "supports" });
  });
  nodes.push({ id: "ans", type: "answer_claim", label: "结论要点", source_type: "inferred", detail: cleanAnswerTextForDisplay(answerText).slice(0, 220) });
  return { nodes, edges };
}

function extractEvidenceKeywords(text) {
  const stop = new Set(["请", "解释", "一下", "什么", "如何", "the", "and", "with", "about", "current"]);
  const matches = String(text || "").match(/[\u4e00-\u9fffA-Za-z0-9][\u4e00-\u9fffA-Za-z0-9_/-]{1,24}/g) || [];
  const seen = new Set();
  const values = [];
  for (const match of matches) {
    const key = match.toLowerCase();
    if (stop.has(key) || seen.has(key)) continue;
    seen.add(key);
    values.push(match);
    if (values.length >= 5) break;
  }
  return values.length ? values : ["关键词"];
}

function renderEvidenceChain(graphId, graph, evidence, sessionGraph = null) {
  const empty = !evidence.length;
  const graphSvg = empty ? `<div class="evidence-empty">当前回答没有可展示的依据链。</div>` : renderEvidenceFlowSvg(graphId, graph);
  const sessionSvg = sessionGraph ? renderEvidenceSessionSvg(graphId, sessionGraph) : `<div class="evidence-empty">当前会话还没有累积依据链。</div>`;
  const rawButton = SHOW_TECH_DETAILS ? `<button class="evidence-view-button debug-toggle" type="button" data-evidence-view="raw">调试数据</button>` : "";
  const rawPanel = SHOW_TECH_DETAILS ? `<pre class="evidence-raw-view hidden" data-evidence-panel="raw">${escapeHtml(JSON.stringify({ graph, sessionGraph, evidence }, null, 2))}</pre>` : "";
  return `
    <section class="evidence-chain evidence-flow-shell" data-evidence-chain data-graph-id="${escapeHtml(graphId)}">
      <div class="evidence-flow-header">
        <div>
          <h3>依据链</h3>
          <p>展示问题、关键概念、文档依据和回答要点之间的支持关系。</p>
        </div>
        <div class="evidence-view-toggle" role="tablist" aria-label="依据视图">
          <button class="evidence-view-button active" type="button" data-evidence-view="graph">当前视角</button>
          <button class="evidence-view-button" type="button" data-evidence-view="session">会话视角</button>
          <button class="evidence-view-button" type="button" data-evidence-view="list">来源列表</button>
          ${rawButton}
        </div>
      </div>
      ${renderSourceLegend()}
      <div class="evidence-flow-view" data-evidence-panel="graph">${graphSvg}</div>
      <div class="evidence-session-view hidden" data-evidence-panel="session">${sessionSvg}</div>
      <div class="evidence-list-view hidden" data-evidence-panel="list">${renderEvidenceList(evidence)}</div>
      ${rawPanel}
      <div class="evidence-detail" data-evidence-detail>点击依据节点查看来源、相关概念和原文片段。</div>
    </section>`;
}

function renderSourceLegend() {
  return `
    <div class="source-legend" aria-label="来源图例">
      <span><i class="source-dot source-document"></i>文档依据</span>
      <span><i class="source-dot source-inferred"></i>综合判断</span>
      <span><i class="source-dot source-web_search"></i>联网资料</span>
      <span><i class="source-dot source-model_prior"></i>补充说明</span>
      <span><i class="source-dot source-unsupported"></i>待核实</span>
    </div>`;
}

function renderEvidenceFlowSvg(graphId, graph) {
  const typed = {
    query: graph.nodes.filter((node) => node.type === "query"),
    entity: graph.nodes.filter((node) => node.type === "entity").slice(0, 6),
    evidence: graph.nodes.filter((node) => ["evidence", "retrieved_chunk", "web_result"].includes(node.type)).slice(0, 8),
    answer: graph.nodes.filter((node) => ["answer", "answer_claim", "inference", "model_prior", "unsupported"].includes(node.type)).slice(0, 8),
  };
  const columns = [
    { type: "query", x: 36, width: 148, title: "问题" },
    { type: "entity", x: 230, width: 156, title: "关键概念" },
    { type: "evidence", x: 432, width: 238, title: "文档依据" },
    { type: "answer", x: 726, width: 168, title: "回答要点" },
  ];
  const rowHeight = 82;
  const maxRows = Math.max(1, typed.entity.length, typed.evidence.length);
  const height = Math.max(250, 92 + maxRows * rowHeight);
  const nodePositions = new Map();
  const layers = [];
  for (const column of columns) {
    const nodes = typed[column.type] || [];
    const gap = height / (nodes.length + 1);
    nodes.forEach((node, index) => {
      const y = Math.max(76, gap * (index + 1));
      const h = node.type === "evidence" ? 58 : 44;
      nodePositions.set(node.id, { x: column.x, y, width: column.width, height: h });
      layers.push(renderEvidenceSvgNode(graphId, node, column.x, y, column.width, h));
    });
  }
  const edges = [];
  for (const edge of graph.edges || []) {
    const source = nodePositions.get(edge.source);
    const target = nodePositions.get(edge.target);
    if (!source || !target) continue;
    const sx = source.x + source.width;
    const sy = source.y;
    const tx = target.x;
    const ty = target.y;
    const mx = (sx + tx) / 2;
    edges.push(`<path class="evidence-flow-edge ${escapeHtml(edge.type || "")}" data-edge-source="${escapeHtml(edge.source)}" data-edge-target="${escapeHtml(edge.target)}" d="M ${sx} ${sy} C ${mx} ${sy}, ${mx} ${ty}, ${tx} ${ty}" />`);
  }
  const columnTitles = columns
    .map((column) => `<text class="evidence-column-title" x="${column.x}" y="28">${escapeHtml(column.title)}</text>`)
    .join("");
  return `
    <div class="evidence-flow-canvas">
      <svg class="evidence-flow-svg" viewBox="0 0 930 ${height}" role="img" aria-label="实时依据链图">
        <g class="evidence-column-titles">${columnTitles}</g>
        <g class="evidence-flow-edges">${edges.join("")}</g>
        <g class="evidence-flow-nodes">${layers.join("")}</g>
      </svg>
    </div>`;
}

function renderEvidenceSessionSvg(graphId, sessionGraph) {
  const turns = Array.isArray(sessionGraph.turns) ? sessionGraph.turns : [];
  if (!turns.length) return `<div class="evidence-empty">当前会话还没有累积依据链。</div>`;
  const nodesByQuery = new Map();
  for (const node of sessionGraph.nodes || []) {
    const queryId = node.query_id || (node.type === "query" ? node.id : "");
    if (!queryId) continue;
    if (!nodesByQuery.has(queryId)) nodesByQuery.set(queryId, []);
    nodesByQuery.get(queryId).push(node);
  }
  const width = 980;
  const rowHeight = 132;
  const height = Math.max(220, 78 + turns.length * rowHeight);
  const positions = new Map();
  const layers = [];
  const columns = {
    query: { x: 36, width: 150 },
    entity: { x: 230, width: 150 },
    evidence: { x: 430, width: 230 },
    claim: { x: 730, width: 190 },
  };
  turns.slice(-8).forEach((turn, turnIndex) => {
    const yBase = 70 + turnIndex * rowHeight;
    const turnNodes = nodesByQuery.get(turn.query_id) || [];
    const queryNode = turnNodes.find((node) => node.type === "query") || { id: turn.query_id, type: "query", label: "用户问题", detail: turn.query, source_type: "query" };
    const entityNodes = turnNodes.filter((node) => node.type === "entity").slice(0, 2);
    const evidenceNodes = turnNodes.filter((node) => ["retrieved_chunk", "evidence", "web_result"].includes(node.type)).slice(0, 2);
    const claimNodes = turnNodes.filter((node) => ["answer_claim", "model_prior", "unsupported", "inference"].includes(node.type)).slice(0, 2);
    [
      [queryNode, columns.query, yBase, 46],
      ...entityNodes.map((node, index) => [node, columns.entity, yBase + (index - 0.5) * 38, 34]),
      ...evidenceNodes.map((node, index) => [node, columns.evidence, yBase + (index - 0.5) * 46, 42]),
      ...claimNodes.map((node, index) => [node, columns.claim, yBase + (index - 0.5) * 46, 42]),
    ].forEach(([node, column, y, h]) => {
      positions.set(node.id, { x: column.x, y, width: column.width, height: h });
      layers.push(renderEvidenceSvgNode(graphId, node, column.x, y, column.width, h));
    });
  });
  const edges = [];
  for (const edge of sessionGraph.edges || []) {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) continue;
    const sx = source.x + source.width;
    const sy = source.y;
    const tx = target.x;
    const ty = target.y;
    const mx = (sx + tx) / 2;
    edges.push(`<path class="evidence-flow-edge ${escapeHtml(edge.type || "")}" data-edge-source="${escapeHtml(edge.source)}" data-edge-target="${escapeHtml(edge.target)}" d="M ${sx} ${sy} C ${mx} ${sy}, ${mx} ${ty}, ${tx} ${ty}" />`);
  }
  const titles = [
    ["问题", columns.query.x],
    ["关键概念", columns.entity.x],
    ["文档依据", columns.evidence.x],
    ["回答要点", columns.claim.x],
  ]
    .map(([label, x]) => `<text class="evidence-column-title" x="${x}" y="28">${label}</text>`)
    .join("");
  return `
    <div class="evidence-flow-canvas session-canvas">
      <svg class="evidence-flow-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="完整会话依据链图">
        <g class="evidence-column-titles">${titles}</g>
        <g class="evidence-flow-edges">${edges.join("")}</g>
        <g class="evidence-flow-nodes">${layers.join("")}</g>
      </svg>
    </div>`;
}

function renderEvidenceSvgNode(graphId, node, x, y, width, height) {
  const title = evidenceNodeTooltip(node);
  const sourceType = node.source_type || (node.type === "entity" ? "entity" : node.type === "query" ? "query" : "document");
  const isEvidence = ["evidence", "retrieved_chunk", "web_result"].includes(node.type);
  const label = isEvidence ? `${humanEvidenceLabel(node.evidence_id)} ${shortFileName(node.doc_name || node.file_name || node.label)}` : node.label;
  const meta = isEvidence
    ? `${sourceTypeLabel(sourceType)}${formatScore(node.score) ? ` · 相关度 ${formatScore(node.score)}` : ""}${node.page ? ` · 第 ${node.page} 页` : ""}`
    : `${sourceTypeLabel(sourceType)} · ${nodeTypeLabel(node.type)}`;
  return `
    <g class="evidence-flow-node ${escapeHtml(node.type)} source-${escapeHtml(sourceType)}" tabindex="0" data-graph-id="${escapeHtml(graphId)}" data-node-id="${escapeHtml(node.id)}" transform="translate(${x},${y - height / 2})">
      <title>${escapeHtml(title)}</title>
      <rect width="${width}" height="${height}" rx="8"></rect>
      <text class="node-label" x="12" y="${height / 2 - 3}">${escapeHtml(shorten(label, isEvidence ? 30 : 20))}</text>
      <text class="node-meta" x="12" y="${height / 2 + 17}">${escapeHtml(shorten(meta, 28))}</text>
    </g>`;
}

function renderEvidenceList(evidence) {
  if (!evidence.length) return `<div class="evidence-empty">当前回答没有可展示的依据链。</div>`;
  return evidence.map((item, index) => `<article class="evidence-item">
    <strong>依据 ${index + 1} · ${escapeHtml(item.doc_name || "未命名来源")}</strong>
    <span><b class="source-pill source-${escapeHtml(item.source_type)}">${escapeHtml(sourceTypeLabel(item.source_type))}</b>${formatScore(item.score) ? ` · 相关度 ${escapeHtml(formatScore(item.score))}` : ""}${item.page ? ` · 第 ${escapeHtml(item.page)} 页` : ""}</span>
    <p>${escapeHtml(item.snippet || "")}</p>
  </article>`).join("");
}

function evidenceNodeTooltip(node) {
  if (!["evidence", "retrieved_chunk", "web_result"].includes(node.type)) return `${node.label || ""}
${node.detail || node.text || ""}`;
  const entities = (node.entities || []).join(", ");
  return `${sourceTypeLabel(node.source_type || "document")} ${node.doc_name || node.file_name || ""}
相关度: ${formatScore(node.score)}${node.page ? `
页码: ${node.page}` : ""}${entities ? `
关键概念: ${entities}` : ""}
${node.snippet || node.raw_text || node.detail || ""}`;
}

function formatScore(value) {
  const score = Number(value);
  return Number.isFinite(score) ? score.toFixed(3).replace(/0+$/, "").replace(/\.$/, "") : "";
}

function shortFileName(value) {
  return String(value || "未命名来源").split(/[\/]/).pop();
}

function humanEvidenceLabel(value) {
  const match = String(value || "").match(/^E(\d+)$/i);
  return match ? `依据 ${match[1]}` : "依据";
}

function nodeTypeLabel(value) {
  const labels = { query: "用户问题", entity: "关键概念", evidence: "文档依据", retrieved_chunk: "文档依据", web_result: "联网资料", answer: "回答要点", answer_claim: "回答要点", inference: "综合判断", model_prior: "补充说明", unsupported: "待核实", document: "文档", section: "章节", topic: "主题", chunk: "依据", chunk_type: "主题", root: "总览", analysis: "分析" };
  return labels[value] || value || "节点";
}

function nodeKindLabel(value) { return nodeTypeLabel(value); }

function sourceTypeLabel(value) {
  const labels = { document: "文档依据", inferred: "综合判断", web_search: "联网资料", model_prior: "补充说明", unsupported: "待核实", query: "用户问题", entity: "关键概念" };
  return labels[value] || value || "来源";
}

function displayNodeText(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  const exact = {
    "Knowledge Base": "知识库总览",
    evidence: "文档依据",
    document: "文档",
    section: "章节",
    topic: "主题",
    chunk: "依据",
    entity: "关键概念",
    keyword: "关键词",
    "document entity / keyword": "文档概念",
  };
  if (exact[text]) return exact[text];
  return text;
}

function clampSpeechRate(value) {
  const rate = Number(value);
  if (!Number.isFinite(rate)) return DEFAULT_SPEECH_RATE;
  return Math.min(MAX_SPEECH_RATE, Math.max(MIN_SPEECH_RATE, rate));
}

function loadSpeechRate() {
  try {
    return clampSpeechRate(window.localStorage?.getItem(SPEECH_RATE_STORAGE_KEY));
  } catch {
    return DEFAULT_SPEECH_RATE;
  }
}

function persistSpeechRate(value) {
  try {
    window.localStorage?.setItem(SPEECH_RATE_STORAGE_KEY, String(value));
  } catch {
    // localStorage may be unavailable in some embedded browsers.
  }
}

function formatSpeechRate(value) {
  return `${clampSpeechRate(value).toFixed(2).replace(/0$/, "").replace(/\.$/, "")}x`;
}

function syncSpeechRateUi() {
  if (speechRateInput) speechRateInput.value = String(speechRate);
  if (speechRateLabel) speechRateLabel.textContent = formatSpeechRate(speechRate);
}

function handleSpeechRateInput(event) {
  speechRate = clampSpeechRate(event.target.value);
  persistSpeechRate(speechRate);
  syncSpeechRateUi();
  if (!isSpeaking || !currentSpeechText) return;
  voiceStatus.textContent = `语速已调整为 ${formatSpeechRate(speechRate)}，正在重新朗读...`;
  window.clearTimeout(speechRateRestartTimer);
  speechRateRestartTimer = window.setTimeout(() => {
    if (!currentSpeechText || !("speechSynthesis" in window)) return;
    pendingSpeechRestart = true;
    window.speechSynthesis.cancel();
    window.setTimeout(() => speakText(currentSpeechText), 80);
  }, 260);
}

function initVoiceInteraction() {
  const canSpeak = "speechSynthesis" in window;

  if (speakLastButton) {
    speakLastButton.disabled = true;
    speakLastButton.addEventListener("click", speakLastAnswer);
  }
  if (stopSpeechButton) {
    stopSpeechButton.disabled = true;
    stopSpeechButton.textContent = "停朗读";
    stopSpeechButton.title = "停止朗读";
    stopSpeechButton.addEventListener("click", stopSpeaking);
  }
  if (speechRateInput) speechRateInput.disabled = !canSpeak;
  syncSpeechRateUi();
  if (voiceStatus) voiceStatus.textContent = canSpeak ? "朗读就绪" : "当前浏览器不支持朗读";
  speechRateInput?.addEventListener("input", handleSpeechRateInput);
}

function speakLastAnswer() {
  if (isSpeaking) {
    stopSpeaking();
    return;
  }
  const readableText = getReadableAnswerText();
  if (!readableText) return;
  speakText(readableText);
}

async function handleMessageSpeakClick(event) {
  const button = event.currentTarget;
  if (isSpeaking && currentSpeechButton === button) {
    stopSpeaking();
    return;
  }
  const readableText = getReadableMessageText(button.closest(".message"));
  if (!readableText) return;
  await speakText(readableText, { sourceButton: button });
}

function setActiveSpeechButton(button) {
  if (currentSpeechButton && currentSpeechButton !== button) {
    currentSpeechButton.classList.remove("is-speaking");
    currentSpeechButton.setAttribute("aria-label", "朗读这条回答");
    currentSpeechButton.title = "朗读这条回答";
  }
  currentSpeechButton = button || null;
  if (currentSpeechButton) {
    currentSpeechButton.classList.add("is-speaking");
    currentSpeechButton.setAttribute("aria-label", "停止朗读这条回答");
    currentSpeechButton.title = "停止朗读这条回答";
  }
}

async function speakText(readableText, options = {}) {
  const token = ttsPlaybackToken + 1;
  ttsPlaybackToken = token;
  stopSpeaking({ silent: true });
  ttsPlaybackToken = token;
  currentSpeechText = readableText;
  isSpeaking = true;
  setActiveSpeechButton(options.sourceButton || null);
  voiceStatus.textContent = "正在生成本地中文朗读...";
  speakLastButton.textContent = "\u505c\u6b62\u6717\u8bfb";
  stopSpeechButton.textContent = "停朗读";
  stopSpeechButton.title = "停止朗读";
  stopSpeechButton.disabled = false;
  try {
    const response = await fetch(`${API_BASE}/api/voice/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: readableText, rate: speechRate }),
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `HTTP ${response.status}`);
    }
    const blob = await response.blob();
    if (token !== ttsPlaybackToken) return;
    if (currentTtsAudioUrl) URL.revokeObjectURL(currentTtsAudioUrl);
    currentTtsAudioUrl = URL.createObjectURL(blob);
    currentTtsAudio = new Audio(currentTtsAudioUrl);
    currentTtsAudio.onplay = () => {
      isSpeaking = true;
      voiceStatus.textContent = `正在用本地中文TTS朗读... 语速 ${formatSpeechRate(speechRate)}`;
    };
    currentTtsAudio.onended = () => resetSpeechUi("朗读就绪");
    currentTtsAudio.onerror = () => resetSpeechUi("本地TTS播放被中断");
    await currentTtsAudio.play();
  } catch (error) {
    if (token !== ttsPlaybackToken) return;
    if ("speechSynthesis" in window) {
      voiceStatus.textContent = "本地TTS不可用，已切换浏览器朗读";
      speakTextWithBrowser(readableText);
    } else {
      resetSpeechUi("本地TTS不可用，当前浏览器也不能朗读");
      showToast(`中文TTS启动失败：${error.message}`, "error", 4200);
    }
  }
}

function speakTextWithBrowser(readableText) {
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(readableText);
  utterance.lang = "zh-CN";
  utterance.rate = speechRate;
  utterance.pitch = 1;
  currentSpeechText = readableText;
  utterance.onstart = () => {
    pendingSpeechRestart = false;
    isSpeaking = true;
    voiceStatus.textContent = `正在朗读... 语速 ${formatSpeechRate(speechRate)}`;
    speakLastButton.textContent = "\u505c\u6b62\u6717\u8bfb";
    stopSpeechButton.textContent = "停朗读";
    stopSpeechButton.title = "停止朗读";
    stopSpeechButton.disabled = false;
  };
  utterance.onend = () => {
    if (pendingSpeechRestart) return;
    isSpeaking = false;
    currentSpeechText = "";
    voiceStatus.textContent = "朗读就绪";
    speakLastButton.textContent = "\u6717\u8bfb";
    stopSpeechButton.disabled = true;
  };
  utterance.onerror = () => {
    if (pendingSpeechRestart) return;
    isSpeaking = false;
    currentSpeechText = "";
    voiceStatus.textContent = "朗读播放被中断";
    speakLastButton.textContent = "\u6717\u8bfb";
    stopSpeechButton.disabled = true;
  };
  window.speechSynthesis.speak(utterance);
}

function resetSpeechUi(statusText = "朗读就绪") {
  isSpeaking = false;
  currentSpeechText = "";
  setActiveSpeechButton(null);
  voiceStatus.textContent = statusText;
  speakLastButton.textContent = "\u6717\u8bfb";
  stopSpeechButton.textContent = "停朗读";
  stopSpeechButton.title = "停止朗读";
  stopSpeechButton.disabled = true;
}

function stopSpeaking(options = {}) {
  window.clearTimeout(speechRateRestartTimer);
  ttsPlaybackToken += 1;
  pendingSpeechRestart = false;
  if (currentTtsAudio) {
    currentTtsAudio.pause();
    currentTtsAudio.currentTime = 0;
    currentTtsAudio = null;
  }
  if (currentTtsAudioUrl) {
    URL.revokeObjectURL(currentTtsAudioUrl);
    currentTtsAudioUrl = "";
  }
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  resetSpeechUi(options.silent ? "朗读就绪" : "已停止朗读");
}

function updateSpeechButtons() {
  speakLastButton.disabled = !getReadableAnswerText();
}

function setIngestState(nextState = {}) {
  activeIngestState = {
    ...activeIngestState,
    ...nextState,
  };
  updateAskAvailability();
  document.body.classList.toggle("ingest-running", Boolean(activeIngestState.running));
  document.body.classList.toggle("coarse-ready", Boolean(activeIngestState.coarseReady));
}

function updateAskAvailability() {
  const ingestRunning = Boolean(activeIngestState.running);
  if (!sendButton) return;
  sendButton.disabled = isGeneratingAnswer;
  if (isGeneratingAnswer) {
    sendButton.textContent = "...";
    sendButton.title = "正在生成回答";
  } else if (ingestRunning) {
    sendButton.textContent = activeIngestState.coarseReady ? "↑" : "...";
    sendButton.title = activeIngestState.coarseReady ? "可基于当前内容提问" : "正在整理知识";
  } else {
    sendButton.textContent = "↑";
    sendButton.title = "发送并生成答案";
  }
}

function positionFloatingComposer() {
  const composer = document.querySelector("#chatForm.floating-composer");
  const panel = document.querySelector(".conversation-panel");
  if (!composer || !panel) return;
  const rect = panel.getBoundingClientRect();
  const compact = window.innerWidth <= 920;
  const centerX = compact ? window.innerWidth / 2 : rect.left + rect.width / 2;
  document.documentElement.style.setProperty("--composer-center-x", `${Math.round(centerX)}px`);
  document.documentElement.style.setProperty("--composer-bottom", compact ? "0.72rem" : "1.1rem");
  document.documentElement.style.setProperty("--composer-panel-width", `${Math.round(Math.max(320, compact ? window.innerWidth : rect.width))}px`);
}

function currentIngestLockMessage() {
  const total = activeIngestState.totalDocs || "?";
  const processed = activeIngestState.processedDocs || 0;
  const chunks = activeIngestState.chunks || 0;
  const currentFile = activeIngestState.currentFile ? `，正在整理 ${shorten(activeIngestState.currentFile, 34)}` : "";
  return `知识库仍在整理中：已处理 ${processed}/${total} 个文档，形成 ${chunks} 条可用知识${currentFile}。本次回答会基于当前已整理内容，右侧知识树会继续更新。`;
}

function getReadableAnswerText() {
  const selected = String(window.getSelection?.() || "").trim();
  if (selected) return cleanAnswerTextForSpeech(selected);
  const answerEls = messages.querySelectorAll("[data-answer-main]");
  const answerEl = answerEls.length ? answerEls[answerEls.length - 1] : null;
  const raw = answerEl ? answerEl.innerText : currentAnswerText || lastAssistantAnswer;
  return cleanAnswerTextForSpeech(raw);
}

function getReadableMessageText(messageCard) {
  if (!messageCard) return "";
  const answerEl = messageCard.querySelector("[data-answer-main]");
  const body = messageCard.querySelector(".message-body");
  const raw = answerEl ? answerEl.innerText : body?.innerText || "";
  return cleanAnswerTextForSpeech(raw);
}

function setFeatureButtonsDisabled(disabled) {
  featureButtons.forEach((button) => {
    if (disabled && !button.classList.contains("loading")) button.disabled = true;
    else if (!disabled) button.disabled = false;
  });
}

function setFeatureLoading(button, loading) {
  if (!button) return;
  button.classList.toggle("loading", loading);
  button.disabled = loading;
  button.setAttribute("aria-busy", loading ? "true" : "false");
}

function compactVisibleText(value, maxLength = 160) {
  return shorten(String(value || "").replace(/\s+/g, " ").trim(), maxLength);
}

function buildAssistantModuleContext() {
  const config = FEATURE_SHOWCASES[activeFeatureShowcaseKey] || FEATURE_SHOWCASES.crop;
  const lines = [
    `当前打开模块：${config.title}。${config.summary}`,
  ];
  if (activeFeatureDetailState) {
    lines.push(`当前点开的详情：${activeFeatureDetailState.title}。${activeFeatureDetailState.body}`);
  }
  const metricText = (config.metrics || [])
    .slice(0, 4)
    .map(([label, value, status]) => `${label}:${value}/${status}`)
    .join("；");
  if (metricText) lines.push(`模块指标：${metricText}`);
  const actionText = (config.cards || [])
    .slice(0, 3)
    .map(([title, body]) => `${title}:${body}`)
    .join("；");
  if (actionText) lines.push(`模块动作：${actionText}`);
  const liveText = [liveTemperature?.innerText, liveWeatherRisk?.innerText].filter(Boolean).join("；");
  if (liveText) lines.push(`天气提醒：${compactVisibleText(liveText, 140)}`);
  if (latestWeatherHorizons.length) {
    const horizonText = latestWeatherHorizons.slice(0, 3).map((item) => `${item.label}:${item.risk || ""}${item.action ? `，${item.action}` : ""}`).join("；");
    lines.push(`天气分时段：${compactVisibleText(horizonText, 220)}`);
  }
  const routeText = compactVisibleText(routeMarketPanel?.innerText || "", 220);
  if (routeText) lines.push(`产地到市场：${routeText}`);
  const marketText = compactVisibleText([marketPriceDecision?.innerText, marketPriceInsight?.innerText].filter(Boolean).join("；"), 240);
  if (marketText) lines.push(`行情农资：${marketText}`);
  const trendText = compactVisibleText(competitionTrendCard?.innerText || "", 240);
  if (trendText) lines.push(`创业大赛与头条趋势：${trendText}`);
  const newsText = latestHeadlineItems.slice(0, 4).map((item) => item.title || item.snippet || "").filter(Boolean).join("；");
  if (newsText) lines.push(`资讯线索：${compactVisibleText(newsText, 220)}`);
  return lines.map((line) => `- ${line}`).join("\n");
}

async function runRealtimeQuery(query, options = {}) {
  const trimmedQuery = String(query || "").trim();
  if (!trimmedQuery || isGeneratingAnswer) return;
  updateLocationContextFromInputs();
  const triggerButton = options.triggerButton || null;
  const displayQuery = String(options.displayQuery || trimmedQuery).trim();

  if (activeIngestState.running) {
    addMessage("system", currentIngestLockMessage(), "system");
    showToast("已基于当前可用内容开始回答，后台会继续完善知识树。", "success", 3000);
  }

  addMessage("user", escapeHtml(userFacingQueryLabel(displayQuery)));
  lastUserQuery = trimmedQuery;
  if (options.clearInput !== false) queryInput.value = "";
  isGeneratingAnswer = true;
  setFeatureLoading(triggerButton, true);
  setFeatureButtonsDisabled(true);
  updateAskAvailability();

  try {
    const moduleContext = options.skipModuleAggregation ? "" : buildAssistantModuleContext();
    const queryPayload = {
      query: trimmedQuery,
      top_k: options.topK || 3,
      session_id: currentSessionId,
      regional_intelligence: options.regionalIntelligence ?? true,
      production_location: locationContextState.productionLocation || DEFAULT_PRODUCTION_LOCATION,
      market_location: locationContextState.marketLocation || DEFAULT_MARKET_LOCATION,
      answer_language: appSettings.answerLanguage || "auto",
    };
    if (moduleContext) queryPayload.module_context = moduleContext;
    appendLocationPointPayload(queryPayload);
    const shouldSearch = options.useWebSearch ?? Boolean(webSearchToggle?.checked);
    if (shouldSearch) {
      queryPayload.web_search = true;
      queryPayload.web_search_k = options.webSearchK || 3;
    }
    if (appliedAnswerModel) queryPayload.model = appliedAnswerModel;
    const result = await fetchJson("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(queryPayload),
    });
    if (result.selected_model && modelActiveName) modelActiveName.textContent = result.selected_model;
    if (result.session_id) {
      currentSessionId = result.session_id;
      try {
        window.localStorage?.setItem(SESSION_STORAGE_KEY, currentSessionId);
      } catch {
        // Session still works in memory.
      }
    }
    const answerText = cleanAnswerTextForDisplay(stripEvidenceChain(result.answer || "\u672a\u751f\u6210\u56de\u7b54\u3002"));
    currentAnswerText = answerText;
    lastAssistantAnswer = answerText;
    updateSpeechButtons();
    addMessage("assistant", renderAssistantResponse(result));
    renderTree();
    updateSessionMemorySummary(result.session_evidence_graph || {});
    await loadSessions();
  } catch (error) {
    addMessage("system", `\u751f\u6210\u5931\u8d25\uff1a${escapeHtml(error.message)}`, "system");
  } finally {
    isGeneratingAnswer = false;
    setFeatureLoading(triggerButton, false);
    setFeatureButtonsDisabled(false);
    updateAskAvailability();
  }
}

async function handleFeatureAction(button) {
  const feature = FEATURE_ACTIONS[button?.dataset?.feature];
  if (!feature || isGeneratingAnswer) return;
  const showcaseKey = button?.dataset?.showcaseFeature;
  if (showcaseKey && FEATURE_SHOWCASES[showcaseKey]) {
    openFeatureWorkbench(showcaseKey);
    showToast(`已打开：${FEATURE_SHOWCASES[showcaseKey].title}`, "success", 1400);
    return;
  }
  queryInput.value = feature.title;
  showToast(`实时进入：${feature.title}`, "success", 1600);
  await runRealtimeQuery(feature.query, {
    displayQuery: feature.title,
    clearInput: true,
    triggerButton: button,
    topK: feature.topK || 7,
    useWebSearch: feature.useWebSearch ?? Boolean(webSearchToggle?.checked),
    webSearchK: feature.webSearchK || 6,
    regionalIntelligence: true,
  });
}

function handleQueryInputKeydown(event) {
  if (event.key !== "Enter") return;
  if (event.shiftKey || event.ctrlKey || event.altKey || event.metaKey) return;
  if (event.isComposing || event.keyCode === 229) return;
  event.preventDefault();
  if (!queryInput.value.trim() || isGeneratingAnswer || sendButton?.disabled) return;
  if (chatForm.requestSubmit) {
    chatForm.requestSubmit(sendButton);
  } else {
    chatForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  }
}

queryInput?.addEventListener("keydown", handleQueryInputKeydown);

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await runRealtimeQuery(queryInput.value, {
    clearInput: true,
    topK: 6,
    useWebSearch: Boolean(webSearchToggle?.checked),
    webSearchK: 6,
    regionalIntelligence: true,
  });
});

featureButtons.forEach((button) => {
  button.addEventListener("click", () => handleFeatureAction(button));
});

leftFeatureButtons.forEach((button) => {
  button.addEventListener("click", () => openFeatureWorkbench(button.dataset.showcaseFeature));
});

featureWorkbench?.addEventListener("click", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  const detailAsk = target?.closest("[data-feature-detail-ask]");
  if (detailAsk) {
    askActiveFeatureDetail(detailAsk);
    return;
  }
  const detailButton = target?.closest("[data-feature-detail]");
  if (detailButton) {
    const kind = detailButton.dataset.featureDetail || "visual";
    const index = Number(detailButton.dataset.featureDetailIndex || 0);
    renderFeatureDrilldown(buildFeatureDetail(kind, index, detailButton));
    detailButton.classList.add("was-opened");
    showToast("已展开详情", "success", 1000);
    return;
  }
  const button = target?.closest("[data-feature-workbench-ask]");
  if (button) askFeatureWorkbench(button.dataset.featureWorkbenchAsk, button);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) uploadFiles([...fileInput.files]);
  fileInput.value = "";
});

["dragenter", "dragover"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragging");
  });
});

["dragleave", "drop"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragging");
  });
});

dropzone.addEventListener("drop", (event) => {
  const files = [...event.dataTransfer.files];
  if (files.length) uploadFiles(files);
});

async function uploadFiles(files) {
  if (activeUploadController) {
    addMessage("system", "\u5df2\u6709\u4e0a\u4f20\u4efb\u52a1\u5728\u8fdb\u884c\uff0c\u9700\u8981\u5148\u4e2d\u65ad\u5f53\u524d\u4e0a\u4f20\u3002", "system");
    return;
  }
  activeUploadController = new AbortController();
  uploadCancelled = false;
  primeNotifySound();
  cancelUploadButton.classList.remove("hidden");
  cancelUploadButton.disabled = false;
  setIngestState({
    running: true,
    coarseReady: false,
    stage: "coarse_indexing",
    processedDocs: 0,
    totalDocs: files.length,
    chunks: 0,
    coarseDocs: 0,
    refinedDocs: 0,
    coarseChunks: 0,
    refinedChunks: 0,
    currentFile: "",
  });
  uploadStatus.textContent = `\u51c6\u5907\u4e0a\u4f20 ${files.length} \u4e2a\u6587\u4ef6`;
  addMessage("system", `\u5f00\u59cb\u5feb\u901f\u4e0a\u4f20 ${files.length} \u4e2a\u6587\u4ef6\uff1a\u6587\u4ef6\u5148\u5feb\u901f\u843d\u5230\u672c\u5730\uff0c\u968f\u540e\u5408\u5e76\u4e3a\u4e00\u4e2a\u540e\u53f0\u6444\u53d6\u4efb\u52a1\uff0c\u5b8c\u6210\u540e\u4f1a\u63d0\u793a\u53ef\u4ee5\u5f00\u59cb\u63d0\u95ee\u3002`, "system");
  const summaries = [];

  try {
    const smallFiles = files.filter((file) => file.size <= LARGE_FILE_BYTES);
    const largeFiles = files.filter((file) => file.size > LARGE_FILE_BYTES);
    const batches = createUploadBatches(smallFiles);
    const jobIds = [];
    const ingestPaths = [];
    const savedPaths = [];
    const extractedPaths = [];
    let completedJobs = [];

    for (let index = 0; index < batches.length; index += 1) {
      assertUploadActive(activeUploadController.signal);
      const batch = batches[index];
      uploadStatus.textContent = `\u6b63\u5728\u6279\u91cf\u4e0a\u4f20 ${index + 1}/${batches.length}\uff1a${batch.length} \u4e2a\u6587\u4ef6`;
      const summary = await uploadBatch(batch, activeUploadController.signal);
      summaries.push(summary);
      if (summary.job_id) jobIds.push(summary.job_id);
      collectDeferredIngest(summary, ingestPaths, savedPaths, extractedPaths);
    }

    for (let index = 0; index < largeFiles.length; index += 1) {
      const file = largeFiles[index];
      assertUploadActive(activeUploadController.signal);
      uploadStatus.textContent = `\u6b63\u5728\u5e76\u53d1\u4e0a\u4f20\u5927\u6587\u4ef6 ${index + 1}/${largeFiles.length}\uff1a${file.name}`;
      const summary = await uploadChunked(file, activeUploadController.signal);
      summaries.push(summary);
      if (summary.job_id) jobIds.push(summary.job_id);
      collectDeferredIngest(summary, ingestPaths, savedPaths, extractedPaths);
    }

    if (ingestPaths.length) {
      const dedupedPaths = [...new Set(ingestPaths)];
      uploadStatus.textContent = `\u6587\u4ef6\u5df2\u4fdd\u5b58\uff0c\u6b63\u5728\u542f\u52a8\u5408\u5e76\u6444\u53d6\u4efb\u52a1\uff1a${dedupedPaths.length} \u4e2a\u53ef\u5904\u7406\u6587\u4ef6`;
      const scheduled = await createIngestJob(dedupedPaths, savedPaths, extractedPaths, activeUploadController.signal);
      summaries.push(scheduled);
      if (scheduled.job_id) jobIds.push(scheduled.job_id);
    }

    if (jobIds.length) {
      uploadStatus.textContent = "后台整理中：先生成初版知识树，就绪后即可先问，随后继续深度完善";
      treeLiveStatusText = "正在生成初版知识树";
      uploadStatus.textContent = `后台整理：${jobIds.length} 个任务，先出初版知识树再持续完善`;
      completedJobs = await waitForIngestJobs(jobIds, activeUploadController.signal);
    }

    const finalSummaries = completedJobs.length ? completedJobs : summaries;
    const docs = finalSummaries.reduce((sum, item) => sum + (item.documents_processed || 0), 0);
    const chunks = finalSummaries.reduce((sum, item) => sum + (item.chunks_written || 0), 0);
    const extracted = finalSummaries.reduce((sum, item) => sum + (item.files_extracted?.length || 0), 0);
    const duration = finalSummaries.reduce((sum, item) => sum + (item.duration_seconds || 0), 0);
    treeLiveStatusText = "";
    setIngestState({
      running: false,
      coarseReady: false,
      stage: "refined",
      processedDocs: docs,
      totalDocs: docs || files.length,
      chunks,
      coarseDocs: docs,
      refinedDocs: docs,
      coarseChunks: 0,
      refinedChunks: chunks,
      currentFile: "",
    });
    uploadStatus.textContent = `整理完成：${docs} 个文档，${chunks} 条知识，可以开始提问`;
    addMessage("assistant", `上传整理完成：处理 ${docs} 个文档，形成 ${chunks} 条可用知识${extracted ? `，从压缩包中解出 ${extracted} 个可整理文件` : ""}。`);
    showIngestReadyNotification(docs, chunks, extracted, duration);
    await loadTree();
    await loadRuleMemory();
  } catch (error) {
    if (error.name === "AbortError" || uploadCancelled) {
      uploadStatus.textContent = "\u4e0a\u4f20\u5df2\u4e2d\u65ad";
      addMessage("system", "\u5df2\u4e2d\u65ad\u4e0a\u4f20\uff0c\u672a\u5b8c\u6210\u7684\u5206\u5757\u5df2\u6e05\u7406\u3002", "system");
    } else {
      uploadStatus.textContent = "\u4e0a\u4f20\u5931\u8d25";
      addMessage("system", `\u4e0a\u4f20\u5931\u8d25\uff1a${escapeHtml(error.message)}`, "system");
    }
    setIngestState({ running: false, currentFile: "" });
  } finally {
    activeUploadController = null;
    activeChunkFileId = "";
    cancelUploadButton.disabled = true;
    cancelUploadButton.classList.add("hidden");
  }
}

async function uploadSingle(file, signal) {
  return uploadBatch([file], signal);
}

async function uploadBatch(files, signal) {
  const form = new FormData();
  for (const file of files) form.append("files", file, file.name);
  form.append("defer_ingest", "true");
  return fetchJson("/upload", { method: "POST", body: form, signal });
}

async function uploadChunked(file, signal) {
  const totalChunks = Math.ceil(file.size / CHUNK_BYTES);
  const fileId = `${Date.now()}-${file.name}-${file.size}`.replace(/[^a-zA-Z0-9_-]/g, "_");
  let summary = { complete: false };
  activeChunkFileId = fileId;
  let nextIndex = 0;
  let uploaded = 0;

  try {
    const worker = async () => {
      while (nextIndex < totalChunks) {
        assertUploadActive(signal);
        const index = nextIndex;
        nextIndex += 1;
        const result = await uploadOneChunk(file, fileId, index, totalChunks, signal);
        if (result.complete) summary = result;
        uploaded += 1;
        uploadStatus.textContent = `${file.name}: ${uploaded}/${totalChunks} \u5206\u5757\u5df2\u4e0a\u4f20`;
        treeSummary.textContent = uploadStatus.textContent;
      }
    };
    const workers = Array.from({ length: Math.min(CHUNK_UPLOAD_CONCURRENCY, totalChunks) }, () => worker());
    await Promise.all(workers);
  } catch (error) {
    if (signal.aborted) await cleanupChunkUpload(fileId);
    throw error;
  } finally {
    if (activeChunkFileId === fileId) activeChunkFileId = "";
  }

  return summary;
}

async function uploadOneChunk(file, fileId, index, totalChunks, signal) {
  const start = index * CHUNK_BYTES;
  const end = Math.min(start + CHUNK_BYTES, file.size);
  const form = new FormData();
  form.append("file_id", fileId);
  form.append("filename", file.name);
  form.append("chunk_index", String(index));
  form.append("total_chunks", String(totalChunks));
  form.append("defer_ingest", "true");
  form.append("chunk", file.slice(start, end), `${file.name}.part${index}`);
  return fetchJson("/upload/chunk", { method: "POST", body: form, signal });
}

function collectDeferredIngest(summary, ingestPaths, savedPaths, extractedPaths) {
  for (const path of summary.ingest_paths || []) ingestPaths.push(path);
  for (const path of summary.files_saved || []) savedPaths.push(path);
  for (const path of summary.files_extracted || []) extractedPaths.push(path);
}

async function createIngestJob(paths, savedPaths, extractedPaths, signal) {
  return fetchJson("/ingest/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paths,
      saved_paths: [...new Set(savedPaths)],
      extracted_paths: [...new Set(extractedPaths)],
    }),
    signal,
  });
}

function createUploadBatches(files) {
  const batches = [];
  let current = [];
  let currentBytes = 0;
  for (const file of files) {
    const wouldOverflow =
      current.length >= UPLOAD_BATCH_MAX_FILES || (current.length > 0 && currentBytes + file.size > UPLOAD_BATCH_MAX_BYTES);
    if (wouldOverflow) {
      batches.push(current);
      current = [];
      currentBytes = 0;
    }
    current.push(file);
    currentBytes += file.size;
  }
  if (current.length) batches.push(current);
  return batches;
}

async function waitForIngestJobs(jobIds, signal) {
  const pending = new Set(jobIds);
  const completed = [];
  while (pending.size) {
    assertUploadActive(signal);
    await delay(INGEST_POLL_MS, signal);
    const status = await fetchJson("/ingest/jobs-batch-status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_ids: [...pending] }),
      signal,
    });
    for (const job of status.jobs || []) {
      const jobId = job.job_id;
      if (job.status === "completed") {
        pending.delete(jobId);
        completed.push(job);
      } else if (job.status === "failed") {
        throw new Error(job.error || "\u540e\u53f0\u6444\u53d6\u5931\u8d25");
      }
    }
    const finished = jobIds.length - pending.size;
    const running = (status.jobs || []).filter((job) => job.status === "running").length;
    const processedDocs = (status.jobs || []).reduce((sum, job) => sum + (job.documents_processed || 0), 0);
    const writtenChunks = (status.jobs || []).reduce((sum, job) => sum + (job.chunks_written || 0), 0);
    const coarseReady = (status.jobs || []).some((job) => job.coarse_ready);
    const coarseDocs = (status.jobs || []).reduce((sum, job) => sum + (job.documents_coarse || 0), 0);
    const refinedDocs = (status.jobs || []).reduce((sum, job) => sum + (job.documents_refined || 0), 0);
    const coarseChunks = (status.jobs || []).reduce((sum, job) => sum + (job.chunks_coarse || 0), 0);
    const refinedChunks = (status.jobs || []).reduce((sum, job) => sum + (job.chunks_refined || 0), 0);
    const totalPaths = (status.jobs || []).reduce((sum, job) => sum + (job.total_paths || 0), 0);
    const currentFile = (status.jobs || []).find((job) => job.current_file)?.current_file || "";
    const progressText = totalPaths
      ? `已处理 ${processedDocs}/${totalPaths} 个文档，形成 ${writtenChunks} 条知识`
      : `形成 ${writtenChunks} 条知识`;
    setIngestState({
      running: true,
      coarseReady,
      stage: coarseReady ? "refining" : "coarse_indexing",
      processedDocs,
      totalDocs: totalPaths,
      chunks: writtenChunks,
      coarseDocs,
      refinedDocs,
      coarseChunks,
      refinedChunks,
      currentFile,
    });
    const progressiveText = coarseReady
      ? `可先提问，正在继续精炼：${refinedDocs}/${totalPaths || "?"} 个文档，${refinedChunks || writtenChunks} 条知识`
      : `正在生成初版知识树：${coarseDocs}/${totalPaths || "?"} 个文档`;
    uploadStatus.textContent = `后台整理：${finished}/${jobIds.length} 个任务完成${running ? `，${running} 个处理中` : ""}，${progressiveText}`;
    treeLiveStatusText = `${progressiveText}${currentFile ? `，当前 ${shorten(currentFile, 24)}` : ""}`;
    await refreshTreeDuringIngest();
  }
  treeLiveStatusText = "";
  return completed;
}

function delay(ms, signal) {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        reject(new DOMException("Upload cancelled", "AbortError"));
      },
      { once: true },
    );
  });
}

async function refreshTreeDuringIngest(force = false) {
  const now = Date.now();
  if (!force && (liveTreeRefreshInFlight || now - lastLiveTreeRefreshAt < 2200)) return;
  liveTreeRefreshInFlight = true;
  lastLiveTreeRefreshAt = now;
  try {
    const params = new URLSearchParams();
    params.set("limit", String(Math.min(INITIAL_TREE_LIMIT, 160)));
    if (lastUserQuery) params.set("q", lastUserQuery);
    treeData = normalizeDynamicTreePayload(await fetchJson(`/api/knowledge/tree?${params.toString()}`));
    if (!visualFrozen) renderTree();
    else {
      const live = treeLiveStatusText ? ` | ${treeLiveStatusText}` : "";
      treeSummary.textContent = treeSummaryText(` | 视图已冻结${live}`);
    }
  } catch {
    // Keep upload flow moving even if one live tree refresh fails.
  } finally {
    liveTreeRefreshInFlight = false;
  }
}

function normalizeDynamicTreePayload(payload) {
  const root = payload?.root || payload;
  const stats = payload?.stats || {};
  function normalizeNode(node) {
    const normalized = {
      ...node,
      name: node?.name || node?.label || "unnamed",
      label: node?.label || node?.name || "unnamed",
      kind: node?.kind || node?.type || "node",
      type: node?.type || node?.kind || "node",
      chunk_count: node?.chunk_count || (node?.type === "chunk" || node?.kind === "chunk" ? 1 : 0),
      preview: node?.preview || node?.raw_text || node?.snippet || "",
      children: Array.isArray(node?.children) ? node.children.map(normalizeNode) : [],
    };
    if (!normalized.children.length && normalized.kind !== "chunk" && normalized.kind !== "entity") delete normalized.children;
    return normalized;
  }
  const tree = normalizeNode(root || { name: "Knowledge Base", kind: "root", children: [] });
  tree.document_count = root?.document_count || stats.documents || (tree.children || []).length;
  tree.chunk_count = root?.chunk_count || stats.chunks || 0;
  tree.entity_count = stats.entities || 0;
  tree.generated_at = payload?.generated_at || root?.generated_at || "";
  return tree;
}

function showIngestReadyNotification(docs, chunks, extracted, durationSeconds = 0) {
  const timeText = durationSeconds ? `，耗时 ${durationSeconds.toFixed(1)}s` : "";
  const zipText = extracted ? `，压缩包解出 ${extracted} 个文件` : "";
  showToast(`整理完成：${docs} 个文档，${chunks} 条知识${zipText}${timeText}。可以开始提问了。`, "success", 3000);
  playReadyTone();
}

function showToast(message, type = "success", duration = 3000) {
  let root = document.querySelector("#toastRoot");
  if (!root) {
    root = document.createElement("div");
    root.id = "toastRoot";
    root.className = "toast-root";
    root.setAttribute("aria-live", "polite");
    document.body.appendChild(root);
  }
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  root.appendChild(toast);
  window.setTimeout(() => toast.classList.add("visible"), 20);
  window.setTimeout(() => {
    toast.classList.remove("visible");
    window.setTimeout(() => toast.remove(), 260);
  }, duration);
}

async function loadRuleMemory(query = "") {
  if (!ruleMemoryList) return;
  try {
    const limit = query ? Math.max(RULE_INITIAL_LIMIT, 36) : RULE_INITIAL_LIMIT;
    const suffix = query ? `?q=${encodeURIComponent(query)}&limit=${limit}` : `?limit=${limit}`;
    renderRuleMemory(await fetchJson(`/api/memory/rules${suffix}`));
  } catch (error) {
    ruleMemorySummary.textContent = `规则记忆加载失败：${error.message}`;
  }
}

function renderRuleMemory(payload) {
  if (!ruleMemoryList || !ruleMemorySummary) return;
  currentRuleMemoryPayload = payload || {};
  const rules = Array.isArray(payload?.rules) ? payload.rules : [];
  ruleMemoryById.clear();
  rules.forEach((rule) => {
    if (rule?.id) ruleMemoryById.set(String(rule.id), rule);
    if (rule?.id && rule.latest_ai_interpretation) ruleInterpretationCache.set(String(rule.id), rule.latest_ai_interpretation);
  });
  const stats = payload?.stats || {};
  const kindStats = stats.memory_kinds || {};
  const kindText = Object.entries(kindStats)
    .slice(0, 4)
    .map(([kind, count]) => `${memoryKindLabel(kind)} ${count}`)
    .join(" · ");
  const statText = [
    `已沉淀 ${payload?.total_count ?? rules.length} 条经验规则`,
    stats.added ? `新增 ${stats.added}` : "",
    stats.merged ? `合并 ${stats.merged}` : "",
    kindText,
  ]
    .filter(Boolean)
    .join(" · ");
  ruleMemorySummary.textContent =
    statText || "经验记忆会从文档依据和多轮问答中提炼可迁移规则，并自动去重、合并和保留证据边界。";
  if (!rules.length) {
    ruleMemoryList.innerHTML = `<div class="rule-empty">暂无可展示经验规则。上传/整理文档或完成一次有依据支撑的问答后会自动生成。</div>`;
    return;
  }
  ruleMemoryList.innerHTML = rules
    .slice(0, 12)
    .map((rule) => {
      const ruleId = String(rule.id || "");
      const source = rule.source_type || "document";
      const docs = (rule.doc_names || []).slice(0, 2).map((name) => escapeHtml(shorten(name, 28))).join(" · ");
      const keywords = (rule.keywords || []).slice(0, 5).map((item) => `<span>${escapeHtml(item)}</span>`).join("");
      const kind = rule.memory_kind || "principle";
      const actionSteps = Array.isArray(rule.action_steps)
        ? rule.action_steps
            .slice(0, 4)
            .map((step) => escapeHtml(shorten(step, 42)))
            .join("；")
        : "";
      const explanation = rule.plain_explanation
        ? `<div class="rule-nuwa-line primary"><b>说明</b>${escapeHtml(shorten(rule.plain_explanation, 150))}</div>`
        : "";
      const steps = actionSteps ? `<div class="rule-nuwa-line"><b>怎么做</b>${actionSteps}</div>` : "";
      const conditions = rule.applicable_conditions
        ? `<div class="rule-nuwa-line muted"><b>适用</b>${escapeHtml(shorten(rule.applicable_conditions, 110))}</div>`
        : "";
      const risk = rule.risk_warning
        ? `<div class="rule-nuwa-line warning"><b>注意</b>${escapeHtml(shorten(rule.risk_warning, 120))}</div>`
        : "";
      const trigger = rule.decision_trigger ? `<div class="rule-nuwa-line"><b>何时用</b>${escapeHtml(shorten(rule.decision_trigger, 90))}</div>` : "";
      const heuristic = rule.heuristic ? `<div class="rule-nuwa-line"><b>做法</b>${escapeHtml(shorten(rule.heuristic, 120))}</div>` : "";
      const boundary = rule.boundary ? `<div class="rule-nuwa-line muted"><b>依据</b>${escapeHtml(shorten(rule.boundary, 110))}</div>` : "";
      const scope = rule.transfer_scope ? `<div class="rule-nuwa-line muted"><b>范围</b>${escapeHtml(shorten(rule.transfer_scope, 100))}</div>` : "";
      const validation = rule.validation?.status ? `<span class="rule-validation">${escapeHtml(validationLabel(rule.validation.status))}</span>` : "";
      const evidenceCount = Number(rule.validation?.evidence_count || rule.support_count || 1);
      const evidenceText = evidenceCount >= 2 ? `依据完整 · ${evidenceCount} 条资料` : `需再核验 · ${evidenceCount} 条资料`;
      return `<article class="rule-item source-border-${escapeHtml(source)}" data-rule-id="${escapeHtml(ruleId)}" tabindex="0" aria-label="查看规则AI解读">
        <div class="rule-topline">
          <span class="source-chip source-${escapeHtml(source)}">${escapeHtml(sourceTypeLabel(source))}</span>
          <span class="rule-kind">${escapeHtml(memoryKindLabel(kind))}</span>
          <span class="rule-score">${evidenceText} ${validation}</span>
        </div>
        <p>${escapeHtml(rule.text || "")}</p>
        <div class="rule-nuwa">${explanation}${steps}${conditions}${risk}${trigger}${heuristic}${boundary}${scope}</div>
        <div class="rule-keywords">${keywords}</div>
        ${docs ? `<div class="rule-docs">${docs}</div>` : ""}
        <div class="rule-actions">
          <button type="button" class="secondary-button" data-rule-action="interpret" data-rule-id="${escapeHtml(ruleId)}">AI解读</button>
          <button type="button" class="secondary-button" data-rule-action="export" data-rule-id="${escapeHtml(ruleId)}">导出</button>
          <button type="button" class="secondary-button" data-rule-action="persist" data-rule-id="${escapeHtml(ruleId)}">沉淀</button>
        </div>
        <div class="rule-ai-panel" data-rule-ai-panel="${escapeHtml(ruleId)}">${renderRuleInterpretationPanel(ruleId)}</div>
      </article>`;
    })
    .join("");
}

function renderRuleInterpretationPanel(ruleId) {
  const interpretation = ruleInterpretationCache.get(String(ruleId));
  if (!interpretation) return "";
  return ruleInterpretationHtml(interpretation);
}

function ruleInterpretationHtml(interpretation = {}) {
  const steps = Array.isArray(interpretation.action_steps) ? interpretation.action_steps : [];
  const links = Array.isArray(interpretation.policy_market_weather_links) ? interpretation.policy_market_weather_links : [];
  const dataItems = Array.isArray(interpretation.next_data_to_collect) ? interpretation.next_data_to_collect : [];
  const list = (items) => (items || []).slice(0, 6).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const provider = interpretation.provider ? `<span>${escapeHtml(interpretation.provider)}</span>` : "";
  const promptHtml = renderPromptDisclosure(interpretation.model_prompt || interpretation.prompt || "", "本次规则分析 Prompt");
  return `<div class="rule-ai-card">
    <div class="rule-ai-head"><strong>AI解读</strong>${provider}</div>
    <p class="rule-ai-summary">${escapeHtml(interpretation.summary || interpretation.farmer_action || "已生成规则解读。")}</p>
    ${interpretation.farmer_action ? `<div class="rule-ai-action"><b>建议动作</b>${escapeHtml(interpretation.farmer_action)}</div>` : ""}
    ${interpretation.why ? `<div class="rule-ai-line"><b>为什么</b>${escapeHtml(interpretation.why)}</div>` : ""}
    ${interpretation.when_to_use ? `<div class="rule-ai-line"><b>何时用</b>${escapeHtml(interpretation.when_to_use)}</div>` : ""}
    ${steps.length ? `<div class="rule-ai-list"><b>执行步骤</b><ol>${list(steps)}</ol></div>` : ""}
    ${links.length ? `<div class="rule-ai-list"><b>关联信息</b><ul>${list(links)}</ul></div>` : ""}
    ${interpretation.risk_boundary ? `<div class="rule-ai-line warning"><b>边界风险</b>${escapeHtml(interpretation.risk_boundary)}</div>` : ""}
    ${dataItems.length ? `<div class="rule-ai-list muted"><b>继续沉淀</b><ul>${list(dataItems)}</ul></div>` : ""}
    ${promptHtml}
  </div>`;
}

function renderRuleChatBubble(rule, interpretation = {}, options = {}) {
  const loading = options.loading;
  const error = options.error || "";
  const ruleText = rule?.text || "这条农业规则";
  const steps = Array.isArray(interpretation.action_steps) ? interpretation.action_steps : [];
  const links = Array.isArray(interpretation.policy_market_weather_links) ? interpretation.policy_market_weather_links : [];
  const dataItems = Array.isArray(interpretation.next_data_to_collect) ? interpretation.next_data_to_collect : [];
  const list = (items) => (items || []).slice(0, 5).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const promptHtml = renderPromptDisclosure(interpretation.model_prompt || interpretation.prompt || "", "本次规则分析 Prompt");
  if (loading) {
    return `<section class="rule-chat-bubble rule-chat-loading" data-answer-main>
      <div class="rule-chat-kicker">农业规则解释</div>
      <div class="rule-chat-title">${escapeHtml(shorten(ruleText, 84))}</div>
      <p>正在把这条规则解释成可以直接执行的建议...</p>
    </section>`;
  }
  if (error) {
    return `<section class="rule-chat-bubble rule-chat-error" data-answer-main>
      <div class="rule-chat-kicker">农业规则解释</div>
      <div class="rule-chat-title">${escapeHtml(shorten(ruleText, 84))}</div>
      <p>解释失败：${escapeHtml(error)}</p>
    </section>`;
  }
  return `<section class="rule-chat-bubble" data-answer-main>
    <div class="rule-chat-kicker">农业规则解释</div>
    <div class="rule-chat-title">${escapeHtml(shorten(ruleText, 96))}</div>
    <p class="rule-chat-summary">${escapeHtml(interpretation.summary || rule?.plain_explanation || "这条规则用于辅助农业经营判断。")}</p>
    ${interpretation.farmer_action ? `<div class="rule-chat-block action"><b>今天怎么做</b><p>${escapeHtml(interpretation.farmer_action)}</p></div>` : ""}
    ${interpretation.why ? `<div class="rule-chat-block"><b>为什么这样判断</b><p>${escapeHtml(interpretation.why)}</p></div>` : ""}
    ${interpretation.when_to_use ? `<div class="rule-chat-block"><b>什么时候用</b><p>${escapeHtml(interpretation.when_to_use)}</p></div>` : ""}
    ${steps.length ? `<div class="rule-chat-block"><b>执行步骤</b><ol>${list(steps)}</ol></div>` : ""}
    ${links.length ? `<div class="rule-chat-block"><b>要一起看的信息</b><ul>${list(links)}</ul></div>` : ""}
    ${interpretation.risk_boundary ? `<div class="rule-chat-block warning"><b>边界和风险</b><p>${escapeHtml(interpretation.risk_boundary)}</p></div>` : ""}
    ${dataItems.length ? `<div class="rule-chat-block muted"><b>继续补充的数据</b><ul>${list(dataItems)}</ul></div>` : ""}
    ${promptHtml}
  </section>`;
}

function updateRuleChatBubble(card, html) {
  const body = card?.querySelector(".message-body");
  if (!body) return;
  body.innerHTML = html;
  const existingActions = card.querySelector(".message-actions");
  existingActions?.remove();
  attachMessageSpeaker(card);
  messages.scrollTop = messages.scrollHeight;
}

function ruleContextForInterpretation() {
  const production = locationContextState.productionLocation || DEFAULT_PRODUCTION_LOCATION;
  const market = locationContextState.marketLocation || DEFAULT_MARKET_LOCATION;
  const latest = locationContextState.latest || {};
  const weather = latest.production_weather || {};
  const temp = weather.temperature_2m === undefined ? "" : `气温${weather.temperature_2m}°C`;
  const risk = liveWeatherRisk?.textContent || "";
  return `${production}到${market}；${temp}；${risk}；关注政策、市场、气象、收购和物流。`;
}

async function requestRuleInterpretation(ruleId, persist = false, options = {}) {
  const id = String(ruleId || "");
  if (!id) return;
  const rule = ruleMemoryById.get(id) || { id, text: "这条农业规则" };
  const showChat = Boolean(options.chatBubble);
  let chatCard = null;
  if (showChat) {
    chatCard = addMessage("assistant", renderRuleChatBubble(rule, ruleInterpretationCache.get(id), { loading: true }));
  }
  const panel = ruleMemoryList?.querySelector(`[data-rule-ai-panel="${cssEscape(id)}"]`);
  if (panel) panel.innerHTML = '<div class="rule-ai-loading">正在生成AI解读...</div>';
  try {
    const payload = await fetchJson("/api/memory/rules/interpret", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rule_id: id, context: ruleContextForInterpretation(), persist, answer_language: appSettings.answerLanguage || "auto" }),
    });
    if (payload.rule?.id) ruleMemoryById.set(String(payload.rule.id), payload.rule);
    if (payload.interpretation && payload.prompt) payload.interpretation.model_prompt = payload.prompt;
    if (payload.interpretation) ruleInterpretationCache.set(id, payload.interpretation);
    if (panel) panel.innerHTML = ruleInterpretationHtml(payload.interpretation || {});
    if (chatCard) updateRuleChatBubble(chatCard, renderRuleChatBubble(payload.rule || rule, payload.interpretation || {}));
    showToast(persist ? "规则解读已沉淀。" : "AI解读已生成。", "success", 2400);
    return payload.interpretation;
  } catch (error) {
    if (panel) panel.innerHTML = `<div class="rule-ai-error">AI解读失败：${escapeHtml(error.message)}</div>`;
    if (chatCard) updateRuleChatBubble(chatCard, renderRuleChatBubble(rule, {}, { error: error.message }));
    showToast(`规则解读失败：${error.message}`, "error", 4200);
    return null;
  }
}

async function persistRuleInterpretation(ruleId) {
  const id = String(ruleId || "");
  let interpretation = ruleInterpretationCache.get(id);
  if (!interpretation) {
    await requestRuleInterpretation(id, true);
    return;
  }
  try {
    const payload = await fetchJson("/api/memory/rules/interpretation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rule_id: id, interpretation }),
    });
    if (payload.rule?.id) {
      ruleMemoryById.set(String(payload.rule.id), payload.rule);
      if (payload.rule.latest_ai_interpretation) ruleInterpretationCache.set(id, payload.rule.latest_ai_interpretation);
    }
    showToast("规则解读已沉淀到长期记忆。", "success", 2800);
  } catch (error) {
    showToast(`沉淀失败：${error.message}`, "error", 4200);
  }
}

function exportRuleMemory(ruleId) {
  const id = String(ruleId || "");
  const rule = ruleMemoryById.get(id);
  if (!rule) return;
  const markdown = ruleExportMarkdown(rule, ruleInterpretationCache.get(id));
  downloadBlob(markdown, `农业规则-${safeFilename(rule.text || id)}.md`, "text/markdown;charset=utf-8");
  showToast("规则已导出。", "success", 2200);
}

function exportAllRuleMemory() {
  const rules = Array.isArray(currentRuleMemoryPayload?.rules) ? currentRuleMemoryPayload.rules : [];
  if (!rules.length) {
    showToast("当前没有可导出的规则。", "error", 2600);
    return;
  }
  const markdown = [
    "# 农业规则与AI解读导出",
    "",
    `导出时间：${new Date().toLocaleString("zh-CN")}`,
    "",
    ...rules.map((rule, index) => `## ${index + 1}. ${rule.text || rule.id}\n\n${ruleExportMarkdown(rule, ruleInterpretationCache.get(String(rule.id)), false)}`),
  ].join("\n");
  downloadBlob(markdown, `农业规则导出-${Date.now()}.md`, "text/markdown;charset=utf-8");
  showToast("规则列表已导出。", "success", 2400);
}

function ruleExportMarkdown(rule, interpretation, includeTitle = true) {
  const lines = [];
  if (includeTitle) lines.push(`# ${rule.text || "农业规则"}`, "");
  lines.push(`- 规则ID：${rule.id || ""}`);
  lines.push(`- 类型：${memoryKindLabel(rule.memory_kind || "principle")}`);
  lines.push(`- 依据：${(rule.doc_names || []).join("；") || rule.boundary || "知识库规则记忆"}`);
  lines.push("");
  if (rule.plain_explanation) lines.push("## 规则说明", rule.plain_explanation, "");
  if (Array.isArray(rule.action_steps) && rule.action_steps.length) lines.push("## 怎么做", ...rule.action_steps.map((item) => `- ${item}`), "");
  if (rule.applicable_conditions) lines.push("## 适用条件", rule.applicable_conditions, "");
  if (rule.risk_warning) lines.push("## 风险边界", rule.risk_warning, "");
  if (interpretation) {
    lines.push("## AI解读", interpretation.summary || "", "");
    if (interpretation.farmer_action) lines.push("### 建议动作", interpretation.farmer_action, "");
    if (interpretation.why) lines.push("### 为什么", interpretation.why, "");
    if (interpretation.when_to_use) lines.push("### 何时使用", interpretation.when_to_use, "");
    if (Array.isArray(interpretation.action_steps)) lines.push("### 执行步骤", ...interpretation.action_steps.map((item) => `- ${item}`), "");
    if (interpretation.risk_boundary) lines.push("### 边界风险", interpretation.risk_boundary, "");
  }
  return lines.join("\n");
}

function safeFilename(value) {
  return String(value || "rule").replace(/[\\/:*?"<>|]+/g, " ").replace(/\s+/g, " ").trim().slice(0, 36) || "rule";
}

function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(value);
  return String(value).replace(/["\\]/g, "\\$&");
}

function handleRuleMemoryClick(event) {
  const target = event.target instanceof Element ? event.target : null;
  const actionButton = target?.closest("[data-rule-action]");
  if (actionButton) {
    event.preventDefault();
    event.stopPropagation();
    const ruleId = actionButton.dataset.ruleId;
    const action = actionButton.dataset.ruleAction;
    if (action === "interpret") requestRuleInterpretation(ruleId, false, { chatBubble: true });
    if (action === "export") exportRuleMemory(ruleId);
    if (action === "persist") persistRuleInterpretation(ruleId);
    return;
  }
  const item = target?.closest("[data-rule-id]");
  if (item) requestRuleInterpretation(item.dataset.ruleId, false, { chatBubble: true });
}

function handleRuleMemoryKeydown(event) {
  if (event.key !== "Enter" && event.key !== " ") return;
  const item = event.target?.closest?.("[data-rule-id]");
  if (!item) return;
  event.preventDefault();
  requestRuleInterpretation(item.dataset.ruleId, false, { chatBubble: true });
}

function memoryKindLabel(kind) {
  const map = {
    mental_model: "经营模型",
    decision_heuristic: "经营规则",
    principle: "农业原则",
    anti_pattern: "风险提醒",
    expression_pattern: "表达建议",
    boundary: "依据边界",
  };
  return map[kind] || "农业原则";
}

function validationLabel(status) {
  const map = {
    validated: "已核验",
    provisional: "待复核",
    weak: "证据少",
    excluded: "未纳入",
  };
  return map[status] || status;
}

async function refreshRuleMemoryFromChunks(reset = false) {
  if (!refreshRules) return;
  refreshRules.disabled = true;
  refreshRules.textContent = reset ? "重建中" : "融合中";
  try {
    const payload = await fetchJson("/api/memory/rules/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reset, limit: 1200 }),
    });
    renderRuleMemory(payload);
    showToast(reset ? "规则记忆已重建。" : "规则记忆已融合更新。", "success", 3000);
  } catch (error) {
    showToast(`规则融合失败：${error.message}`, "error", 4000);
  } finally {
    refreshRules.disabled = false;
    refreshRules.textContent = "融合规则";
  }
}

async function clearRuleMemory() {
  if (!window.confirm("确定清空当前规则记忆？这不会删除知识库文档。")) return;
  try {
    const payload = await fetchJson("/api/memory/rules", { method: "DELETE" });
    renderRuleMemory(payload);
    showToast("规则记忆已清空。", "success", 3000);
  } catch (error) {
    showToast(`规则清空失败：${error.message}`, "error", 4000);
  }
}

async function resetKnowledgeTree() {
  const ok = window.confirm(
    "将清空当前知识树、会话记录和规则记忆，但默认保留原始上传文件。继续？",
  );
  if (!ok) return;
  resetKnowledge.disabled = true;
  resetKnowledge.textContent = "重置中";
  try {
    const result = await fetchJson("/api/knowledge/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ include_raw: false, clear_sessions: true, clear_rules: true }),
    });
    treeData = normalizeDynamicTreePayload(result.tree);
    collapsedNodes.clear();
    treeMapExpandedNodes.clear();
    currentSessionId = loadSessionId();
    renderTree();
    renderRuleMemory({ rules: [], total_count: 0, stats: { cleared: true } });
    await checkHealth();
    showToast("知识树已清空，原始上传文件已保留。可以重新整理或继续上传。", "success", 3000);
  } catch (error) {
    showToast(`知识树重置失败：${error.message}`, "error", 5000);
  } finally {
    resetKnowledge.disabled = false;
    resetKnowledge.textContent = "重置知识树";
  }
}

function primeNotifySound() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return;
  try {
    notifyAudioContext = notifyAudioContext || new AudioContextClass();
    if (notifyAudioContext.state === "suspended") notifyAudioContext.resume().catch(() => {});
  } catch {
    notifyAudioContext = null;
  }
}

function playReadyTone() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return;
  try {
    const context = notifyAudioContext || new AudioContextClass();
    notifyAudioContext = context;
    const start = context.currentTime;
    const gain = context.createGain();
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(0.08, start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.55);
    gain.connect(context.destination);

    [660, 880].forEach((frequency, index) => {
      const osc = context.createOscillator();
      osc.type = "sine";
      osc.frequency.setValueAtTime(frequency, start + index * 0.12);
      osc.connect(gain);
      osc.start(start + index * 0.12);
      osc.stop(start + index * 0.12 + 0.24);
    });
  } catch {
    // Notification sound is best-effort and should never block upload flow.
  }
}

function cancelActiveUpload() {
  if (!activeUploadController) return;
  uploadCancelled = true;
  cancelUploadButton.disabled = true;
  uploadStatus.textContent = "\u6b63\u5728\u4e2d\u65ad\u4e0a\u4f20...";
  activeUploadController.abort();
  if (activeChunkFileId) cleanupChunkUpload(activeChunkFileId);
}

async function cleanupChunkUpload(fileId) {
  const form = new FormData();
  form.append("file_id", fileId);
  try {
    await fetch(`${API_BASE}/upload/chunk/cancel`, { method: "POST", body: form });
  } catch {
    // Cleanup is best-effort; the next upload can use a different file id.
  }
}

function assertUploadActive(signal) {
  if (signal.aborted) throw new DOMException("Upload cancelled", "AbortError");
}

cancelUploadButton.addEventListener("click", cancelActiveUpload);
newSessionButton?.addEventListener("click", startNewSession);
clearSessionsButton?.addEventListener("click", clearAllSessions);
sessionList?.addEventListener("click", (event) => {
  const deleteButton = event.target.closest("[data-delete-session-id]");
  if (deleteButton) {
    event.preventDefault();
    event.stopPropagation();
    deleteSession(deleteButton.dataset.deleteSessionId);
    return;
  }
  const button = event.target.closest("[data-session-id]");
  if (button) {
    switchSession(button.dataset.sessionId);
    return;
  }
  const row = event.target.closest("[data-session-row]");
  if (row) switchSession(row.dataset.sessionRow);
});
sessionList?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  if (event.target.closest("[data-delete-session-id]")) return;
  const row = event.target.closest("[data-session-row]");
  if (!row) return;
  event.preventDefault();
  switchSession(row.dataset.sessionRow);
});
function setKnowledgeTreeExpanded(expanded) {
  treeCard?.classList.toggle("is-expanded", Boolean(expanded));
  if (toggleTreePanel) {
    toggleTreePanel.textContent = expanded ? "收起" : "展开";
    toggleTreePanel.setAttribute("aria-expanded", expanded ? "true" : "false");
  }
  if (expanded) {
    window.setTimeout(() => treeCard?.scrollIntoView({ block: "nearest", behavior: "smooth" }), 40);
  }
}

toggleTreePanel?.addEventListener("click", () => setKnowledgeTreeExpanded(!treeCard?.classList.contains("is-expanded")));
refreshTree.addEventListener("click", () => loadTree({ limit: SEARCH_TREE_LIMIT }));
resetKnowledge?.addEventListener("click", resetKnowledgeTree);
refreshRules?.addEventListener("click", () => refreshRuleMemoryFromChunks(false));
exportRules?.addEventListener("click", exportAllRuleMemory);
clearRules?.addEventListener("click", clearRuleMemory);
ruleMemoryList?.addEventListener("click", handleRuleMemoryClick);
ruleMemoryList?.addEventListener("keydown", handleRuleMemoryKeydown);
simpleCausalMap?.addEventListener("click", handleSimpleCausalMapClick);
treeSearch.addEventListener("input", scheduleTreeSearch);
treeListMode.addEventListener("click", () => setTreeMode("list"));
treeGraphMode.addEventListener("click", () => setTreeMode("graph"));
treeMapMode.addEventListener("click", () => setTreeMode("map"));
freezeVisual.addEventListener("click", toggleVisualFreeze);
exportVisual.addEventListener("click", exportCurrentVisual);
screenshotVisual.addEventListener("click", screenshotCurrentVisual);
openDynamicGraph.addEventListener("click", openBackendDynamicGraph);
downloadHdGraph.addEventListener("click", downloadBackendGraphSvg);
downloadWordReport.addEventListener("click", downloadBackendWordReport);
syncTreeModeButtons();
graphZoomOut.addEventListener("click", () => zoomGraphAtCenter(1.24));
graphZoomIn.addEventListener("click", () => zoomGraphAtCenter(0.8));
graphZoomReset.addEventListener("click", resetGraphViewport);
graphFit.addEventListener("click", fitGraphViewport);
graphExpand.addEventListener("click", toggleGraphExpanded);
treeGraphSvg.addEventListener("wheel", handleGraphWheel, { passive: false });
treeGraphSvg.addEventListener("pointerdown", startGraphPan);
treeGraphSvg.addEventListener("pointermove", moveGraphPan);
treeGraphSvg.addEventListener("pointerup", stopGraphPan);
treeGraphSvg.addEventListener("pointercancel", stopGraphPan);
window.addEventListener("resize", () => {
  if (visualFrozen) return;
  if (treeViewMode === "graph" && treeData) renderGraph(buildDisplayTreeData(), treeSearch.value.trim().toLowerCase());
  if (treeViewMode === "map" && treeData) renderTreeMap(buildDisplayTreeData(), treeSearch.value.trim().toLowerCase());
});
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && treeGraph.classList.contains("expanded")) toggleGraphExpanded(false);
});
messages.addEventListener("click", handleEvidenceInteraction);
messages.addEventListener("keydown", (event) => {
  if ((event.key === "Enter" || event.key === " ") && event.target.closest(".evidence-flow-node")) {
    event.preventDefault();
    handleEvidenceNodeSelect(event.target.closest(".evidence-flow-node"));
  }
});

function handleEvidenceInteraction(event) {
  const viewButton = event.target.closest("[data-evidence-view]");
  if (viewButton) {
    switchEvidenceView(viewButton.closest("[data-evidence-chain]"), viewButton.dataset.evidenceView);
    return;
  }
  const node = event.target.closest(".evidence-flow-node");
  if (node) {
    handleEvidenceNodeSelect(node);
    return;
  }
  const copyButton = event.target.closest("[data-copy-evidence]");
  if (copyButton) {
    const shell = copyButton.closest("[data-evidence-chain]");
    const id = shell?.dataset.selectedEvidenceNode;
    const graphId = shell?.dataset.graphId;
    const item = graphId && id ? evidenceGraphStore.get(graphId)?.graph?.nodes?.find((nodeItem) => nodeItem.id === id) : null;
    if (item?.snippet || item?.raw_text || item?.detail) navigator.clipboard?.writeText(item.snippet || item.raw_text || item.detail);
  }
}

function switchEvidenceView(shell, view) {
  if (!shell) return;
  shell.querySelectorAll("[data-evidence-panel]").forEach((panel) => panel.classList.toggle("hidden", panel.dataset.evidencePanel !== view));
  shell.querySelectorAll("[data-evidence-view]").forEach((button) => button.classList.toggle("active", button.dataset.evidenceView === view));
}

function handleEvidenceNodeSelect(nodeEl) {
  const shell = nodeEl.closest("[data-evidence-chain]");
  const graphId = nodeEl.dataset.graphId;
  const nodeId = nodeEl.dataset.nodeId;
  const store = evidenceGraphStore.get(graphId);
  if (!shell || !store) return;
  shell.dataset.selectedEvidenceNode = nodeId;
  shell.querySelectorAll(".evidence-flow-node").forEach((node) => node.classList.toggle("selected", node.dataset.nodeId === nodeId));
  shell.querySelectorAll(".evidence-flow-edge").forEach((edge) => {
    const related = edge.dataset.edgeSource === nodeId || edge.dataset.edgeTarget === nodeId;
    edge.classList.toggle("selected", related);
    edge.classList.toggle("dimmed", !related);
  });
  const item = store.graph.nodes.find((node) => node.id === nodeId);
  showEvidenceDetail(shell, item);
}

function showEvidenceDetail(shell, node) {
  const detail = shell.querySelector("[data-evidence-detail]");
  if (!detail || !node) return;
  if (!["evidence", "retrieved_chunk", "web_result"].includes(node.type)) {
    const sourceType = node.source_type || (node.type === "query" ? "query" : node.type === "entity" ? "entity" : "model_prior");
    detail.innerHTML = `
      <strong>${escapeHtml(node.label || node.type)}</strong>
      <span><b class="source-pill source-${escapeHtml(sourceType)}">${escapeHtml(sourceTypeLabel(sourceType))}</b> ${escapeHtml(nodeTypeLabel(node.type))}${Number.isFinite(Number(node.confidence)) ? ` · 可信度 ${escapeHtml(formatScore(node.confidence))}` : ""}</span>
      ${node.warning ? `<p class="source-warning">${escapeHtml(node.warning)}</p>` : ""}
      ${node.detail || node.text ? `<p>${escapeHtml(node.detail || node.text)}</p>` : ""}
    `;
    return;
  }
  const entities = (node.entities || []).map((item) => `<span class="evidence-chip">${escapeHtml(item)}</span>`).join("");
  const sourceType = node.source_type || "document";
  detail.innerHTML = `
    <div class="evidence-detail-head">
      <strong>${escapeHtml(humanEvidenceLabel(node.evidence_id))} · ${escapeHtml(node.doc_name || "未命名来源")}</strong>
      <button class="secondary-button" type="button" data-copy-evidence>复制依据</button>
    </div>
    <span><b class="source-pill source-${escapeHtml(sourceType)}">${escapeHtml(sourceTypeLabel(sourceType))}</b>${formatScore(node.score) ? ` · 相关度 ${escapeHtml(formatScore(node.score))}` : ""}${node.page ? ` · 第 ${escapeHtml(node.page)} 页` : ""}</span>
    ${entities ? `<div class="evidence-chips">${entities}</div>` : ""}
    <p>${escapeHtml(node.snippet || node.raw_text || node.detail || "")}</p>
  `;
}

function setTreeMode(mode) {
  treeViewMode = mode;
  if (mode === "graph") history.replaceState(null, "", "#graph");
  else if (mode === "map") history.replaceState(null, "", "#map");
  else if (window.location.hash === "#graph" || window.location.hash === "#map") history.replaceState(null, "", window.location.pathname + window.location.search);
  syncTreeModeButtons();
  renderTree();
}

function syncTreeModeButtons() {
  treeListMode.classList.toggle("active", treeViewMode === "list");
  treeGraphMode.classList.toggle("active", treeViewMode === "graph");
  treeMapMode.classList.toggle("active", treeViewMode === "map");
  treeCard?.classList.toggle("is-simple-mode", treeViewMode === "list");
  freezeVisual.textContent = visualFrozen ? "解冻" : "冻结";
}

async function checkHealth() {
  try {
    const health = await fetchJson("/health");
    if (healthBadge) healthBadge.textContent = health.provider_available ? "系统已就绪" : "系统未连接";
  } catch {
    if (healthBadge) healthBadge.textContent = "未连接后端";
  }
}

function treeEndpoint(limit = INITIAL_TREE_LIMIT, query = "") {
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (query) params.set("q", query);
  const suffix = params.toString();
  return `/api/knowledge/tree${suffix ? `?${suffix}` : ""}`;
}

async function loadTree(options = {}) {
  if (!treeLiveStatusText) {
    treeSummary.textContent = visualFrozen ? "知识视图已冻结，正在后台刷新数据" : "知识树加载中";
  }
  try {
    const query = typeof options.query === "string" ? options.query : treeSearch.value.trim();
    const limit = options.full ? 0 : Number(options.limit || treeLastLoadLimit || INITIAL_TREE_LIMIT);
    treeLastLoadLimit = limit || treeLastLoadLimit;
    treeData = normalizeDynamicTreePayload(await fetchJson(treeEndpoint(limit, query)));
    if (!visualFrozen) renderTree();
    else treeSummary.textContent = treeSummaryText(" | 视图已冻结");
  } catch (error) {
    treeSummary.textContent = "知识树加载失败";
    treeRoot.innerHTML = `<p>${escapeHtml(error.message)}</p>`;
  }
}

function scheduleTreeSearch() {
  window.clearTimeout(treeSearchTimer);
  treeSearchTimer = window.setTimeout(() => {
    const query = treeSearch.value.trim();
    if (query.length >= 2) {
      loadTree({ query, limit: SEARCH_TREE_LIMIT });
    } else {
      renderTree();
    }
  }, 260);
}

function renderTree() {
  if (!treeData) return;
  const live = treeLiveStatusText ? ` | ${treeLiveStatusText}` : "";
  if (visualFrozen && treeViewMode !== "list") {
    treeSummary.textContent = treeSummaryText(` | 视图已冻结${live}`);
    return;
  }
  const displayTree = buildDisplayTreeData();
  const query = treeSearch.value.trim().toLowerCase();
  treeSummary.textContent =
    treeViewMode === "list"
      ? "按经营因果展示：先看风险从哪里来、影响谁、今天该怎么做。"
      : treeSummaryText(live);
  if (treeViewMode === "graph") {
    simpleCausalMap?.classList.add("hidden");
    treeRoot.classList.add("hidden");
    treeGraph.classList.remove("hidden");
    treeMap.classList.add("hidden");
    renderGraph(displayTree, query);
    return;
  }
  if (treeViewMode === "map") {
    simpleCausalMap?.classList.add("hidden");
    treeRoot.classList.add("hidden");
    treeGraph.classList.add("hidden");
    treeMap.classList.remove("hidden");
    renderTreeMap(displayTree, query);
    return;
  }
  simpleCausalMap?.classList.remove("hidden");
  treeGraph.classList.add("hidden");
  treeMap.classList.add("hidden");
  treeRoot.classList.add("hidden");
  renderSimpleCausalMap(displayTree);
}

function renderSimpleCausalMap(displayTree) {
  if (!simpleCausalMap) return;
  const cards = buildSimpleCausalCards(displayTree);
  const proverb = buildSimpleCausalProverb(cards);
  const rules = buildSimpleCausalRuleList(cards);
  simpleCausalMap.innerHTML = `
    <div class="causal-proverb">
      <span>经营口诀</span>
      <strong>${escapeHtml(proverb.title)}</strong>
      <p>${escapeHtml(proverb.note)}</p>
    </div>
    <div class="causal-rule-strip" aria-label="经营规则速记">
      ${rules
        .map(
          (rule, index) => `
            <button class="causal-rule-chip" type="button" data-rule-kind="${escapeHtml(rule.kind)}">
              <b>${index + 1}</b><span>${escapeHtml(rule.text)}</span>
            </button>`,
        )
        .join("")}
    </div>
    <div class="causal-card-grid">
      ${cards
        .map(
          (card) => `
            <article class="causal-card causal-${escapeHtml(card.kind)}" data-causal-kind="${escapeHtml(card.kind)}">
              <div class="causal-card-head">
                <span>${escapeHtml(card.icon)}</span>
                <div>
                  <strong>${escapeHtml(card.title)}</strong>
                  <em>${escapeHtml(card.saying)}</em>
                </div>
              </div>
              <div class="causal-rule">
                <b>规则</b>
                <p>${escapeHtml(card.rule)}</p>
              </div>
              <div class="causal-flow">
                <div><b>如果</b><p>${escapeHtml(card.cause)}</p></div>
                <i aria-hidden="true">→</i>
                <div><b>会影响</b><p>${escapeHtml(card.effect)}</p></div>
                <i aria-hidden="true">→</i>
                <div><b>今天做</b><p>${escapeHtml(card.action)}</p></div>
              </div>
              <p class="causal-stake">${escapeHtml(card.stake)}</p>
            </article>`,
        )
        .join("")}
    </div>
    <details class="advanced-tree-details">
      <summary>查看详细资料来源</summary>
      <div class="advanced-tree-list" role="tree"></div>
    </details>`;
  const detail = simpleCausalMap.querySelector(".advanced-tree-list");
  if (detail) {
    detail.innerHTML = "";
    treeRenderCounter = 0;
    detail.appendChild(renderNode(displayTree, "root", treeSearch.value.trim().toLowerCase(), 0));
  }
}

function handleSimpleCausalMapClick(event) {
  const target = event.target instanceof Element ? event.target : null;
  const chip = target?.closest(".causal-rule-chip");
  if (!chip || !simpleCausalMap) return;
  const kind = chip.dataset.ruleKind || "";
  const card = simpleCausalMap.querySelector(`[data-causal-kind="${cssEscape(kind)}"]`);
  if (!card) return;
  simpleCausalMap.querySelectorAll(".causal-card.is-focused").forEach((item) => item.classList.remove("is-focused"));
  card.classList.add("is-focused");
  card.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
}

function buildSimpleCausalCards(displayTree) {
  const latest = locationContextState.latest || {};
  const production = latest.production_location || latest.region || {};
  const market = latest.market_location || {};
  const weather = latest.production_weather || latest.weather || {};
  const marketWeather = latest.market_weather || {};
  const route = latest.route || {};
  const productionName = production.short_name || locationContextState.productionLocation || "当前产地";
  const marketName = market.short_name || locationContextState.marketLocation || "目标市场";
  const rain = maxWeatherRain(weather);
  const marketRain = maxWeatherRain(marketWeather);
  const highTemp = maxWeatherTemp(weather);
  const distance = Number(route.distance_km || 0);
  const docs = countTreeDocuments(displayTree);
  const chunks = Number(displayTree?.chunk_count || treeData?.chunk_count || 0);
  const weatherCause =
    rain >= 8
      ? `${productionName}未来有明显降雨`
      : highTemp >= 32
        ? `${productionName}有高温时段`
        : `${productionName}天气整体平稳`;
  const weatherAction =
    rain >= 8
      ? "成熟果菜先抢采，装筐垫高，包装防潮"
      : highTemp >= 32
        ? "采收避开中午，先做遮阴、补水和预冷"
        : "按订单采收，保留批次记录，正常发货";
  const routeCause = distance ? `${productionName}到${marketName}约${distance}公里` : `${productionName}到${marketName}路线待估算`;
  const routeAction =
    distance > 120 || marketRain >= 8
      ? "优先冷链或凌晨发车，到货前联系档口确认接货"
      : "先询价锁单，再按市场到货窗口采收装车";
  return [
    {
      kind: "weather",
      icon: "天",
      title: "天气到采收",
      saying: rain >= 8 ? "天变果先收" : highTemp >= 32 ? "日头毒早晚收" : "天稳也要看单",
      rule:
        rain >= 8
          ? "天气转坏时，不等满熟；先抢成熟货，分级防潮后再卖。"
          : highTemp >= 32
            ? "高温时段不硬采；早晚采、快预冷，减少软果和坏果。"
            : "天气平稳也不盲采；先看订单和价格，再安排采收量。",
      cause: weatherCause,
      effect: "果菜品质、病虫害、田间作业和发货节奏",
      action: weatherAction,
      stake: "利害关系：处理早，少烂果少延误；处理晚，损耗和压价都会上来。",
    },
    {
      kind: "market",
      icon: "市",
      title: "市场到价格",
      saying: "货到先问价",
      rule: "价格不确定时，不先采一车货；先问收购价、到货量和付款方式，再决定采多少。",
      cause: `${marketName}收购、批发和电商渠道变化`,
      effect: "今天卖给谁、走本地收购还是电商、是否需要错峰",
      action: "先问价和到货量，再决定现采现卖、预售或短期冷藏",
      stake: "利害关系：先锁渠道再采收，避免货到市场才被动议价。",
    },
    {
      kind: "logistics",
      icon: "运",
      title: "路线到损耗",
      saying: distance > 120 || marketRain >= 8 ? "路远货要冷" : "近路也要准点",
      rule:
        distance > 120 || marketRain >= 8
          ? "路远或雨大时，不赌普通运输；先定冷链、定温度、定到货时间。"
          : "短途也要先定接货窗口；车、人、筐、票据对齐后再发。",
      cause: routeCause,
      effect: "运输时间、冷链成本、到货新鲜度和退货风险",
      action: routeAction,
      stake: "利害关系：路线和包装安排好，售价更稳；雨天和长途要防潮保温。",
    },
    {
      kind: "policy",
      icon: "策",
      title: "政策到补贴",
      saying: "有账才好报",
      rule: "想拿扶持，先留主体证明、订单、票据和台账；材料齐，政策才可能落袋。",
      cause: `${productionName}有新农人、品牌、电商、冷链和质量认证相关扶持`,
      effect: "合作社、家庭农场、农企能不能申报项目和降低投入成本",
      action: "准备主体证明、地块或订单、发票台账、培训和认证材料",
      stake: "利害关系：材料齐，政策能变成钱和渠道；材料散，申报容易错过。",
    },
    {
      kind: "evidence",
      icon: "据",
      title: "资料到判断",
      saying: "有据才敢拍板",
      rule: "平时看一句建议，申报、谈单、追责时再展开来源；能追溯，才敢决策。",
      cause: `当前知识库整理了${docs || "多类"}个资料主题、${chunks || "多条"}条可用依据`,
      effect: "回答是否可靠、能否追溯、农业局和企业是否看同一套依据",
      action: "问答先看结论，需要核实时再展开资料来源",
      stake: "利害关系：默认看行动建议，追责和申报时再看证据。",
    },
  ];
}

function buildSimpleCausalProverb(cards) {
  const weather = cards.find((card) => card.kind === "weather");
  const market = cards.find((card) => card.kind === "market");
  const logistics = cards.find((card) => card.kind === "logistics");
  const weatherAction = weather?.action || "先看天气";
  const marketAction = market?.action || "再看市场";
  const routeAction = logistics?.action || "再定运输";
  let title = "天要看，价要问，车要定，账要留";
  if (/抢采|降雨|防潮/.test(weatherAction)) {
    title = "天要变，果先收；价要稳，单先锁";
  } else if (/高温|预冷|补水/.test(weatherAction)) {
    title = "日头毒，早晚收；先预冷，再发货";
  }
  return {
    title,
    note: `${weatherAction}；${marketAction}；${routeAction}。`,
  };
}

function buildSimpleCausalRuleList(cards) {
  return cards.map((card) => ({
    kind: card.kind,
    text: card.rule,
  }));
}

function maxWeatherRain(weather = {}) {
  const values = [Number(weather.precipitation || 0), ...((weather.daily_precipitation_sum || []).map((item) => Number(item || 0)))];
  return Math.max(0, ...values.filter((item) => Number.isFinite(item)));
}

function maxWeatherTemp(weather = {}) {
  const values = (weather.daily_temperature_2m_max || []).map((item) => Number(item || 0));
  return Math.max(Number(weather.temperature_2m || 0), ...values.filter((item) => Number.isFinite(item)));
}

function countTreeDocuments(node) {
  if (!node) return 0;
  let total = node.type === "document" || node.kind === "document" ? 1 : 0;
  for (const child of node.children || []) total += countTreeDocuments(child);
  return total;
}

function buildDisplayTreeData() {
  if (!treeData) return treeData;
  const children = Array.isArray(treeData.children) ? [...treeData.children] : [];
  if (activeIngestState.running) {
    children.unshift({
      name: "实时整理进行中",
      label: "实时整理进行中",
      kind: "analysis",
      type: "analysis",
      source_type: "inferred",
      chunk_count: activeIngestState.chunks || 0,
      preview: currentIngestLockMessage(),
      children: [
        {
          name: `已完成 ${activeIngestState.processedDocs || 0}/${activeIngestState.totalDocs || "?"} 个文档`,
          label: `已完成 ${activeIngestState.processedDocs || 0}/${activeIngestState.totalDocs || "?"} 个文档`,
          kind: "topic",
          type: "topic",
          source_type: "inferred",
          chunk_count: activeIngestState.chunks || 0,
          preview: `${activeIngestState.chunks || 0} 条知识已进入整理流程`,
          children: [],
        },
        {
          name: activeIngestState.currentFile ? `当前：${shorten(activeIngestState.currentFile, 44)}` : "等待下一篇文档",
          label: activeIngestState.currentFile ? `当前：${shorten(activeIngestState.currentFile, 44)}` : "等待下一篇文档",
          kind: "chunk",
          type: "chunk",
          source_type: "document",
          chunk_count: 1,
          preview: activeIngestState.currentFile || "",
          children: [],
        },
      ],
    });
  }
  if (activeAnalysisTreeNode) children.unshift(activeAnalysisTreeNode);
  return {
    ...treeData,
    children,
    document_count: (treeData.document_count || 0) + (activeAnalysisTreeNode ? 1 : 0) + (activeIngestState.running ? 1 : 0),
  };
}

function treeSummaryText(suffix = "") {
  const updated = treeData?.generated_at ? ` | 更新 ${treeData.generated_at.replace("T", " ")}` : "";
  return `${treeData?.document_count || 0} 个文档，${treeData?.chunk_count || 0} 条知识，${treeData?.entity_count || 0} 个关键概念${updated}${suffix}`;
}

function renderNode(node, path, query, depth = 0) {
  const wrapper = document.createElement("ul");
  const item = document.createElement("li");
  treeRenderCounter += 1;
  if (treeRenderCounter > TREE_RENDER_NODE_BUDGET) {
    item.className = "tree-more-item";
    item.textContent = "为保证页面流畅，已折叠其余节点。请搜索关键词或点击刷新缩小范围。";
    wrapper.appendChild(item);
    return wrapper;
  }
  const row = document.createElement("div");
  const nodePath = `${path}/${node.name}`;
  const rawChildren = Array.isArray(node.children) ? node.children : [];
  const depthLimit = query ? TREE_RENDER_DEPTH_LIMIT + 1 : TREE_RENDER_DEPTH_LIMIT;
  const childLimit = depth <= 1 ? TREE_RENDER_CHILD_LIMIT : Math.max(8, Math.floor(TREE_RENDER_CHILD_LIMIT / 2));
  const visibleChildren = depth >= depthLimit ? [] : rawChildren.slice(0, query ? Math.max(childLimit, 48) : childLimit);
  const hiddenChildCount = Math.max(0, rawChildren.length - visibleChildren.length);
  const hasChildren = visibleChildren.length > 0;
  const isCollapsed = collapsedNodes.has(nodePath);
  const text = `${node.name || ""} ${node.kind || ""} ${node.preview || ""}`.toLowerCase();

  row.className = `tree-node ${node.kind || "node"}`;
  if (query && text.includes(query)) row.classList.add("highlight");

  if (hasChildren) {
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "node-toggle";
    toggle.textContent = isCollapsed ? "+" : "-";
    toggle.addEventListener("click", () => {
      if (collapsedNodes.has(nodePath)) collapsedNodes.delete(nodePath);
      else collapsedNodes.add(nodePath);
      renderTree();
    });
    row.appendChild(toggle);
  }

  const label = document.createElement(node.wiki_url ? "a" : "span");
  label.className = "node-label";
  label.textContent = displayNodeText(node.name) || "未命名";
  if (node.wiki_url) {
    label.href = node.wiki_url;
    label.target = "_blank";
  }

  const meta = document.createElement("span");
  meta.className = "node-meta";
  meta.textContent = displayNodeText(node.preview) || `${nodeKindLabel(node.kind || "node")}${node.chunk_count ? ` | ${node.chunk_count} 条内容` : ""}`;
  label.appendChild(meta);
  row.appendChild(label);
  item.appendChild(row);

  if (hasChildren && !isCollapsed) {
    const children = document.createElement("ul");
    visibleChildren.forEach((child, index) => {
      children.appendChild(renderNode(child, `${nodePath}-${index}`, query, depth + 1).firstElementChild);
    });
    if (hiddenChildCount > 0) {
      const more = document.createElement("li");
      more.className = "tree-more-item";
      more.textContent = `还有 ${hiddenChildCount} 个节点已折叠，搜索关键词可定位到更深来源。`;
      children.appendChild(more);
    }
    item.appendChild(children);
  }

  wrapper.appendChild(item);
  return wrapper;
}

function renderTreeMap(root, query) {
  const map = buildTreeMap(root, query);
  const width = Math.max(760, treeMap.clientWidth || 760);
  const height = Math.max(420, map.maxDepth * 96 + 140);
  const layout = layoutTreeMap(map.root, width, height);
  treeMapStats.textContent = `${map.nodeCount} 个节点 | ${map.maxDepth + 1} 层 | ${map.leafCount} 个叶节点`;
  treeMapSvg.style.width = `${layout.width}px`;
  treeMapSvg.setAttribute("viewBox", `0 0 ${layout.width} ${height}`);
  treeMapSvg.setAttribute("preserveAspectRatio", "xMidYMin meet");
  treeMapSvg.innerHTML = "";

  const linkLayer = svgElement("g", { class: "tree-map-links" });
  const nodeLayer = svgElement("g", { class: "tree-map-nodes" });
  for (const link of map.links) {
    linkLayer.appendChild(
      svgElement("path", {
        d: treeMapPath(link.source, link.target),
        class: `tree-map-link${query && !link.source.matched && !link.target.matched ? " dimmed" : ""}`,
      }),
    );
  }
  for (const node of map.nodes) {
    const group = svgElement("g", {
      class: `tree-map-node ${node.kind}${node.id === selectedTreeMapNodeId ? " selected" : ""}${query && !node.matched ? " dimmed" : ""}${node.matched ? " matched" : ""}`,
      transform: `translate(${node.x},${node.y})`,
      tabindex: "0",
    });
    group.appendChild(svgElement("rect", { x: -node.width / 2, y: -18, width: node.width, height: 36, rx: 8, ry: 8 }));
    const label = svgElement("text", { y: 4, "text-anchor": "middle" });
    label.textContent = shorten(compactGraphLabel(node.label), node.depth <= 1 ? 22 : node.depth === 2 ? 14 : 10);
    group.appendChild(label);
    if (node.hasChildren) {
      const mark = svgElement("text", { x: node.width / 2 - 15, y: 5, class: "tree-map-toggle" });
      mark.textContent = node.collapsed ? "+" : "-";
      group.appendChild(mark);
    }
    group.appendChild(svgElement("title", {}, `${node.label}\n${node.preview || node.kind}`));
    group.addEventListener("click", () => {
      selectedTreeMapNodeId = node.id;
      if (node.hasChildren) {
        if (node.collapsed) treeMapExpandedNodes.add(node.path);
        else treeMapExpandedNodes.delete(node.path);
      }
      showTreeMapDetail(node);
      renderTreeMap(buildDisplayTreeData(), treeSearch.value.trim().toLowerCase());
    });
    group.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      selectedTreeMapNodeId = node.id;
      if (node.hasChildren) {
        if (node.collapsed) treeMapExpandedNodes.add(node.path);
        else treeMapExpandedNodes.delete(node.path);
      }
      showTreeMapDetail(node);
      renderTreeMap(buildDisplayTreeData(), treeSearch.value.trim().toLowerCase());
    });
    nodeLayer.appendChild(group);
  }
  treeMapSvg.appendChild(linkLayer);
  treeMapSvg.appendChild(nodeLayer);
}

function buildTreeMap(root, query) {
  const nodes = [];
  const links = [];
  let maxDepth = 0;
  let leafCount = 0;

  function walk(source, path, depth, parent = null, index = 0) {
    const children = Array.isArray(source.children) ? source.children : [];
    const hasChildren = children.length > 0;
    const defaultExpanded = depth < 1;
    const collapsed = hasChildren && !(defaultExpanded || treeMapExpandedNodes.has(path));
    const visibleChildren = collapsed ? [] : limitTreeMapChildren(children, depth);
    const node = {
      id: path,
      path,
      label: displayNodeText(source.name) || "未命名",
      kind: source.kind || "node",
      preview: displayNodeText(source.preview) || "",
      chunkCount: source.chunk_count || 0,
      depth,
      index,
      hasChildren,
      collapsed,
      matched: matchesGraphQuery(source, query),
      width: depth <= 1 ? 176 : depth === 2 ? 146 : 126,
      children: [],
    };
    nodes.push(node);
    maxDepth = Math.max(maxDepth, depth);
    if (parent) links.push({ source: parent, target: node });
    if (!visibleChildren.length) leafCount += 1;
    visibleChildren.forEach((child, childIndex) => {
      const childNode = walk(child, `${path}/${child.kind || "node"}:${child.name || childIndex}:${childIndex}`, depth + 1, node, childIndex);
      node.children.push(childNode);
      if (childNode.matched) node.matched = true;
    });
    return node;
  }

  const rootNode = walk(root, "root", 0);
  return { root: rootNode, nodes, links, maxDepth, leafCount, nodeCount: nodes.length };
}

function limitTreeMapChildren(children, depth) {
  if (depth === 0) return children.slice(0, 18);
  if (depth === 1) return children.slice(0, 5);
  if (depth === 2) {
    const entities = children.filter((child) => child.kind === "entity").slice(0, 5);
    const chunks = children.filter((child) => child.kind === "chunk").slice(0, 2);
    return [...entities, ...chunks];
  }
  return children.slice(0, 4);
}

function layoutTreeMap(root, width, height) {
  const levelGap = 96;
  const marginX = 120;
  let cursor = marginX;

  function assign(node) {
    if (!node.children.length) {
      node.x = cursor;
      cursor += Math.max(150, node.width + 34);
    } else {
      node.children.forEach(assign);
      node.x = (node.children[0].x + node.children[node.children.length - 1].x) / 2;
    }
    node.y = 54 + node.depth * levelGap;
  }

  assign(root);
  const usedWidth = Math.max(width, cursor + marginX);
  const offset = usedWidth > width ? 0 : (width - usedWidth) / 2;
  function shift(node) {
    node.x += offset;
    node.children.forEach(shift);
  }
  shift(root);
  return { width: usedWidth };
}

function treeMapPath(source, target) {
  const midY = (source.y + target.y) / 2;
  return `M ${source.x.toFixed(1)} ${source.y + 18} C ${source.x.toFixed(1)} ${midY.toFixed(1)}, ${target.x.toFixed(1)} ${midY.toFixed(1)}, ${target.x.toFixed(1)} ${target.y - 18}`;
}

function showTreeMapDetail(node) {
  treeMapDetail.innerHTML = `
    <strong>${escapeHtml(node.label)}</strong>
    <span>${escapeHtml(nodeKindLabel(node.kind))}${node.chunkCount ? ` | ${node.chunkCount} 条内容` : ""}${node.collapsed ? " | 已折叠" : ""}</span>
    ${node.preview ? `<p>${escapeHtml(node.preview)}</p>` : ""}
  `;
}

function renderGraph(root, query) {
  const graph = buildGraph(root, query);
  currentGraph = graph;
  const width = Math.max(680, treeGraph.clientWidth || 720);
  const expanded = treeGraph.classList.contains("expanded");
  const height = expanded ? Math.max(560, treeGraph.clientHeight - 170) : Math.max(390, Math.min(620, width * 0.58));
  const ringRadii = layoutGraph(graph.nodes, width, height);
  const previousBase = graphBaseViewBox;
  graphBaseViewBox = { x: 0, y: 0, width, height };
  if (!graphViewBox || !previousBase || previousBase.width !== width || previousBase.height !== height) {
    graphViewBox = { ...graphBaseViewBox };
  }
  const focusIds = collectGraphFocusIds(graph, selectedGraphNodeId);
  const labelIds = chooseGraphLabels(graph.nodes, query, focusIds, selectedGraphNodeId);
  graphStats.textContent = `${graph.totalDocumentCount} 个文档 | 展示 ${graph.documentCount} 个文档 / ${graph.entityCount} 个关键概念 / ${graph.chunkCount} 条依据`;

  treeGraphSvg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  treeGraphSvg.innerHTML = "";

  const defs = svgElement("defs");
  const glow = svgElement("filter", { id: "nodeGlow", x: "-40%", y: "-40%", width: "180%", height: "180%" });
  glow.appendChild(svgElement("feGaussianBlur", { stdDeviation: "3", result: "coloredBlur" }));
  const merge = svgElement("feMerge");
  merge.appendChild(svgElement("feMergeNode", { in: "coloredBlur" }));
  merge.appendChild(svgElement("feMergeNode", { in: "SourceGraphic" }));
  glow.appendChild(merge);
  defs.appendChild(glow);
  treeGraphSvg.appendChild(defs);

  const rings = svgElement("g", { class: "graph-rings" });
  for (const radius of ringRadii) {
    rings.appendChild(svgElement("circle", { cx: width / 2, cy: height / 2, r: radius }));
  }
  treeGraphSvg.appendChild(rings);

  const linkLayer = svgElement("g", { class: "graph-links" });
  for (const link of graph.links) {
    const source = graph.nodeMap.get(link.source);
    const target = graph.nodeMap.get(link.target);
    if (!source || !target) continue;
    const isSelectedLink = selectedGraphNodeId && (link.source === selectedGraphNodeId || link.target === selectedGraphNodeId);
    const isDimmedLink = query && !source.matched && !target.matched;
    const isOutOfFocusLink = selectedGraphNodeId && (!focusIds.has(link.source) || !focusIds.has(link.target));
    linkLayer.appendChild(
      svgElement("path", {
        d: curvedPath(source, target, width / 2, height / 2),
        class: `graph-link${isSelectedLink ? " selected" : ""}${isDimmedLink ? " dimmed" : ""}${isOutOfFocusLink ? " out-of-focus" : ""}`,
      }),
    );
  }
  treeGraphSvg.appendChild(linkLayer);

  const nodeLayer = svgElement("g", { class: "graph-nodes" });
  for (const node of graph.nodes) {
    const isSelectedNode = node.id === selectedGraphNodeId;
    const isFocusedNode = focusIds.has(node.id);
    const group = svgElement("g", {
      class: `graph-node ${node.kind} source-${node.sourceType || "document"}${query && !node.matched ? " dimmed" : ""}${node.matched ? " matched" : ""}${isSelectedNode ? " selected" : ""}${isFocusedNode ? " focused" : ""}${selectedGraphNodeId && !isFocusedNode ? " out-of-focus" : ""}`,
      transform: `translate(${node.x},${node.y})`,
      tabindex: "0",
    });
    group.appendChild(svgElement("circle", { r: node.radius }));
    if (labelIds.has(node.id)) {
      const label = svgElement("text", {
        x: node.labelOffsetX,
        y: node.labelOffsetY,
        "text-anchor": node.textAnchor || "middle",
        class: node.labelClass,
      });
      label.textContent = shorten(compactGraphLabel(node.label), node.labelLength);
      group.appendChild(label);
    }
    group.appendChild(svgElement("title", {}, `${node.label}\n${node.preview || node.kind}`));
    group.addEventListener("click", () => {
      selectedGraphNodeId = node.id;
      pendingGraphFocusId = node.id;
      showGraphDetail(node);
      renderGraph(buildDisplayTreeData(), treeSearch.value.trim().toLowerCase());
    });
    group.addEventListener("dblclick", (event) => {
      event.preventDefault();
      selectedGraphNodeId = node.id;
      pendingGraphFocusId = node.id;
      showGraphDetail(node);
      focusGraphNode(node, graph);
    });
    group.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      selectedGraphNodeId = node.id;
      pendingGraphFocusId = node.id;
      showGraphDetail(node);
      renderGraph(buildDisplayTreeData(), treeSearch.value.trim().toLowerCase());
    });
    nodeLayer.appendChild(group);
  }
  treeGraphSvg.appendChild(nodeLayer);
  applyGraphViewBox(graphViewBox);
  if (pendingGraphFocusId) {
    const node = graph.nodeMap.get(pendingGraphFocusId);
    pendingGraphFocusId = "";
    if (node) focusGraphNode(node, graph);
  }
}

function buildGraph(root, query) {
  const nodes = [];
  const links = [];
  const nodeMap = new Map();

  function addNode(node) {
    nodes.push(node);
    nodeMap.set(node.id, node);
    return node;
  }

  const rootNode = addNode({
    id: "root",
    label: displayNodeText(root.name) || "知识库总览",
    kind: "root",
    sourceType: root.source_type || "document",
    depth: 0,
    chunkCount: root.chunk_count || 0,
    preview: `${root.document_count || 0} 个文档，${root.chunk_count || 0} 条知识`,
    matched: true,
    radius: 24,
    angle: -Math.PI / 2,
  });

  const allDocuments = (root.children || []).slice().sort((a, b) => (b.chunk_count || 0) - (a.chunk_count || 0));
  const expanded = treeGraph.classList.contains("expanded");
  const documents = allDocuments.slice(0, expanded ? 48 : 18);
  const docCount = documents.length;
  const totalDocumentCount = root.document_count || allDocuments.length;
  let entityCount = 0;
  let chunkCount = 0;

  documents.forEach((doc, docIndex) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * docIndex) / Math.max(docCount, 1);
    const docId = `doc:${doc.name}`;
    const docNode = addNode({
      id: docId,
      label: displayNodeText(doc.name) || "文档",
      kind: "document",
      sourceType: doc.source_type || "document",
      depth: 1,
      chunkCount: doc.chunk_count || 0,
      preview: `${doc.chunk_count || 0} 条知识`,
      matched: matchesGraphQuery(doc, query),
      radius: graphRadius(doc),
      wikiUrl: doc.wiki_url || "",
      angle,
      sectorStart: angle - Math.PI / Math.max(docCount, 1) * 0.72,
      sectorEnd: angle + Math.PI / Math.max(docCount, 1) * 0.72,
    });
    links.push({ source: rootNode.id, target: docNode.id });

    const typeNodes = (doc.children || []).slice(0, expanded ? 3 : 2);
    typeNodes.forEach((type, typeIndex) => {
      const typeAngle = interpolate(docNode.sectorStart, docNode.sectorEnd, (typeIndex + 1) / (typeNodes.length + 1));
      const typeId = `${docId}:type:${type.name}`;
      const typeNode = addNode({
        id: typeId,
        label: displayNodeText(type.name) || "主题",
        kind: type.kind === "topic" ? "topic" : "chunk_type",
        sourceType: type.source_type || "document",
        depth: 2,
        chunkCount: type.chunk_count || 0,
        preview: `${type.chunk_count || 0} 条知识`,
        matched: matchesGraphQuery(type, query) || docNode.matched,
        radius: graphRadius(type),
        angle: typeAngle,
        sectorStart: typeAngle - 0.22,
        sectorEnd: typeAngle + 0.22,
      });
      links.push({ source: docNode.id, target: typeNode.id });

      const children = type.children || [];
      const chunks = children.filter((child) => child.kind === "chunk").slice(0, 1);
      const entities = children
        .flatMap((child) => (child.children || []).filter((nested) => nested.kind === "entity"))
        .slice(0, expanded ? 2 : 1);
      const leafNodes = [...chunks, ...entities];
      leafNodes.forEach((leaf, leafIndex) => {
        const leafAngle = interpolate(typeNode.sectorStart, typeNode.sectorEnd, (leafIndex + 1) / (leafNodes.length + 1));
        const leafId = `${typeId}:leaf:${leaf.kind}:${leaf.name}:${leafIndex}`;
        const leafNode = addNode({
          id: leafId,
          label: displayNodeText(leaf.name) || nodeKindLabel(leaf.kind),
          kind: leaf.kind || "chunk",
          sourceType: leaf.source_type || "document",
          depth: leaf.kind === "entity" ? 3 : 4,
          chunkCount: leaf.chunk_count || 0,
          preview: displayNodeText(leaf.preview) || "",
          matched: matchesGraphQuery(leaf, query) || typeNode.matched,
          radius: graphRadius(leaf),
          angle: leafAngle,
          wikiUrl: leaf.wiki_url || "",
        });
        if (leaf.kind === "entity") entityCount += 1;
        if (leaf.kind === "chunk") chunkCount += 1;
        links.push({ source: typeNode.id, target: leafNode.id });
      });
    });
  });

  return {
    nodes,
    links,
    nodeMap,
    totalDocumentCount,
    documentCount: docCount,
    entityCount,
    chunkCount,
    rings: [],
  };
}

function graphRadius(node) {
  const count = node.chunk_count || 0;
  if (node.kind === "root") return 24;
  if (node.kind === "document") return 15 + Math.min(8, count / 4);
  if (node.kind === "topic") return 12 + Math.min(5, count / 8);
  if (node.kind === "chunk_type") return 12 + Math.min(5, count / 8);
  if (node.kind === "entity") return 8 + Math.min(4, count / 2);
  return 6;
}

function layoutGraph(nodes, width, height) {
  const cx = width / 2;
  const cy = height / 2;
  const maxRing = Math.min(width, height) / 2 - 52;
  const rings = {
    root: 0,
    document: maxRing * 0.34,
    topic: maxRing * 0.58,
    chunk_type: maxRing * 0.58,
    entity: maxRing * 0.78,
    chunk: maxRing * 0.92,
  };
  for (const node of nodes) {
    const radius = rings[node.kind] ?? rings.chunk;
    const direction = Math.cos(node.angle || 0);
    node.x = cx + Math.cos(node.angle || 0) * radius;
    node.y = cy + Math.sin(node.angle || 0) * radius;
    node.labelLength = node.kind === "document" ? 19 : node.kind === "chunk_type" ? 12 : node.kind === "root" ? 18 : 14;
    node.labelClass = direction < -0.25 ? "left-label" : direction > 0.25 ? "right-label" : "center-label";
    node.textAnchor = direction < -0.25 ? "end" : direction > 0.25 ? "start" : "middle";
    if (node.kind === "root") {
      node.labelOffsetX = 0;
      node.labelOffsetY = 42;
      node.textAnchor = "middle";
      node.labelClass = "center-label";
    } else {
      const outward = node.radius + 12;
      node.labelOffsetX = Math.cos(node.angle || 0) * outward;
      node.labelOffsetY = Math.sin(node.angle || 0) * outward + 4;
    }
  }
  return [rings.document, rings.chunk_type, rings.entity, rings.chunk];
}

function curvedPath(source, target, cx, cy) {
  const midX = (source.x + target.x) / 2;
  const midY = (source.y + target.y) / 2;
  const pull = 0.18;
  const controlX = midX + (cx - midX) * pull;
  const controlY = midY + (cy - midY) * pull;
  return `M ${source.x.toFixed(1)} ${source.y.toFixed(1)} Q ${controlX.toFixed(1)} ${controlY.toFixed(1)} ${target.x.toFixed(1)} ${target.y.toFixed(1)}`;
}

function collectGraphFocusIds(graph, nodeId) {
  const ids = new Set();
  if (!nodeId || !graph.nodeMap.has(nodeId)) return ids;
  ids.add(nodeId);
  for (const link of graph.links) {
    if (link.source === nodeId) ids.add(link.target);
    if (link.target === nodeId) ids.add(link.source);
  }
  return ids;
}

function chooseGraphLabels(nodes, query, focusIds, selectedId) {
  const candidates = nodes
    .filter((node) => node.id === selectedId || focusIds.has(node.id) || (query && node.matched))
    .map((node) => ({
      node,
      score:
        (node.id === selectedId ? 1000 : 0) +
        (focusIds.has(node.id) ? 500 : 0) +
        (query && node.matched ? 300 : 0) +
        (node.kind === "document" ? 80 : node.kind === "chunk_type" ? 60 : node.kind === "root" ? 50 : 20) +
        Math.min(40, node.chunkCount || 0),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, query ? 24 : 14);
  const accepted = [];
  const ids = new Set();
  for (const { node } of candidates) {
    const box = estimateGraphLabelBox(node);
    if (node.id !== selectedId && accepted.some((item) => boxesOverlap(item, box))) continue;
    accepted.push(box);
    ids.add(node.id);
  }
  return ids;
}

function estimateGraphLabelBox(node) {
  const text = shorten(compactGraphLabel(node.label), node.labelLength);
  const width = Math.max(30, text.length * 7.2);
  const height = node.kind === "entity" || node.kind === "chunk" ? 14 : 16;
  const x = node.x + (node.labelOffsetX || 0);
  const y = node.y + (node.labelOffsetY || 0) - height * 0.75;
  if (node.textAnchor === "end") return { x: x - width - 5, y: y - 4, width: width + 10, height: height + 8 };
  if (node.textAnchor === "start") return { x: x - 5, y: y - 4, width: width + 10, height: height + 8 };
  return { x: x - width / 2 - 5, y: y - 4, width: width + 10, height: height + 8 };
}

function boxesOverlap(a, b) {
  return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
}

function focusGraphNode(node, graph) {
  if (!graphBaseViewBox || node.kind === "root") {
    applyGraphViewBox(graphBaseViewBox, true);
    return;
  }
  const focusIds = collectGraphFocusIds(graph, node.id);
  focusIds.add(node.id);
  const focusNodes = graph.nodes.filter((item) => focusIds.has(item.id));
  const bounds = graphBounds(focusNodes.length ? focusNodes : [node]);
  const zoomScale = node.kind === "document" ? 0.5 : node.kind === "chunk_type" ? 0.36 : 0.28;
  const minWidth = graphBaseViewBox.width * zoomScale;
  const width = Math.max(bounds.width + 130, (bounds.height + 110) * (graphBaseViewBox.width / graphBaseViewBox.height), minWidth);
  const height = width * (graphBaseViewBox.height / graphBaseViewBox.width);
  applyGraphViewBox(
    {
      x: bounds.cx - width / 2,
      y: bounds.cy - height / 2,
      width,
      height,
    },
    true,
  );
}

function graphBounds(nodes) {
  const xs = nodes.map((node) => node.x);
  const ys = nodes.map((node) => node.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    x: minX,
    y: minY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
    cx: (minX + maxX) / 2,
    cy: (minY + maxY) / 2,
  };
}

function applyGraphViewBox(box, animate = false) {
  if (!box || !graphBaseViewBox) return;
  const next = constrainGraphViewBox(box);
  cancelAnimationFrame(graphFrameId);
  if (!animate || !graphViewBox) {
    graphViewBox = next;
    treeGraphSvg.setAttribute("viewBox", formatViewBox(next));
    updateGraphViewportLabel();
    return;
  }
  const start = { ...graphViewBox };
  const started = performance.now();
  const duration = 620;
  const tick = (now) => {
    const progress = clamp((now - started) / duration, 0, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    graphViewBox = {
      x: start.x + (next.x - start.x) * eased,
      y: start.y + (next.y - start.y) * eased,
      width: start.width + (next.width - start.width) * eased,
      height: start.height + (next.height - start.height) * eased,
    };
    treeGraphSvg.setAttribute("viewBox", formatViewBox(graphViewBox));
    updateGraphViewportLabel();
    if (progress < 1) graphFrameId = requestAnimationFrame(tick);
  };
  graphFrameId = requestAnimationFrame(tick);
}

function constrainGraphViewBox(box) {
  const base = graphBaseViewBox;
  const minWidth = base.width / 5.2;
  const maxWidth = base.width * 1.14;
  const width = clamp(box.width, minWidth, maxWidth);
  const height = width * (base.height / base.width);
  const padX = base.width * 0.16;
  const padY = base.height * 0.16;
  const minX = base.x - padX;
  const maxX = base.x + base.width + padX - width;
  const minY = base.y - padY;
  const maxY = base.y + base.height + padY - height;
  return {
    x: clamp(box.x, Math.min(minX, maxX), Math.max(minX, maxX)),
    y: clamp(box.y, Math.min(minY, maxY), Math.max(minY, maxY)),
    width,
    height,
  };
}

function formatViewBox(box) {
  return `${box.x.toFixed(2)} ${box.y.toFixed(2)} ${box.width.toFixed(2)} ${box.height.toFixed(2)}`;
}

function updateGraphViewportLabel() {
  if (!graphViewportLabel || !graphBaseViewBox || !graphViewBox) return;
  const zoom = Math.round((graphBaseViewBox.width / graphViewBox.width) * 100);
  graphViewportLabel.textContent = `${zoom}%`;
}

function zoomGraphAtCenter(factor) {
  if (!graphViewBox) return;
  zoomGraphAtPoint(
    {
      x: graphViewBox.x + graphViewBox.width / 2,
      y: graphViewBox.y + graphViewBox.height / 2,
    },
    factor,
    true,
  );
}

function zoomGraphAtPoint(point, factor, animate = false) {
  if (!graphViewBox) return;
  const width = graphViewBox.width * factor;
  const height = graphViewBox.height * factor;
  const ratioX = (point.x - graphViewBox.x) / graphViewBox.width;
  const ratioY = (point.y - graphViewBox.y) / graphViewBox.height;
  applyGraphViewBox(
    {
      x: point.x - width * ratioX,
      y: point.y - height * ratioY,
      width,
      height,
    },
    animate,
  );
}

function fitGraphViewport() {
  if (!currentGraph || !currentGraph.nodes.length || !graphBaseViewBox) {
    applyGraphViewBox(graphBaseViewBox, true);
    return;
  }
  const bounds = graphBounds(currentGraph.nodes);
  const pad = 90;
  const aspect = graphBaseViewBox.width / graphBaseViewBox.height;
  let width = Math.max(bounds.width + pad * 2, (bounds.height + pad * 2) * aspect);
  let height = width / aspect;
  if (height < bounds.height + pad * 2) {
    height = bounds.height + pad * 2;
    width = height * aspect;
  }
  applyGraphViewBox(
    {
      x: bounds.cx - width / 2,
      y: bounds.cy - height / 2,
      width,
      height,
    },
    true,
  );
}

function resetGraphViewport() {
  selectedGraphNodeId = "";
  pendingGraphFocusId = "";
  graphDetail.textContent = "\u70b9\u51fb\u56fe\u8c31\u8282\u70b9\u67e5\u770b\u8be6\u60c5\u3002";
  if (treeData) renderGraph(buildDisplayTreeData(), treeSearch.value.trim().toLowerCase());
  applyGraphViewBox(graphBaseViewBox, true);
}

function toggleGraphExpanded(force) {
  const shouldExpand = typeof force === "boolean" ? force : !treeGraph.classList.contains("expanded");
  treeGraph.classList.toggle("expanded", shouldExpand);
  document.body.classList.toggle("graph-modal-open", shouldExpand);
  document.body.classList.toggle("graph-fullscreen-active", shouldExpand);
  graphExpand.textContent = shouldExpand ? "退出" : "大画布";
  graphExpand.setAttribute("title", shouldExpand ? "\u5173\u95ed\u753b\u5e03" : "\u5c55\u5f00\u753b\u5e03");
  graphExpand.setAttribute("aria-label", shouldExpand ? "\u5173\u95ed\u753b\u5e03" : "\u5c55\u5f00\u753b\u5e03");
  graphBaseViewBox = null;
  graphViewBox = null;
  if (treeData) renderGraph(buildDisplayTreeData(), treeSearch.value.trim().toLowerCase());
}

function graphPointFromEvent(event) {
  const rect = treeGraphSvg.getBoundingClientRect();
  return {
    x: graphViewBox.x + ((event.clientX - rect.left) / rect.width) * graphViewBox.width,
    y: graphViewBox.y + ((event.clientY - rect.top) / rect.height) * graphViewBox.height,
  };
}

function handleGraphWheel(event) {
  if (treeViewMode !== "graph" || !graphViewBox) return;
  event.preventDefault();
  const factor = event.deltaY > 0 ? 1.16 : 0.86;
  zoomGraphAtPoint(graphPointFromEvent(event), factor);
}

function startGraphPan(event) {
  if (treeViewMode !== "graph" || !graphViewBox || event.button !== 0) return;
  if (event.target.closest && event.target.closest(".graph-node")) return;
  graphDrag = {
    clientX: event.clientX,
    clientY: event.clientY,
    viewBox: { ...graphViewBox },
  };
  treeGraphSvg.classList.add("is-panning");
  treeGraphSvg.setPointerCapture(event.pointerId);
}

function moveGraphPan(event) {
  if (!graphDrag) return;
  const rect = treeGraphSvg.getBoundingClientRect();
  const dx = ((event.clientX - graphDrag.clientX) / rect.width) * graphDrag.viewBox.width;
  const dy = ((event.clientY - graphDrag.clientY) / rect.height) * graphDrag.viewBox.height;
  applyGraphViewBox({
    x: graphDrag.viewBox.x - dx,
    y: graphDrag.viewBox.y - dy,
    width: graphDrag.viewBox.width,
    height: graphDrag.viewBox.height,
  });
}

function stopGraphPan(event) {
  if (!graphDrag) return;
  graphDrag = null;
  treeGraphSvg.classList.remove("is-panning");
  if (treeGraphSvg.hasPointerCapture(event.pointerId)) treeGraphSvg.releasePointerCapture(event.pointerId);
}

function compactGraphLabel(value) {
  return String(value || "")
    .replace(/\.(markdown|md|txt|pdf|docx|xlsx|csv)$/i, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function matchesGraphQuery(node, query) {
  if (!query) return true;
  return `${node.name || ""} ${node.kind || ""} ${node.preview || ""}`.toLowerCase().includes(query);
}

function interpolate(start, end, ratio) {
  return start + (end - start) * ratio;
}

function showGraphDetail(node) {
  graphDetail.innerHTML = `
    <strong>${escapeHtml(node.label)}</strong>
    <span><b class="source-pill source-${escapeHtml(node.sourceType || "document")}">${escapeHtml(sourceTypeLabel(node.sourceType || "document"))}</b> ${escapeHtml(nodeKindLabel(node.kind))}${node.chunkCount ? ` | ${node.chunkCount} 条内容` : ""}</span>
    ${node.preview ? `<p>${escapeHtml(displayNodeText(node.preview))}</p>` : ""}
    ${node.wikiUrl ? `<a href="${escapeHtml(node.wikiUrl)}" target="_blank">打开文档</a>` : ""}
  `;
}

function svgElement(name, attrs = {}, text = "") {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
  if (text) element.textContent = text;
  return element;
}

function shorten(value, maxLength) {
  const text = String(value || "");
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}\u2026` : text;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function toggleVisualFreeze() {
  visualFrozen = !visualFrozen;
  syncTreeModeButtons();
  treeSummary.textContent = treeSummaryText(visualFrozen ? " | 视图已冻结" : "");
  if (!visualFrozen) renderTree();
}

function exportCurrentVisual() {
  const payload = {
    exported_at: new Date().toISOString(),
    mode: treeViewMode,
    frozen: visualFrozen,
    query: treeSearch.value.trim(),
    selected_graph_node_id: selectedGraphNodeId,
    selected_tree_node_id: selectedTreeMapNodeId,
    graph_view_box: graphViewBox,
    tree: treeData,
  };
  downloadBlob(JSON.stringify(payload, null, 2), `knowledge-${treeViewMode}-${Date.now()}.json`, "application/json");
}

function openBackendDynamicGraph() {
  window.open(`${API_BASE}/exports/knowledge-graph.html`, "_blank", "noopener,noreferrer");
}

async function downloadBackendGraphSvg() {
  downloadHdGraph.disabled = true;
  const originalText = downloadHdGraph.textContent;
  downloadHdGraph.textContent = "生成中";
  try {
    const response = await fetch(`${API_BASE}/exports/knowledge-graph.svg?max_nodes=760`);
    if (!response.ok) throw new Error(await response.text());
    const blob = await response.blob();
    downloadBlob(blob, `knowledge-graph-hd-${Date.now()}.svg`, "image/svg+xml");
  } catch (error) {
    addMessage("system", `高清图生成失败：${escapeHtml(error.message)}`, "system");
  } finally {
    downloadHdGraph.disabled = false;
    downloadHdGraph.textContent = originalText;
  }
}

async function downloadBackendWordReport() {
  downloadWordReport.disabled = true;
  const originalText = downloadWordReport.textContent;
  downloadWordReport.textContent = "生成中";
  const query = lastUserQuery || queryInput.value.trim() || "请生成当前农业知识库的专业概览报告";
  try {
    const response = await fetch(`${API_BASE}/exports/word-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        title: "AgriKB 农业知识库分析报告",
        top_k: 8,
        include_graph: true,
      }),
    });
    if (!response.ok) throw new Error(await response.text());
    const blob = await response.blob();
    downloadBlob(blob, `knowledge-report-${Date.now()}.docx`, "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
    addMessage("system", "已生成 Word 报告，包含依据链、知识图谱和分析说明。", "system");
  } catch (error) {
    addMessage("system", `Word 报告生成失败：${escapeHtml(error.message)}`, "system");
  } finally {
    downloadWordReport.disabled = false;
    downloadWordReport.textContent = originalText;
  }
}

async function screenshotCurrentVisual() {
  const svg = treeViewMode === "map" ? treeMapSvg : treeViewMode === "graph" ? treeGraphSvg : null;
  if (!svg) {
    setTreeMode("map");
    await new Promise((resolve) => requestAnimationFrame(resolve));
    return screenshotSvg(treeMapSvg, `knowledge-tree-${Date.now()}.png`);
  }
  return screenshotSvg(svg, `knowledge-${treeViewMode}-${Date.now()}.png`);
}

async function screenshotSvg(svg, filename) {
  const clone = svg.cloneNode(true);
  const box = svg.viewBox?.baseVal;
  const width = Math.max(800, Math.round(box?.width || svg.clientWidth || 1000));
  const height = Math.max(500, Math.round(box?.height || svg.clientHeight || 620));
  clone.setAttribute("width", width);
  clone.setAttribute("height", height);
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const style = document.createElement("style");
  style.textContent = [...document.styleSheets]
    .map((sheet) => {
      try {
        return [...sheet.cssRules].map((rule) => rule.cssText).join("\n");
      } catch {
        return "";
      }
    })
    .join("\n");
  clone.insertBefore(style, clone.firstChild);
  const svgText = new XMLSerializer().serializeToString(clone);
  const blob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const image = new Image();
  image.decoding = "async";
  const loaded = new Promise((resolve, reject) => {
    image.onload = resolve;
    image.onerror = reject;
  });
  image.src = url;
  await loaded;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#f6f7f3";
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(image, 0, 0, width, height);
  URL.revokeObjectURL(url);
  canvas.toBlob((png) => {
    if (png) downloadBlob(png, filename, "image/png");
  }, "image/png");
}

function downloadBlob(content, filename, type) {
  const blob = content instanceof Blob ? content : new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function scheduleNonCriticalStartup() {
  const schedule = window.requestIdleCallback || ((callback) => window.setTimeout(callback, 80));
  schedule(() => loadRuntimeSettings({ quiet: true }), { timeout: 900 });
  schedule(() => loadOllamaModels({ quiet: true }), { timeout: 1100 });
  schedule(() => loadLocalLivePanel(), { timeout: 1300 });
  schedule(() => loadCompetitionHeadlines(), { timeout: 1380 });
  schedule(() => loadMarketPricePanel(), { timeout: 1450 });
  schedule(() => loadPolicyIntelligencePanel({ quiet: true }), { timeout: 1600 });
  schedule(() => loadRuleMemory(), { timeout: 1750 });
  schedule(() => loadSessions(), { timeout: 1900 });
}

syncLocationInputsFromState();
if (queryInput) queryInput.placeholder = "问政策补贴、行情价格、天气风险、收购渠道，或上传资料后继续问。";
syncAppSettingsUi();
updateAskAvailability();
positionFloatingComposer();
initMarketPriceControls();
renderIpLocationStatus(locationContextState.ipLocation);
productionLocationInput?.addEventListener("input", () => clearMapPointForManualInput("production"));
marketLocationInput?.addEventListener("input", () => clearMapPointForManualInput("market"));
weatherLocationInput?.addEventListener("input", () => clearMapPointForManualInput("weather"));
openProductionMapPicker?.addEventListener("click", () => openLocationMapPicker("production"));
openMarketMapPicker?.addEventListener("click", () => openLocationMapPicker("market"));
openWeatherMapPicker?.addEventListener("click", () => openLocationMapPicker("weather"));
openFilePanel?.addEventListener("click", () => openUtilityPanel(filePanelOverlay));
closeFilePanel?.addEventListener("click", () => closeUtilityPanel(filePanelOverlay));
openSettingsPanel?.addEventListener("click", openSettingsDialog);
closeSettingsPanel?.addEventListener("click", () => closeUtilityPanel(settingsPanelOverlay));
filePanelOverlay?.addEventListener("click", (event) => {
  if (event.target === filePanelOverlay) closeUtilityPanel(filePanelOverlay);
});
settingsPanelOverlay?.addEventListener("click", (event) => {
  if (event.target === settingsPanelOverlay) closeUtilityPanel(settingsPanelOverlay);
});
fileImportKnowledge?.addEventListener("click", () => fileInput?.click());
fileImportSettings?.addEventListener("click", () => settingsImportInput?.click());
fileExportSettings?.addEventListener("click", exportRuntimeSettings);
fileExportSession?.addEventListener("click", exportCurrentSessionJson);
fileExportRulesButton?.addEventListener("click", exportAllRuleMemory);
fileExportGraph?.addEventListener("click", exportCurrentVisual);
fileExportWord?.addEventListener("click", downloadBackendWordReport);
fileExportAnswer?.addEventListener("click", exportLastAnswerMarkdown);
settingsImportInput?.addEventListener("change", () => importRuntimeSettingsFile(settingsImportInput.files?.[0]));
reloadSettingsButton?.addEventListener("click", () => loadRuntimeSettings());
saveSettingsButton?.addEventListener("click", saveRuntimeSettings);
testBackendApiButton?.addEventListener("click", () => testRuntimeApiKey("backend"));
testFrontendApiButton?.addEventListener("click", () => testRuntimeApiKey("frontend"));
testAllApiButton?.addEventListener("click", () => testRuntimeApiKey("both"));
copyMobileUrlButton?.addEventListener("click", copyMobileAccessUrl);
webSearchToggle?.addEventListener("change", () => {
  appSettings.defaultWebSearch = Boolean(webSearchToggle.checked);
  saveAppSettings();
  syncAppSettingsUi();
});
closeMapPicker?.addEventListener("click", closeLocationMapPicker);
mapPickerOverlay?.addEventListener("click", (event) => {
  if (event.target === mapPickerOverlay) closeLocationMapPicker();
});
mapPickerSearchButton?.addEventListener("click", searchMapPickerLocation);
mapPickerSearch?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    searchMapPickerLocation();
  }
});
confirmMapPicker?.addEventListener("click", confirmMapPickerPoint);
marketPriceCategory?.addEventListener("change", () => {
  renderMarketPricePresetOptions();
  loadMarketPricePanel();
});
marketPricePreset?.addEventListener("change", () => {
  if (marketPriceInput) marketPriceInput.value = marketPricePreset.value;
  loadMarketPricePanel();
});
refreshMarketPrice?.addEventListener("click", loadMarketPricePanel);
refreshCompetitionHeadlines?.addEventListener("click", () => loadCompetitionHeadlines({ force: true }));
refreshPolicyIntelligence?.addEventListener("click", () => loadPolicyIntelligencePanel());
policyActionButtons.forEach((button) => {
  button.addEventListener("click", handlePolicyActionClick);
});
marketPriceRows?.addEventListener("click", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  const button = target?.closest(".market-product-link");
  if (!button) return;
  requestMarketPriceInsight(button.dataset.marketProduct || button.textContent);
});
marketPriceInsight?.addEventListener("click", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  const button = target?.closest(".market-insight-trigger");
  if (!button) return;
  requestMarketPriceInsight(button.dataset.marketProduct || lastMarketPricePayload?.product);
});
marketPriceInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    loadMarketPricePanel();
  }
});
applyWeatherLocation?.addEventListener("click", applyWeatherLocationFromInput);
weatherLocationInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    applyWeatherLocationFromInput();
  }
});
weatherHorizonGrid?.addEventListener("click", handleWeatherHorizonClick);
weatherHorizonGrid?.addEventListener("keydown", handleWeatherHorizonKeydown);
weatherHorizonGrid?.addEventListener("touchstart", handleWeatherHorizonTouchStart, { passive: true });
weatherHorizonGrid?.addEventListener("touchend", handleWeatherHorizonTouchEnd, { passive: true });
refreshLocalLive?.addEventListener("click", () => {
  updateLocationContextFromInputs();
  loadLocalLivePanel({ force: true });
  loadMarketPricePanel();
  loadPolicyIntelligencePanel({ quiet: true });
  refreshDynamicHeadlines({ force: true });
});
localNewsTrack?.addEventListener("click", handleHeadlineChipActivation);
document.addEventListener("pointerdown", handleHeadlineChipActivation, { capture: true });
applyLocationContext?.addEventListener("click", () => {
  updateLocationContextFromInputs();
  loadLocalLivePanel({ force: true });
  loadCompetitionHeadlines({ force: true });
  loadMarketPricePanel();
  loadPolicyIntelligencePanel({ quiet: true });
  refreshDynamicHeadlines({ force: true });
});
detectIpLocation?.addEventListener("click", detectIpAndUseAsProductionLocation);
refreshModelsButton?.addEventListener("click", () => loadOllamaModels());
applyModelButton?.addEventListener("click", applySelectedAnswerModel);
modelSelect?.addEventListener("change", () => {
  if (applyModelButton) applyModelButton.disabled = !modelSelect.value;
  if (!modelStatusText) return;
  modelStatusText.textContent = modelSelect.value
    ? "点击“用于回答”完成切换"
    : "默认使用新农人助手";
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeHeadlineDetail();
  if (event.key === "Escape") {
    closeUtilityPanel(filePanelOverlay);
    closeUtilityPanel(settingsPanelOverlay);
  }
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refreshDynamicHeadlines({ force: true });
});
window.addEventListener("resize", positionFloatingComposer);
window.addEventListener("scroll", positionFloatingComposer, { passive: true });

initVoiceInteraction();
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  navigator.serviceWorker.register("./service-worker.js").catch(() => {});
}
openFeatureWorkbench("crop", { silent: true });
showWelcomeMessage();
checkHealth();
loadTree({ limit: INITIAL_TREE_LIMIT });
scheduleNonCriticalStartup();
startDynamicRecommendationRefresh();
window.setInterval(() => loadCompetitionHeadlines(), 8 * 60 * 1000);
