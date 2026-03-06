# -*- coding: utf-8 -*-
"""
JEB MCP Plugin - HTTP Server with Control UI

Usage:
    1. In JEB: Tools -> Scripts -> Load this script
    2. Server starts at http://127.0.0.1:16161/mcp
    3. Use the UI window to control the server
"""
import json
import threading
import traceback
import BaseHTTPServer
import time
import socket

from com.pnfsoftware.jeb.client.api import IScript, IGraphicalClientContext
from core.project_manager import ProjectManager
from core.jeb_operations import JebOperations
from api.jsonrpc_handler import JSONRPCHandler
from api.compressor import Compressor

# Compression threshold (bytes)
COMPRESSION_THRESHOLD = 256

# Global server instance for singleton check
_global_server = None
_global_ui = None


class JSONRPCError(Exception):
    def __init__(self, code, message, data=None):
        super(JSONRPCError, self).__init__(message)
        self.code = code
        self.message = message
        self.data = data


class JSONRPCRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """HTTP handler for JSON-RPC requests"""

    def do_POST(self):
        if self.path != "/mcp":
            self.send_response(404)
            self.end_headers()
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                return self._send_error(-32700, "Missing request body")

            request_data = self.rfile.read(content_length)

            # Check for gzip compressed request
            content_encoding = self.headers.get("Content-Encoding", "")
            if "gzip" in content_encoding.lower():
                request_data = Compressor.decompress(request_data)

            request = json.loads(request_data)
            method = request.get("method", "unknown")
            response, method = self._handle_request(request)
            self._send_json(response, method)
        except ValueError:
            self._send_error(-32700, "Invalid JSON")
        except Exception as e:
            traceback.print_exc()
            self._send_error(-32603, "Internal error: " + str(e))

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write('{"status":"ok","server":"JEB MCP"}')
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_request(self, request):
        response = {"jsonrpc": "2.0", "id": request.get("id")}
        method = request.get("method", "unknown")
        try:
            if request.get("jsonrpc") != "2.0":
                raise JSONRPCError(-32600, "Invalid JSON-RPC version")
            if "method" not in request:
                raise JSONRPCError(-32600, "Method not specified")

            handler = getattr(self.server, 'rpc_handler', None)
            if not handler:
                raise JSONRPCError(-32603, "RPC handler not initialized")

            result = handler.handle_request(request["method"], request.get("params", []))
            response["result"] = result
        except JSONRPCError as e:
            response["error"] = {"code": e.code, "message": e.message}
            if e.data:
                response["error"]["data"] = e.data
        return response, method

    def _send_json(self, data, method="unknown"):
        body = json.dumps(data).encode("utf-8") if isinstance(data, dict) else data
        original_size = len(body)

        # Check if client accepts gzip encoding
        accept_encoding = self.headers.get("Accept-Encoding", "")
        use_compression = ("gzip" in accept_encoding.lower() and
                          Compressor.should_compress(original_size))

        if use_compression:
            compressed_body = Compressor.compress(body)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(compressed_body)))
            self.end_headers()
            self.wfile.write(compressed_body)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(original_size))
            self.end_headers()
            self.wfile.write(body)

    def _send_error(self, code, message, data=None):
        error = {"code": code, "message": message}
        if data:
            error["data"] = data
        self._send_json({"jsonrpc": "2.0", "error": error}, method="error")

    def log_message(self, format, *args):
        pass


class MCPServer(object):
    HOST = "127.0.0.1"
    PORT = 16161

    def __init__(self, rpc_handler):
        self.rpc_handler = rpc_handler
        self.server = None
        self.thread = None
        self.running = False
        self.start_time = None
        self.start_error = None

    def start(self):
        if self.running:
            return True
        self.running = True
        self.start_error = None
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        time.sleep(0.3)
        return self.start_error is None

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except:
                pass
        self.server = None
        print("[MCP] Server stopped")

    def get_uptime(self):
        if self.start_time:
            return int(time.time() - self.start_time)
        return 0

    def _run(self):
        try:
            self.server = BaseHTTPServer.HTTPServer(
                (self.HOST, self.PORT),
                JSONRPCRequestHandler
            )
            self.server.rpc_handler = self.rpc_handler
            print("[MCP] Server started at http://{0}:{1}/mcp".format(self.HOST, self.PORT))
            self.server.serve_forever()
        except Exception as e:
            if hasattr(e, 'errno') and e.errno in (98, 10048) or 'Address already in use' in str(e):
                print("[MCP] Error: Port {0} already in use".format(self.PORT))
            else:
                print("[MCP] Server error: {0}".format(e))
            self.start_error = e
            self.running = False


