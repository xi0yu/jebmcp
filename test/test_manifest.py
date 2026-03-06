# -*- coding: utf-8 -*-
"""
get_current_app_manifest 各 info_type 集成测试

运行前需要：
1. JEB 已启动并加载了 APK 项目 + MCP.py 插件 (端口 16161)
2. MCP server 已启动: python src/server.py --transport http --host 0.0.0.0 --port 16162

运行:
    python test/test_manifest.py
    或
    pytest test/test_manifest.py -v -s
"""

import json
import uuid
import urllib.request

MCP_URL = "http://127.0.0.1:16162/mcp"
SESSION_ID = None


def _post(body: dict) -> dict:
    """发送 POST 请求到 MCP server，返回解析后的 JSON 对象"""
    global SESSION_ID
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if SESSION_ID:
        headers["mcp-session-id"] = SESSION_ID

    req = urllib.request.Request(
        MCP_URL,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        sid = resp.getheader("mcp-session-id")
        if sid:
            SESSION_ID = sid

        raw = resp.read().decode("utf-8")

        # 通知类请求返回空 body
        if not raw.strip():
            return {}

        content_type = resp.getheader("Content-Type", "")
        if "text/event-stream" in content_type:
            # SSE 格式: event: message\ndata: {...}\n\n
            for line in reversed(raw.splitlines()):
                if line.startswith("data: "):
                    return json.loads(line[6:])
            return {}
        else:
            return json.loads(raw)


def initialize():
    """MCP 握手"""
    result = _post({
        "jsonrpc": "2.0",
        "id": f"init-{uuid.uuid4().hex[:8]}",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    })
    print(f"[init] session_id={SESSION_ID}")
    _post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    return result


def call_tool(tool_name: str, arguments: dict = None) -> dict:
    """调用 MCP tool，返回业务数据（已剥离 MCP 协议包装）

    返回值就是 server.py 里 return 的那个 json.loads 后的对象，例如：
    - {"result": {"success": True, "component_type": "activity", ...}}
    - {"result": "<xml ...>"}
    - {"error": "Connection refused ..."}
    """
    resp = _post({
        "jsonrpc": "2.0",
        "id": f"req-{uuid.uuid4().hex[:8]}",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments or {}},
    })
    # MCP 包装: resp["result"]["content"][0]["text"] 是 server.py return 的字符串
    content_list = resp.get("result", {}).get("content", [])
    for item in content_list:
        if item.get("type") == "text":
            text = item["text"]
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw_text": text}
    return resp


# ──────────────────────────────────────────────
#  测试用例
# ──────────────────────────────────────────────

class TestManifestInfoType:
    """测试 get_current_app_manifest 的各种 info_type"""

    @staticmethod
    def _check_jeb_error(data: dict):
        """如果 JEB 连接失败则跳过（而非报错）"""
        err = data.get("error", "")
        if "Connection refused" in err or "timeout" in err.lower():
            raise RuntimeError(f"JEB 未连接: {err}")

    def test_activity(self):
        """info_type=activity"""
        data = call_tool("get_current_app_manifest", {"info_type": "activity"})
        self._check_jeb_error(data)
        r = data["result"]
        print(f"[activity] count={r['count']}, 前3: {[c.get('name') for c in r['components'][:3]]}")
        assert r["success"] is True
        assert r["component_type"] == "activity"
        assert isinstance(r["components"], list)
        assert r["count"] == len(r["components"])

    def test_service(self):
        """info_type=service"""
        data = call_tool("get_current_app_manifest", {"info_type": "service"})
        self._check_jeb_error(data)
        r = data["result"]
        print(f"[service] count={r['count']}")
        assert r["success"] is True
        assert r["component_type"] == "service"
        assert isinstance(r["components"], list)

    def test_receiver(self):
        """info_type=receiver"""
        data = call_tool("get_current_app_manifest", {"info_type": "receiver"})
        self._check_jeb_error(data)
        r = data["result"]
        print(f"[receiver] count={r['count']}")
        assert r["success"] is True
        assert r["component_type"] == "receiver"
        assert isinstance(r["components"], list)

    def test_provider(self):
        """info_type=provider"""
        data = call_tool("get_current_app_manifest", {"info_type": "provider"})
        self._check_jeb_error(data)
        r = data["result"]
        print(f"[provider] count={r['count']}")
        assert r["success"] is True
        assert r["component_type"] == "provider"
        assert isinstance(r["components"], list)

    def test_permission(self):
        """info_type=permission"""
        data = call_tool("get_current_app_manifest", {"info_type": "permission"})
        self._check_jeb_error(data)
        r = data["result"]
        perms = r["uses_permissions"]
        print(f"[permission] count={len(perms)}, 前5: {[p['name'].split('.')[-1] for p in perms[:5]]}")
        assert r["success"] is True
        assert isinstance(perms, list)
        assert isinstance(r["custom_permissions"], list)

    def test_info(self):
        """info_type=info"""
        data = call_tool("get_current_app_manifest", {"info_type": "info"})
        self._check_jeb_error(data)
        r = data["result"]
        print(f"[info] package={r.get('package')}, sdk={r.get('sdk')}")
        assert r["success"] is True
        assert r.get("package"), "package 不应为空"
        assert isinstance(r.get("sdk"), dict)

    def test_invalid_info_type(self):
        """无效 info_type 应返回错误（纯本地逻辑，不需要 JEB）"""
        data = call_tool("get_current_app_manifest", {"info_type": "bad_type"})
        r = data["result"]
        print(f"[invalid] {r}")
        assert r["success"] is False
        assert "error" in r
        assert "raw" not in r["error"], "raw 不应出现在可选值中"


# ──────────────────────────────────────────────
#  运行入口
# ──────────────────────────────────────────────

def run_all():
    print("=" * 60)
    print("  get_current_app_manifest info_type 集成测试")
    print("=" * 60)

    initialize()
    print()

    suite = TestManifestInfoType()
    tests = [m for m in sorted(dir(suite)) if m.startswith("test_")]
    passed = failed = errors = skipped = 0

    for name in tests:
        print(f"--- {name} ---")
        try:
            getattr(suite, name)()
            print("  => PASSED\n")
            passed += 1
        except RuntimeError as e:
            # JEB 未连接，标记 SKIP
            print(f"  => SKIP: {e}\n")
            skipped += 1
        except AssertionError as e:
            print(f"  => FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  => ERROR: {type(e).__name__}: {e}\n")
            errors += 1

    print("=" * 60)
    total = len(tests)
    print(f"  结果: {passed} passed, {failed} failed, {errors} errors, {skipped} skipped / {total} total")
    print("=" * 60)
    return failed == 0 and errors == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if run_all() else 1)
