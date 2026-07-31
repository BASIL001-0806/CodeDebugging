import json
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, jsonify, session, redirect, url_for
)

from config import (
    SECRET_KEY, MAX_TAB_WARNINGS,
    ADMIN_NAME, ADMIN_YEAR, ADMIN_DEPT,
    SCORE_EASY, SCORE_MEDIUM, SCORE_HARD,
)
from models import (
    init_db, get_db, User, Question, TestCase, Submission,
    Violation, Leaderboard, Score
)
from judge0_client import run_code, run_test_case

app = Flask(__name__)
app.secret_key = SECRET_KEY


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('entry'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return redirect(url_for('entry'))
        return f(*args, **kwargs)
    return decorated


def is_admin_credentials(name, year, department):
    return (
        name.lower() == ADMIN_NAME.lower()
        and year.lower() == ADMIN_YEAR.lower()
        and department.lower() == ADMIN_DEPT.lower()
    )


def get_json_data():
    """Safely read a JSON request body, defaulting to {} for missing/invalid bodies."""
    return request.get_json(silent=True) or {}


def is_contest_locked():
    return bool(session.get('locked'))


# ─── Entry (no sign-in / login) ────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def entry():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        year = (request.form.get('year') or '').strip()
        department = (request.form.get('department') or '').strip()
        if not all([name, year, department]):
            return render_template('entry.html', error='Please fill in all the fields.')

        is_admin = 1 if is_admin_credentials(name, year, department) else 0
        user = User.find_or_create(name, year, department, is_admin)

        session.clear()
        session['user_id'] = user['id']
        session['name'] = user['name']
        session['year'] = user['year']
        session['department'] = user['department']
        session['is_admin'] = bool(user['is_admin'])

        if session['is_admin']:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('contest'))

    return render_template('entry.html')


# ─── Contest Routes ────────────────────────────────────────────────

@app.route('/contest')
@login_required
def contest():
    questions = Question.get_all()
    questions_list = []
    for q in questions:
        status = Question.get_user_status(q['id'], session['user_id'])
        questions_list.append({**dict(q), 'status': status})
    violation_count = Violation.count_today(session['user_id'])
    return render_template(
        'index.html',
        questions=questions_list,
        username=session.get('name'),
        year=session.get('year'),
        department=session.get('department'),
        violation_count=violation_count,
        max_violations=MAX_TAB_WARNINGS,
        locked=is_contest_locked(),
        first_question=questions_list[0] if questions_list else None,
    )


# ─── API Routes ────────────────────────────────────────────────────

@app.route('/api/questions')
@login_required
def api_questions():
    questions = Question.get_all()
    result = []
    for q in questions:
        qdict = dict(q)
        qdict['status'] = Question.get_user_status(q['id'], session['user_id'])
        result.append(qdict)
    return jsonify(result)


@app.route('/api/questions/<int:question_id>')
@login_required
def api_question(question_id):
    question = Question.get_by_id(question_id)
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    return jsonify(dict(question))


@app.route('/api/run', methods=['POST'])
@login_required
def api_run():
    if is_contest_locked():
        return jsonify({'error': 'Contest locked due to too many violations.'}), 403

    data = get_json_data()
    code = data.get('code', '')
    language = data.get('language', 'python')
    custom_input = data.get('input', '')

    if not code.strip():
        return jsonify({'error': 'No code provided'}), 400

    result = run_code(code, language, custom_input)

    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 500

    return jsonify({
        'output': result.get('output', ''),
        'compilation_error': result.get('compilation_error', ''),
        'runtime_error': result.get('runtime_error', ''),
        'execution_time': result.get('time', 0),
        'memory_used': result.get('memory', 0),
        'status': result.get('status', ''),
    })


@app.route('/api/submit', methods=['POST'])
@login_required
def api_submit():
    if is_contest_locked():
        return jsonify({'error': 'Contest locked due to too many violations.'}), 403

    data = get_json_data()
    code = data.get('code', '')
    language = data.get('language', 'python')
    question_id = data.get('question_id')

    if not code.strip():
        return jsonify({'error': 'No code provided'}), 400
    if not question_id:
        return jsonify({'error': 'No question specified'}), 400

    question = Question.get_by_id(question_id)
    if not question:
        return jsonify({'error': 'Question not found'}), 404

    test_cases = TestCase.get_by_question(question_id, hidden_only=True)
    if not test_cases:
        test_cases = TestCase.get_by_question(question_id, hidden_only=False)

    total = len(test_cases)
    if total == 0:
        return jsonify({'error': 'No test cases configured'}), 500

    sub_id = Submission.create(
        session['user_id'], question_id, language, code
    )

    results = []
    all_passed = True
    total_time = 0.0
    total_memory = 0.0
    failed_case = None
    error_status = None

    for i, tc in enumerate(test_cases):
        result = run_test_case(code, language, tc['input'], tc['expected_output'])

        if isinstance(result, dict) and 'error' in result:
            error_status = result.get('status') or 'Error'
            results.append({
                'case': i + 1,
                'passed': False,
                'error': result['error'],
            })
            all_passed = False
            failed_case = {'case': i + 1, 'error': result['error']}
            break

        passed = result.get('is_success', False)
        results.append({
            'case': i + 1,
            'passed': passed,
            'execution_time': result.get('time', 0),
            'memory_used': result.get('memory', 0),
        })

        total_time += float(result.get('time', 0) or 0)
        total_memory += float(result.get('memory', 0) or 0)

        if not passed:
            all_passed = False
            user_output = result.get('output', '').strip()
            expected = tc['expected_output'].strip()
            failed_case = {
                'case': i + 1,
                'expected_output': expected,
                'user_output': user_output,
                'execution_time': result.get('time', 0),
                'memory_used': result.get('memory', 0),
            }
            break

    if all_passed:
        verdict = 'Accepted'
    elif error_status:
        verdict = error_status
    else:
        verdict = 'Wrong Answer'

    avg_time = round(total_time / total, 4) if total else 0
    avg_memory = round(total_memory / total, 2) if total else 0

    Submission.update_result(
        sub_id, verdict, avg_time, avg_memory,
        json.dumps(results)
    )

    response = {
        'submission_id': sub_id,
        'verdict': verdict,
        'results': results,
        'execution_time': avg_time,
        'memory_used': avg_memory,
    }

    if failed_case and not all_passed:
        response['failed_case'] = failed_case

    if verdict == 'Accepted':
        response['message'] = 'All test cases passed!'
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        response['submission_time'] = now

        points = {
            'Easy': SCORE_EASY,
            'Medium': SCORE_MEDIUM,
            'Hard': SCORE_HARD,
        }.get(question['difficulty'], SCORE_EASY)
        Score.award(session['user_id'], question_id, points)
        response['score_awarded'] = points
        response['total_score'] = Score.get_total(session['user_id'])

    return jsonify(response)


