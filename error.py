from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class ErrorServerRequestHandler(BaseHTTPRequestHandler):
    def send_error_response(self):
        message = {
            "error": "Minecraft-Chocolate API is down, restarting (please try again in a few minutes)"
        }
        self.send_response(500)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        return message

    def do_GET(self):
        message = self.send_error_response()
        self.wfile.write(bytes(json.dumps(message), "utf8"))
        
    def do_HEAD(self):
        self.send_error_response()

if __name__ == "__main__":
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, ErrorServerRequestHandler)
    httpd.handle_request()