class MCPUI(object):
    """MCP Server Control UI - Compact status window"""

    def __init__(self, server):
        self.server = server
        self.frame = None
        self.status_label = None
        self.uptime_label = None
        self.update_timer = None
        self._init_ui()

    def _init_ui(self):
        """Initialize compact Swing UI"""
        from javax.swing import JFrame, JPanel, JLabel, JButton, WindowConstants, UIManager, Timer, BorderFactory
        from java.awt import BorderLayout, Color, Font, Dimension, FlowLayout
        from java.awt.event import ActionListener

        # Set system Look and Feel
        try:
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName())
        except:
            pass

        # Main window - compact size
        frame = JFrame("JEB MCP")
        frame.setDefaultCloseOperation(WindowConstants.DISPOSE_ON_CLOSE)
        frame.setSize(320, 140)
        frame.setLocationRelativeTo(None)
        frame.setResizable(False)

        # Main panel with padding
        main_panel = JPanel(BorderLayout())
        main_panel.setBorder(BorderFactory.createEmptyBorder(10, 15, 10, 15))

        # Status panel (top)
        status_panel = JPanel(BorderLayout())
        status_panel.setBorder(BorderFactory.createEmptyBorder(0, 0, 8, 0))

        # Status indicator
        status_indicator = JPanel(FlowLayout(FlowLayout.LEFT, 5, 0))
        status_indicator.setOpaque(False)

        self.dot_label = JLabel()
        self.dot_label.setText("  ")  # Will be styled as colored dot
        self.dot_label.setOpaque(True)
        self.dot_label.setBackground(Color(46, 204, 113))  # Green
        self.dot_label.setPreferredSize(Dimension(10, 10))

        self.status_label = JLabel(" Running on port 16161")
        self.status_label.setFont(Font("SansSerif", Font.BOLD, 13))

        status_indicator.add(self.dot_label)
        status_indicator.add(self.status_label)

        # URL label
        url_label = JLabel("http://127.0.0.1:16161/mcp")
        url_label.setFont(Font("SansSerif", Font.PLAIN, 11))
        url_label.setForeground(Color(100, 100, 100))

        # Uptime
        self.uptime_label = JLabel("Uptime: 0s")
        self.uptime_label.setFont(Font("SansSerif", Font.PLAIN, 10))
        self.uptime_label.setForeground(Color(120, 120, 120))

        status_panel.add(status_indicator, BorderLayout.NORTH)
        status_panel.add(url_label, BorderLayout.CENTER)
        status_panel.add(self.uptime_label, BorderLayout.SOUTH)

        # Button panel (bottom)
        button_panel = JPanel(FlowLayout(FlowLayout.CENTER))
        button_panel.setOpaque(False)

        stop_btn = JButton("Stop Server")
        stop_btn.setFont(Font("SansSerif", Font.PLAIN, 12))
        stop_btn.setPreferredSize(Dimension(120, 30))
        stop_btn.setFocusPainted(False)

        class StopListener(ActionListener):
            def __init__(self, ui):
                self.ui = ui

            def actionPerformed(self, e):
                self.ui._stop_server()

        stop_btn.addActionListener(StopListener(self))
        button_panel.add(stop_btn)

        main_panel.add(status_panel, BorderLayout.CENTER)
        main_panel.add(button_panel, BorderLayout.SOUTH)

        frame.add(main_panel)
        self.frame = frame

        # Start uptime timer
        self._start_uptime_timer()

        # Handle window close
        class WindowListener:
            def __init__(self, ui):
                self.ui = ui

        from java.awt.event import WindowAdapter
        class CloseHandler(WindowAdapter):
            def __init__(self, ui):
                self.ui = ui

            def windowClosing(self, e):
                self.ui._stop_server()

        frame.addWindowListener(CloseHandler(self))

    def _start_uptime_timer(self):
        """Start timer to update uptime display"""
        from javax.swing import Timer
        from java.awt.event import ActionListener

        class UpdateListener(ActionListener):
            def __init__(self, ui):
                self.ui = ui

            def actionPerformed(self, e):
                if self.ui.server and self.ui.server.running:
                    uptime = self.ui.server.get_uptime()
                    if uptime < 60:
                        self.ui.uptime_label.setText("Uptime: %ds" % uptime)
                    elif uptime < 3600:
                        self.ui.uptime_label.setText("Uptime: %dm %ds" % (uptime // 60, uptime % 60))
                    else:
                        self.ui.uptime_label.setText("Uptime: %dh %dm" % (uptime // 3600, (uptime % 3600) // 60))

        self.update_timer = Timer(1000, UpdateListener(self))
        self.update_timer.start()

    def _stop_server(self):
        """Stop server and close UI"""
        if self.update_timer:
            self.update_timer.stop()
        if self.server:
            self.server.stop()
        if self.frame:
            self.frame.dispose()

    def show(self):
        """Display the UI window"""
        from javax.swing import SwingUtilities

        def display():
            self.frame.setVisible(True)
            print("[MCP] Control UI displayed")

        SwingUtilities.invokeLater(display)

    def hide(self):
        """Hide and dispose the UI"""
        self._stop_server()


class MCP(IScript):
    """JEB script entry point - MCP Server with UI"""

    def run(self, ctx):
        global _global_server, _global_ui

        # Check if server is already running
        if _global_server and _global_server.running:
            print("[MCP] Server is already running")
            # Bring existing UI to front
            if _global_ui and _global_ui.frame:
                _global_ui.frame.toFront()
                _global_ui.frame.requestFocus()
            return

        # Check if port is already in use
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(1)
        try:
            test_socket.connect(("127.0.0.1", 16161))
            test_socket.close()
            print("[MCP] ERROR: Port 16161 is already in use by another process")
            print("[MCP] Please stop the existing server or check for conflicts")
            return
        except:
            test_socket.close()

        print("[MCP] Starting JEB MCP Server...")

        # Initialize components
        project_mgr = ProjectManager(ctx)
        jeb_ops = JebOperations(project_mgr, ctx)
        rpc_handler = JSONRPCHandler(jeb_ops)

        # Start server
        server = MCPServer(rpc_handler)
        if not server.start():
            print("[MCP] ERROR: Failed to start server!")
            return

        _global_server = server
        print("[MCP] Server started successfully")

        # Show UI in graphical mode
        if isinstance(ctx, IGraphicalClientContext):
            ui = MCPUI(server)
            _global_ui = ui
            ui.show()
        else:
            print("[MCP] Running in console mode. Press Ctrl+C to stop.")
            try:
                while server.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                server.stop()
                print("[MCP] Server stopped")

        # Keep reference to prevent garbage collection
        self._server = server
        self._ctx = ctx
