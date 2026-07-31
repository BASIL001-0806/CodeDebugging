import requests
import time
import json
import subprocess
import tempfile
import os
import sys
import platform
from config import JUDGE0_URL, JUDGE0_API_KEY, JUDGE0_HOST, LANGUAGE_IDS

USE_RESOURCE = platform.system() != 'Windows'
if USE_RESOURCE:
    import resource
else:
    resource = None  # type: ignore[assignment]  # platform module, guarded by USE_RESOURCE


language_ids_cache = None
USE_JUDGE0 = bool(JUDGE0_API_KEY)


def get_language_id(language):
    return LANGUAGE_IDS.get(language.lower(), 71)


def _timeout_result(status, message):
    return {
        'status': status,
        'status_id': 9,
        'stdout': '', 'stderr': '', 'compile_output': '',
        'output': '', 'time': 0, 'memory': 0,
        'compilation_error': message, 'runtime_error': message,
        'is_error': True, 'is_success': False, 'is_wrong_answer': False,
        'message': message,
    }


def run_code(source_code, language, stdin) -> dict:
    if USE_JUDGE0:
        result = run_code_judge0(source_code, language, stdin)
        if isinstance(result, dict) and 'error' not in result:
            return result
        print(f"Judge0 failed, falling back to local: {result.get('error')}")
    return run_code_local(source_code, language, stdin)


def run_test_case(source_code, language, stdin, expected_output) -> dict:
    result = run_code(source_code, language, stdin)
    if not isinstance(result, dict):
        return {'error': 'Unexpected runner response', 'status': 'Error'}
    if 'error' in result:
        return result
    if result.get('compilation_error'):
        result['is_error'] = True
        result['is_success'] = False
        result['is_wrong_answer'] = False
        result['status'] = 'Compilation Error'
        result['error'] = result['compilation_error']
        return result
    if result.get('runtime_error'):
        result['is_error'] = True
        result['is_success'] = False
        result['is_wrong_answer'] = False
        result['error'] = result['runtime_error']
        return result
    user_output = result.get('output', '').strip()
    expected = expected_output.strip()
    result['is_success'] = (user_output == expected)
    result['is_wrong_answer'] = not result['is_success']
    if not result['is_success']:
        result['status'] = 'Wrong Answer'
        result['status_id'] = 4
    else:
        result['status'] = 'Accepted'
        result['status_id'] = 3
    return result


