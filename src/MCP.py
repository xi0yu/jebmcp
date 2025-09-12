# -*- coding: utf-8 -*-
"""
JEB MCP Plugin - Main entry point and plugin management
Refactored with modular architecture for better maintainability
"""
import sys
import json
import threading
import traceback
import os
from urlparse import urlparse
import BaseHTTPServer

# JEB imports
from com.pnfsoftware.jeb.client.api import IScript, IGraphicalClientContext

from javax.swing import JFrame, JLabel
from java.awt import BorderLayout, Color
from java.lang import Runnable, Thread
from java.awt.event import WindowAdapter

# Import our modular components
from core.project_manager import ProjectManager
from core.jeb_operations import JebOperations
from api.jsonrpc_handler import JSONRPCHandler

class JSONRPCError(Exception):
    """Custom JSON-RPC error class"""
    def __init__(self, code, message, data=None):
        Exception.__init__(self, message)
        self.code = code
        self.message = message
        self.data = data

class JSONRPCRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """HTTP request handler for JSON-RPC calls"""
    
    def __init__(self, *args, **kwargs):
        self.rpc_handler = kwargs.pop('rpc_handler', None)
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
    
    def send_jsonrpc_error(self, code, message, id=None):
        """Send JSON-RPC error response"""
        response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            }
        }
        if id is not None:
            response["id"] = id
        response_body = json.dumps(response)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(response_body))
        self.end_headers()
        self.wfile.write(response_body)

    def do_POST(self):
        """Handle POST requests for JSON-RPC calls"""
        parsed_path = urlparse(self.path)
        if parsed_path.path != "/mcp":
            self.send_jsonrpc_error(-32098, "Invalid endpoint", None)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_jsonrpc_error(-32700, "Parse error: missing request body", None)
            return

        request_body = self.rfile.read(content_length)
        try:
            request = json.loads(request_body)
        except ValueError:
            self.send_jsonrpc_error(-32700, "Parse error: invalid JSON", None)
            return

        # Prepare the response
        response = {
            "jsonrpc": "2.0"
        }
        if request.get("id") is not None:
            response["id"] = request.get("id")

        try:
            # Basic JSON-RPC validation
            if not isinstance(request, dict):
                raise JSONRPCError(-32600, "Invalid Request")
            if request.get("jsonrpc") != "2.0":
                raise JSONRPCError(-32600, "Invalid JSON-RPC version")
            if "method" not in request:
                raise JSONRPCError(-32600, "Method not specified")

            # Handle the method call through our RPC handler
            if self.rpc_handler:
                result = self.rpc_handler.handle_request(
                    request["method"], 
                    request.get("params", [])
                )
                response["result"] = result
            else:
                raise JSONRPCError(-32603, "RPC handler not initialized")

        except JSONRPCError as e:
            response["error"] = {
                "code": e.code,
                "message": e.message
            }
            if e.data is not None:
                response["error"]["data"] = e.data
        except Exception as e:
            traceback.print_exc()
            response["error"] = {
                "code": -32603,
                "message": "Internal error (please report a bug)",
                "data": traceback.format_exc(),
            }

        try:
            response_body = json.dumps(response)
        except Exception as e:
            traceback.print_exc()
            response_body = json.dumps({
                "error": {
                    "code": -32603,
                    "message": "Internal error (please report a bug)",
                    "data": traceback.format_exc(),
                }
            })

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(response_body))
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format, *args):
        """Suppress logging"""
        pass

class MCPHTTPServer(BaseHTTPServer.HTTPServer):
    """Custom HTTP server for MCP"""
    allow_reuse_address = False

