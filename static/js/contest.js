// ─── Question Navigation ───────────────────────────────────────────

function switchQuestion(questionId) {
    autoSave();
    currentQuestionId = questionId;
    document.querySelectorAll('.question-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.id) === questionId);
    });
    fetch(`/api/questions/${questionId}`)
        .then(r => r.json())
        .then(q => {
            document.getElementById('problemTitle').textContent = q.title;
            const badge = document.getElementById('problemDifficulty');
            badge.textContent = q.difficulty;
            badge.className = 'difficulty-badge ' + q.difficulty.toLowerCase();
            document.getElementById('problemNumber').textContent = q.id;
            document.getElementById('problemDescription').textContent = q.description;
            document.getElementById('problemInputFormat').textContent = q.input_format;
            document.getElementById('problemOutputFormat').textContent = q.output_format;
            document.getElementById('problemConstraints').textContent = q.constraints;
            document.getElementById('problemSampleInput').textContent = q.sample_input;
            document.getElementById('problemSampleOutput').textContent = q.sample_output;
            const explSec = document.getElementById('explanationSection');
            const explEl = document.getElementById('problemExplanation');
            if (explSec && explEl) {
                if (q.explanation) { explEl.textContent = q.explanation; explSec.style.display = ''; }
                else { explSec.style.display = 'none'; }
            }
            const notesSec = document.getElementById('notesSection');
            const notesEl = document.getElementById('problemNotes');
            if (notesSec && notesEl) {
                if (q.notes) { notesEl.textContent = q.notes; notesSec.style.display = ''; }
                else { notesSec.style.display = 'none'; }
            }
        });
    loadSavedCode(questionId);
    switchBottomTab('input');
    clearRunResults();
}

function nextQuestion() {
    const items = [...document.querySelectorAll('.question-item')];
    const idx = items.findIndex(el => parseInt(el.dataset.id) === currentQuestionId);
    if (idx >= 0 && idx < items.length - 1) {
        switchQuestion(parseInt(items[idx + 1].dataset.id));
    }
}

function prevQuestion() {
    const items = [...document.querySelectorAll('.question-item')];
    const idx = items.findIndex(el => parseInt(el.dataset.id) === currentQuestionId);
    if (idx > 0) {
        switchQuestion(parseInt(items[idx - 1].dataset.id));
    }
}

// ─── Bottom Panel Tabs ────────────────────────────────────────────

function switchBottomTab(tab) {
    document.querySelectorAll('.bottom-panel .tabs button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.bottom-panel .tab-content').forEach(t => t.classList.remove('active'));
    document.querySelector(`.bottom-panel .tabs button[data-tab="${tab}"]`).classList.add('active');
    document.getElementById(`tab-${tab}`).classList.add('active');
}

// ─── Run Code ─────────────────────────────────────────────────────