def run_code_local(source_code, language, stdin):
    ext_map = {
        'python': '.py',
        'java': '.java',
        'c': '.c',
        'cpp': '.cpp',
    }
    compile_cmd_map = {
        'java': ['javac'],
        'c': ['gcc', '-o'],
        'cpp': ['g++', '-o'],
    }
    run_cmd_map = {
        'python': [sys.executable],
        'java': ['java'],
        'c': [],
        'cpp': [],
    }

    lang = language.lower()
    ext = ext_map.get(lang, '.txt')

    try:
        start_time = time.time()
        usage_before = resource.getrusage(resource.RUSAGE_CHILDREN) if USE_RESOURCE else None  # type: ignore[union-attr, attr-defined, name-defined]

        with tempfile.TemporaryDirectory() as tmpdir:
            class_name = None
            if lang == 'java':
                class_name = extract_java_class(source_code) or 'Main'
            src_file = os.path.join(tmpdir, f'{class_name or "Main"}{ext}' if lang == 'java' else f'source{ext}')

            with open(src_file, 'w', encoding='utf-8') as f:
                f.write(source_code)

            executable = os.path.join(tmpdir, 'program' + ('.exe' if os.name == 'nt' else ''))
            compile_error = None

            if lang == 'c':
                try:
                    result = subprocess.run(
                        ['gcc', src_file, '-o', executable],
                        capture_output=True, text=True, timeout=30
                    )
                except subprocess.TimeoutExpired:
                    return _timeout_result('Compilation Timed Out', 'Compilation timed out after 30s')
                if result.returncode != 0:
                    compile_error = result.stderr or result.stdout
                    return {
                        'status': 'Compilation Error',
                        'status_id': 6,
                        'stdout': '', 'stderr': '', 'compile_output': compile_error,
                        'output': '', 'time': 0, 'memory': 0,
                        'compilation_error': compile_error, 'runtime_error': '',
                        'is_error': True, 'is_success': False, 'is_wrong_answer': False,
                        'message': compile_error,
                    }
                run_cmd = [executable]
            elif lang == 'cpp':
                try:
                    result = subprocess.run(
                        ['g++', src_file, '-o', executable],
                        capture_output=True, text=True, timeout=30
                    )
                except subprocess.TimeoutExpired:
                    return _timeout_result('Compilation Timed Out', 'Compilation timed out after 30s')
                if result.returncode != 0:
                    compile_error = result.stderr or result.stdout
                    return {
                        'status': 'Compilation Error',
                        'status_id': 6,
                        'stdout': '', 'stderr': '', 'compile_output': compile_error,
                        'output': '', 'time': 0, 'memory': 0,
                        'compilation_error': compile_error, 'runtime_error': '',
                        'is_error': True, 'is_success': False, 'is_wrong_answer': False,
                        'message': compile_error,
                    }
                run_cmd = [executable]
            elif lang == 'java':
                try:
                    result = subprocess.run(
                        ['javac', src_file],
                        capture_output=True, text=True, timeout=30
                    )
                except subprocess.TimeoutExpired:
                    return _timeout_result('Compilation Timed Out', 'Compilation timed out after 30s')
                if result.returncode != 0:
                    compile_error = result.stderr or result.stdout
                    return {
                        'status': 'Compilation Error',
                        'status_id': 6,
                        'stdout': '', 'stderr': '', 'compile_output': compile_error,
                        'output': '', 'time': 0, 'memory': 0,
                        'compilation_error': compile_error, 'runtime_error': '',
                        'is_error': True, 'is_success': False, 'is_wrong_answer': False,
                        'message': compile_error,
                    }
                run_cmd = ['java', '-cp', tmpdir, class_name]
            else:
                run_cmd = [sys.executable, src_file]

            try:
                result = subprocess.run(
                    run_cmd,
                    input=stdin,
                    capture_output=True, text=True, timeout=10
                )

                end_time = time.time()

                exec_time = round(end_time - start_time, 4)
                mem_used = 0.0
                if USE_RESOURCE and usage_before is not None:
                    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)  # type: ignore[union-attr, attr-defined, name-defined]
                    try:
                        mem_used = round((usage_after.ru_maxrss - usage_before.ru_maxrss) / 1024, 2)
                    except Exception:
                        mem_used = 0.0

                if result.returncode != 0:
                    return {
                        'status': 'Runtime Error',
                        'status_id': 7,
                        'stdout': result.stdout, 'stderr': result.stderr,
                        'compile_output': '', 'output': result.stdout,
                        'time': exec_time, 'memory': mem_used,
                        'compilation_error': '', 'runtime_error': result.stderr or f'Exit code: {result.returncode}',
                        'is_error': True, 'is_success': False, 'is_wrong_answer': False,
                        'message': result.stderr or '',
                    }

                return {
                    'status': 'Accepted',
                    'status_id': 3,
                    'stdout': result.stdout, 'stderr': result.stderr,
                    'compile_output': '', 'output': result.stdout,
                    'time': exec_time, 'memory': mem_used,
                    'compilation_error': '', 'runtime_error': '',
                    'is_error': False, 'is_success': True, 'is_wrong_answer': False,
                    'message': '',
                }
            except subprocess.TimeoutExpired:
                return {
                    'status': 'Time Limit Exceeded',
                    'status_id': 9,
                    'stdout': '', 'stderr': '', 'compile_output': '',
                    'output': '', 'time': 10, 'memory': 0,
                    'compilation_error': '', 'runtime_error': 'Time Limit Exceeded',
                    'is_error': True, 'is_success': False, 'is_wrong_answer': False,
                    'message': 'Time Limit Exceeded',
                }
    except FileNotFoundError as e:
        compiler = {'c': 'gcc', 'cpp': 'g++', 'java': 'javac'}.get(lang, lang)
        return {
            'status': 'Compilation Error',
            'status_id': 6,
            'stdout': '', 'stderr': '', 'compile_output': '',
            'output': '', 'time': 0, 'memory': 0,
            'compilation_error': f'Compiler not found: {compiler}. Please install {compiler} or configure Judge0 API key.',
            'runtime_error': '', 'is_error': True, 'is_success': False,
            'is_wrong_answer': False, 'message': '',
        }
    except Exception as e:
        return {
            'status': 'Runtime Error',
            'status_id': 7,
            'stdout': '', 'stderr': str(e), 'compile_output': '',
            'output': '', 'time': 0, 'memory': 0,
            'compilation_error': '', 'runtime_error': str(e),
            'is_error': True, 'is_success': False, 'is_wrong_answer': False,
            'message': str(e),
        }


