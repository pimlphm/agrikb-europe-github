def __getattr__(name: str):
    if name == "KnowledgeBaseService":
        from .service import KnowledgeBaseService
        return KnowledgeBaseService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["KnowledgeBaseService"]
