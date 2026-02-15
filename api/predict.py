from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            from predictor import XAUTPredictor
            result = XAUTPredictor().run()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
        except Exception as e:
            import traceback
            self.wfile.write(json.dumps({
                "error": str(e),
                "trace": traceback.format_exc()
            }).encode())
