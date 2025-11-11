from flask import Flask, jsonify, request
from functools import wraps
import datetime

app = Flask(__name__)

# Фиктивные данные
USERS = [
    {
        "id": "1",
        "email": "user1@company.com",
        "fullName": "Иван Иванов",
        "department": "IT",
        "role": "employee"
    },
    {
        "id": "2",
        "email": "manager@company.com",
        "fullName": "Петр Петров",
        "department": "HR",
        "role": "manager"
    }
]

SURVEYS = [
    {
        "id": "1",
        "title": "Оценка корпоративной культуры",
        "description": "Опрос о атмосфере в компании",
        "estimatedTime": 10,
        "questionsCount": 3,
        "createdAt": "2024-01-15T10:00:00Z",
        "isActive": True
    }
]

QUESTIONS = [
    {
        "id": "1",
        "surveyId": "1",
        "text": "Насколько вы удовлетворены атмосферой в коллективе?",
        "type": "scale",
        "options": {"min": 1, "max": 10},
        "required": True
    }
]

RESPONSES = []
ANSWERS = []


# Декоратор для проверки авторизации
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        if token != "fake-jwt-token-123":
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)

    return decorated


# Эндпоинты аутентификации
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    if any(user['email'] == data['email'] for user in USERS):
        return jsonify({'error': 'User already exists'}), 400

    new_user = {
        "id": str(len(USERS) + 1),
        "email": data['email'],
        "fullName": data.get('fullName', ''),
        "department": data.get('department', ''),
        "role": "employee"
    }
    USERS.append(new_user)

    return jsonify({
        'message': 'User registered successfully',
        'userId': new_user['id']
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    user = next((u for u in USERS if u['email'] == data['email']), None)

    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    return jsonify({
        'token': 'fake-jwt-token-123',
        'userId': user['id'],
        'email': user['email'],
        'fullName': user['fullName'],
        'role': user['role'],
        'expiresIn': 3600
    })


# Эндпоинты опросов
@app.route('/api/surveys', methods=['GET'])
@token_required
def get_surveys():
    active_surveys = [s for s in SURVEYS if s['isActive']]
    return jsonify({
        'surveys': active_surveys,
        'totalCount': len(active_surveys)
    })


@app.route('/api/surveys/<survey_id>/start', methods=['POST'])
@token_required
def start_survey(survey_id):
    survey = next((s for s in SURVEYS if s['id'] == survey_id), None)
    if not survey:
        return jsonify({'error': 'Survey not found'}), 404

    response_id = f"resp-{len(RESPONSES) + 1}"
    new_response = {
        'id': response_id,
        'surveyId': survey_id,
        'userId': '1',
        'startedAt': datetime.datetime.now().isoformat(),
        'status': 'in_progress'
    }
    RESPONSES.append(new_response)

    return jsonify(new_response), 201


@app.route('/api/responses/<response_id>', methods=['GET'])
@token_required
def get_response_questions(response_id):
    response = next((r for r in RESPONSES if r['id'] == response_id), None)
    if not response:
        return jsonify({'error': 'Response not found'}), 404

    survey = next((s for s in SURVEYS if s['id'] == response['surveyId']), None)
    if not survey:
        return jsonify({'error': 'Survey not found'}), 404

    survey_questions = [q for q in QUESTIONS if q['surveyId'] == response['surveyId']]

    return jsonify({
        'responseId': response_id,
        'survey': survey,
        'questions': survey_questions,
        'progress': {
            'current': 0,
            'total': len(survey_questions)
        }
    })


@app.route('/api/responses/<response_id>/answers', methods=['POST'])
@token_required
def submit_answer(response_id):
    data = request.get_json()

    if not data or not data.get('questionId'):
        return jsonify({'error': 'questionId is required'}), 400

    answer_id = f"answer-{len(ANSWERS) + 1}"
    new_answer = {
        'id': answer_id,
        'responseId': response_id,
        'questionId': data['questionId'],
        'answer': data.get('answer', ''),
        'submittedAt': datetime.datetime.now().isoformat()
    }
    ANSWERS.append(new_answer)

    return jsonify({
        'answerId': answer_id,
        'questionId': data['questionId'],
        'responseId': response_id,
        'savedAt': new_answer['submittedAt']
    }), 201


@app.route('/api/responses/<response_id>/complete', methods=['POST'])
@token_required
def complete_survey(response_id):
    response = next((r for r in RESPONSES if r['id'] == response_id), None)
    if not response:
        return jsonify({'error': 'Response not found'}), 404

    response['status'] = 'completed'
    response['completedAt'] = datetime.datetime.now().isoformat()

    response_answers = [a for a in ANSWERS if a['responseId'] == response_id]

    return jsonify({
        'responseId': response_id,
        'surveyId': response['surveyId'],
        'status': 'completed',
        'completedAt': response['completedAt'],
        'totalQuestions': len([q for q in QUESTIONS if q['surveyId'] == response['surveyId']]),
        'answeredQuestions': len(response_answers)
    })


@app.route('/api/surveys/<survey_id>/results', methods=['GET'])
@token_required
def get_survey_results(survey_id):
    return jsonify({
        'surveyId': survey_id,
        'surveyTitle': 'Оценка корпоративной культуры',
        'statistics': {
            'totalParticipants': 45,
            'completionRate': 0.85
        },
        'results': [
            {
                'questionId': '1',
                'questionText': 'Насколько вы удовлетворены атмосферой в коллективе?',
                'type': 'scale',
                'summary': {
                    'average': 7.8,
                    'distribution': {
                        '1-2': 2,
                        '3-4': 3,
                        '5-6': 5,
                        '7-8': 20,
                        '9-10': 15
                    }
                }
            }
        ]
    })


@app.route('/')
def root():
    return jsonify({
        'message': 'Feedback System API is running',
        'version': '1.0.0'
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)