function runCode() {
    const code = getCode();
    const lang = getLanguage();
    const input = document.getElementById('customInput').value;

    if (!code.trim()) {
        showError('Please write some code before running.');
        return;
    }

    const btn = document.querySelector('.btn-run');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Running...';

    switchBottomTab('runresult');
    document.getElementById('runResultArea').innerHTML = '<div class="text-muted"><span class="spinner"></span> Compiling and running...</div>';
    document.getElementById('runStatus').textContent = 'Running...';

    fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, language: lang, input }),
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play"></i> Run';

        if (data.error) {
            document.getElementById('runResultArea').innerHTML =
                `<div class="text-danger">Error: ${escapeHtml(data.error)}</div>`;
            document.getElementById('runStatus').textContent = 'Error';
            document.getElementById('runStatus').style.color = '#ff4757';
            return;
        }

        document.getElementById('programOutput').textContent = data.output || '(no output)';
        document.getElementById('execTime').textContent = data.execution_time || '0';
        document.getElementById('memUsage').textContent = data.memory_used || '0';

        let html = '';

        if (data.compilation_error) {
            document.getElementById('compilationErrors').textContent = data.compilation_error;
            html += '<div class="test-case-result"><span class="fail"><i class="fas fa-times-circle"></i></span> Compilation Error</div>';
            html += `<pre class="text-danger" style="margin-top:8px;font-size:13px;">${escapeHtml(data.compilation_error)}</pre>`;
            document.getElementById('runStatus').textContent = 'Compilation Error';
            document.getElementById('runStatus').style.color = '#ff4757';
        } else if (data.runtime_error) {
            html += '<div class="test-case-result"><span class="fail"><i class="fas fa-exclamation-triangle"></i></span> Runtime Error</div>';
            html += `<pre class="text-danger" style="margin-top:8px;font-size:13px;">${escapeHtml(data.runtime_error)}</pre>`;
            document.getElementById('runStatus').textContent = 'Runtime Error';
            document.getElementById('runStatus').style.color = '#ff4757';
        } else {
            html += '<div class="test-case-result"><span class="pass"><i class="fas fa-check-circle"></i></span> Program executed successfully</div>';
            html += `<div style="margin-top:8px;padding:10px;background:#1a1a2e;border-radius:6px;"><pre style="font-size:13px;">${escapeHtml(data.output || '(no output)')}</pre></div>`;
            document.getElementById('runStatus').textContent = 'Success';
            document.getElementById('runStatus').style.color = '#2ed573';
        }

        html += `<div style="margin-top:12px;display:flex;gap:16px;font-size:12px;color:rgba(255,255,255,0.5);">
            <span>Time: ${data.execution_time || 0}s</span>
            <span>Memory: ${data.memory_used || 0} KB</span>
        </div>`;

        document.getElementById('runResultArea').innerHTML = html;
        if (data.compilation_error) switchBottomTab('errors');
    })
    .catch(err => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play"></i> Run';
        document.getElementById('runResultArea').innerHTML = `<div class="text-danger">Error: ${err.message}</div>`;
        document.getElementById('runStatus').textContent = 'Error';
    });
}

// ─── Submit Code ──────────────────────────────────────────────────

function submitCode() {
    const code = getCode();
    const lang = getLanguage();

    if (!code.trim()) {
        showError('Please write some code before submitting.');
        return;
    }

    const btn = document.querySelector('.btn-submit');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Running...';

    switchBottomTab('runresult');
    document.getElementById('runResultArea').innerHTML = '<div class="text-muted"><span class="spinner"></span> Running test cases...</div>';
    document.getElementById('runStatus').textContent = 'Testing...';

    fetch('/api/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            code,
            language: lang,
            question_id: currentQuestionId,
        }),
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check"></i> Submit';

        if (data.error) {
            document.getElementById('runResultArea').innerHTML =
                `<div class="text-danger">Error: ${escapeHtml(data.error)}</div>`;
            document.getElementById('runStatus').textContent = 'Error';
            document.getElementById('runStatus').style.color = '#ff4757';
            return;
        }

        const verdict = data.verdict || 'Wrong Answer';
        let html = '<div class="run-progress">';
        const results = data.results || [];

        results.forEach(r => {
            if (r.passed) {
                html += `<div class="test-case-result"><span class="pass"><i class="fas fa-check-circle"></i></span> Test Case ${r.case} - Passed</div>`;
            } else if (r.error) {
                html += `<div class="test-case-result"><span class="fail"><i class="fas fa-times-circle"></i></span> Test Case ${r.case} - Error: ${escapeHtml(r.error)}</div>`;
            } else {
                html += `<div class="test-case-result"><span class="fail"><i class="fas fa-times-circle"></i></span> Test Case ${r.case} - Failed</div>`;
            }
        });
        html += '</div>';

        document.getElementById('runResultArea').innerHTML = html;

        if (data.verdict === 'Accepted') {
            showSuccess(data);
            document.getElementById('runStatus').textContent = 'Accepted';
            document.getElementById('runStatus').style.color = '#2ed573';
            updateQuestionStatus(currentQuestionId, 'accepted');
        } else {
            showFailure(data);
            document.getElementById('runStatus').textContent = verdict;
            document.getElementById('runStatus').style.color = '#ff4757';
            updateQuestionStatus(currentQuestionId, 'wrong_answer');

            if (data.failed_case) {
                const fc = data.failed_case;
                html += `<div style="margin-top:16px;padding:12px;background:#1a1a2e;border-radius:8px;border-left:3px solid #ff4757;">
                    <div style="font-weight:600;margin-bottom:8px;color:#ff4757;">Failed Test Case #${fc.case}</div>
                    <div style="font-size:13px;margin-bottom:4px;"><span class="text-muted">Expected:</span></div>
                    <pre style="font-size:13px;background:#16213e;padding:8px;border-radius:4px;color:#2ed573;">${escapeHtml(fc.expected_output)}</pre>
                    <div style="font-size:13px;margin:8px 0 4px;"><span class="text-muted">Your Output:</span></div>
                    <pre style="font-size:13px;background:#16213e;padding:8px;border-radius:4px;color:#ff4757;">${escapeHtml(fc.user_output)}</pre>
                    <div style="margin-top:8px;font-size:12px;color:rgba(255,255,255,0.4);">
                        Time: ${fc.execution_time || 0}s | Memory: ${fc.memory_used || 0} KB
                    </div>
                </div>`;
                document.getElementById('runResultArea').innerHTML = html;
            }
        }

        document.getElementById('execTime').textContent = data.execution_time || '0';
        document.getElementById('memUsage').textContent = data.memory_used || '0';
    })
    .catch(err => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check"></i> Submit';
        document.getElementById('runResultArea').innerHTML = `<div class="text-danger">Error: ${err.message}</div>`;
        document.getElementById('runStatus').textContent = 'Error';
    });
}

