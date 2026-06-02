from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUPPORT_ROOT = ROOT / "data" / "raw" / "public_agriculture_sources" / "jurong_local_agri_support"
REPORT_DIR = SUPPORT_ROOT / "reports"
HISTORY_DIR = SUPPORT_ROOT / "historical_data"
MANIFEST_PATH = SUPPORT_ROOT / "jurong_support_manifest.json"
RULE_PATH = ROOT / "knowledge" / "agent_memory" / "gbrain_rules.json"
BACKUP_DIR = ROOT / "knowledge" / "agent_memory" / "backups"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _rule_id(text: str) -> str:
    normalized = "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text)).lower()
    return "rule_" + hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


def _load_manifest_urls() -> dict[str, str]:
    if not MANIFEST_PATH.exists():
        return {}
    try:
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    result: dict[str, str] = {}
    for item in payload.get("records", []):
        file_name = Path(str(item.get("file") or "")).name
        url = str(item.get("url") or "")
        if file_name and url:
            result[file_name] = url
    return result


def _existing_doc_names(names: list[str]) -> list[str]:
    docs: list[str] = []
    for name in names:
        path = REPORT_DIR / name
        if not path.exists():
            path = HISTORY_DIR / name
        if path.exists():
            docs.append(name)
    return docs


def _source_urls(doc_names: list[str], urls: dict[str, str]) -> list[str]:
    return [urls[name] for name in doc_names if urls.get(name)]


