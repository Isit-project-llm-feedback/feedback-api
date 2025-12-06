from flask import Flask, jsonify, request
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
import datetime
import json
import os

app = Flask(__name__)


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "feedback.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)




class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120))
    department = db.Column(db.String(120))
    role = db.Column(db.String(50), default="employee")


class Survey(db.Model):
    __tablename__ = "surveys"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    estimated_time = db.Column(db.Integer)  
    questions_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey("surveys.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    options_json = db.Column(db.Text)  
    required = db.Column(db.Boolean, default=True)

    survey = db.relationship("Survey", backref=db.backref("questions", lazy=True))


class SurveyResponse(db.Model):
    """
    Отдельное название, чтобы не конфликтовать с flask.Response
    """
    __tablename__ = "responses"

    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey("surveys.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(50), default="in_progress")
    completed_at = db.Column(db.DateTime, nullable=True)

    survey = db.relationship("Survey", backref=db.backref("responses", lazy=True))
    user = db.relationship("User", backref=db.backref("responses", lazy=True))


class Answer(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey("responses.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    answer = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    response = db.relationship("SurveyResponse", backref=db.backref("answers", lazy=True))
    question = db.relationship("Question", backref=db.backref("answers", lazy=True))




def encode_response_id(db_id: int) -> str:
    return f"resp-{db_id}"


def decode_response_id(response_id: str) -> int:
    """
    Принимаем либо "resp-1", либо "1"
    """
    if response_id.startswith("resp-"):
        return int(response_id.split("-", 1)[1])
    return int(response_id)


def encode_answer_id(db_id: int) -> str:
    return f"answer-{db_id}"


def decode_answer_id(answer_id: str) -> int:
    if answer_id.startswith("answer-"):
        return int(answer_id.split("-", 1)[1])
    return int(answer_id)




def user_to_dict(user: User):
    return {
        "id": str(user.id),
        "email": user.email,
        "fullName": user.full_name or "",
        "department": user.department or "",
        "role": user.role or "employee"
    }


def survey_to_dict(s: Survey):
    return {
        "id": str(s.id),
        "title": s.title,
        "description": s.description or "",
        "estimatedTime": s.estimated_time,
        "questionsCount": s.questions_count,
        "createdAt": (s.created_at.isoformat() + "Z") if s.created_at else None,
        "isActive": bool(s.is_active)
    }


def question_to_dict(q: Question):
    options = None
    if q.options_json:
        try:
            options = json.loads(q.options_json)
        except json.JSONDecodeError:
            options = None

    return {
        "id": str(q.id),
        "surveyId": str(q.survey_id),
        "text": q.text,
        "type": q.type,
        "options": options,
        "required": bool(q.required)
    }




def seed_data():
    if User.query.count() == 0:
        user1 = User(
            email="user1@company.com",
            full_name="Иван Иванов",
            department="IT",
            role="employee"
        )
        manager = User(
            email="manager@company.com",
            full_name="Петр Петров",
            department="HR",
            role="manager"
        )
        db.session.add_all([user1, manager])
        db.session.commit()

    if Survey.query.count() == 0:
        survey = Survey(
            title="Оценка корпоративной культуры",
            description="Опрос о атмосфере в компании",
            estimated_time=10,
            questions_count=3,
            created_at=datetime.datetime(2024, 1, 15, 10, 0, 0),
            is_active=True
        )
        db.session.add(survey)
        db.session.commit()

        q1 = Question(
            survey_id=survey.id,
            text="Насколько вы удовлетворены атмосферой в коллективе?",
            type="scale",
            options_json=json.dumps({"min": 1, "max": 10}),
            required=True
        )
        db.session.add(q1)

        db.session.commit()


def setup_db():
    db.create_all()
    seed_data()





def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"error": "Token is missing"}), 401

        if token != "fake-jwt-token-123":
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)

    return decorated




@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password are required"}), 400

    existing = User.query.filter_by(email=data["email"]).first()
    if existing:
        return jsonify({"error": "User already exists"}), 400

    new_user = User(
        email=data["email"],
        full_name=data.get("fullName", ""),
        department=data.get("department", ""),
        role="employee"
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": "User registered successfully",
        "userId": str(new_user.id)
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=data["email"]).first()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401


    return jsonify({
        "token": "fake-jwt-token-123",
        "userId": str(user.id),
        "email": user.email,
        "fullName": user.full_name or "",
        "role": user.role or "employee",
        "expiresIn": 3600
    })




@app.route("/api/surveys", methods=["GET"])
@token_required
def get_surveys():
    active_surveys = Survey.query.filter_by(is_active=True).all()
    surveys_data = [survey_to_dict(s) for s in active_surveys]
    return jsonify({
        "surveys": surveys_data,
        "totalCount": len(surveys_data)
    })


@app.route("/api/surveys/<survey_id>/start", methods=["POST"])
@token_required
def start_survey(survey_id):
    survey = Survey.query.filter_by(id=survey_id, is_active=True).first()
    if not survey:
        return jsonify({"error": "Survey not found"}), 404

    user = User.query.filter_by(id=1).first()
    if not user:
        return jsonify({"error": "Default user not found in DB"}), 500

    new_response = SurveyResponse(
        survey_id=survey.id,
        user_id=user.id,
        started_at=datetime.datetime.utcnow(),
        status="in_progress"
    )
    db.session.add(new_response)
    db.session.commit()

    response_id = encode_response_id(new_response.id)

    return jsonify({
        "id": response_id,
        "surveyId": str(survey.id),
        "userId": str(user.id),
        "startedAt": new_response.started_at.isoformat(),
        "status": new_response.status
    }), 201


@app.route("/api/responses/<response_id>", methods=["GET"])
@token_required
def get_response_questions(response_id):
    try:
        db_id = decode_response_id(response_id)
    except ValueError:
        return jsonify({"error": "Invalid response id"}), 400

    response_obj = SurveyResponse.query.get(db_id)
    if not response_obj:
        return jsonify({"error": "Response not found"}), 404

    survey = response_obj.survey
    if not survey:
        return jsonify({"error": "Survey not found"}), 404

    survey_questions = Question.query.filter_by(survey_id=survey.id).all()
    questions_data = [question_to_dict(q) for q in survey_questions]

    answered_count = Answer.query.filter_by(response_id=response_obj.id).count()

    return jsonify({
        "responseId": response_id,
        "survey": survey_to_dict(survey),
        "questions": questions_data,
        "progress": {
            "current": answered_count,
            "total": len(survey_questions)
        }
    })


@app.route("/api/responses/<response_id>/answers", methods=["POST"])
@token_required
def submit_answer(response_id):
    try:
        db_id = decode_response_id(response_id)
    except ValueError:
        return jsonify({"error": "Invalid response id"}), 400

    response_obj = SurveyResponse.query.get(db_id)
    if not response_obj:
        return jsonify({"error": "Response not found"}), 404

    data = request.get_json()
    if not data or not data.get("questionId"):
        return jsonify({"error": "questionId is required"}), 400

    question = Question.query.get(int(data["questionId"]))
    if not question or question.survey_id != response_obj.survey_id:
        return jsonify({"error": "Question not found for this survey"}), 400

    new_answer = Answer(
        response_id=response_obj.id,
        question_id=question.id,
        answer=data.get("answer", ""),
        submitted_at=datetime.datetime.utcnow()
    )
    db.session.add(new_answer)
    db.session.commit()

    answer_id = encode_answer_id(new_answer.id)

    return jsonify({
        "answerId": answer_id,
        "questionId": str(question.id),
        "responseId": response_id,
        "savedAt": new_answer.submitted_at.isoformat()
    }), 201


@app.route("/api/responses/<response_id>/complete", methods=["POST"])
@token_required
def complete_survey(response_id):
    try:
        db_id = decode_response_id(response_id)
    except ValueError:
        return jsonify({"error": "Invalid response id"}), 400

    response_obj = SurveyResponse.query.get(db_id)
    if not response_obj:
        return jsonify({"error": "Response not found"}), 404

    response_obj.status = "completed"
    response_obj.completed_at = datetime.datetime.utcnow()
    db.session.commit()

    response_answers = Answer.query.filter_by(response_id=response_obj.id).all()
    total_questions = Question.query.filter_by(survey_id=response_obj.survey_id).count()

    return jsonify({
        "responseId": response_id,
        "surveyId": str(response_obj.survey_id),
        "status": response_obj.status,
        "completedAt": response_obj.completed_at.isoformat(),
        "totalQuestions": total_questions,
        "answeredQuestions": len(response_answers)
    })


@app.route("/api/surveys/<survey_id>/results", methods=["GET"])
@token_required
def get_survey_results(survey_id):
    return jsonify({
        "surveyId": survey_id,
        "surveyTitle": "Оценка корпоративной культуры",
        "statistics": {
            "totalParticipants": 45,
            "completionRate": 0.85
        },
        "results": [
            {
                "questionId": "1",
                "questionText": "Насколько вы удовлетворены атмосферой в коллективе?",
                "type": "scale",
                "summary": {
                    "average": 7.8,
                    "distribution": {
                        "1-2": 2,
                        "3-4": 3,
                        "5-6": 5,
                        "7-8": 20,
                        "9-10": 15
                    }
                }
            }
        ]
    })


@app.route("/")
def root():
    return jsonify({
        "message": "Feedback System API is running",
        "version": "1.0.0"
    })


if __name__ == "__main__":
    with app.app_context():
        setup_db()

    app.run(debug=True, port=5000)

