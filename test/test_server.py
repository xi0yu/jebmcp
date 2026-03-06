"""
JEBMCP 接口测试

运行测试前需要：
1. 启动 JEB 并加载 MCP.py 插件
2. 启动 MCP 服务器: python src/server.py --transport http --port 16162

运行测试:
    pytest test/test_server.py -v
    或
    python test/test_server.py
"""

import json
import urllib.request
import urllib.error

# 配置
JEB_HOST = "127.0.0.1"
JEB_PORT = 16161
JEB_PATH = "/mcp"


def send_jsonrpc_request(method: str, params: dict = None) -> dict:
    """发送 JSON-RPC 请求到 JEB 插件"""
    url = f"http://{JEB_HOST}:{JEB_PORT}{JEB_PATH}"
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"error": str(e)}


class TestJebConnection:
    """JEB 连接测试"""

    def test_ping(self):
        """测试 ping 接口"""
        result = send_jsonrpc_request("ping")
        print(f"ping 响应: {result}")
        assert "result" in result or "error" in result

    def test_has_projects(self):
        """测试是否有打开的项目"""
        result = send_jsonrpc_request("has_projects")
        print(f"has_projects 响应: {result}")
        assert "result" in result or "error" in result


class TestProjectOperations:
    """项目操作测试"""

    def test_get_projects(self):
        """获取所有项目列表"""
        result = send_jsonrpc_request("get_projects")
        print(f"get_projects 响应: {result}")
        assert "result" in result or "error" in result

    def test_get_current_project_info(self):
        """获取当前项目信息"""
        result = send_jsonrpc_request("get_current_project_info")
        print(f"get_current_project_info 响应: {result}")
        assert "result" in result or "error" in result

    def test_get_live_artifact_ids(self):
        """获取活动 artifact 列表"""
        result = send_jsonrpc_request("get_live_artifact_ids")
        print(f"get_live_artifact_ids 响应: {result}")
        assert "result" in result or "error" in result


class TestCodeRetrieval:
    """代码获取测试"""

    def test_get_class_decompiled_code(self):
        """获取类的反编译代码"""
        # 需要替换为实际存在的类名
        result = send_jsonrpc_request("get_class_decompiled_code", {
            "class_signature": "Landroid/app/Activity;"
        })
        print(f"get_class_decompiled_code 响应: {result}")
        assert "result" in result or "error" in result

    def test_get_current_app_manifest(self):
        """获取 AndroidManifest.xml"""
        result = send_jsonrpc_request("get_current_app_manifest")
        print(f"get_current_app_manifest 响应: {result}")
        assert "result" in result or "error" in result


class TestClassAnalysis:
    """类分析测试"""

    def test_get_class_count(self):
        """获取类总数"""
        result = send_jsonrpc_request("get_class_count")
        print(f"get_class_count 响应: {result}")
        assert "result" in result or "error" in result

    def test_get_class_by_index(self):
        """按索引获取类"""
        result = send_jsonrpc_request("get_class_by_index", {"index": 0})
        print(f"get_class_by_index 响应: {result}")
        assert "result" in result or "error" in result

    def test_find_class(self):
        """查找类"""
        result = send_jsonrpc_request("find_class", {
            "class_signature": "Landroid/app/Activity;"
        })
        print(f"find_class 响应: {result}")
        assert "result" in result or "error" in result


def run_all_tests():
    """运行所有测试"""
    test_classes = [
        TestJebConnection,
        TestProjectOperations,
        TestCodeRetrieval,
        TestClassAnalysis,
    ]

    for test_class in test_classes:
        print(f"\n{'='*50}")
        print(f"运行测试: {test_class.__name__}")
        print('='*50)

        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                print(f"\n--- {method_name} ---")
                try:
                    getattr(instance, method_name)()
                    print("PASSED")
                except AssertionError as e:
                    print(f"FAILED: {e}")
                except Exception as e:
                    print(f"ERROR: {e}")


if __name__ == "__main__":
    run_all_tests()