@app.route('/api/submissions/<int:question_id>')
@login_required
def api_submissions(question_id):
    subs = Submission.get_by_user_and_question(session['user_id'], question_id)
    return jsonify([dict(s) for s in subs])


@app.route('/api/submissions/recent')
@login_required
def api_recent_submissions():
    subs = Submission.get_recent(session['user_id'])
    return jsonify([dict(s) for s in subs])


@app.route('/api/leaderboard')
@admin_required
def api_leaderboard():
    board = Leaderboard.get()
    return jsonify([dict(row) for row in board])


@app.route('/api/save-code', methods=['POST'])
@login_required
def api_save_code():
    if is_contest_locked():
        return jsonify({'error': 'Contest locked due to too many violations.'}), 403

    data = get_json_data()
    question_id = data.get('question_id')
    language = data.get('language', 'python')
    code = data.get('code', '')

    if not question_id:
        return jsonify({'error': 'No question specified'}), 400

    conn = get_db()
    try:
        existing = conn.execute(
            '''SELECT id FROM submissions
               WHERE user_id = ? AND question_id = ? AND verdict = 'Draft'
               ORDER BY id DESC LIMIT 1''',
            (session['user_id'], question_id)
        ).fetchone()

        if existing:
            conn.execute(
                'UPDATE submissions SET code=?, language=? WHERE id=?',
                (code, language, existing['id'])
            )
        else:
            conn.execute(
                '''INSERT INTO submissions (user_id, question_id, language, code, verdict)
                   VALUES (?, ?, ?, ?, 'Draft')''',
                (session['user_id'], question_id, language, code)
            )
        conn.commit()
    finally:
        conn.close()

    return jsonify({'status': 'saved'})


@app.route('/api/load-code/<int:question_id>')
@login_required
def api_load_code(question_id):
    conn = get_db()
    try:
        sub = conn.execute(
            '''SELECT code, language FROM submissions
               WHERE user_id = ? AND question_id = ?
               ORDER BY id DESC LIMIT 1''',
            (session['user_id'], question_id)
        ).fetchone()
    finally:
        conn.close()
    if sub:
        return jsonify({'code': sub['code'], 'language': sub['language']})
    return jsonify({'code': '', 'language': 'python'})


@app.route('/api/violation', methods=['POST'])
@login_required
def api_violation():
    data = get_json_data()
    vtype = data.get('type', 'tab_switch')
    details = data.get('details', '')

    Violation.log(session['user_id'], vtype, details)
    count = Violation.count_today(session['user_id'])

    if count >= MAX_TAB_WARNINGS:
        session['locked'] = True
        return jsonify({
            'warning_count': count,
            'locked': True,
            'message': 'Maximum violations reached. Contest locked.'
        })

    warnings_left = MAX_TAB_WARNINGS - count
    msg = 'Final Warning!' if warnings_left == 0 else f'Warning! {warnings_left} more violation(s) and contest will be locked.'
    return jsonify({
        'warning_count': count,
        'locked': False,
        'message': msg,
    })


# ─── Admin Routes (visible only to basil / 3rd / CSE) ──────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    questions = Question.get_all()
    violations = Violation.get_all()
    leaderboard = Leaderboard.get()
    return render_template(
        'admin.html',
        questions=questions,
        violations=violations,
        leaderboard=leaderboard,
        username=session.get('name'),
    )


@app.route('/api/admin/question', methods=['POST'])
@admin_required
def admin_create_question():
    data = get_json_data()
    required = (
        'title', 'difficulty', 'description', 'input_format',
        'output_format', 'constraints', 'sample_input', 'sample_output',
    )
    if not data or not all(data.get(k) for k in required):
        return jsonify({'error': 'Missing required fields'}), 400

    qid = Question.create(
        title=data['title'],
        difficulty=data['difficulty'],
        description=data['description'],
        input_format=data['input_format'],
        output_format=data['output_format'],
        constraints=data['constraints'],
        sample_input=data['sample_input'],
        sample_output=data['sample_output'],
        explanation=data.get('explanation', ''),
        notes=data.get('notes', ''),
        order_num=data.get('order_num', 0),
    )

    for tc in data.get('test_cases', []):
        TestCase.create(
            question_id=qid,
            input=tc.get('input', ''),
            expected_output=tc.get('expected_output', ''),
            is_hidden=tc.get('is_hidden', 1),
        )

    return jsonify({'status': 'created', 'question_id': qid})


@app.route('/api/admin/test-cases/<int:question_id>')
@admin_required
def admin_test_cases(question_id):
    cases = TestCase.get_by_question(question_id)
    return jsonify([dict(c) for c in cases])


# ─── Main ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