// ─── Reset Code ───────────────────────────────────────────────────

function resetCode() {
    if (!confirm('Reset code to template? This cannot be undone.')) return;
    loadTemplateCode(currentQuestionId);
    document.getElementById('customInput').value = '';
    clearRunResults();
}

function clearRunResults() {
    document.getElementById('programOutput').textContent = 'Output will appear here...';
    document.getElementById('compilationErrors').textContent = 'No errors.';
    document.getElementById('runResultArea').innerHTML = '<div class="text-muted">Run your code to see results here.</div>';
    document.getElementById('execTime').textContent = '-';
    document.getElementById('memUsage').textContent = '-';
    document.getElementById('runStatus').textContent = 'Ready';
    document.getElementById('runStatus').style.color = '';
}

// ─── Result Modal ─────────────────────────────────────────────────

function showSuccess(data) {
    const overlay = document.getElementById('resultOverlay');
    overlay.classList.remove('hidden');
    document.getElementById('resultIcon').className = 'icon success';
    document.getElementById('resultIcon').innerHTML = '<i class="fas fa-check-circle"></i>';
    const title = document.getElementById('resultTitle');
    title.className = 'success';
    title.textContent = '✅ Accepted';
    const scoreBox = data.score_awarded
        ? `<div class="score-box"><i class="fas fa-star"></i> +${data.score_awarded} points &nbsp;|&nbsp; Total: ${data.total_score}</div>`
        : '';
    document.getElementById('resultDetails').innerHTML = `
        <div><span class="label">Time:</span> ${data.execution_time || 0}s</div>
        <div><span class="label">Memory:</span> ${data.memory_used || 0} KB</div>
        <div><span class="label">Submitted:</span> ${data.submission_time || new Date().toLocaleString()}</div>
        ${scoreBox}
    `;
}

function showFailure(data) {
    const overlay = document.getElementById('resultOverlay');
    overlay.classList.remove('hidden');
    document.getElementById('resultIcon').className = 'icon fail';
    document.getElementById('resultIcon').innerHTML = '<i class="fas fa-times-circle"></i>';
    const title = document.getElementById('resultTitle');
    title.className = 'fail';
    title.textContent = '❌ ' + (data.verdict || 'Wrong Answer');
    const fc = data.failed_case;
    let details = `<div><span class="label">Time:</span> ${data.execution_time || 0}s</div>`;
    details += `<div><span class="label">Memory:</span> ${data.memory_used || 0} KB</div>`;
    if (fc) {
        details += `<div style="margin-top:12px;"><span class="label">Failed at Test Case #${fc.case}</span></div>`;
        if (fc.error) {
            details += `<pre style="margin-top:8px;text-align:left;font-size:13px;color:#ff4757;white-space:pre-wrap;">${escapeHtml(fc.error)}</pre>`;
        }
    }
    document.getElementById('resultDetails').innerHTML = details;
}

function closeResult() {
    document.getElementById('resultOverlay').classList.add('hidden');
}

