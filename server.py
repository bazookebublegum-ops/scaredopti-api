from flask import Flask, request, jsonify

app = Flask(__name__)

# база ключей (пока простая версия)
keys = {
    "ABC-123": False,  # False = не использован
    "TEST-999": False
}

@app.route("/")
def home():
    return "ScaredOpti API is running"

@app.route("/check", methods=["POST"])
def check_key():
    data = request.json
    key = data.get("key")

    # если ключ не существует
    if key not in keys:
        return jsonify({"status": "invalid"})

    # если уже использован
    if keys[key] == True:
        return jsonify({"status": "used"})

    # первый раз используем
    keys[key] = True
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)