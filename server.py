from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# база ключей (простая версия)
keys = {
    "ABC-123": False,  # False = не использован
    "TEST-999": False
}

# ======================
# UI (интерфейс сайта)
# ======================
@app.route("/")
def home():
    return render_template("index.html")


# ======================
# API проверки ключа
# ======================
@app.route("/check", methods=["POST"])
def check_key():
    data = request.json
    key = data.get("key")

    if not key:
        return jsonify({"status": "error", "message": "no key provided"})

    # ключ не существует
    if key not in keys:
        return jsonify({"status": "invalid"})

    # уже использован
    if keys[key]:
        return jsonify({"status": "used"})

    # первый запуск
    keys[key] = True
    return jsonify({"status": "ok"})


# ======================
# запуск сервера
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)