from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
import uuid
from copy import deepcopy
from typing import Any, List, Optional
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from core.doc_parser import PARSER_MAP
from src.agent_capabilities import (
    RowboatCapabilityAdapter,
    build_word_report,
    render_knowledge_graph_html,
    render_knowledge_graph_png,
    render_knowledge_graph_svg,
)
from src.backend.headline_recommender import recommend_headlines
from src.backend.competition_intelligence import build_competition_headline_intelligence
from src.backend.providers.ollama import OllamaProvider
from src.backend.providers.kimi_cli import KimiCliProvider
from src.backend.providers.openai_compatible import OpenAICompatibleProvider
from src.backend.market_intelligence import build_market_price_intelligence
from src.backend.regional_intelligence import build_location_market_context, build_regional_intelligence
from src.backend.service import KnowledgeBaseService
from src.backend.utils import load_config
from src.backend.voice_tts import get_tts_status, synthesize_chinese_tts_bytes
from src.backend.web_search import search_web


try:  # pragma: no cover - optional dependency during bootstrap
    from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - handled gracefully at runtime
    FastAPI = None
    BackgroundTasks = None
    File = None
    Form = None
    HTTPException = RuntimeError
    Request = object
    UploadFile = object
    CORSMiddleware = None
    FileResponse = None
    HTMLResponse = None
    RedirectResponse = None
    Response = None
    StaticFiles = None
    BaseModel = object
    Field = lambda default=None, **_: default


ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"
INGEST_JOBS: dict[str, dict] = {}
CHUNK_UPLOAD_LOCKS: dict[str, threading.Lock] = {}
INGEST_LOCK = threading.Lock()


class InlineDocument(BaseModel):
    name: str
    content: str


class IngestRequest(BaseModel):
    paths: List[str] = Field(default_factory=list)
    documents: List[InlineDocument] = Field(default_factory=list)


class IngestJobRequest(BaseModel):
    paths: List[str] = Field(default_factory=list)
    saved_paths: List[str] = Field(default_factory=list)
    extracted_paths: List[str] = Field(default_factory=list)


class IngestJobsStatusRequest(BaseModel):
    job_ids: List[str] = Field(default_factory=list)


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 8


class GenerateRequest(BaseModel):
    query: str
    top_k: int = 8
    use_llm: Optional[bool] = None
    model: Optional[str] = None
    answer_language: str = "auto"


class QueryRequest(BaseModel):
    query: str
    module_context: str = ""
    session_id: Optional[str] = None
    top_k: int = 8
    use_llm: Optional[bool] = None
    model: Optional[str] = None
    web_search: bool = False
    web_search_k: int = 5
    regional_intelligence: bool = True
    production_location: str = "Toulouse, Occitanie, France"
    market_location: str = "Toulouse MIN Occitanie wholesale market"
    production_lat: Optional[float] = None
    production_lon: Optional[float] = None
    market_lat: Optional[float] = None
    market_lon: Optional[float] = None
    answer_language: str = "auto"


class WebSearchRequest(BaseModel):
    query: str
    max_results: int = 5


class HeadlineRecommendRequest(BaseModel):
    query: str = "Toulouse Occitanie agriculture policy weather market cooperative traceability"
    production_location: str = "Toulouse, Occitanie, France"
    market_location: str = "Toulouse MIN Occitanie wholesale market"
    items: list[dict[str, Any]] = Field(default_factory=list)
    limit: int = 12


class ModelSelectRequest(BaseModel):
    model: str


class RuntimeSettingsRequest(BaseModel):
    backend: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    frontend_base_url: Optional[str] = None
    frontend_model: Optional[str] = None
    frontend_api_key: Optional[str] = None
    ollama_model: Optional[str] = None
    kimi_executable: Optional[str] = None
    save_to_env: bool = True


class RuntimeSettingsTestRequest(BaseModel):
    target: str = "both"
    backend: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    frontend_base_url: Optional[str] = None
    frontend_model: Optional[str] = None
    frontend_api_key: Optional[str] = None
    kimi_executable: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    rate: float = 1.0


class KnowledgeResetRequest(BaseModel):
    include_raw: bool = False
    clear_sessions: bool = True
    clear_rules: bool = True


class RuleMemoryRefreshRequest(BaseModel):
    reset: bool = False
    limit: int = 900


class RuleInterpretRequest(BaseModel):
    rule_id: str
    context: str = ""
    persist: bool = False
    answer_language: str = "auto"


class RuleInterpretationSaveRequest(BaseModel):
    rule_id: str
    interpretation: dict[str, Any] = Field(default_factory=dict)


class RLMRequest(BaseModel):
    query: str
    top_k: int = 20
    max_iterations: int = 10


class MemoryCaptureRequest(BaseModel):
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    source: str = "manual"
    links: List[str] = Field(default_factory=list)
    ingest: bool = True


class AgentBriefRequest(BaseModel):
    query: str
    top_k: int = 8
    use_llm: Optional[bool] = None
    save_memory: bool = True


class WordReportRequest(BaseModel):
    query: str = ""
    title: str = "AgriKB Toulouse Agriculture Knowledge Graph Report"
    top_k: int = 8
    use_llm: Optional[bool] = None
    include_graph: bool = True


