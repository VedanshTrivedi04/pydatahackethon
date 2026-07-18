import urllib.request
import json

try:
    with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=3) as response:
        html = response.read()
        print("Success! Health response:")
        print(html.decode("utf-8"))
except Exception as e:
    print("Health check failed:", e)
