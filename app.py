from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

DATA_PATH = "data/data.json"

def load_data():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH) as f:
            return json.load(f)
    return {}

@app.route("/")
def index():
    data = load_data()
    return render_template("index.html", states=list(data.keys()))

@app.route("/get_cities", methods=["POST"])
def get_cities():
    state = request.form.get("state")
    data = load_data()
    return jsonify(list(data.get(state, {}).keys()))

@app.route("/get_news", methods=["POST"])
def get_news():
    state = request.form.get("state")
    city = request.form.get("city")
    data = load_data()
    articles = data.get(state, {}).get(city, [])
    return jsonify(articles)

if __name__ == "__main__":
    app.run(debug=True)