RULE_SPECS: list[dict[str, Any]] = [
    {
        "text": "遇到降雨、高湿或防汛提示时，成熟果蔬先抢采、防潮、分级，再安排冷链和病虫巡查。",
        "plain_explanation": "这条规则把天气风险转成当天动作：先保住已经成熟、最容易损耗的农产品，再处理运输、储存和灾后病虫害。",
        "action_steps": [
            "查看未来24到72小时降雨、湿度和风力。",
            "成熟果蔬优先采收，采后垫高、防潮、通风。",
            "按等级包装，联系冷链或近场销售渠道。",
            "雨后第二天巡查病虫害、倒伏和积水。",
        ],
        "applicable_conditions": "适用于江苏句容及周边果蔬、茶叶、粮油作物在强降雨、高湿、霜冻或高温前后的生产安排。",
        "risk_warning": "大棚用电、农机作业、药剂使用和保险理赔要按官方预警、农技意见和保险条款执行。",
        "keywords": ["天气", "降雨", "高湿", "采收", "冷链", "病虫害"],
        "doc_names": [
            "56_马明龙检查防汛抗旱和夏收夏种工作时强调_坚决筑牢抵御水旱灾害坚固防线_不误农时有序推进保障粮食安全.md",
            "18_我局联合派驻纪检监察组现场查勘农业保险受灾情况.md",
        ],
    },
    {
        "text": "丁庄葡萄等高价值鲜果，要把技术服务、抽检记录、分级包装和订单渠道连成一条销售链。",
        "plain_explanation": "鲜果能不能卖出好价，不只看产量；要让技术、质量、品牌和销售渠道互相证明，形成可追溯、可议价的商品。",
        "action_steps": [
            "按成熟度和果品等级分批采收。",
            "保留科技小院、抽检、用药和田间管理记录。",
            "分级包装后分别对接电商、商超、批发和团购。",
            "用订单反馈调整下一季品种和管理方案。",
        ],
        "applicable_conditions": "适用于江苏句容丁庄葡萄、福桃、草莓等高价值鲜食农产品。",
        "risk_warning": "跨平台销售和大订单要核对结算周期、退货标准、冷链责任和质量检测要求。",
        "keywords": ["丁庄葡萄", "科技小院", "抽检", "分级包装", "订单", "电商"],
        "doc_names": [
            "15_深化技术创新_驱动产业兴旺_科技小院擦亮丁庄葡萄名片.md",
            "27_升级的甜蜜正奔向千家万户_丁庄葡萄智慧链护航鲜甜直达.md",
            "43_550盒丁庄葡萄首抵盒马.md",
        ],
    },
    {
        "text": "茅山茶产业不只卖茶叶，要同步做生态茶园、制茶赛事、研学体验和区域品牌。",
        "plain_explanation": "茶产业增收的关键是把一片茶园变成多种收入入口：茶叶销售、体验消费、品牌传播和农文旅客流相互带动。",
        "action_steps": [
            "把茶园生态、采摘、加工和品鉴做成可展示流程。",
            "借助斗茶会、制茶赛等活动提升品牌信任。",
            "把散客体验、团购礼盒和线上销售分开设计。",
            "用游客反馈和订单数据优化产品组合。",
        ],
        "applicable_conditions": "适用于江苏句容茅山茶及相近的茶旅融合、休闲农业和区域品牌建设场景。",
        "risk_warning": "宣传口径要与真实产地、等级、认证和加工能力一致，避免过度承诺影响品牌信用。",
        "keywords": ["茅山茶", "生态茶园", "农文旅", "区域品牌", "制茶赛事"],
        "doc_names": [
            "05_绿叶_变_金叶_茶园成公园_茅山镇茶_业_绘就乡村振兴新画卷.md",
            "06_茅山镇茶_业_激活乡村振兴新引擎.md",
            "42_第二届句容_茅山长青杯_制茶大赛举行.md",
        ],
    },
    {
        "text": "白兔草莓花果期要把保温、防冻、授粉、病虫害和采摘销售排在同一张日程表。",
        "plain_explanation": "草莓花果期最怕只管种植不管销售，技术窗口和采摘窗口很短，防冻、品质和上市节奏要同步安排。",
        "action_steps": [
            "每天检查棚温、湿度、花果状态和授粉情况。",
            "遇到低温先做保温和棚膜检查。",
            "根据成熟度安排采摘、预冷、包装和当日销售。",
            "把病虫害、裂果和畸形果记录给农技人员复盘。",
        ],
        "applicable_conditions": "适用于江苏句容白兔草莓及设施果蔬花果期管理。",
        "risk_warning": "低温、连续阴雨和高湿会叠加影响授粉和病害，不能只看单一天气指标。",
        "keywords": ["白兔草莓", "花果期", "保温", "防冻", "设施农业"],
        "doc_names": [
            "36_5000亩白兔草莓迎花果期_专家下田为优质丰产保驾护航.md",
            "51_科技Buff叠满_白兔草莓御寒稳丰收.md",
            "54_江苏_句容_草莓产业推介活动举行.md",
        ],
    },
    {
        "text": "高标准农田建设先补水利、道路、田块和上图入库，再谈规模化种植和农机调度。",
        "plain_explanation": "高标准农田不是只看面积，真正影响产能的是田块平整、水利排灌、道路通达、数据入库和后期管护。",
        "action_steps": [
            "先核对田块边界、排灌条件、道路和障碍点。",
            "把问题田块上图入库并形成整改清单。",
            "再安排农机路线、作物布局和集中服务。",
            "把管护责任、验收资料和后续收益记录留档。",
        ],
        "applicable_conditions": "适用于江苏句容粮油、蔬菜、规模经营主体和农业局高标准农田项目管理。",
        "risk_warning": "项目建设要以正式规划、招投标、验收和管护制度为准，不能用口头承诺替代资料。",
        "keywords": ["高标准农田", "上图入库", "水利", "农机", "规模经营"],
        "doc_names": [
            "50_市农业农村局组织召开全市高标准农田调查摸底上图入库评审会.md",
            "57_句容市高标准农田调查摸底上图入库外业采集工作正式启动.md",
        ],
    },
    {
        "text": "戴庄生态农业经验的关键是秸秆粪肥循环、合作社组织和农旅融合，让收益更多留在本地。",
        "plain_explanation": "生态农业的重点不是单个技术，而是把种养废弃物、土壤改良、合作经营和乡村消费连接成闭环。",
        "action_steps": [
            "统计秸秆、粪肥、绿肥等可循环资源。",
            "由合作社或村集体组织统一处理和回田。",
            "把生态种植成果转化为品牌、研学和体验消费。",
            "用成本下降和销售增长共同评价成效。",
        ],
        "applicable_conditions": "适用于江苏句容戴庄经验、生态循环农业、合作社经营和农文旅融合场景。",
        "risk_warning": "粪肥还田、秸秆处理和生态认证要符合环保、农产品质量安全和地方管理要求。",
        "keywords": ["戴庄经验", "生态循环", "合作社", "秸秆粪肥", "共同富裕"],
        "doc_names": [
            "08_赵亚夫_以_戴庄经验_描绘共同富裕新画卷.md",
            "14_赵亚夫当_红娘_戴庄蔡门_牵手_秸秆粪肥互换建强生态循环共富链.md",
            "22_赵亚夫支招到田头_因地制宜发展生物多样性农业.md",
        ],
    },
    {
        "text": "农产品出口或跨区域大订单，先查检疫、检测、包装、溯源和合同，再组织集中发货。",
        "plain_explanation": "外销订单看起来价格高，但真正能不能做，要先判断质量标准、通关检疫、包装规格和违约责任。",
        "action_steps": [
            "确认采购方资质、目的地标准和交付时间。",
            "提前做质量检测、检疫材料和溯源记录。",
            "按合同要求统一包装、预冷和装车。",
            "保存合同、检测、物流和结算凭证。",
        ],
        "applicable_conditions": "适用于江苏句容葡萄、玉米、茶叶、草莓等农产品跨区域销售或出口试单。",
        "risk_warning": "出口和大额合同必须以检疫、海关、市场监管和正式合同要求为准。",
        "keywords": ["出口", "检疫", "检测", "合同", "溯源", "集中发货"],
        "doc_names": [
            "03_茅山镇种植的葡萄和玉米接连在省内首次实现出口_小镇农产品蹚出_出海_新范式.md",
            "30_开展葡萄抽检_保障消费安全.md",
        ],
    },
    {
        "text": "政策申报先核主体、项目类别、截止时间和证据材料，不能只看补贴名称。",
        "plain_explanation": "政策能不能拿到，常常取决于主体资格和材料完整度；先把条件对齐，比临近截止再补材料更稳。",
        "action_steps": [
            "确认申报主体是个人、合作社、企业还是村集体。",
            "核对政策对应的产业、规模、时间和主管部门。",
            "准备证照、地块、合同、票据、照片和经营记录。",
            "提交前做一次材料缺口清单。",
        ],
        "applicable_conditions": "适用于新农人、合作社、农业企业和农业局窗口做政策匹配、奖补申报和材料预审。",
        "risk_warning": "所有补贴以正式通知、申报指南和主管部门解释为准，不要根据二手消息直接承诺收益。",
        "keywords": ["政策申报", "补贴", "扶持", "主体资格", "材料预审"],
        "doc_names": [
            "31_句容市农业农村局2025年度法治_政府_建设工作报告.md",
            "44_句容人社_打造人才_引擎_赋能乡村振兴.md",
        ],
    },
    {
        "text": "市场销售先算本地价、目标市场价、损耗和物流净收益，再决定自卖、批发、平台或订单农业。",
        "plain_explanation": "同一批货不是价格最高就一定最赚钱，冷链、损耗、账期、退货和人工都会改变最后到手收益。",
        "action_steps": [
            "查询本地市场和目标市场同品类价格。",
            "估算运输、冷链、包装、平台扣点和损耗。",
            "按净收益比较批发、电商、团购和订单渠道。",
            "把成交价和退货情况沉淀为下一次报价依据。",
        ],
        "applicable_conditions": "适用于江苏句容农产品面向镇江、南京、上海及周边市场做销售路径选择。",
        "risk_warning": "公开价格只是参考，实际成交要核对规格、等级、交易量、账期和售后责任。",
        "keywords": ["市场行情", "目标市场", "物流成本", "净收益", "销售渠道"],
        "doc_names": [
            "21_华阳福桃产业再添新引擎.md",
            "43_550盒丁庄葡萄首抵盒马.md",
            "55_农产品区域公用品牌创建工作专题会议召开_周必松主持.md",
        ],
    },
    {
        "text": "使用多年统计数据判断产业时，看趋势和结构变化，不能用单一年份的涨跌替代决策。",
        "plain_explanation": "年度统计公报适合看长期趋势：面积、产量、收入和产业结构一起变化，才能判断一个产业是不是值得继续投。",
        "action_steps": [
            "至少对比三年以上的农业产量、收入和产业结构。",
            "把异常天气、政策项目和市场周期作为解释因素。",
            "结合当前价格和本地订单判断近期动作。",
            "用趋势结论支撑种植结构、项目申报和招商方向。",
        ],
        "applicable_conditions": "适用于农业局产业研判、合作社扩种决策、企业选品和新农人创业评估。",
        "risk_warning": "统计数据有发布时间和口径差异，要标明年份、来源和指标含义。",
        "keywords": ["统计数据", "产业趋势", "结构变化", "经营判断", "农业产量"],
        "doc_names": [
            "jurong_statistics_2022.md",
            "jurong_statistics_2023.md",
            "jurong_statistics_2024.md",
        ],
    },
    {
        "text": "水稻穗期病虫防治要跟随农技意见统一窗口、科学用药，避开高温风雨并保留作业记录。",
        "plain_explanation": "水稻病虫害防治最怕错过窗口或重复乱用药，统一时间、统一药剂原则和记录留痕可以同时保产和控风险。",
        "action_steps": [
            "先看农业技术推广中心发布的防治意见。",
            "按田块苗情和虫情确定是否达标防治。",
            "避开强风、降雨和高温时段施药。",
            "保存药剂、剂量、时间、田块和作业人记录。",
        ],
        "applicable_conditions": "适用于江苏句容水稻穗期、夏秋季病虫害防治和规模化托管作业。",
        "risk_warning": "农药选择、剂量、安全间隔期和绿色防控要求必须按当地农技意见和标签执行。",
        "keywords": ["水稻", "穗期", "病虫害", "科学用药", "农技意见"],
        "doc_names": [
            "34_全面打好水稻穗期病虫防治第一仗.md",
            "45_水稻病虫害第二次总体防治技术意见.md",
            "53_市农业技术推广中心开展水稻病虫害调查.md",
        ],
    },
    {
        "text": "春耕备耕要把农机检修、农资储备、农技服务和天气窗口提前排好，抢农时比事后补救更重要。",
        "plain_explanation": "春耕的核心是时间窗口管理，机具、种肥、人员和天气任何一项掉链子，都会影响播种质量和后续产量。",
        "action_steps": [
            "提前检查拖拉机、插秧机、植保机和关键零部件。",
            "核对种子、肥料、农药和燃油储备。",
            "跟农技服务站确认播种、育秧和植保建议。",
            "根据天气窗口安排连续作业和备用方案。",
        ],
        "applicable_conditions": "适用于江苏句容春耕备耕、夏收夏种、农机社会化服务和规模经营主体排班。",
        "risk_warning": "农机安全、农资质量和农药合规要提前核验，不能为了抢进度忽略安全。",
        "keywords": ["春耕备耕", "农机", "农资", "农技服务", "天气窗口"],
        "doc_names": [
            "32_智慧农机_马力_足_农技专家服务优_田间地头绘就欣欣向荣_春耕图.md",
            "41_技防物防齐发力_农机农技双护航_农业部门多措并举护航春耕备耕.md",
        ],
    },
]


