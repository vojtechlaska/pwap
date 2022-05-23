from flask import Flask, request, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_api import status
import jwt
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.sqlite'
SECRET_KEY = "kocka"
JWT_SECRET = "pes"


db = SQLAlchemy(app)

def token_required(f):
    """
    Autorizační middleware, definovaný pomocí dekorátoru. 
    Dekorátory už umíte používat při definici routy. Zde je ukázáno jak se takový
    dekorátor vytváří. 

    Princip není složitý, vyžaduje ale určité znalosti. Zjednodušeně řečeno jde o fukci, 
    která převezme jako parametr funkci a modifikuje její chování
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("x-access-token", None)
        if not token:
            return jsonify({"message": "auth token is missing"}), 401

        try:
            jwt.decode(token, JWT_SECRET, algorithms="HS256")
        except jwt.DecodeError:
            return jsonify({"message": "auth token is invalid"}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "auth token expired"}), 401

        return f(*args, **kwargs)

    return decorated

@app.route("/auth", methods=["GET"])
def authorize():
    """
    Tento endpoint vygeneruje JWT token, používaný pro práci.
    Pro vygenerování je potřeba tajný klíč uživatele.
    Ten se posílá v hlavičce pomocí hlaviček http tak aby nebyl zobrazen v logu serveru,
    kam by byl zapsán pokud by byl parametrem v URL.
    """
    #jwt_key = app.config.get("JWT_SECRET")
    #secret_key = app.config.get("SECRET_KEY")
    user_key = request.headers.get('x-user-key', None)
    
    if user_key == SECRET_KEY:
        payload = {
            "user": "api",
            "exp": datetime.now() + timedelta(minutes=30),
        }
        encoded = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        return jsonify({"token": encoded})
    else:
        payload = {"message": "user key is invalid"}
        return jsonify(payload), 403

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    content = db.Column(db.Text)
    complete = db.Column(db.Boolean, default=True)
    #1


@app.route('/task', methods=['POST'])
@token_required
def create_task():
    data = request.get_json()

    new_task = Task(name=data['name'], content=data['content'], complete=False)

    db.session.add(new_task)
    db.session.commit()

    return make_response(jsonify("New task is created!"), 200)


@app.route('/', methods=['GET'])
def get_all_tasks():
    filters = {
        "ALL": "all",
        "COMPLETED": "completed",
        "NOT_COMPLETED": "not_completed"
    }
    filter = request.args.get('filter', None)

    if filter == filters["ALL"]:
        task_query = Task.query.all()

    elif filter == filters["COMPLETED"]:
        task_query = Task.query.filter_by(complete=True).all()

    elif filter == filters["NOT_COMPLETED"]:
        task_query = Task.query.filter_by(complete=False).all()

    else:
        return make_response(jsonify("Filter not found!"), 404)


    output = []

    for task in task_query:
        task_data = {}
        task_data['id'] = task.id
        task_data['name'] = task.name
        task_data['content'] = task.content
        task_data['complete'] = task.complete
        output.append(task_data)

    response = jsonify(
        {
            "items":
             output
        }
    )

    return response, status.HTTP_201_CREATED


@app.route('/task/<id>', methods=['PUT'])
@token_required
def update_task(id):
    data = request.get_json()

    name = data.get('name', None)
    content = data.get('content', None)
    complete = data.get('complete', None)

    task = Task.query.filter_by(id=id).first()

    if not task:
        return make_response(jsonify("Task not found!"), 404)

    task.name = name
    task.content = content
    task.complete = complete

    db.session.commit()

    return make_response(jsonify("Updated!"), 200)


@app.route("/task/<id>", methods=["DELETE"])
@token_required
def delete_task(id):
    task = Task.query.filter_by(id=id).first()

    if not task:
        return make_response(jsonify("Task id not found"), 404)

    db.session.delete(task)
    db.session.commit()

    return make_response(jsonify("Deleted!"), 200)

if __name__ == '__main__':
    app.run(debug=True, port="80", host="0.0.0.0")