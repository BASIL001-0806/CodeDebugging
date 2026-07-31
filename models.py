import sqlite3
from datetime import datetime
from config import DATABASE_PATH


def get_db():
    conn = sqlite3.connect(DATABASE_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=8000")
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            year TEXT NOT NULL,
            department TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            difficulty TEXT NOT NULL CHECK(difficulty IN ('Easy','Medium','Hard')),
            description TEXT NOT NULL,
            input_format TEXT NOT NULL,
            output_format TEXT NOT NULL,
            constraints TEXT NOT NULL,
            sample_input TEXT NOT NULL,
            sample_output TEXT NOT NULL,
            explanation TEXT,
            notes TEXT,
            order_num INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            input TEXT NOT NULL,
            expected_output TEXT NOT NULL,
            is_hidden INTEGER DEFAULT 1,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            language TEXT NOT NULL,
            code TEXT NOT NULL,
            verdict TEXT NOT NULL DEFAULT 'Pending',
            execution_time REAL,
            memory_used REAL,
            test_results TEXT,
            submitted_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            points INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, question_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            violation_type TEXT NOT NULL,
            details TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

    ''')

    conn.commit()

    _remove_duplicate_questions(conn)

    conn.close()


def _remove_duplicate_questions(conn):
    """Delete questions that are duplicated by title (keeps the lowest id).
    Prevents the sidebar from showing the same question more than once even
    if the seed script was run multiple times in the past."""
    conn.execute(
        '''DELETE FROM questions
           WHERE id NOT IN (SELECT MIN(id) FROM questions GROUP BY title)'''
    )
    conn.commit()


class User:
    @staticmethod
    def find_or_create(name, year, department, is_admin=0):
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE name = ? AND year = ? AND department = ?',
            (name, year, department)
        ).fetchone()
        if user:
            conn.close()
            return user
        conn.execute(
            'INSERT INTO users (name, year, department, is_admin) VALUES (?, ?, ?, ?)',
            (name, year, department, is_admin)
        )
        conn.commit()
        user = conn.execute(
            'SELECT * FROM users WHERE name = ? AND year = ? AND department = ?',
            (name, year, department)
        ).fetchone()
        conn.close()
        return user

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        return user


class Question:
    @staticmethod
    def get_all():
        conn = get_db()
        questions = conn.execute('SELECT * FROM questions ORDER BY order_num, id').fetchall()
        conn.close()
        return questions

    @staticmethod
    def get_by_id(question_id):
        conn = get_db()
        question = conn.execute('SELECT * FROM questions WHERE id = ?', (question_id,)).fetchone()
        conn.close()
        return question

    @staticmethod
    def create(title, difficulty, description, input_format, output_format,
               constraints, sample_input, sample_output, explanation, notes, order_num):
        conn = get_db()
        cursor = conn.execute(
            '''INSERT INTO questions (title, difficulty, description, input_format, output_format,
               constraints, sample_input, sample_output, explanation, notes, order_num)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (title, difficulty, description, input_format, output_format,
             constraints, sample_input, sample_output, explanation, notes, order_num)
        )
        conn.commit()
        question_id = cursor.lastrowid
        conn.close()
        return question_id

    @staticmethod
    def get_user_status(question_id, user_id):
        conn = get_db()
        result = conn.execute(
            '''SELECT verdict FROM submissions
               WHERE question_id = ? AND user_id = ?
               ORDER BY (verdict = 'Accepted') DESC, id DESC LIMIT 1''',
            (question_id, user_id)
        ).fetchone()
        conn.close()
        if not result:
            return 'not_attempted'
        verdict = result['verdict']
        if verdict == 'Accepted':
            return 'accepted'
        if verdict in ('Pending', 'Draft'):
            return 'attempted'
        return 'wrong_answer'

    @staticmethod
    def get_attempted_count(user_id):
        conn = get_db()
        count = conn.execute(
            '''SELECT COUNT(DISTINCT question_id) FROM submissions WHERE user_id = ?''',
            (user_id,)
        ).fetchone()[0]
        conn.close()
        return count


