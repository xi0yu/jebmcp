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
import time

# JEB imports
from com.pnfsoftware.jeb.client.api import IScript, IGraphicalClientContext

from javax.swing import JFrame, JLabel, JButton, JPanel
from java.awt import BorderLayout, Color, Font, GridLayout
from java.awt.event import ActionListener, WindowAdapter, WindowEvent
from java.lang import Runnable, Thread

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
        # 从Server传入的rpc_handler实例
        self.rpc_handler = JSONRPCHandler.instance if hasattr(JSONRPCHandler, 'instance') else None
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def do_POST(self):
        """Handle POST requests for JSON-RPC calls"""
        # 直接检查路径
        if self.path != "/mcp":
            self._send_error_response(-32098, "Invalid endpoint")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_error_response(-32700, "Parse error: missing request body")
            return

        request_body = self.rfile.read(content_length)
        try:
            request = json.loads(request_body)
        except ValueError:
            self._send_error_response(-32700, "Parse error: invalid JSON")
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

        # 直接发送响应
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body.encode('utf-8'))

    def _send_error_response(self, code, message, request_id=None):
        """Send JSON-RPC error response"""
        response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            }
        }
        if request_id is not None:
            response["id"] = request_id
        response_body = json.dumps(response)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(response_body.encode('utf-8'))

    def log_message(self, format, *args):
        """Suppress logging"""
        pass

class MCPHTTPServer(BaseHTTPServer.HTTPServer):
    """Custom HTTP server for MCP"""
    # 保持默认配置，allow_reuse_address 默认为 False

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
            # 设置rpc_handler为类属性，这样所有请求处理实例都能访问
            JSONRPCHandler.instance = self.rpc_handler
            # Create server with custom request handler
            self.server = MCPHTTPServer((Server.HOST, Server.PORT), JSONRPCRequestHandler)
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
    def __init__(self, listener, mcp_server):
        self.listener = listener
        self.mcp_server = mcp_server

    def run(self):
        frame = JFrame(u"🌸 JEB MCP 服务 🌸")
        frame.setSize(500, 180)
        frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
        frame.setLocationRelativeTo(None)

        # 主面板
        panel = JPanel()
        panel.setLayout(BorderLayout())
        frame.add(panel)

        # 状态标签
        status_text = u"<html>" \
                    u"<center>" \
                    u"<b><font color='#FF69B4' size='5'>JEB MCP 服务正在运行</font></b><br>" \
                    u"<font color='#4B0082' size='4'>关闭窗口或点击按钮将停止服务</font><br>" \
                    u"<font color='#0000FF' size='3'>更多信息请参考文档</font>" \
                    u"</center>" \
                    u"</html>"
        status_label = JLabel(status_text)
        status_label.setHorizontalAlignment(JLabel.CENTER)
        status_label.setVerticalAlignment(JLabel.CENTER)
        panel.add(status_label, BorderLayout.CENTER)

        # 按钮面板
        button_panel = JPanel()
        button_panel.setLayout(GridLayout(1, 1, 5, 5))
        panel.add(button_panel, BorderLayout.SOUTH)

        # 停止按钮
        class StopButtonListener(ActionListener):
            def actionPerformed(self, event):
                # 统一触发窗口关闭事件
                frame.dispatchEvent(WindowEvent(frame, WindowEvent.WINDOW_CLOSING))
            def __init__(self):
                pass

        stop_button = JButton(u"Stop MCP!")
        stop_button.addActionListener(StopButtonListener())
        stop_button.setBackground(Color(255, 182, 193))
        stop_button.setForeground(Color.BLACK)
        stop_button.setFont(Font("Arial", Font.BOLD, 14))
        button_panel.add(stop_button)

        # 显示窗口
        frame.setVisible(True)
        frame.addWindowListener(self.listener)
# class UIThread(Runnable):
#     def __init__(self, listener):
#         self.listener = listener

#     def run(self):
#         frame = JFrame(u"JEB MCP 服务")
#         frame.setSize(400, 100)
#         frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
#         frame.setLocationRelativeTo(None)

        
#         label = JLabel(u"<html>JEB MCP 服务正在运行<br>关闭窗口将停止服务</html>")
#         label.setForeground(Color.BLACK)
#         label.setHorizontalAlignment(JLabel.CENTER)
#         label.setVerticalAlignment(JLabel.CENTER)
#         frame.add(label, BorderLayout.CENTER)
        
#         frame.setVisible(True)

#         frame.addWindowListener(self.listener)


class MCP(IScript):
    def __init__(self):
        self.mcpServer = MCPServer()

    def run(self, ctx):
        is_graphical = isinstance(ctx, IGraphicalClientContext)
        
        if is_graphical:
            print(u"[MCP] 在图形客户端环境中运行")
            
            class WindowCloseListener(WindowAdapter):
                def __init__(self, mcpServer):
                    self.mcp_server = mcpServer

                def windowClosed(self, event):
                    self.mcp_server.term()
                    print(u"[MCP] 窗口已关闭，停止 JEBMCP 服务")

            listener = WindowCloseListener(self.mcpServer)
            ui_thread = UIThread(WindowCloseListener(self.mcpServer), self.mcpServer)
            t = Thread(ui_thread)
            t.start()
            # t = Thread(UIThread(WindowCloseListener(self.mcpServer)))
            # t.start()
            self.mcpServer.run(ctx)
        else:
            print(u"[MCP] 服务已启动，按回车退出")
            self.mcpServer.run(ctx)
            try:
                raw_input()  # 等待用户按回车
            finally:
                self.mcpServer.term()
