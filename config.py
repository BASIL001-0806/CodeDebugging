import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY', 'contest-secret-key-change-in-production')
DATABASE_PATH = os.path.join(BASE_DIR, 'contest.db')

JUDGE0_URL = os.environ.get('JUDGE0_URL', 'https://judge0-ce.p.rapidapi.com')
JUDGE0_API_KEY = os.environ.get('JUDGE0_API_KEY', '')
JUDGE0_HOST = os.environ.get('JUDGE0_HOST', 'judge0-ce.p.rapidapi.com')

LANGUAGE_IDS = {
    'java': 62,
    'python': 71,
    'c': 50,
    'cpp': 54,
}

ADMIN_NAME = 'basil'
ADMIN_YEAR = '3rd'
ADMIN_DEPT = 'CSE'

SCORE_EASY = 100
SCORE_MEDIUM = 200
SCORE_HARD = 300

MAX_TAB_WARNINGS = 3
AUTO_SAVE_INTERVAL = 5