def create_app() -> "FastAPI":
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Install requirements.txt to run the backend API.")

    config = load_config()
    service = KnowledgeBaseService(config)
    agent_layer = RowboatCapabilityAdapter(config)
    app = FastAPI(title="AgriKB Public Agriculture RAG Service", version="5.0.0")

    if config.get("api", {}).get("enable_cors", True):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.get("api", {}).get("allowed_origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if WEB_DIR.exists():
        app.mount("/ui", StaticFiles(directory=str(WEB_DIR), html=True), name="ui")
    wiki_dir = service.config.get("storage", {}).get("wiki_dir", "./knowledge/wiki")
    wiki_path = Path(wiki_dir)
    if not wiki_path.is_absolute():
        wiki_path = ROOT / wiki_path
    if wiki_path.exists():
        app.mount("/wiki", StaticFiles(directory=str(wiki_path), html=False), name="wiki")

    @app.get("/")
    def root_redirect():
        return RedirectResponse(url="/ui/") if WEB_DIR.exists() else {"service": "AgriKB Public Agriculture RAG Service"}

    @app.get("/health")
    def health() -> dict:
        provider_available = service.provider.check_connection()
        ollama_available = OllamaProvider(config).check_connection()
        return {
            "status": "ok",
            "backend": config.get("backend", "ollama"),
            "active_provider": service.provider.__class__.__name__,
            "provider_available": provider_available,
            "ollama_available": ollama_available,
            "model": service.active_model_name(),
            "indexed_chunk_count": service._indexed_chunk_count,
        }

    @app.post("/ingest")
    def ingest(request: IngestRequest) -> dict:
        if not request.paths and not request.documents:
            raise HTTPException(status_code=400, detail="Provide either document paths or inline documents.")
        summary = {"documents_processed": 0, "chunks_written": 0, "wiki_pages_written": 0}
        if request.paths:
            result = service.ingest_paths(request.paths)
            for key, value in result.items():
                summary[key] += value
        if request.documents:
            payloads = [{"name": item.name, "content": item.content} for item in request.documents]
            result = service.ingest_documents(payloads)
            for key, value in result.items():
                summary[key] += value
        return summary

    @app.post("/upload")
    def upload(
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        background: bool = Form(False),
        defer_ingest: bool = Form(False),
    ) -> dict:
        saved_paths: list[str] = []
        for upload_file in files:
            target = _unique_upload_target(service.raw_dir, upload_file.filename or "upload.bin")
            target.write_bytes(upload_file.file.read())
            saved_paths.append(str(target))

        ingest_paths, extracted_paths = _prepare_ingest_paths(service.raw_dir, saved_paths)
        if defer_ingest:
            return {
                "accepted": True,
                "background": False,
                "deferred": True,
                "files_saved": saved_paths,
                "files_extracted": extracted_paths,
                "ingest_paths": ingest_paths,
                "documents_processed": 0,
                "chunks_written": 0,
                "wiki_pages_written": 0,
            }
        if background:
            return _schedule_ingest_job(background_tasks, service, ingest_paths, saved_paths, extracted_paths)

        summary = service.ingest_paths(ingest_paths)
        summary["files_saved"] = saved_paths
        summary["files_extracted"] = extracted_paths
        return summary

    @app.post("/upload/chunk")
    def upload_chunk(
        background_tasks: BackgroundTasks,
        file_id: str = Form(...),
        filename: str = Form(...),
        chunk_index: int = Form(...),
        total_chunks: int = Form(...),
        chunk: UploadFile = File(...),
        background: bool = Form(False),
        defer_ingest: bool = Form(False),
    ) -> dict:
        safe_file_id = Path(file_id).name.replace(".", "_")
        chunk_dir = service.raw_dir / ".upload_chunks" / safe_file_id
        chunk_dir.mkdir(parents=True, exist_ok=True)
        (chunk_dir / f"{chunk_index:06d}.part").write_bytes(chunk.file.read())

        lock = CHUNK_UPLOAD_LOCKS.setdefault(safe_file_id, threading.Lock())
        with lock:
            expected = [chunk_dir / f"{idx:06d}.part" for idx in range(total_chunks)]
            if not all(path.exists() for path in expected):
                return {"complete": False, "received_chunk": chunk_index, "total_chunks": total_chunks}

            target = _unique_upload_target(service.raw_dir, filename)
            with target.open("wb") as output:
                for part in expected:
                    output.write(part.read_bytes())
                    part.unlink()
            chunk_dir.rmdir()
            CHUNK_UPLOAD_LOCKS.pop(safe_file_id, None)

        ingest_paths, extracted_paths = _prepare_ingest_paths(service.raw_dir, [str(target)])
        if defer_ingest:
            return {
                "complete": True,
                "accepted": True,
                "background": False,
                "deferred": True,
                "files_saved": [str(target)],
                "files_extracted": extracted_paths,
                "ingest_paths": ingest_paths,
                "documents_processed": 0,
                "chunks_written": 0,
                "wiki_pages_written": 0,
            }
        if background:
            result = _schedule_ingest_job(background_tasks, service, ingest_paths, [str(target)], extracted_paths)
            result["complete"] = True
            return result

        summary = service.ingest_paths(ingest_paths)
        summary["complete"] = True
        summary["files_saved"] = [str(target)]
        summary["files_extracted"] = extracted_paths
        return summary

    @app.post("/upload/chunk/cancel")
    def cancel_chunk_upload(file_id: str = Form(...)) -> dict:
        safe_file_id = Path(file_id).name.replace(".", "_")
        chunk_dir = service.raw_dir / ".upload_chunks" / safe_file_id
        if chunk_dir.exists():
            shutil.rmtree(chunk_dir)
            CHUNK_UPLOAD_LOCKS.pop(safe_file_id, None)
            return {"cancelled": True, "cleaned": True}
        CHUNK_UPLOAD_LOCKS.pop(safe_file_id, None)
        return {"cancelled": True, "cleaned": False}

    @app.get("/ingest/jobs/{job_id}")
    def ingest_job_status(job_id: str) -> dict:
        job = INGEST_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Unknown ingest job")
        return job

    @app.post("/ingest/jobs")
    def create_ingest_job(background_tasks: BackgroundTasks, request: IngestJobRequest) -> dict:
        paths = list(dict.fromkeys(request.paths))
        if not paths:
            raise HTTPException(status_code=400, detail="Provide paths to ingest.")
        return _schedule_ingest_job(background_tasks, service, paths, request.saved_paths, request.extracted_paths)

    @app.post("/ingest/jobs/status")
    def ingest_jobs_status(request: IngestJobsStatusRequest) -> dict:
        jobs = []
        for job_id in request.job_ids:
            job = INGEST_JOBS.get(job_id)
            if job:
                jobs.append(job)
        return {"jobs": jobs}

    @app.post("/ingest/jobs-batch-status")
    def ingest_jobs_batch_status(request: IngestJobsStatusRequest) -> dict:
        return ingest_jobs_status(request)

    @app.post("/retrieve")
    def retrieve(request: RetrieveRequest) -> dict:
        return service.retrieve(request.query, top_k=request.top_k)

    @app.post("/generate")
    def generate(request: GenerateRequest) -> dict:
        try:
            return service.generate(request.query, top_k=request.top_k, use_llm=request.use_llm, model=request.model, answer_language=request.answer_language)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/models")
    def api_models() -> dict:
        return service.get_model_status()

    @app.get("/api/settings")
    def api_settings() -> dict:
        return _runtime_settings_payload(service, config)

    @app.post("/api/settings")
    def api_settings_update(request: RuntimeSettingsRequest) -> dict:
        try:
            settings = request.model_dump(exclude_unset=True) if hasattr(request, "model_dump") else request.dict(exclude_unset=True)
            payload = service.apply_runtime_settings(settings)
            if request.save_to_env:
                _write_runtime_env(settings)
            return {"saved": bool(request.save_to_env), "settings": _runtime_settings_payload(service, config), "models": payload}
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/settings/test")
    def api_settings_test(request: RuntimeSettingsTestRequest) -> dict:
        settings = request.model_dump(exclude_unset=True) if hasattr(request, "model_dump") else request.dict(exclude_unset=True)
        return _test_runtime_settings(service, config, settings)

    @app.post("/api/models/select")
    def api_models_select(request: ModelSelectRequest) -> dict:
        try:
            return service.select_ollama_model(request.model)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/voice/tts/status")
    def api_voice_tts_status() -> dict:
        return get_tts_status()

    @app.post("/api/voice/tts")
    async def api_voice_tts(request: TTSRequest):
        try:
            audio_bytes, filename = synthesize_chinese_tts_bytes(request.text, rate=request.rate)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    @app.get("/api/knowledge/tree")
    def api_knowledge_tree(limit: int = 0, doc_id: str = "", q: str = "") -> dict:
        return service.get_dynamic_knowledge_tree(limit=limit or None, doc_id=doc_id, q=q)

    @app.get("/api/knowledge/graph")
    def api_knowledge_graph(limit: int = 300, doc_id: str = "", q: str = "", full: bool = False) -> dict:
        return service.get_knowledge_graph(limit=limit, doc_id=doc_id, q=q, full=full)

    @app.post("/api/query")
    def api_query(request: QueryRequest, http_request: Request) -> dict:
        try:
            web_results = search_web(request.query, request.web_search_k) if request.web_search else []
            client_ip = http_request.client.host if http_request.client else ""
            regional_payload = build_regional_intelligence(
                request.query,
                enabled=request.regional_intelligence,
                production_location=request.production_location,
                market_location=request.market_location,
                production_lat=request.production_lat,
                production_lon=request.production_lon,
                market_lat=request.market_lat,
                market_lon=request.market_lon,
                client_ip=client_ip,
                llm_provider=service.provider,
            )
            result = service.query(
                request.query,
                session_id=request.session_id,
                top_k=request.top_k,
                use_llm=request.use_llm,
                model=request.model,
                answer_language=request.answer_language,
                web_results=web_results,
                regional_intelligence=regional_payload,
                module_context=request.module_context,
            )
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if request.web_search:
            result["web_search_results"] = web_results
        if request.regional_intelligence:
            result["regional_intelligence"] = regional_payload
        result["active_ingest"] = _active_ingest_snapshot()
        return result

    @app.post("/api/web/search")
    def api_web_search(request: WebSearchRequest) -> dict:
        return {"query": request.query, "results": search_web(request.query, request.max_results)}

    @app.post("/api/headlines/recommend")
    def api_headline_recommend(request: HeadlineRecommendRequest) -> dict:
        return {
            "algorithm": "BM25 + MMR diversity rerank",
            "headlines": recommend_headlines(
                request.items,
                query=request.query,
                production_name=request.production_location,
                market_name=request.market_location,
                limit=max(1, min(request.limit, 24)),
            ),
        }

    @app.get("/api/competition/headlines")
    def api_competition_headlines(location: str = "Toulouse, Occitanie, France", force: bool = False) -> dict:
        return build_competition_headline_intelligence(
            location=location,
            llm_provider=service.provider,
            force_refresh=force,
        )

    @app.get("/api/regional/live")
    def api_regional_live(
        http_request: Request,
        query: str = "Toulouse Occitanie agriculture weather temperature market CAP policy news",
        production_location: str = "Toulouse, Occitanie, France",
        market_location: str = "Toulouse MIN Occitanie wholesale market",
        weather_location: str = "Toulouse, Occitanie, France",
        production_lat: Optional[float] = None,
        production_lon: Optional[float] = None,
        market_lat: Optional[float] = None,
        market_lon: Optional[float] = None,
        weather_lat: Optional[float] = None,
        weather_lon: Optional[float] = None,
    ) -> dict:
        client_ip = http_request.client.host if http_request.client else ""
        return build_regional_intelligence(
            query,
            enabled=True,
            production_location=production_location,
            market_location=market_location,
            weather_location=weather_location,
            production_lat=production_lat,
            production_lon=production_lon,
            market_lat=market_lat,
            market_lon=market_lon,
            weather_lat=weather_lat,
            weather_lon=weather_lon,
            client_ip=client_ip,
            llm_provider=service.provider,
        )

    @app.get("/api/location/context")
    def api_location_context(
        http_request: Request,
        query: str = "Toulouse agriculture policy market logistics weather",
        production_location: str = "Toulouse, Occitanie, France",
        market_location: str = "Toulouse MIN Occitanie wholesale market",
        production_lat: Optional[float] = None,
        production_lon: Optional[float] = None,
        market_lat: Optional[float] = None,
        market_lon: Optional[float] = None,
    ) -> dict:
        client_ip = http_request.client.host if http_request.client else ""
        return build_location_market_context(
            query=query,
            production_location=production_location,
            market_location=market_location,
            production_lat=production_lat,
            production_lon=production_lon,
            market_lat=market_lat,
            market_lon=market_lon,
            client_ip=client_ip,
            llm_provider=service.provider,
            enabled=True,
        )

    @app.get("/api/market/prices")
    def api_market_prices(
        product: str = "grape",
        category: str = "produce",
        production_location: str = "Toulouse, Occitanie, France",
        market_location: str = "Toulouse MIN Occitanie wholesale market",
        include_ai: bool = False,
    ) -> dict:
        return build_market_price_intelligence(
            product=product,
            category=category,
            production_location=production_location,
            market_location=market_location,
            llm_provider=service.provider if include_ai else None,
            include_ai=include_ai,
        )

    @app.post("/api/knowledge/reset")
    def api_knowledge_reset(request: KnowledgeResetRequest) -> dict:
        return service.reset_knowledge_tree(
            include_raw=request.include_raw,
            clear_sessions=request.clear_sessions,
            clear_rules=request.clear_rules,
        )

    @app.get("/api/memory/rules")
    def api_memory_rules(q: str = "", limit: int = 80) -> dict:
        return service.get_rule_memory(query=q, limit=limit)

    @app.post("/api/memory/rules/refresh")
    def api_memory_rules_refresh(request: RuleMemoryRefreshRequest) -> dict:
        return service.refresh_rule_memory(reset=request.reset, limit=request.limit)

    @app.post("/api/memory/rules/interpret")
    def api_memory_rules_interpret(request: RuleInterpretRequest) -> dict:
        try:
            return service.interpret_rule_memory(request.rule_id, context=request.context, persist=request.persist, answer_language=request.answer_language)
        except (RuntimeError, ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/memory/rules/interpretation")
    def api_memory_rules_interpretation_save(request: RuleInterpretationSaveRequest) -> dict:
        try:
            return service.persist_rule_interpretation(request.rule_id, request.interpretation)
        except (RuntimeError, ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/memory/rules")
    def api_memory_rules_clear() -> dict:
        return service.clear_rule_memory()

    @app.get("/api/session/{session_id}/evidence-graph")
    def api_session_evidence_graph(session_id: str) -> dict:
        return service.get_session_evidence_graph(session_id)

    @app.get("/api/sessions")
    def api_sessions(limit: int = 80) -> dict:
        return service.list_sessions(limit=limit)

    @app.delete("/api/sessions")
    def api_sessions_clear() -> dict:
        return service.clear_sessions()

    @app.get("/api/session/{session_id}")
    def api_session(session_id: str) -> dict:
        return service.get_session_evidence_graph(session_id)

    @app.delete("/api/session/{session_id}")
    def api_session_clear(session_id: str) -> dict:
        return service.clear_session(session_id)

    @app.post("/status")
    def refresh_status() -> dict:
        available = service.refresh_provider_status()
        return {
            "provider_available": available,
            "ollama_available": OllamaProvider(config).check_connection(),
            "indexed_chunk_count": service._indexed_chunk_count,
            "backend": config.get("backend", "ollama"),
            "active_provider": service.provider.__class__.__name__,
            "model": service.active_model_name(),
        }

    @app.post("/rlm")
    def rlm_generate(request: RLMRequest) -> dict:
        from src.rlm.recursive_retrieval import RecursiveRetrievalEngine

        rlm_config = dict(config)
        rlm_config.setdefault("rlm", {})["max_iterations"] = request.max_iterations
        rlm_config.setdefault("feature_flags", {})["ENABLE_RLM"] = True

        engine = RecursiveRetrievalEngine(service, config=rlm_config)
        result = engine.run(request.query, top_k=request.top_k)
        return result.to_dict()

    @app.get("/tree")
    def tree() -> dict:
        return service.get_knowledge_tree()

    @app.get("/agent/capabilities")
    def agent_capabilities() -> dict:
        return agent_layer.describe(indexed_chunk_count=service._indexed_chunk_count)

    @app.get("/agent/workflows")
    def agent_workflows() -> dict:
        return {"templates": agent_layer.workflow_templates()}

    @app.get("/agent/memory")
    def agent_memory(query: str = "", limit: int = 20) -> dict:
        return agent_layer.search_memory(query=query, limit=limit)

    @app.post("/agent/memory")
    def capture_agent_memory(request: MemoryCaptureRequest) -> dict:
        note = agent_layer.capture_memory(
            title=request.title,
            content=request.content,
            tags=request.tags,
            source=request.source,
            links=request.links,
        )
        ingest_summary: dict[str, Any] = {}
        if request.ingest:
            ingest_summary = service.ingest_documents(
                [
                    {
                        "name": Path(note["path"]).name,
                        "path": note["path"],
                        "content": request.content,
                    }
                ]
            )
        return {"note": note, "ingest": ingest_summary}

    @app.post("/agent/workflows/brief")
    def run_agent_brief(request: AgentBriefRequest) -> dict:
        result = service.generate(request.query, top_k=request.top_k, use_llm=request.use_llm)
        note = None
        if request.save_memory:
            note = agent_layer.capture_memory(
                title=f"Evidence brief - {request.query[:60]}",
                content=_brief_markdown(request.query, result),
                tags=["agent-brief", "rowboat-compatible", "evidence-grounded"],
                source="agent_workflow",
            )
        workflow = agent_layer.save_workflow_run(
            "evidence_brief",
            {
                "query": request.query,
                "top_k": request.top_k,
                "citations": result.get("citations", []),
                "memory_note": note,
            },
        )
        result["workflow"] = workflow
        result["memory_note"] = note
        result["capability_layer"] = "rowboat_compatible_agent_layer"
        return result

    @app.get("/exports/knowledge-graph.svg")
    def export_knowledge_graph_svg(max_nodes: int = 520):
        svg = render_knowledge_graph_svg(service.get_dynamic_knowledge_tree()["root"], max_nodes=max_nodes)
        return Response(content=svg, media_type="image/svg+xml; charset=utf-8")

    @app.get("/exports/knowledge-graph.html")
    def export_knowledge_graph_html():
        html = render_knowledge_graph_html(service.get_dynamic_knowledge_tree()["root"])
        return HTMLResponse(content=html)

    @app.get("/exports/knowledge-graph.png")
    def export_knowledge_graph_png(max_nodes: int = 360):
        target = agent_layer.exports_dir / f"knowledge-graph-{int(time.time())}.png"
        render_knowledge_graph_png(service.get_dynamic_knowledge_tree()["root"], target, max_nodes=max_nodes)
        return FileResponse(path=str(target), filename=target.name, media_type="image/png")

    def _create_word_report(request: WordReportRequest):
        query = request.query.strip() or "Generate a professional overview report for the current agriculture knowledge base."
        generation = service.generate(query, top_k=request.top_k, use_llm=request.use_llm)
        tree_payload = service.get_dynamic_knowledge_tree()["root"]
        stamp = time.strftime("%Y%m%d_%H%M%S")
        graph_svg_path = None
        graph_html_path = None
        graph_png_path = None
        if request.include_graph:
            graph_svg_path = agent_layer.exports_dir / f"knowledge-graph-{stamp}.svg"
            graph_html_path = agent_layer.exports_dir / f"knowledge-graph-{stamp}.html"
            graph_svg_path.write_text(render_knowledge_graph_svg(tree_payload), encoding="utf-8")
            graph_html_path.write_text(render_knowledge_graph_html(tree_payload), encoding="utf-8")
            try:
                graph_png_path = agent_layer.exports_dir / f"knowledge-graph-{stamp}.png"
                render_knowledge_graph_png(tree_payload, graph_png_path)
            except Exception:
                graph_png_path = None
        report_path = agent_layer.exports_dir / f"agent-report-{stamp}.docx"
        build_word_report(
            report_path,
            title=request.title,
            query=query,
            generation=generation,
            tree=tree_payload,
            capabilities=agent_layer.describe(indexed_chunk_count=service._indexed_chunk_count),
            graph_image_path=graph_png_path,
            graph_svg_path=graph_svg_path,
            graph_html_path=graph_html_path,
        )
        return FileResponse(
            path=str(report_path),
            filename=report_path.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    @app.post("/exports/word-report")
    def export_word_report(request: WordReportRequest):
        return _create_word_report(request)

    @app.get("/exports/word-report")
    def export_word_report_get(query: str = "", top_k: int = 8):
        return _create_word_report(WordReportRequest(query=query, top_k=top_k, use_llm=False))

    return app


app = create_app() if FastAPI is not None else None


def _active_model_name(config: dict) -> str:
    backend = str(config.get("backend", "ollama")).lower()
    if backend == "kimi_cli":
        return config.get("kimi_cli", {}).get("model") or config.get("openai_compatible", {}).get("model", "kimi-for-coding")
    if backend in {"openai", "openai_compatible", "api_key"}:
        return config.get("openai_compatible", {}).get("model", "unknown")
    return config.get("ollama", {}).get("model", "unknown")


def _runtime_settings_payload(service: KnowledgeBaseService, config: dict) -> dict:
    openai_cfg = config.get("openai_compatible", {}) or {}
    kimi_cfg = config.get("kimi_cli", {}) or {}
    frontend_cfg = config.get("frontend_api", {}) or {}
    ollama_cfg = config.get("ollama", {}) or {}
    api_key = kimi_cfg.get("api_key") or openai_cfg.get("api_key") or os.environ.get("KIMI_API_KEY") or os.environ.get("KNOWLEDGE_RAG_API_KEY") or ""
    frontend_api_key = (
        frontend_cfg.get("api_key")
        or os.environ.get("AGRIKB_FRONTEND_KIMI_API_KEY")
        or os.environ.get("FRONTEND_RAG_API_KEY")
        or ""
    )
    model_status = service.get_model_status()
    return {
        "backend": config.get("backend", "auto"),
        "base_url": kimi_cfg.get("base_url") or openai_cfg.get("base_url", ""),
        "model": kimi_cfg.get("model") or openai_cfg.get("model", ""),
        "frontend_base_url": frontend_cfg.get("base_url") or os.environ.get("AGRIKB_FRONTEND_BASE_URL") or kimi_cfg.get("base_url") or openai_cfg.get("base_url", ""),
        "frontend_model": frontend_cfg.get("model") or os.environ.get("AGRIKB_FRONTEND_MODEL") or kimi_cfg.get("model") or openai_cfg.get("model", ""),
        "ollama_model": ollama_cfg.get("model", ""),
        "kimi_executable": kimi_cfg.get("executable", "kimi"),
        "api_key_present": bool(api_key),
        "api_key_hint": _mask_secret(api_key),
        "backend_api_key_present": bool(api_key),
        "backend_api_key_hint": _mask_secret(api_key),
        "frontend_api_key_present": bool(frontend_api_key),
        "frontend_api_key_hint": _mask_secret(frontend_api_key),
        "active_provider": model_status.get("active_provider"),
        "active_model": model_status.get("active_model"),
        "provider_available": model_status.get("provider_available"),
        "ollama_available": model_status.get("ollama_available"),
        "models": model_status.get("models", []),
    }


def _test_runtime_settings(service: KnowledgeBaseService, config: dict, settings: dict[str, Any]) -> dict:
    target = str(settings.get("target") or "both").strip().lower()
    if target not in {"backend", "frontend", "both"}:
        target = "both"
    payload = {"target": target, "tested_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if target in {"backend", "both"}:
        payload["backend_test"] = _run_runtime_connection_test("backend", config, settings)
    if target in {"frontend", "both"}:
        payload["frontend_test"] = _run_runtime_connection_test("frontend", config, settings)
    payload["ok"] = all(item.get("ok") for key, item in payload.items() if key.endswith("_test"))
    return payload


def _run_runtime_connection_test(channel: str, config: dict, settings: dict[str, Any]) -> dict:
    started = time.time()
    effective = _effective_runtime_channel(channel, config, settings)
    marker = f"AGRIKB_API_TEST_OK_{channel.upper()}_{int(started)}"
    test_config = _build_runtime_test_config(config, effective)
    provider_name = "kimi_cli" if _should_use_kimi_cli(effective) else "openai_compatible"
    test_config["backend"] = provider_name
    old_timeout = os.environ.get("AGRIKB_KIMI_TIMEOUT")
    try:
        if provider_name == "kimi_cli":
            os.environ["AGRIKB_KIMI_TIMEOUT"] = str(min(_safe_int(old_timeout, 180), 60))
            provider = KimiCliProvider(test_config)
        else:
            provider = OpenAICompatibleProvider(test_config)
        answer = provider.generate(
            f"请只返回下面这一段连通性测试标记，不要解释：\n{marker}",
            system="Connection test only. Return the exact marker text and nothing else.",
        )
        sample = _sanitize_secret_error(str(answer or "").strip())[:160]
        ok = marker in str(answer or "")
        return {
            "ok": bool(ok),
            "channel": channel,
            "provider": provider_name,
            "base_url": _safe_public_url(effective.get("base_url", "")),
            "model": effective.get("model", ""),
            "api_key_present": bool(effective.get("api_key")),
            "api_key_hint": _mask_secret(effective.get("api_key", "")),
            "seconds": round(time.time() - started, 2),
            "message": "真实模型调用通过。" if ok else "模型有返回，但未包含测试标记，请检查模型或中间代理。",
            "sample": sample,
        }
    except Exception as exc:
        return {
            "ok": False,
            "channel": channel,
            "provider": provider_name,
            "base_url": _safe_public_url(effective.get("base_url", "")),
            "model": effective.get("model", ""),
            "api_key_present": bool(effective.get("api_key")),
            "api_key_hint": _mask_secret(effective.get("api_key", "")),
            "seconds": round(time.time() - started, 2),
            "message": _sanitize_secret_error(str(exc)),
        }
    finally:
        if old_timeout is None:
            os.environ.pop("AGRIKB_KIMI_TIMEOUT", None)
        else:
            os.environ["AGRIKB_KIMI_TIMEOUT"] = old_timeout


def _effective_runtime_channel(channel: str, config: dict, settings: dict[str, Any]) -> dict[str, str]:
    openai_cfg = config.get("openai_compatible", {}) or {}
    kimi_cfg = config.get("kimi_cli", {}) or {}
    frontend_cfg = config.get("frontend_api", {}) or {}
    backend_values = {
        "backend": str(settings.get("backend") or config.get("backend") or "auto"),
        "base_url": _first_value(settings.get("base_url"), kimi_cfg.get("base_url"), openai_cfg.get("base_url"), os.environ.get("KNOWLEDGE_RAG_BASE_URL"), "https://api.kimi.com/coding/v1"),
        "model": _first_value(settings.get("model"), kimi_cfg.get("model"), openai_cfg.get("model"), os.environ.get("KNOWLEDGE_RAG_MODEL"), "kimi-for-coding"),
        "api_key": _first_value(settings.get("api_key"), kimi_cfg.get("api_key"), openai_cfg.get("api_key"), os.environ.get("KIMI_API_KEY"), os.environ.get("KNOWLEDGE_RAG_API_KEY")),
        "kimi_executable": _first_value(settings.get("kimi_executable"), kimi_cfg.get("executable"), "./runtime/kimi/kimi.exe"),
    }
    if channel == "backend":
        return backend_values
    return {
        "backend": backend_values["backend"],
        "base_url": _first_value(settings.get("frontend_base_url"), frontend_cfg.get("base_url"), os.environ.get("AGRIKB_FRONTEND_BASE_URL"), backend_values["base_url"]),
        "model": _first_value(settings.get("frontend_model"), frontend_cfg.get("model"), os.environ.get("AGRIKB_FRONTEND_MODEL"), backend_values["model"]),
        "api_key": _first_value(settings.get("frontend_api_key"), frontend_cfg.get("api_key"), os.environ.get("AGRIKB_FRONTEND_KIMI_API_KEY"), os.environ.get("FRONTEND_RAG_API_KEY"), settings.get("api_key"), backend_values["api_key"]),
        "kimi_executable": backend_values["kimi_executable"],
    }


def _build_runtime_test_config(config: dict, effective: dict[str, str]) -> dict:
    test_config = deepcopy(config)
    openai_cfg = test_config.setdefault("openai_compatible", {})
    kimi_cfg = test_config.setdefault("kimi_cli", {})
    openai_cfg.update(
        {
            "base_url": effective.get("base_url", ""),
            "model": effective.get("model", ""),
            "api_key": effective.get("api_key", ""),
            "temperature": 0,
            "max_tokens": 48,
        }
    )
    kimi_cfg.update(
        {
            "base_url": effective.get("base_url", ""),
            "model": effective.get("model", ""),
            "api_key": effective.get("api_key", ""),
            "executable": effective.get("kimi_executable") or "./runtime/kimi/kimi.exe",
            "timeout": 60,
            "max_retries": 1,
        }
    )
    return test_config


def _should_use_kimi_cli(effective: dict[str, str]) -> bool:
    backend = str(effective.get("backend") or "").lower()
    base_url = str(effective.get("base_url") or "").lower()
    model = str(effective.get("model") or "")
    api_key = str(effective.get("api_key") or "")
    return backend == "kimi_cli" or "api.kimi.com/coding" in base_url or model == "kimi-for-coding" or api_key.startswith("sk-kimi-")


def _is_kimi_coding_plan_key(value: Any) -> bool:
    return str(value or "").strip().startswith("sk-kimi-")


def _first_value(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _safe_public_url(value: str) -> str:
    text = str(value or "")
    return re.sub(r"(api_key|key|token)=([^&]+)", r"\1=***", text, flags=re.I)


def _sanitize_secret_error(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", text)
    text = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer ***", text, flags=re.I)
    return text[:900]


def _mask_secret(value: str) -> str:
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= 12:
        return "***"
    return f"***{value[-4:]}"


def _write_runtime_env(settings: dict[str, Any]) -> None:
    updates: dict[str, str] = {}
    backend = str(settings.get("backend") or "").strip()
    if backend:
        updates["KNOWLEDGE_RAG_BACKEND"] = backend
    base_url = str(settings.get("base_url") or "").strip()
    if base_url:
        updates["KIMI_BASE_URL"] = base_url
        updates["KNOWLEDGE_RAG_BASE_URL"] = base_url
    model = str(settings.get("model") or "").strip()
    if model:
        updates["KIMI_MODEL"] = model
        updates["KNOWLEDGE_RAG_MODEL"] = model
    api_key = str(settings.get("api_key") or "").strip()
    if api_key:
        updates["KIMI_API_KEY"] = api_key
        updates["MOONSHOT_API_KEY"] = api_key
        updates["KNOWLEDGE_RAG_API_KEY"] = api_key
    frontend_base_url = str(settings.get("frontend_base_url") or "").strip()
    if frontend_base_url:
        updates["AGRIKB_FRONTEND_BASE_URL"] = frontend_base_url
    frontend_model = str(settings.get("frontend_model") or "").strip()
    if frontend_model:
        updates["AGRIKB_FRONTEND_MODEL"] = frontend_model
    frontend_api_key = str(settings.get("frontend_api_key") or "").strip()
    if frontend_api_key:
        updates["AGRIKB_FRONTEND_KIMI_API_KEY"] = frontend_api_key
    effective_backend_key = (
        api_key
        or os.environ.get("KIMI_API_KEY")
        or os.environ.get("KNOWLEDGE_RAG_API_KEY")
        or os.environ.get("MOONSHOT_API_KEY")
        or ""
    )
    effective_frontend_key = frontend_api_key or os.environ.get("AGRIKB_FRONTEND_KIMI_API_KEY") or ""
    if _is_kimi_coding_plan_key(effective_backend_key):
        updates["KNOWLEDGE_RAG_BACKEND"] = "kimi_cli"
        updates["KIMI_BASE_URL"] = "https://api.kimi.com/coding/v1"
        updates["KIMI_MODEL"] = "kimi-for-coding"
        updates["KNOWLEDGE_RAG_BASE_URL"] = "https://api.kimi.com/coding/v1"
        updates["KNOWLEDGE_RAG_MODEL"] = "kimi-for-coding"
        updates["KIMI_API_KEY"] = effective_backend_key
        updates["MOONSHOT_API_KEY"] = effective_backend_key
        updates["KNOWLEDGE_RAG_API_KEY"] = effective_backend_key
    if _is_kimi_coding_plan_key(effective_frontend_key):
        updates["AGRIKB_FRONTEND_BASE_URL"] = "https://api.kimi.com/coding/v1"
        updates["AGRIKB_FRONTEND_MODEL"] = "kimi-for-coding"
        updates["AGRIKB_FRONTEND_KIMI_API_KEY"] = effective_frontend_key
    ollama_model = str(settings.get("ollama_model") or "").strip()
    if ollama_model:
        updates["OLLAMA_MODEL"] = ollama_model
    if not updates:
        return
    env_path = ROOT / ".env"
    existing: dict[str, str] = {}
    comments: list[str] = []
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                comments.append(raw_line)
                continue
            key, value = raw_line.split("=", 1)
            existing[key.strip()] = value.strip()
    existing.update(updates)
    ordered_keys = [
        "KNOWLEDGE_RAG_BACKEND",
        "KIMI_BASE_URL",
        "KIMI_MODEL",
        "KIMI_API_KEY",
        "KNOWLEDGE_RAG_BASE_URL",
        "KNOWLEDGE_RAG_MODEL",
        "KNOWLEDGE_RAG_API_KEY",
        "MOONSHOT_API_KEY",
        "AGRIKB_FRONTEND_BASE_URL",
        "AGRIKB_FRONTEND_MODEL",
        "AGRIKB_FRONTEND_KIMI_API_KEY",
        "OLLAMA_MODEL",
    ]
    lines = [
        "# AgriKB local runtime settings. Keep this file private.",
        "# Updated by the GUI settings panel.",
    ]
    for key in ordered_keys:
        if key in existing:
            lines.append(f"{key}={_quote_env(existing[key])}")
    for key in sorted(k for k in existing if k not in ordered_keys):
        lines.append(f"{key}={_quote_env(existing[key])}")
    env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    for key, value in updates.items():
        os.environ[key] = value.strip('"').strip("'")


def _quote_env(value: str) -> str:
    raw = str(value or "").strip().strip('"').strip("'")
    if not raw:
        return ""
    if re.search(r"\s|#|=|\"", raw):
        return json.dumps(raw, ensure_ascii=False)
    return raw


def _brief_markdown(query: str, result: dict) -> str:
    lines = [
        "## Query",
        query,
        "",
        "## Answer",
        str(result.get("answer", "")).strip(),
        "",
        "## Evidence Chain",
    ]
    evidence = result.get("evidence_chain") or result.get("evidence_chunks") or result.get("retrieval_results") or []
    for index, item in enumerate(evidence[:10], start=1):
        source = item.get("doc_name") or item.get("source") or "unknown"
        support = item.get("supports") or item.get("chunk_type") or "evidence"
        excerpt = item.get("excerpt") or item.get("text") or ""
        lines.extend(
            [
                f"### E{index}: {source}",
                f"- Support: {support}",
                f"- Excerpt: {excerpt[:420]}",
                "",
            ]
        )
    return "\n".join(lines)


def _unique_upload_target(raw_dir: Path, filename: str) -> Path:
    safe_name = Path(filename).name
    target = raw_dir / safe_name
    if not target.exists():
        return target
    suffix = target.suffix
    stem = target.stem
    counter = 2
    while target.exists():
        target = raw_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    return target


def _schedule_ingest_job(
    background_tasks: "BackgroundTasks",
    service: KnowledgeBaseService,
    ingest_paths: list[str],
    saved_paths: list[str],
    extracted_paths: list[str],
) -> dict:
    job_id = uuid.uuid4().hex
    INGEST_JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "stage": "queued",
        "coarse_ready": False,
        "queued_at": time.time(),
        "started_at": None,
        "completed_at": None,
        "duration_seconds": None,
        "total_paths": len(ingest_paths),
        "current_file": "",
        "progress_percent": 0,
        "documents_processed": 0,
        "chunks_written": 0,
        "chunks_coarse": 0,
        "chunks_refined": 0,
        "documents_coarse": 0,
        "documents_refined": 0,
        "wiki_pages_written": 0,
        "files_saved": saved_paths,
        "files_extracted": extracted_paths,
        "error": "",
    }
    background_tasks.add_task(_run_ingest_job, job_id, service, ingest_paths)
    return {
        "accepted": True,
        "background": True,
        "job_id": job_id,
        "status": "queued",
        "files_saved": saved_paths,
        "files_extracted": extracted_paths,
        "documents_processed": 0,
        "chunks_written": 0,
        "wiki_pages_written": 0,
    }


def _run_ingest_job(job_id: str, service: KnowledgeBaseService, ingest_paths: list[str]) -> None:
    job = INGEST_JOBS[job_id]
    job["status"] = "running"
    job["stage"] = "coarse_indexing"
    job["started_at"] = time.time()
    total_paths = max(1, len(ingest_paths))
    last_refresh = 0.0

    def update_progress(progress: dict) -> None:
        nonlocal last_refresh
        processed = int(progress.get("documents_processed", job.get("documents_processed", 0)) or 0)
        job.update(progress)
        job["status"] = "running"
        if progress.get("coarse_ready") or job.get("stage") == "coarse_indexing":
            job["coarse_ready"] = True
            job["stage"] = "coarse_indexing"
            job["documents_coarse"] = max(int(job.get("documents_coarse") or 0), processed)
            job["chunks_coarse"] = max(int(job.get("chunks_coarse") or 0), int(progress.get("chunks_written", 0) or 0))
            job["progress_percent"] = min(18, round((processed / total_paths) * 18))
        else:
            job["stage"] = "refining"
            job["documents_refined"] = processed
            job["chunks_refined"] = int(progress.get("chunks_written", 0) or 0)
            job["progress_percent"] = min(99, 18 + round((processed / total_paths) * 81))
        job["updated_at"] = time.time()
        if job["updated_at"] - last_refresh > 0.9:
            service.refresh_indexes_from_disk()
            last_refresh = job["updated_at"]

    try:
        coarse_summary = service.ingest_coarse_paths(ingest_paths, progress_callback=update_progress)
        job.update(
            {
                "coarse_ready": True,
                "stage": "refining",
                "documents_coarse": coarse_summary.get("coarse_documents", coarse_summary.get("documents_processed", 0)),
                "chunks_coarse": coarse_summary.get("chunks_written", 0),
                "progress_percent": max(job.get("progress_percent", 0), 18),
            }
        )
        with INGEST_LOCK:
            summary = service.ingest_paths(ingest_paths, progress_callback=update_progress)
        service.refresh_indexes_from_disk()
        job.update(summary)
        job["stage"] = "completed"
        job["documents_refined"] = summary.get("documents_processed", 0)
        job["chunks_refined"] = summary.get("chunks_written", 0)
        job["progress_percent"] = 100
        job["status"] = "completed"
    except Exception as exc:  # pragma: no cover - surfaced through job endpoint
        job["status"] = "failed"
        job["error"] = str(exc)
    finally:
        job["completed_at"] = time.time()
        if job.get("started_at"):
            job["duration_seconds"] = round(job["completed_at"] - job["started_at"], 3)


def _active_ingest_snapshot() -> dict:
    jobs = [job for job in INGEST_JOBS.values() if job.get("status") in {"queued", "running"}]
    if not jobs:
        return {"running": False, "coarse_ready": False, "stage": "idle"}
    total_paths = sum(int(job.get("total_paths") or 0) for job in jobs)
    documents_coarse = sum(int(job.get("documents_coarse") or 0) for job in jobs)
    documents_refined = sum(int(job.get("documents_refined") or 0) for job in jobs)
    chunks_coarse = sum(int(job.get("chunks_coarse") or 0) for job in jobs)
    chunks_refined = sum(int(job.get("chunks_refined") or 0) for job in jobs)
    coarse_ready = any(bool(job.get("coarse_ready")) for job in jobs)
    current_file = next((job.get("current_file") for job in jobs if job.get("current_file")), "")
    return {
        "running": True,
        "coarse_ready": coarse_ready,
        "stage": "refining" if coarse_ready else "coarse_indexing",
        "total_paths": total_paths,
        "documents_coarse": documents_coarse,
        "documents_refined": documents_refined,
        "chunks_coarse": chunks_coarse,
        "chunks_refined": chunks_refined,
        "current_file": current_file,
    }


def _prepare_ingest_paths(raw_dir: Path, saved_paths: list[str]) -> tuple[list[str], list[str]]:
    ingest_paths: list[str] = []
    extracted_paths: list[str] = []
    supported_exts = set(PARSER_MAP)
    for saved_path in saved_paths:
        path = Path(saved_path)
        if path.suffix.lower() != ".zip":
            ingest_paths.append(str(path))
            continue
        extracted = _extract_zip_for_ingest(raw_dir, path, supported_exts)
        extracted_paths.extend(extracted)
        ingest_paths.extend(extracted)
    return ingest_paths, extracted_paths


def _extract_zip_for_ingest(raw_dir: Path, zip_path: Path, supported_exts: set[str]) -> list[str]:
    extract_root = _unique_directory(raw_dir / "_unzipped", f"{zip_path.stem}_{int(time.time())}")
    extracted_paths: list[str] = []
    try:
        with ZipFile(zip_path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                target = _safe_zip_member_target(extract_root, member.filename)
                if target is None:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                if target.suffix.lower() in supported_exts:
                    extracted_paths.append(str(target))
    except BadZipFile as exc:
        raise HTTPException(status_code=400, detail=f"Invalid ZIP file: {zip_path.name}") from exc
    return extracted_paths


def _safe_zip_member_target(extract_root: Path, member_name: str) -> Path | None:
    normalized = member_name.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
        return None
    parts = [part for part in normalized.split("/") if part and part not in {".", "__MACOSX"}]
    if not parts or any(part == ".." for part in parts):
        return None
    return extract_root.joinpath(*parts)


def _unique_directory(parent: Path, name: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    safe_name = Path(name).name or "archive"
    target = parent / safe_name
    counter = 2
    while target.exists():
        target = parent / f"{safe_name}_{counter}"
        counter += 1
    target.mkdir(parents=True, exist_ok=False)
    return target
