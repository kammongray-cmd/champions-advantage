"""
Zapier Lead Receiver API Endpoint
This creates a Flask-based API endpoint for receiving leads from Zapier.
Run separately or integrate with a simple server.
"""
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from services.database_manager import create_lead_from_zapier


class LeadReceiverHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/lead_receiver":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode("utf-8"))
                success, message = create_lead_from_zapier(data)
                
                if success:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "message": message}).encode())
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": message}).encode())
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Invalid JSON"}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == "/api/lead_receiver":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "active",
                "endpoint": "/api/lead_receiver",
                "method": "POST",
                "fields": ["name", "phone", "email", "notes"]
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass


def run_api_server(port=8080):
    """Run the lead receiver API server."""
    server = HTTPServer(("0.0.0.0", port), LeadReceiverHandler)
    print(f"Lead Receiver API running on port {port}")
    print(f"Endpoint: POST /api/lead_receiver")
    server.serve_forever()


if __name__ == "__main__":
    run_api_server()