class TestCase:
    @staticmethod
    def create(question_id, input, expected_output, is_hidden=1):
        conn = get_db()
        conn.execute(
            'INSERT INTO test_cases (question_id, input, expected_output, is_hidden) VALUES (?, ?, ?, ?)',
            (question_id, input, expected_output, is_hidden)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_by_question(question_id, hidden_only=False):
        conn = get_db()
        if hidden_only:
            cases = conn.execute(
                'SELECT * FROM test_cases WHERE question_id = ? AND is_hidden = 1',
                (question_id,)
            ).fetchall()
        else:
            cases = conn.execute(
                'SELECT * FROM test_cases WHERE question_id = ?',
                (question_id,)
            ).fetchall()
        conn.close()
        return cases


class Submission:
    @staticmethod
    def create(user_id, question_id, language, code, verdict='Pending'):
        for attempt in range(5):
            try:
                conn = get_db()
                cursor = conn.execute(
                    'INSERT INTO submissions (user_id, question_id, language, code, verdict) VALUES (?, ?, ?, ?, ?)',
                    (user_id, question_id, language, code, verdict)
                )
                conn.commit()
                sub_id = cursor.lastrowid
                conn.close()
                return sub_id
            except sqlite3.OperationalError as e:
                if 'locked' in str(e) and attempt < 4:
                    import time
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise

    @staticmethod
    def update_result(sub_id, verdict, execution_time=None, memory_used=None, test_results=None):
        for attempt in range(5):
            try:
                conn = get_db()
                conn.execute(
                    '''UPDATE submissions SET verdict=?, execution_time=?, memory_used=?, test_results=?
                       WHERE id=?''',
                    (verdict, execution_time, memory_used, test_results, sub_id)
                )
                conn.commit()
                conn.close()
                return
            except sqlite3.OperationalError as e:
                if 'locked' in str(e) and attempt < 4:
                    import time
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise

    @staticmethod
    def get_by_user_and_question(user_id, question_id):
        conn = get_db()
        subs = conn.execute(
            '''SELECT * FROM submissions
               WHERE user_id = ? AND question_id = ?
               ORDER BY id DESC''',
            (user_id, question_id)
        ).fetchall()
        conn.close()
        return subs

    @staticmethod
    def get_recent(user_id, limit=10):
        conn = get_db()
        subs = conn.execute(
            '''SELECT s.*, q.title as question_title
               FROM submissions s
               JOIN questions q ON s.question_id = q.id
               WHERE s.user_id = ?
               ORDER BY s.id DESC LIMIT ?''',
            (user_id, limit)
        ).fetchall()
        conn.close()
        return subs


class Score:
    @staticmethod
    def award(user_id, question_id, points):
        conn = get_db()
        conn.execute(
            'INSERT OR IGNORE INTO scores (user_id, question_id, points) VALUES (?, ?, ?)',
            (user_id, question_id, points)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_total(user_id):
        conn = get_db()
        row = conn.execute(
            'SELECT COALESCE(SUM(points), 0) AS total FROM scores WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        conn.close()
        return row['total'] if row else 0


class Violation:
    @staticmethod
    def log(user_id, violation_type, details=None):
        conn = get_db()
        conn.execute(
            'INSERT INTO violations (user_id, violation_type, details) VALUES (?, ?, ?)',
            (user_id, violation_type, details)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def count_today(user_id):
        conn = get_db()
        count = conn.execute(
            '''SELECT COUNT(*) FROM violations
               WHERE user_id = ? AND date(created_at) = date('now')''',
            (user_id,)
        ).fetchone()[0]
        conn.close()
        return count

    @staticmethod
    def get_all():
        conn = get_db()
        violations = conn.execute(
            '''SELECT v.*, u.name
               FROM violations v
               JOIN users u ON v.user_id = u.id
               ORDER BY v.created_at DESC''',
        ).fetchall()
        conn.close()
        return violations


class Leaderboard:
    @staticmethod
    def get():
        conn = get_db()
        rows = conn.execute('''
            SELECT
                u.id,
                u.name,
                u.year,
                u.department,
                (SELECT COUNT(DISTINCT question_id) FROM submissions
                 WHERE user_id = u.id AND verdict = 'Accepted') as solved,
                (SELECT COALESCE(SUM(points), 0) FROM scores
                 WHERE user_id = u.id) as score,
                (SELECT COALESCE(SUM(execution_time), 0) FROM submissions
                 WHERE user_id = u.id AND verdict = 'Accepted') as total_time,
                (SELECT COALESCE(SUM(memory_used), 0) FROM submissions
                 WHERE user_id = u.id AND verdict = 'Accepted') as total_memory
            FROM users u
            WHERE u.is_admin = 0
            ORDER BY score DESC, solved DESC, total_time ASC, total_memory ASC
        ''').fetchall()
        conn.close()
        return rows