function showError(msg) {
    const overlay = document.getElementById('resultOverlay');
    overlay.classList.remove('hidden');
    document.getElementById('resultIcon').className = 'icon fail';
    document.getElementById('resultIcon').innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
    document.getElementById('resultTitle').className = 'fail';
    document.getElementById('resultTitle').textContent = 'Error';
    document.getElementById('resultDetails').textContent = msg;
}

// ─── Editor Fullscreen ────────────────────────────────────────────

let editorFullscreen = false;
function toggleEditorFullscreen() {
    const panel = document.getElementById('editorPanel');
    editorFullscreen = !editorFullscreen;
    panel.classList.toggle('fullscreen-editor', editorFullscreen);
    if (editor) editor.layout();
}

// ─── Question Status ──────────────────────────────────────────────

function updateQuestionStatus(questionId, status) {
    const items = document.querySelectorAll('.question-item');
    items.forEach(el => {
        if (parseInt(el.dataset.id) === questionId) {
            const dot = el.querySelector('.status-dot');
            dot.className = 'status-dot ' + status;
        }
    });
}

// ─── Anti-Cheat ───────────────────────────────────────────────────

function initAntiCheat(initialViolations, maxViolations) {
    let violations = initialViolations || 0;
    const MAX_VIOLATIONS = maxViolations || 3;
    let lastViolationTime = 0;

    // Tab visibility
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            logViolation('tab_switch', 'Tab switched away from contest');
        }
    });

    // Window blur (focus loss) - debounced so it does not double-count
    // with the visibilitychange event fired for the same tab switch.
    window.addEventListener('blur', function() {
        logViolation('focus_loss', 'Browser window lost focus');
    });

    // Right-click disable
    document.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        return false;
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (
            e.key === 'F12' ||
            (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'i')) ||
            (e.ctrlKey && e.shiftKey && (e.key === 'J' || e.key === 'j')) ||
            (e.ctrlKey && (e.key === 'U' || e.key === 'u')) ||
            (e.ctrlKey && e.shiftKey && (e.key === 'C' || e.key === 'c'))
        ) {
            e.preventDefault();
            e.stopPropagation();
            logViolation('inspect_attempt', `Blocked shortcut: ${e.key} with ${e.ctrlKey ? 'Ctrl+' : ''}${e.shiftKey ? 'Shift+' : ''}`);
            return false;
        }
    });

    function logViolation(type, details) {
        const now = Date.now();
        if (now - lastViolationTime < 2000) return;
        lastViolationTime = now;

        fetch('/api/violation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, details: details + ' at ' + new Date().toISOString() }),
        })
        .then(r => r.json())
        .then(data => {
            violations = data.warning_count;
            updateViolationBadge(violations);

            if (data.locked) {
                lockContest();
            } else {
                alert(data.message);
            }
        });
    }

    function updateViolationBadge(count) {
        const badge = document.getElementById('violationBadge');
        const countEl = document.getElementById('violationCount');
        if (count > 0) {
            badge.classList.remove('hidden');
            countEl.textContent = count;
        } else {
            badge.classList.add('hidden');
        }
    }

    function lockContest() {
        alert('Maximum violations reached. The contest has been locked.');
        document.querySelector('.btn-run').disabled = true;
        document.querySelector('.btn-submit').disabled = true;
        if (editor) editor.updateOptions({ readOnly: true });
    }
}

// ─── Bottom Panel Collapse ────────────────────────────────────────

function toggleBottomPanel() {
    const panel = document.getElementById('bottomPanel');
    const icon = document.getElementById('panelToggleIcon');
    panel.classList.toggle('collapsed');
    if (icon) {
        icon.className = panel.classList.contains('collapsed') ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
    }
}

// ─── Submission History ───────────────────────────────────────────

function loadSubmissionHistory(questionId) {
    fetch(`/api/submissions/${questionId}`)
        .then(r => r.json())
        .then(subs => {
            if (subs.length > 0) {
                const verdict = subs[0].verdict;
                const status = verdict === 'Accepted' ? 'accepted' :
                               verdict === 'Wrong Answer' ? 'wrong_answer' :
                               verdict === 'Pending' ? 'attempted' : 'not_attempted';
                updateQuestionStatus(questionId, status);
            }
        })
        .catch(() => {});
}

// ─── Utility ──────────────────────────────────────────────────────

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