class Server(object):
    """MCP HTTP server manager"""
    
    HOST = "127.0.0.1"
    PORT = 16161

    def __init__(self, rpc_handler):
        self.server = None
        self.server_thread = None
        self.running = False
        self.rpc_handler = rpc_handler
        if not self.rpc_handler:
            raise ValueError("RPC handler must be provided")

    def start(self):
        """Start the HTTP server"""
        if self.running:
            print("[MCP] Server is already running")
            return

        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.daemon = True
        self.running = True
        self.server_thread.start()

    def stop(self):
        """Stop the HTTP server"""
        if not self.running:
            return

        self.running = False
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.server_thread:
            self.server_thread.join()
            self.server = None
        print("[MCP] Server stopped")

    def _run_server(self):
        """Internal server run method"""
        try:
            # Create server with custom request handler
            handler = lambda *args, **kwargs: JSONRPCRequestHandler(*args, rpc_handler=self.rpc_handler, **kwargs)
            self.server = MCPHTTPServer((Server.HOST, Server.PORT), handler)
            print("[MCP] Server started at http://{0}:{1}".format(Server.HOST, Server.PORT))
            self.server.serve_forever()
        except OSError as e:
            if e.errno == 98 or e.errno == 10048:  # Port already in use
                print("[MCP] Error: Port 16161 is already in use")
            else:
                print("[MCP] Server error: {0}".format(e))
            self.running = False
        except Exception as e:
            print("[MCP] Server error: {0}".format(e))
        finally:
            self.running = False

# Global context variable
CTX = None

class MCPServer:
    """Main MCP plugin class for JEB"""

    def __init__(self):
        self.server = None
        self.project_manager = None
        self.jeb_operations = None
        self.rpc_handler = None
        print("[MCP] Plugin loaded")

    def run(self, ctx):
        """Initialize and start the MCP plugin"""
        global CTX
        CTX = ctx
        
        try:
            # Initialize modular components
            self.project_manager = ProjectManager(ctx)
            self.jeb_operations = JebOperations(self.project_manager, ctx)
            self.rpc_handler = JSONRPCHandler(self.jeb_operations)

            # Start HTTP server
            self.server = Server(self.rpc_handler)
            self.server.start()
            print("[MCP] Plugin running with modular architecture")
        except Exception as e:
            print("[MCP] Error initializing plugin: %s" % str(e))
            traceback.print_exc()
            return

    def term(self):
        """Cleanup when plugin is terminated"""
        if self.server:
            self.server.stop()
        print("[MCP] Plugin terminated")


class UIThread(Runnable):
    def __init__(self, listener):
        self.listener = listener

    def run(self):
        frame = JFrame(u"关闭窗口将停止 JEBMCP")
        frame.setSize(400, 100)
        frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
        frame.setLocationRelativeTo(None)

        
        label = JLabel(u"jeb mcp 服务运行中")
        label.setForeground(Color.BLACK)
        label.setHorizontalAlignment(JLabel.CENTER)  # 居中显示
        frame.add(label, BorderLayout.CENTER)
        
        frame.setVisible(True)

        frame.addWindowListener(self.listener)


class MCP(IScript):
    def __init__(self):
        self.mcpServer = MCPServer()

    def run(self, ctx):
        # 检测是否为图形客户端环境
        is_graphical = isinstance(ctx, IGraphicalClientContext)
        
        if is_graphical:
            # 图形环境：创建UI窗口
            print(u"[MCP] 在图形客户端环境中运行")
            
            class WindowCloseListener(WindowAdapter):
                def __init__(self, mcpServer):
                    self.mcp_server = mcpServer

                def windowClosed(self, event):
                    self.mcp_server.term()
                    print(u"[MCP] 窗口已关闭，停止 JEBMCP 服务")

            t = Thread(UIThread(WindowCloseListener(self.mcpServer)))
            t.start()
        else:
            # 非图形环境（如Linux命令行）：使用后台模式
            print(u"[MCP] 在命令行环境中运行，使用后台模式")
            print(u"[MCP] 服务将持续运行，使用 Ctrl+C 停止")
            
        # 启动MCP服务器
        self.mcpServer.run(ctx)
        
        if not is_graphical:
            print(u"[MCP] 服务已启动，按 Ctrl+C 退出")
            try:
                # 在非图形环境下保持主线程运行
                while True:
                    Thread.sleep(5000)
            except KeyboardInterrupt:
                print(u"[MCP] 接收到中断信号，正在退出...")
                self.mcpServer.term()
            except Exception as e:
                print(u"[MCP] 运行时异常: %s" % str(e))
                self.mcpServer.term()