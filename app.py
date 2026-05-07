import os
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["https://han-data-kwon.github.io"])

SB_URL = os.environ.get("SB_URL", "")
SB_KEY = os.environ.get("SB_KEY", "")

def sb_headers(token=None):
    h = {
        "apikey": SB_KEY,
        "Content-Type": "application/json",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    else:
        h["Authorization"] = f"Bearer {SB_KEY}"
    return h

# ── AUTH: 로그인 ──
@app.route("/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json()
    res = requests.post(
        f"{SB_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SB_KEY, "Content-Type": "application/json"},
        json={"email": data.get("email"), "password": data.get("password")},
        timeout=10
    )
    return Response(res.content, status=res.status_code, mimetype="application/json")

# ── AUTH: 토큰 갱신 ──
@app.route("/auth/refresh", methods=["POST"])
def auth_refresh():
    data = request.get_json()
    res = requests.post(
        f"{SB_URL}/auth/v1/token?grant_type=refresh_token",
        headers={"apikey": SB_KEY, "Content-Type": "application/json"},
        json={"refresh_token": data.get("refresh_token")},
        timeout=10
    )
    return Response(res.content, status=res.status_code, mimetype="application/json")

# ── REST API 프록시 ──
@app.route("/rest/<path:subpath>", methods=["GET", "POST", "PATCH", "DELETE"])
def rest_proxy(subpath):
    token = request.headers.get("X-User-Token")
    headers = sb_headers(token)

    prefer = request.headers.get("X-Prefer")
    if prefer:
        headers["Prefer"] = prefer

    # query string을 그대로 Supabase에 전달 (Flask의 args 파싱 대신 raw query string 사용)
    raw_qs = request.query_string.decode("utf-8")
    if raw_qs:
        url = f"{SB_URL}/rest/v1/{subpath}?{raw_qs}"
    else:
        url = f"{SB_URL}/rest/v1/{subpath}"

    if request.method == "GET":
        res = requests.get(url, headers=headers, timeout=15)
    elif request.method == "POST":
        res = requests.post(url, headers=headers, json=request.get_json(), timeout=15)
    elif request.method == "PATCH":
        res = requests.patch(url, headers=headers, json=request.get_json(), timeout=15)
    elif request.method == "DELETE":
        res = requests.delete(url, headers=headers, timeout=15)
        return Response(status=res.status_code)

    if res.content:
        return Response(res.content, status=res.status_code, mimetype="application/json")
    return Response(status=res.status_code)

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