def extract_java_class(code):
    import re
    match = re.search(r'public\s+class\s+(\w+)', code)
    return match.group(1) if match else None


# ─── Judge0 API (optional, requires API key) ──────────────────────


def run_code_judge0(source_code, language, stdin):
    token = create_judge0_submission(source_code, language, stdin)
    if isinstance(token, dict) and 'error' in token:
        return token
    return get_judge0_result(token)


def create_judge0_submission(source_code, language, stdin=''):
    headers = {'Content-Type': 'application/json'}
    if JUDGE0_API_KEY:
        headers['X-RapidAPI-Key'] = JUDGE0_API_KEY
        headers['X-RapidAPI-Host'] = JUDGE0_HOST

    language_id = get_language_id(language)

    data = {
        'source_code': source_code,
        'language_id': language_id,
        'stdin': stdin,
        'redirect_stderr_to_stdout': False,
    }

    try:
        resp = requests.post(
            f'{JUDGE0_URL}/submissions',
            headers=headers,
            json=data,
            params={'base64_encoded': 'false', 'wait': 'false'},
            timeout=30
        )
        if resp.status_code in (200, 201):
            return resp.json().get('token')
        else:
            return {'error': f'Judge0 API error: {resp.status_code} - {resp.text}'}
    except requests.exceptions.Timeout:
        return {'error': 'Judge0 API request timed out'}
    except Exception as e:
        return {'error': f'Judge0 API error: {str(e)}'}


def get_judge0_result(token):
    headers = {}
    if JUDGE0_API_KEY:
        headers['X-RapidAPI-Key'] = JUDGE0_API_KEY
        headers['X-RapidAPI-Host'] = JUDGE0_HOST

    for _ in range(30):
        try:
            resp = requests.get(
                f'{JUDGE0_URL}/submissions/{token}',
                headers=headers,
                params={'base64_encoded': 'false', 'fields': 'stdout,stderr,status_id,status,compile_output,time,memory,expected_output,message'},
                timeout=15
            )
            if resp.status_code != 200:
                return {'error': f'Failed to get result: {resp.status_code}'}

            result = resp.json()
            status_id = result.get('status_id')

            if status_id <= 2:
                time.sleep(0.5)
                continue

            return parse_judge0_result(result)
        except requests.exceptions.Timeout:
            time.sleep(0.5)
            continue
        except Exception as e:
            return {'error': f'Error fetching result: {str(e)}'}

    return {'error': 'Maximum retries exceeded'}


def parse_judge0_result(result):
    status_id = result.get('status_id')
    status = result.get('status', {})
    status_description = status.get('description', 'Unknown') if isinstance(status, dict) else str(status)

    stdout = result.get('stdout') or ''
    stderr = result.get('stderr') or ''
    compile_output = result.get('compile_output') or ''
    time_val = result.get('time')
    memory_val = result.get('memory')
    message = result.get('message') or ''

    try:
        time_float = float(time_val) if time_val else 0.0
    except (ValueError, TypeError):
        time_float = 0.0

    try:
        memory_float = float(memory_val) if memory_val else 0.0
    except (ValueError, TypeError):
        memory_float = 0.0

    output = stdout if stdout else ''
    compilation_error = ''
    runtime_error = ''

    if status_id == 6:
        compilation_error = compile_output if compile_output else 'Compilation error occurred'
    elif status_id in (7, 8, 9, 10, 11, 12):
        runtime_error = stderr if stderr else message if message else status_description
        if not runtime_error:
            runtime_error = f'Runtime error ({status_description})'

    is_error = status_id in (6, 7, 8, 9, 10, 11, 12, 13)
    is_success = status_id == 3
    is_wrong_answer = status_id == 4

    return {
        'status_id': status_id,
        'status': status_description,
        'stdout': stdout,
        'stderr': stderr,
        'compile_output': compile_output,
        'output': output,
        'time': time_float,
        'memory': memory_float,
        'compilation_error': compilation_error,
        'runtime_error': runtime_error,
        'is_error': is_error,
        'is_success': is_success,
        'is_wrong_answer': is_wrong_answer,
        'message': message,
    }
