# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JEBMCP bridges JEB Decompiler with MCP (Model Context Protocol), enabling AI assistants to interact with JEB programmatically for APK/DEX reverse engineering tasks.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start MCP server (stdio - for Cursor/Trae/VSCode integration)
python src/server.py --transport stdio

# Start MCP server (HTTP - recommended for clean shutdown)
python src/server.py --transport http --host 127.0.0.1 --port 16162

# Start MCP server (SSE)
python src/server.py --transport sse --host 127.0.0.1 --port 16162
```

Environment variables: `JEB_HOST` (default: 127.0.0.1), `JEB_PORT` (default: 16161), `JEB_PATH` (default: /mcp), `TRANSPORT` (default: stdio), `HOST` (default: 127.0.0.1), `PORT` (default: 16162)

## Architecture

```
AI Client (Claude/Cursor/Trae/VSCode)
    ↓ stdio/sse/http
src/server.py (FastMCP server - 40+ MCP tools)
    ↓ HTTP JSON-RPC
src/MCP.py (JEB plugin on port 16161)
    ↓ JEB API
JEB Decompiler
```

**Key Files:**
- `src/server.py` - FastMCP server exposing MCP tools to AI clients
- `src/MCP.py` - JEB plugin (Jython) that runs inside JEB and handles JSON-RPC requests
- `src/core/jeb_operations.py` - Business logic for decompilation, renaming, and code analysis
- `src/core/project_manager.py` - Project and artifact lifecycle management
- `src/utils/signature_utils.py` - Class signature format conversion (JNI format)
- `src/utils/protoParser.py` - Protobuf definition parsing using assets/PBDecoder.jar

## Code Patterns

**Response Format:** All operations return `{"success": bool, "error": str, ...data}`

**Class Signature Normalization:** The system accepts three formats and normalizes to JNI:
- Plain: `MainActivity` → `Lcom/example/MainActivity;`
- Dotted: `com.example.MainActivity` → `Lcom/example/MainActivity;`
- JNI: `Lcom/example/MainActivity;` (passthrough)

**Two Runtime Environments:**
- `src/server.py` runs in Python 3 with FastMCP
- `src/MCP.py` runs in Jython (Python on JVM) inside JEB - uses JEB API directly

## MCP Tool Categories

- **Project:** load_jeb_project, has_projects, get_projects, get_current_project_info, switch_active_artifact
- **Code Retrieval:** get_class_decompiled_code, get_method_decompiled_code, get_method_smali_code, get_current_app_manifest
- **Analysis:** get_class_methods, get_class_fields, get_class_superclass, get_method_callers, get_method_overrides, get_field_callers, parse_protobuf_class
- **Renaming:** rename_class_name, rename_method_name, rename_field_name, rename_local_variable, set_parameter_name