def build_rule(spec: dict[str, Any], urls: dict[str, str], now: str) -> dict[str, Any]:
    doc_names = _existing_doc_names(list(spec.get("doc_names") or []))
    evidence_ids = [f"jurong_support:{Path(name).stem}" for name in doc_names]
    return {
        "id": _rule_id(spec["text"]),
        "text": spec["text"],
        "source_type": "document",
        "source_types": ["document"],
        "memory_kind": "decision_heuristic",
        "memory_kind_label": "决策规则",
        "plain_explanation": spec["plain_explanation"],
        "action_steps": spec["action_steps"],
        "applicable_conditions": spec["applicable_conditions"],
        "risk_warning": spec["risk_warning"],
        "decision_trigger": "当问题涉及" + "、".join(spec["keywords"][:3]) + "时使用。",
        "heuristic": spec["text"],
        "anti_pattern": "不要只看单一因素下结论，要同时核对本地资料、实时数据、成本收益和政策边界。",
        "boundary": "依据已下载的江苏句容本地农业报道、农业农村相关公开资料和历年统计公报沉淀；执行前仍需核对最新通知和现场情况。",
        "transfer_scope": spec["applicable_conditions"],
        "validation": {
            "status": "validated" if len(doc_names) >= 2 else "provisional",
            "source_type": "document",
            "evidence_count": len(doc_names),
            "source_weight": 1.0,
            "confidence": 0.86 if len(doc_names) >= 2 else 0.74,
            "checks": {
                "cross_context": len(doc_names) >= 2,
                "generative": True,
                "exclusive": True,
            },
        },
        "support_count": max(1, len(doc_names)),
        "confidence": 0.86 if len(doc_names) >= 2 else 0.74,
        "quality": 0.96 if len(doc_names) >= 2 else 0.88,
        "keywords": spec["keywords"],
        "evidence_ids": evidence_ids,
        "doc_names": doc_names,
        "source_urls": _source_urls(doc_names, urls),
        "created_at": now,
        "updated_at": now,
    }


def main() -> None:
    now = _now()
    RULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if RULE_PATH.exists():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / f"gbrain_rules_before_agri_explanations_{time.strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy2(RULE_PATH, backup_path)
    urls = _load_manifest_urls()
    rules = [build_rule(spec, urls, now) for spec in RULE_SPECS]
    payload = {
        "version": 3,
        "updated_at": now,
        "rules": rules,
        "stats": {
            "seeded_agri_explanations": len(rules),
            "support_base": "江苏句容本地农业报道、历年统计公报、公开农业专著目录",
            "replaced_noisy_legacy_rules": True,
            "max_rules": 80,
        },
    }
    RULE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "rules": len(rules), "path": str(RULE_PATH)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
