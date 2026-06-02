# User Guide

## What AeroKB Is

AeroKB is a local knowledge workbench for technical documents. You can upload files, let the system organize them into a knowledge tree, ask questions, inspect the evidence chain behind each answer, and continue a multi-turn conversation with session memory.

## Start the App

Run one of these:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Portable.ps1
```

or double-click:

```text
启动迁移版.bat
```

Open:

```text
http://127.0.0.1:8010/ui/
```

## Upload Documents

Use the upload area on the right side of the page. Supported formats include:

```text
PDF, DOCX, DOC, TXT, Markdown, CSV, XLSX, XLS, PPTX, JSON, YAML, XML, HTML, ZIP
```

For large batches, AeroKB first saves files locally, generates a coarse knowledge tree, then continues deeper ingestion in the background. The page shows progress and updates the dynamic tree as documents are processed.

## Ask Questions

Type a question in the input box and click "发送并生成答案". AeroKB retrieves relevant chunks from the local knowledge base and generates a professional answer.

The answer area is separated into:

- Professional answer: clean natural-language response.
- Evidence chain: graph view showing how the answer is supported.
- Evidence details: source file, snippet, page or chunk metadata when available.

## Evidence and Source Labels

Each answer claim can be labeled as:

| Source Type | Meaning |
| --- | --- |
| `document` | Supported by local document chunks |
| `inferred` | Synthesized from multiple document evidence items |
| `web_search` | Reserved for real web-search provider results |
| `model_prior` | Not from documents; generated from model knowledge |
| `unsupported` | Insufficient or unreliable evidence |

If content is not supported by local documents, it is not shown as document evidence.

## Dynamic Knowledge Tree

The knowledge tree is generated from the actual current knowledge base. It can show:

```text
Document -> Topic / Section -> Chunk -> Entity / Keyword
```

Use search, tree view, graph view, zoom, fit, reset and fullscreen controls to inspect the structure.

## Conversation History

The left sidebar lists previous conversations. You can:

- Start a new conversation.
- Load a previous conversation.
- Delete a conversation.
- Continue asking follow-up questions with session memory.

## Voice Interaction

The UI supports:

- Voice question input, if the browser supports speech recognition.
- Reading the professional answer aloud.
- Adjustable speech rate.

The read-aloud feature only reads the answer body, not evidence cards, file names, scores or UI labels.

## Select Local Ollama Model

If Ollama is installed and running, the model selector under the question box detects local models.

1. Click "刷新" to refresh available models.
2. Select a model.
3. Click "用于回答".

Future answers use the selected model. If Ollama is unavailable, AeroKB uses the configured OpenAI-compatible provider.

## Reset Knowledge Tree

The "重置知识树" button clears generated indexes, sessions and rule memory by default, while keeping raw uploaded files. This is useful when you want to rebuild the knowledge tree from scratch.
