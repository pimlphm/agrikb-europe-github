from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests


DEFAULT_BASE_URL = "http://127.0.0.1:8010"
BLOCKED_URL_MARKERS = (
    "baidu.com",
    "m.baidu.com",
    "google.com/search",
    "bing.com/search",
    "duckduckgo.com/y.js",
)
POLLUTION_PATTERNS = [
    ("repeated_unit", re.compile(r"(元/(?:公斤|千克|斤|吨|台|袋|瓶|盒|亩|株|件)\s*,\s*)+元/", re.I)),
    ("list_string", re.compile(r"\[(?:'|\").{0,80}(?:'|\")\]")),
    ("prompt_leak_direct", re.compile(r"直接说人话|直接问一句|请用农民")),
    ("wrong_region_name", re.compile("".join(["南", "京", "句", "容"]))),
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    duration_ms: int = 0
    issues: list[str] = field(default_factory=list)


class SmokeRunner:
    def __init__(self, base_url: str, timeout: int = 45, include_llm: bool = False) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.include_llm = include_llm
        self.session = requests.Session()
        self.results: list[CheckResult] = []
        self.cleaned_files: list[str] = []

    def run(self) -> int:
        checks = [
            self.check_health,
            self.check_static_ui,
            self.check_models,
            self.check_tree_and_graph,
            self.check_retrieve_generate_query,
            self.check_web_search,
            self.check_headlines,
            self.check_regional_live,
            self.check_location_context,
            self.check_market_prices_all_categories,
            self.check_sessions_and_rules_read,
            self.check_agent_read_endpoints,
            self.check_upload_defer_and_cleanup,
            self.check_exports,
        ]
        if self.include_llm:
            checks.insert(6, self.check_real_kimi_model_short_answer)
        for check in checks:
            self._run_check(check)
        self._print_report()
        return 0 if all(item.ok for item in self.results) else 1

    def _run_check(self, fn) -> None:
        started = time.perf_counter()
        try:
            result = fn()
            result.duration_ms = int((time.perf_counter() - started) * 1000)
        except Exception as exc:
            result = CheckResult(fn.__name__, False, str(exc), int((time.perf_counter() - started) * 1000))
        self.results.append(result)

    def get(self, path: str, **params: Any) -> Any:
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            return response.json()
        return response.text

    def post(self, path: str, payload: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        response = self.session.post(f"{self.base_url}{path}", json=payload, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            return response.json()
        return response.text

    def check_health(self) -> CheckResult:
        payload = self.get("/health")
        issues = self.scan_payload(payload, "health", strict_display=False)
        ok = payload.get("status") == "ok" and not issues
        return CheckResult("health", ok, f"provider={payload.get('active_provider')} chunks={payload.get('indexed_chunk_count')}", issues=issues)

    def check_static_ui(self) -> CheckResult:
        html = self.get("/ui/")
        app_js = self.get("/ui/app.js?v=qa")
        style_css = self.get("/ui/style.css?v=qa")
        issues = []
        issues.extend(self.scan_text(html, "ui_html", strict_display=True))
        for label, text in [("app_js", app_js), ("style_css", style_css)]:
            issues.extend(self.scan_text(text, label, strict_display=False))
        required = ("localNewsTrack", "localNewsList", "marketPriceRows", "webSearchToggle", "sessionList", "tree")
        for marker in required:
            if marker not in html + app_js:
                issues.append(f"missing_ui_marker:{marker}")
        return CheckResult("static_ui_assets", not issues, "html/js/css loaded", issues=issues[:40])

    def check_models(self) -> CheckResult:
        payload = self.get("/api/models")
        ok = bool(payload.get("active_provider") or payload.get("active_model"))
        return CheckResult("models_status", ok, f"active={payload.get('active_model') or payload.get('model')}")

    def check_tree_and_graph(self) -> CheckResult:
        tree = self.get("/api/knowledge/tree", limit=40)
        graph = self.get("/api/knowledge/graph", limit=80)
        issues = self.scan_payload(tree, "knowledge_tree", strict_display=False)
        issues.extend(self.scan_payload(graph, "knowledge_graph", strict_display=False))
        ok = isinstance(tree, dict) and isinstance(graph, dict) and not issues
        detail = f"tree_keys={len(tree.keys())} graph_nodes={len(graph.get('nodes', [])) if isinstance(graph.get('nodes'), list) else 'n/a'}"
        return CheckResult("knowledge_tree_graph", ok, detail, issues=issues[:40])

    def check_retrieve_generate_query(self) -> CheckResult:
        query = "江苏句容草莓今天采收、销售和天气风险怎么判断？"
        retrieve = self.post("/retrieve", {"query": query, "top_k": 3})
        generate = self.post("/generate", {"query": query, "top_k": 3, "use_llm": False})
        answer = self.post(
            "/api/query",
            {
                "query": query,
                "session_id": f"qa_smoke_{int(time.time())}",
                "top_k": 3,
                "use_llm": False,
                "web_search": False,
                "regional_intelligence": False,
            },
        )
        issues = []
        for label, payload in [("retrieve", retrieve), ("generate", generate), ("query", answer)]:
            issues.extend(self.scan_payload(payload, label, strict_display=True))
        ok = not issues and isinstance(answer.get("answer", ""), str)
        return CheckResult("retrieve_generate_query", ok, "retrieval and non-LLM answer path ok", issues=issues[:40])

    def check_web_search(self) -> CheckResult:
        payload = self.post("/api/web/search", {"query": "农业农村部 农产品 批发市场 价格", "max_results": 3})
        results = payload.get("results", [])
        issues = self.scan_payload(payload, "web_search", strict_display=False)
        issues.extend(self.scan_urls(payload, "web_search"))
        if not results:
            issues.append("web_search_returned_no_results")
        return CheckResult("web_search", isinstance(results, list) and not issues, f"results={len(results)}", issues=issues[:40])

    def check_headlines(self) -> CheckResult:
        items = [
            {"title": "江苏句容农业政策扶持", "snippet": "新农人培训、电商助农和品牌建设。", "source": "policy"},
            {"title": "镇江农产品批发市场价格", "snippet": "关注收购价和冷链时效。", "source": "market"},
            {"title": "今日降雨提醒", "snippet": "成熟果菜先抢采，包装防潮。", "source": "weather"},
        ]
        payload = self.post(
            "/api/headlines/recommend",
            {
                "query": "江苏句容 农业 政策 市场 天气",
                "production_location": "江苏句容",
                "market_location": "镇江农产品批发市场",
                "items": items,
                "limit": 6,
            },
        )
        issues = self.scan_payload(payload, "headlines", strict_display=True)
        ok = bool(payload.get("headlines")) and not issues
        return CheckResult("headline_recommend", ok, f"headlines={len(payload.get('headlines', []))}", issues=issues[:40])

    def check_real_kimi_model_short_answer(self) -> CheckResult:
        payload = self.post(
            "/api/query",
            {
                "query": "用一句话回答：江苏句容草莓遇到降雨前最先做什么？",
                "session_id": f"qa_real_kimi_{int(time.time())}",
                "top_k": 2,
                "use_llm": True,
                "web_search": False,
                "regional_intelligence": True,
                "production_location": "江苏句容",
                "market_location": "镇江农产品批发市场",
                "production_lat": 31.94869,
                "production_lon": 119.1655,
                "market_lat": 32.21086,
                "market_lon": 119.45508,
            },
        )
        answer = payload.get("answer", "")
        issues = self.scan_payload(payload, "real_kimi_query", strict_display=True)
        forbidden = ("鉴权失败", "API Key", "固定回答", "没有召回足够证据")
        for marker in forbidden:
            if marker in answer:
                issues.append(f"llm_answer_forbidden_marker:{marker}")
        ok = bool(payload.get("llm_used")) and payload.get("selected_model") == "kimi-for-coding" and len(answer.strip()) > 20 and not issues
        return CheckResult("real_kimi_model_query", ok, f"llm_used={payload.get('llm_used')} model={payload.get('selected_model')}", issues=issues[:50])

    def check_regional_live(self) -> CheckResult:
        payload = self.get(
            "/api/regional/live",
            query="江苏句容 农业 天气 政策 市场 收购 冷链",
            production_location="江苏句容",
            market_location="镇江农产品批发市场",
            production_lat=31.94869,
            production_lon=119.1655,
            market_lat=32.21086,
            market_lon=119.45508,
        )
        issues = self.scan_payload(payload, "regional_live", strict_display=True)
        issues.extend(self.scan_urls(payload, "regional_live"))
        route = payload.get("route") or {}
        weather = payload.get("production_weather") or {}
        horizons = weather.get("weather_horizons") or []
        labels = {str(item.get("label", "")) for item in horizons if isinstance(item, dict)}
        required_labels = {"今天", "明天", "未来3天", "5-10天", "15天", "3周趋势"}
        missing_labels = sorted(required_labels - labels)
        if missing_labels:
            issues.append(f"weather_horizon_missing:{','.join(missing_labels)}")
        if int(weather.get("forecast_days") or 0) < 15:
            issues.append(f"weather_forecast_days_too_short:{weather.get('forecast_days')}")
        detail = (
            f"weather={bool(weather)} horizons={len(horizons)} forecast_days={weather.get('forecast_days')} "
            f"route={route.get('distance_km', 'n/a')}km suppliers={len(payload.get('logistics_suppliers', []))}"
        )
        return CheckResult("regional_live", not issues, detail, issues=issues[:60])

    def check_location_context(self) -> CheckResult:
        payload = self.get(
            "/api/location/context",
            query="江苏句容 到 镇江农产品批发市场 农产品销售",
            production_location="江苏句容",
            market_location="镇江农产品批发市场",
            production_lat=31.94869,
            production_lon=119.1655,
            market_lat=32.21086,
            market_lon=119.45508,
        )
        issues = self.scan_payload(payload, "location_context", strict_display=True)
        issues.extend(self.scan_urls(payload, "location_context"))
        return CheckResult("location_context", not issues, "two-location context ok", issues=issues[:40])

    def check_market_prices_all_categories(self) -> CheckResult:
        cases = [
            ("produce", "草莓"),
            ("produce", "大葱"),
            ("produce", "水蜜桃"),
            ("fertilizer", "尿素"),
            ("fertilizer", "复合肥"),
            ("machinery", "拖拉机"),
            ("seed", "草莓苗"),
            ("pesticide", "杀菌剂"),
            ("feed", "玉米饲料"),
        ]
        issues: list[str] = []
        row_counts: list[str] = []
        for category, product in cases:
            payload = self.get(
                "/api/market/prices",
                product=product,
                category=category,
                production_location="江苏句容",
                market_location="镇江农产品批发市场",
            )
            rows = payload.get("price_rows", [])
            row_counts.append(f"{category}:{product}:{len(rows)}")
            issues.extend(self.scan_payload(payload, f"market_prices:{category}:{product}", strict_display=True))
            issues.extend(self.scan_market_rows(rows, category, product))
            issues.extend(self.scan_urls(payload, f"market_prices:{category}:{product}"))
        return CheckResult("market_prices_all_categories", not issues, "; ".join(row_counts), issues=issues[:80])

    def check_sessions_and_rules_read(self) -> CheckResult:
        sessions = self.get("/api/sessions", limit=5)
        rules = self.get("/api/memory/rules", limit=10)
        issues = self.scan_payload(sessions, "sessions", strict_display=True)
        issues.extend(self.scan_payload(rules, "rules", strict_display=True))
        return CheckResult("sessions_rules_read", not issues, f"sessions={len(sessions.get('sessions', []))}", issues=issues[:30])

    def check_agent_read_endpoints(self) -> CheckResult:
        capabilities = self.get("/agent/capabilities")
        workflows = self.get("/agent/workflows")
        memory = self.get("/agent/memory", query="农业", limit=5)
        issues = []
        for label, payload in [("capabilities", capabilities), ("workflows", workflows), ("agent_memory", memory)]:
            issues.extend(self.scan_payload(payload, label, strict_display=False))
        return CheckResult("agent_read_endpoints", not issues, "capabilities/workflows/memory read ok", issues=issues[:40])

    def check_upload_defer_and_cleanup(self) -> CheckResult:
        issues: list[str] = []
        files = {
            "files": ("qa_smoke_test.txt", b"QA smoke upload, defer ingest only.", "text/plain"),
        }
        response = self.session.post(
            f"{self.base_url}/upload",
            data={"defer_ingest": "true"},
            files=files,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        issues.extend(self.scan_payload(payload, "upload_defer", strict_display=False))
        for saved in payload.get("files_saved", []):
            self._cleanup_returned_file(saved, issues)

        chunk_response = self.session.post(
            f"{self.base_url}/upload/chunk",
            data={
                "file_id": f"qa_chunk_{int(time.time())}",
                "filename": "qa_chunk_smoke.txt",
                "chunk_index": "0",
                "total_chunks": "1",
                "defer_ingest": "true",
            },
            files={"chunk": ("chunk.part", b"QA chunk upload, defer ingest only.", "application/octet-stream")},
            timeout=self.timeout,
        )
        chunk_response.raise_for_status()
        chunk_payload = chunk_response.json()
        issues.extend(self.scan_payload(chunk_payload, "chunk_upload_defer", strict_display=False))
        for saved in chunk_payload.get("files_saved", []):
            self._cleanup_returned_file(saved, issues)

        cancel = self.session.post(
            f"{self.base_url}/upload/chunk/cancel",
            data={"file_id": "qa_nonexistent_cancel"},
            timeout=self.timeout,
        )
        cancel.raise_for_status()
        issues.extend(self.scan_payload(cancel.json(), "chunk_cancel", strict_display=False))
        return CheckResult("upload_defer_cleanup", not issues, f"cleaned={len(self.cleaned_files)}", issues=issues[:40])

    def check_exports(self) -> CheckResult:
        svg = self.get("/exports/knowledge-graph.svg", max_nodes=80)
        html = self.get("/exports/knowledge-graph.html")
        issues = []
        if "<svg" not in svg[:500].lower():
            issues.append("knowledge_graph_svg_missing_svg_tag")
        if "html" not in html[:500].lower():
            issues.append("knowledge_graph_html_missing_html_tag")
        issues.extend(self.scan_text(svg, "export_svg", strict_display=False))
        issues.extend(self.scan_text(html, "export_html", strict_display=False))
        return CheckResult("exports_graph", not issues, "svg/html exports ok", issues=issues[:40])

    def scan_market_rows(self, rows: Any, category: str, product: str) -> list[str]:
        issues: list[str] = []
        if not isinstance(rows, list):
            return [f"market_rows_not_list:{category}:{product}"]
        for index, row in enumerate(rows[:20]):
            if not isinstance(row, dict):
                issues.append(f"market_row_not_dict:{category}:{product}:{index}")
                continue
            avg_price = str(row.get("avg_price", ""))
            unit = str(row.get("unit", ""))
            combined = f"{avg_price} {unit}"
            if len(unit) > 18:
                issues.append(f"unit_too_long:{category}:{product}:{index}:{unit[:80]}")
            if "," in unit:
                issues.append(f"unit_contains_comma:{category}:{product}:{index}:{unit[:80]}")
            if re.search(r"元/(公斤|千克|斤|吨|台|袋|瓶|盒|亩|株|件).+元/", combined):
                issues.append(f"unit_repeated_in_price:{category}:{product}:{index}:{combined[:100]}")
            if avg_price and not re.search(r"\d", avg_price):
                issues.append(f"price_without_number:{category}:{product}:{index}:{avg_price[:80]}")
        return issues

    def scan_urls(self, payload: Any, label: str) -> list[str]:
        issues: list[str] = []
        for path, value in iter_strings(payload):
            if not value.startswith(("http://", "https://")):
                continue
            lower = value.lower()
            if any(marker in lower for marker in BLOCKED_URL_MARKERS):
                issues.append(f"blocked_url:{label}:{'.'.join(path)}:{value[:140]}")
        return issues

    def scan_payload(self, payload: Any, label: str, strict_display: bool) -> list[str]:
        issues: list[str] = []
        for path, value in iter_strings(payload):
            issues.extend(self.scan_text(value, f"{label}:{'.'.join(path)}", strict_display=strict_display))
        return issues

    def scan_text(self, text: str, label: str, strict_display: bool) -> list[str]:
        issues: list[str] = []
        if not isinstance(text, str):
            return issues
        for name, pattern in POLLUTION_PATTERNS:
            if not strict_display and name in {"list_string", "prompt_leak_direct"}:
                continue
            if pattern.search(text):
                issues.append(f"{name}:{label}:{text[:160]}")
        if strict_display and re.search(r"\b(undefined|null|None)\b", text):
            issues.append(f"placeholder_leak:{label}:{text[:160]}")
        return issues

    def _cleanup_returned_file(self, saved: str, issues: list[str]) -> None:
        try:
            path = Path(saved).resolve()
            root = Path(__file__).resolve().parents[1]
            raw_dir = (root / "data" / "raw").resolve()
            if raw_dir not in path.parents:
                issues.append(f"cleanup_refused_outside_raw:{saved}")
                return
            if path.exists():
                path.unlink()
                self.cleaned_files.append(str(path))
        except Exception as exc:
            issues.append(f"cleanup_failed:{saved}:{exc}")

    def _print_report(self) -> None:
        print("\nAgriKB full smoke and pollution QA")
        print("=" * 42)
        for result in self.results:
            mark = "PASS" if result.ok else "FAIL"
            print(f"{mark:4} {result.name:32} {result.duration_ms:6} ms  {result.detail}")
            for issue in result.issues[:10]:
                print(f"     - {issue}")
            if len(result.issues) > 10:
                print(f"     - ... {len(result.issues) - 10} more")
        print("=" * 42)
        print(f"summary: passed={sum(1 for r in self.results if r.ok)} failed={sum(1 for r in self.results if not r.ok)}")
        if self.cleaned_files:
            print(f"cleaned temporary upload files: {len(self.cleaned_files)}")


def iter_strings(value: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], str]]:
    output: list[tuple[tuple[str, ...], str]] = []
    if isinstance(value, str):
        output.append((path, value))
    elif isinstance(value, dict):
        for key, child in value.items():
            output.extend(iter_strings(child, path + (str(key),)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            output.extend(iter_strings(child, path + (str(index),)))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AgriKB safe smoke tests and data pollution checks.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--include-llm", action="store_true", help="Also run one short real Kimi model answer check.")
    args = parser.parse_args()
    return SmokeRunner(args.base_url, args.timeout, include_llm=args.include_llm).run()


if __name__ == "__main__":
    sys.exit(main())
