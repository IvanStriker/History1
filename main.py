from random import randint
import os

from flask import Flask, render_template, request, jsonify
import psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])

app = Flask(__name__, static_folder='static')

cards = [
    ["Ha", "HaHa"],
    ["Ha1", "HaHa"],
    ["Ha2", "HaHa"],
    ["Ha3", "HaHa"],
    ["Ha4", "HaHa"],
]

@app.route("/")
@app.route("/home")
def index():
    return render_template("home.html")


@app.route("/train")
def train():
    res = []
    while len(res) < 2:
        while (x := randint(0, 4)) in res:
            pass
        res.append(x)
    return render_template(
        "train.html",
        card_indices=res,
        total_questions=len(res)
    )


@app.route("/card")
def getCard():
    cardId = request.args.get("id", -1, type=int)
    card = cards[cardId]
    res = jsonify({
        "id": cardId,
        "front": {
            "type": "text",
            "content": card[0]
        },
        "back": {
            "type": "text",
            "content": card[1],
            "answer_text": ""
        }
    })
    return res


if __name__ == "__main__":
    app.run(host="0.0.0.0")
