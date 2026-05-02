import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from workflow import TravelPlanWorkflow
from dotenv import load_dotenv

load_dotenv()

_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app = Flask(__name__, static_folder=_STATIC, static_url_path="/static")
_ALLOWED_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
)
CORS(app, origins=list(_ALLOWED_ORIGINS))

# Ensure CORS headers on every response (including OPTIONS and errors)
@app.after_request
def add_cors(resp):
    origin = request.headers.get("Origin")
    if origin in _ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
    return resp

workflow = TravelPlanWorkflow()


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "trip-planner-api"}), 200


@app.route("/api/plan_travel", methods=["OPTIONS", "POST"])
def Home():
    if request.method == "OPTIONS":
        return "", 204
    print("POST /api/plan_travel hit", flush=True)
    try:
        data = request.get_json()
        user_input = data.get('user_input')

        if not user_input:
            return jsonify({"error":"User input is required"}), 400

        result = workflow.plan_travel(user_input)

        if result.get('error'):
            return jsonify({"error":result['error']}), 500

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error':str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=True, host="127.0.0.1", port=port)