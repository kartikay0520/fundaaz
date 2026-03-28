import os
import re
import io
import uuid
import hashlib
from datetime import date, timedelta
from flask import (Flask, render_template, request,
                   redirect, url_for, session, jsonify, send_file, abort)
from database.db import init_db, get_db, close_db
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-fallback-change-in-production')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
    SESSION_COOKIE_SAMESITE='Lax',
)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'static', 'uploads', 'notices')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file_obj):
    """Save uploaded image with a random UUID filename. Returns relative path or None."""
    if not file_obj or file_obj.filename == '':
        return None
    if not allowed_image(file_obj.filename):
        return None
    ext      = file_obj.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_obj.save(os.path.join(UPLOAD_FOLDER, filename))
    return filename

# Import pdf_report at top level so errors surface immediately
try:
    from pdf_report import generate_pdf as _generate_pdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

with app.app_context():
    init_db()

app.teardown_appcontext(close_db)

# ── iOS / browser compatibility headers ──────────────────────────────────────
@app.after_request
def add_ios_headers(response):
    response.headers['Vary'] = 'Accept'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

# ─────────────────────────────────────────────
def hash_pwd(pwd):
    return hashlib.sha256((pwd + '_fz_salt').encode()).hexdigest()

def admin_required():
    return session.get('role') != 'admin'

def student_required():
    return session.get('role') != 'student'

# ─────────────────────────────────────────────
# LANDING
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
@app.route('/login', methods=['POST'])
def login():
    role = request.form.get('role')
    uid  = request.form.get('uid', '').strip()
    pwd  = request.form.get('pwd', '')
    db   = get_db()

    if role == 'admin':
        admin = db.execute('SELECT * FROM admin WHERE username=?', (uid,)).fetchone()
        if admin and admin['password'] == hash_pwd(pwd):
            session['role']    = 'admin'
            session['user_id'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        return render_template('index.html', error='admin', msg='Invalid admin credentials')

    elif role == 'student':
        stu = db.execute('SELECT * FROM students WHERE login_id=?', (uid,)).fetchone()
        if stu and stu['password'] == hash_pwd(pwd):
            session['role']    = 'student'
            session['user_id'] = stu['id']
            return redirect(url_for('student_dashboard'))
        return render_template('index.html', error='student', msg='Invalid student credentials')

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ─────────────────────────────────────────────
# ADMIN DASHBOARD
# ─────────────────────────────────────────────
def _admin_context():
    db = get_db()
    return dict(
        students=db.execute('SELECT * FROM students ORDER BY name').fetchall(),
        tests=db.execute('SELECT * FROM tests ORDER BY date DESC').fetchall(),
        recent_results=db.execute('''
            SELECT tr.id,tr.marks,s.name AS student_name,
                   t.code AS test_code,t.subject,t.total_marks
            FROM test_results tr
            JOIN students s ON tr.student_id=s.id
            JOIN tests t ON tr.test_id=t.id
            ORDER BY tr.id DESC LIMIT 10''').fetchall(),
        all_results=db.execute('''
            SELECT tr.id, tr.marks, tr.student_id,
                   s.name  AS student_name,
                   s.class AS student_class,
                   s.batch AS student_batch,
                   t.code  AS test_code,
                   t.subject, t.total_marks, t.date
            FROM test_results tr
            JOIN students s ON tr.student_id = s.id
            JOIN tests    t ON tr.test_id    = t.id
            ORDER BY t.date DESC, s.name ASC''').fetchall(),
        stats=db.execute('''SELECT
            (SELECT COUNT(*) FROM students)     AS students,
            (SELECT COUNT(*) FROM tests)        AS tests,
            (SELECT COUNT(*) FROM test_results) AS results,
            (SELECT COUNT(DISTINCT class) FROM students) AS classes
        ''').fetchone(),
        notices=db.execute(
            'SELECT * FROM notices ORDER BY display_order ASC, id DESC'
        ).fetchall(),
    )


@app.route('/admin')
def admin_dashboard():
    if admin_required(): return redirect(url_for('index'))
    return render_template('admin.html', **_admin_context())

# ─────────────────────────────────────────────
# STUDENT PROGRESS SEARCH
# ─────────────────────────────────────────────
@app.route('/admin/student-progress')
def student_progress():
    if admin_required(): return redirect(url_for('index'))
    db      = get_db()
    query   = request.args.get('q', '').strip()
    student = None
    results = []
    stats   = {}
    subj_stats  = []
    topic_stats = []

    if query:
        student = db.execute(
            "SELECT * FROM students WHERE login_id=? OR LOWER(name) LIKE ?",
            (query, f'%{query.lower()}%')
        ).fetchone()

        if student:
            results = db.execute('''
                SELECT tr.marks, t.code, t.subject, t.total_marks,
                       t.date, t.chapter, t.topic
                FROM test_results tr
                JOIN tests t ON tr.test_id = t.id
                WHERE tr.student_id = ?
                ORDER BY t.date ASC
            ''', (student['id'],)).fetchall()

            if results:
                pcts = [round(r['marks']/r['total_marks']*100, 1) for r in results]
                stats = dict(avg=round(sum(pcts)/len(pcts),1),
                             best=max(pcts), worst=min(pcts), total=len(pcts))
                sm = {}
                for r in results:
                    s = r['subject']
                    if s not in sm: sm[s] = {'marks':0,'total':0,'count':0}
                    sm[s]['marks'] += r['marks']
                    sm[s]['total'] += r['total_marks']
                    sm[s]['count'] += 1
                subj_stats = [{'subject':k,'pct':round(v['marks']/v['total']*100,1),'tests':v['count']}
                               for k,v in sm.items()]
                tm = {}
                for r in results:
                    if not r['chapter'] and not r['topic']:
                        continue
                    key = (r['chapter'] or 'Uncategorised',
                           r['topic']   or 'General',
                           r['subject'])
                    if key not in tm: tm[key] = {'marks':0,'total':0,'count':0}
                    tm[key]['marks'] += r['marks']
                    tm[key]['total'] += r['total_marks']
                    tm[key]['count'] += 1
                topic_stats = [
                    {'chapter':k[0],'topic':k[1],'subject':k[2],
                     'pct':round(v['marks']/v['total']*100,1),'tests':v['count']}
                    for k,v in tm.items()
                ]

    ctx = _admin_context()
    ctx.update(search_query=query, found_student=student,
               progress_results=results, progress_stats=stats,
               progress_subj=subj_stats, progress_topics=topic_stats,
               init_tab='student-progress')
    return render_template('admin.html', **ctx)

# ─────────────────────────────────────────────
# PDF DOWNLOAD  (admin only)
# ─────────────────────────────────────────────
@app.route('/admin/student-pdf/<int:sid>')
def download_student_pdf(sid):
    if admin_required(): return abort(403)
    if not PDF_AVAILABLE:
        return ('PDF generation unavailable. Run: pip install reportlab', 503)

    db      = get_db()
    student = db.execute('SELECT * FROM students WHERE id=?', (sid,)).fetchone()
    if not student: return abort(404)

    date_from = request.args.get('from', '').strip()
    date_to   = request.args.get('to', '').strip()
    month     = request.args.get('month', '').strip()

    where_parts = ['tr.student_id = ?']
    params      = [sid]
    label       = 'All Time'

    if month:
        where_parts.append("t.date LIKE ?")
        params.append(f'{month}%')
        label = f'Month {month}'
    elif date_from and date_to:
        where_parts.append("t.date >= ? AND t.date <= ?")
        params += [date_from, date_to]
        label = f'{date_from} to {date_to}'
    elif date_from:
        where_parts.append("t.date >= ?")
        params.append(date_from)
        label = f'From {date_from}'
    elif date_to:
        where_parts.append("t.date <= ?")
        params.append(date_to)
        label = f'Until {date_to}'

    where_sql = ' AND '.join(where_parts)
    results = db.execute(f'''
        SELECT tr.marks, t.code, t.subject, t.total_marks,
               t.date, t.chapter, t.topic
        FROM test_results tr
        JOIN tests t ON tr.test_id = t.id
        WHERE {where_sql}
        ORDER BY t.date ASC
    ''', params).fetchall()

    try:
        pdf_bytes = _generate_pdf(student, results, label)
    except Exception as e:
        app.logger.error(f'PDF error for student {sid}: {e}')
        return ('PDF generation failed', 500)

    safe_name  = re.sub(r'[^a-zA-Z0-9]', '_', student['name'])
    safe_label = re.sub(r'[^a-zA-Z0-9]', '_', label)
    filename   = f'FUNDAAZ_{safe_name}_{safe_label}.pdf'

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

# ─────────────────────────────────────────────
# DATABASE DOWNLOAD  (admin only — developer tool)
# ─────────────────────────────────────────────
@app.route('/admin/download-db')
def download_db():
    if admin_required(): return abort(403)
    db_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'database', 'fundaaz.db'
    )
    return send_file(
        db_path,
        as_attachment=True,
        download_name='fundaaz_backup.db'
    )

# ─────────────────────────────────────────────
# STUDENT CRUD
# ─────────────────────────────────────────────
@app.route('/admin/students/add', methods=['POST'])
def add_student():
    if admin_required(): return redirect(url_for('index'))
    db = get_db()
    try:
        db.execute(
            '''INSERT INTO students
               (name,class,batch,subjects,parent_name,parent_contact,login_id,password)
               VALUES (?,?,?,?,?,?,?,?)''',
            (request.form['name'], request.form['class'], request.form['batch'],
             request.form['subjects'], request.form['parent_name'],
             request.form['parent_contact'], request.form['login_id'],
             hash_pwd(request.form['password']))
        )
        db.commit()
    except Exception as e:
        if 'UNIQUE' in str(e):
            return redirect(url_for('admin_dashboard')+'?tab=add-student&msg=Login+ID+already+exists&err=1')
        return redirect(url_for('admin_dashboard')+'?tab=add-student&msg=Error+adding+student&err=1')
    return redirect(url_for('admin_dashboard')+'?tab=students&msg=Student+added+successfully')


@app.route('/admin/students/edit/<int:sid>', methods=['POST'])
def edit_student(sid):
    if admin_required(): return redirect(url_for('index'))
    db = get_db()
    db.execute(
        '''UPDATE students SET name=?,class=?,batch=?,subjects=?,
           parent_name=?,parent_contact=? WHERE id=?''',
        (request.form['name'], request.form['class'], request.form['batch'],
         request.form['subjects'], request.form['parent_name'],
         request.form['parent_contact'], sid)
    )
    db.commit()
    return redirect(url_for('admin_dashboard')+'?tab=students&msg=Student+updated')


@app.route('/admin/students/delete/<int:sid>', methods=['POST'])
def delete_student(sid):
    if admin_required(): return redirect(url_for('index'))
    db = get_db()
    db.execute('DELETE FROM test_results WHERE student_id=?', (sid,))
    db.execute('DELETE FROM students WHERE id=?', (sid,))
    db.commit()
    return redirect(url_for('admin_dashboard')+'?tab=students&msg=Student+deleted')

# ─────────────────────────────────────────────
# TEST CRUD
# ─────────────────────────────────────────────
@app.route('/admin/tests/add', methods=['POST'])
def add_test():
    if admin_required(): return redirect(url_for('index'))
    db = get_db()
    try:
        db.execute(
            '''INSERT INTO tests
               (code,subject,total_marks,class,batch,date,chapter,topic)
               VALUES (?,?,?,?,?,?,?,?)''',
            (request.form['code'].upper(), request.form['subject'],
             int(request.form['total_marks']), request.form['class'],
             request.form['batch'], request.form['date'],
             request.form.get('chapter','').strip() or None,
             request.form.get('topic','').strip()   or None)
        )
        db.commit()
    except Exception as e:
        if 'UNIQUE' in str(e):
            return redirect(url_for('admin_dashboard')+'?tab=add-test&msg=Test+code+already+exists&err=1')
        return redirect(url_for('admin_dashboard')+'?tab=add-test&msg=Error+creating+test&err=1')
    return redirect(url_for('admin_dashboard')+'?tab=tests&msg=Test+created')


@app.route('/admin/tests/edit/<int:tid>', methods=['POST'])
def edit_test(tid):
    if admin_required(): return redirect(url_for('index'))
    db = get_db()
    db.execute(
        '''UPDATE tests SET code=?,subject=?,total_marks=?,class=?,batch=?,
           date=?,chapter=?,topic=? WHERE id=?''',
        (request.form['code'].upper(), request.form['subject'],
         int(request.form['total_marks']), request.form['class'],
         request.form['batch'], request.form['date'],
         request.form.get('chapter','').strip() or None,
         request.form.get('topic','').strip()   or None,
         tid)
    )
    db.commit()
    return redirect(url_for('admin_dashboard')+'?tab=tests&msg=Test+updated')


@app.route('/admin/tests/delete/<int:tid>', methods=['POST'])
def delete_test(tid):
    if admin_required(): return redirect(url_for('index'))
    db = get_db()
    db.execute('DELETE FROM test_results WHERE test_id=?', (tid,))
    db.execute('DELETE FROM tests WHERE id=?', (tid,))
    db.commit()
    return redirect(url_for('admin_dashboard')+'?tab=tests&msg=Test+deleted')

# ─────────────────────────────────────────────
# MARKS CRUD
# ─────────────────────────────────────────────
@app.route('/admin/marks/add', methods=['POST'])
def add_marks():
    if admin_required(): return redirect(url_for('index'))
    db    = get_db()
    sid   = int(request.form['student_id'])
    tid   = int(request.form['test_id'])
    marks = int(request.form['marks'])
    test  = db.execute('SELECT total_marks FROM tests WHERE id=?', (tid,)).fetchone()
    if marks > test['total_marks']:
        return redirect(url_for('admin_dashboard')+'?tab=marks&msg=Marks+exceed+total&err=1')
    existing = db.execute(
        'SELECT id FROM test_results WHERE student_id=? AND test_id=?', (sid, tid)
    ).fetchone()
    if existing:
        db.execute('UPDATE test_results SET marks=? WHERE id=?', (marks, existing['id']))
    else:
        db.execute('INSERT INTO test_results (student_id,test_id,marks) VALUES (?,?,?)',
                   (sid, tid, marks))
    db.commit()
    return redirect(url_for('admin_dashboard')+'?tab=marks&msg=Marks+saved')


@app.route('/admin/marks/delete/<int:rid>', methods=['POST'])
def delete_marks(rid):
    if admin_required(): return redirect(url_for('index'))
    db = get_db()
    db.execute('DELETE FROM test_results WHERE id=?', (rid,))
    db.commit()
    return redirect(url_for('admin_dashboard')+'?tab=marks&msg=Result+deleted')

# ─────────────────────────────────────────────
# ADMIN CHANGE PASSWORD
# ─────────────────────────────────────────────
@app.route('/admin/change-password', methods=['POST'])
def admin_change_password():
    if admin_required(): return redirect(url_for('index'))
    db      = get_db()
    admin   = db.execute('SELECT * FROM admin').fetchone()
    old     = request.form.get('old_password', '')
    new     = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')
    if admin['password'] != hash_pwd(old):
        return redirect(url_for('admin_dashboard')+'?tab=settings&msg=Wrong+current+password&err=1')
    if new != confirm or len(new) < 6:
        return redirect(url_for('admin_dashboard')+'?tab=settings&msg=Password+mismatch+or+too+short&err=1')
    db.execute('UPDATE admin SET password=?', (hash_pwd(new),))
    db.commit()
    return redirect(url_for('admin_dashboard')+'?tab=settings&msg=Password+updated')

# ─────────────────────────────────────────────
# STUDENT DASHBOARD
# ─────────────────────────────────────────────
@app.route('/student')
def student_dashboard():
    if student_required(): return redirect(url_for('index'))
    db  = get_db()
    sid = session['user_id']
    stu = db.execute('SELECT * FROM students WHERE id=?', (sid,)).fetchone()
    results = db.execute('''
        SELECT tr.*, t.code, t.subject, t.total_marks, t.date, t.chapter, t.topic
        FROM test_results tr JOIN tests t ON tr.test_id = t.id
        WHERE tr.student_id=? ORDER BY t.date DESC
    ''', (sid,)).fetchall()
    return render_template('student.html', student=stu, results=results)


@app.route('/student/change-password', methods=['POST'])
def student_change_password():
    if student_required(): return redirect(url_for('index'))
    db      = get_db()
    sid     = session['user_id']
    stu     = db.execute('SELECT * FROM students WHERE id=?', (sid,)).fetchone()
    old     = request.form.get('old_password', '')
    new     = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')
    if stu['password'] != hash_pwd(old):
        return redirect(url_for('student_dashboard')+'?tab=settings&msg=Wrong+current+password&err=1')
    if new != confirm or len(new) < 6:
        return redirect(url_for('student_dashboard')+'?tab=settings&msg=Password+mismatch&err=1')
    db.execute('UPDATE students SET password=? WHERE id=?', (hash_pwd(new), sid))
    db.commit()
    return redirect(url_for('student_dashboard')+'?tab=settings&msg=Password+updated')

# ─────────────────────────────────────────────
# CHART DATA APIs
# ─────────────────────────────────────────────
@app.route('/api/student/chart-data')
def student_chart_data():
    if student_required(): return jsonify({})
    db        = get_db()
    sid       = session['user_id']
    filter_by = request.args.get('filter', 'all')
    today     = date.today()

    where_parts = ['tr.student_id = ?']
    params      = [sid]

    if filter_by == 'daily':
        where_parts.append('t.date = ?')
        params.append(str(today))
    elif filter_by == 'weekly':
        where_parts.append('t.date >= ?')
        params.append(str(today - timedelta(days=7)))
    elif filter_by == 'monthly':
        where_parts.append('t.date >= ?')
        params.append(str(today.replace(day=1)))
    elif filter_by == 'yearly':
        where_parts.append('t.date >= ?')
        params.append(str(today.replace(month=1, day=1)))

    where_sql = ' AND '.join(where_parts)
    rows = db.execute(f'''
        SELECT t.code,t.subject,t.total_marks,tr.marks,t.date,t.chapter,t.topic
        FROM test_results tr JOIN tests t ON tr.test_id=t.id
        WHERE {where_sql} ORDER BY t.date
    ''', params).fetchall()

    trend  = [{'label':r['code'],'pct':round(r['marks']/r['total_marks']*100,1),'date':r['date']}
               for r in rows]
    subj   = {}
    topics = {}
    for r in rows:
        s = r['subject']
        if s not in subj: subj[s] = {'total':0,'max':0}
        subj[s]['total'] += r['marks']; subj[s]['max'] += r['total_marks']
        if r['chapter'] or r['topic']:
            key = f"{r['chapter'] or 'Uncategorised'} \u203a {r['topic'] or 'General'}"
            if key not in topics: topics[key] = {'total':0,'max':0,'subject':r['subject']}
            topics[key]['total'] += r['marks']; topics[key]['max'] += r['total_marks']

    return jsonify({
        'trend':    trend,
        'subjects': [{'subject':k,'pct':round(v['total']/v['max']*100,1)} for k,v in subj.items()],
        'topics':   [{'label':k,'pct':round(v['total']/v['max']*100,1),'subject':v['subject']}
                      for k,v in topics.items()],
    })


@app.route('/api/admin/student-chart/<int:sid>')
def admin_student_chart(sid):
    if admin_required(): return jsonify({})
    db   = get_db()
    rows = db.execute('''
        SELECT t.code,t.subject,t.total_marks,tr.marks,t.date,t.chapter,t.topic
        FROM test_results tr JOIN tests t ON tr.test_id=t.id
        WHERE tr.student_id=? ORDER BY t.date
    ''', (sid,)).fetchall()

    trend  = [{'label':r['code'],'pct':round(r['marks']/r['total_marks']*100,1),'date':r['date']}
               for r in rows]
    subj   = {}
    topics = {}
    for r in rows:
        s = r['subject']
        if s not in subj: subj[s] = {'total':0,'max':0}
        subj[s]['total'] += r['marks']; subj[s]['max'] += r['total_marks']
        if r['chapter'] or r['topic']:
            key = f"{r['chapter'] or 'Uncategorised'} \u203a {r['topic'] or 'General'}"
            if key not in topics: topics[key] = {'total':0,'max':0,'subject':r['subject']}
            topics[key]['total'] += r['marks']; topics[key]['max'] += r['total_marks']

    return jsonify({
        'trend':    trend,
        'subjects': [{'subject':k,'pct':round(v['total']/v['max']*100,1)} for k,v in subj.items()],
        'topics':   [{'label':k,'pct':round(v['total']/v['max']*100,1),'subject':v['subject']}
                      for k,v in topics.items()],
    })

# ─────────────────────────────────────────────
# NOTICE BOARD — ADMIN ROUTES
# ─────────────────────────────────────────────

def _get_notices_all():
    return get_db().execute(
        'SELECT * FROM notices ORDER BY display_order ASC, id DESC'
    ).fetchall()

def _get_notices_active():
    return get_db().execute(
        'SELECT * FROM notices WHERE is_active=1 ORDER BY display_order ASC, id DESC'
    ).fetchall()


@app.route('/admin/notices')
def admin_notices():
    if admin_required(): return redirect(url_for('index'))
    ctx = _admin_context()
    ctx['notices']  = _get_notices_all()
    ctx['init_tab'] = 'noticeboard'
    return render_template('admin.html', **ctx)


@app.route('/admin/notices/add', methods=['POST'])
def add_notice():
    if admin_required(): return redirect(url_for('index'))
    db      = get_db()
    title   = request.form.get('title', '').strip()[:200]
    content = request.form.get('content', '').strip()[:2000]
    ntype   = request.form.get('type', 'text')
    order   = int(request.form.get('display_order', 0) or 0)

    if not title:
        return redirect(url_for('admin_notices') + '?msg=Title+is+required&err=1')

    image_path = None
    if 'image' in request.files:
        image_path = save_image(request.files['image'])

    db.execute(
        'INSERT INTO notices (type, title, content, image_path, display_order) VALUES (?,?,?,?,?)',
        (ntype, title, content or None, image_path, order)
    )
    db.commit()
    return redirect(url_for('admin_notices') + '?msg=Notice+added')


@app.route('/admin/notices/edit/<int:nid>', methods=['POST'])
def edit_notice(nid):
    if admin_required(): return redirect(url_for('index'))
    db      = get_db()
    title   = request.form.get('title', '').strip()[:200]
    content = request.form.get('content', '').strip()[:2000]
    ntype   = request.form.get('type', 'text')
    order   = int(request.form.get('display_order', 0) or 0)
    active  = 1 if request.form.get('is_active') else 0

    notice = db.execute('SELECT * FROM notices WHERE id=?', (nid,)).fetchone()
    if not notice:
        return redirect(url_for('admin_notices'))

    image_path = notice['image_path']

    if 'image' in request.files and request.files['image'].filename:
        new_path = save_image(request.files['image'])
        if new_path:
            if image_path:
                old_file = os.path.join(UPLOAD_FOLDER, image_path)
                if os.path.exists(old_file):
                    os.remove(old_file)
            image_path = new_path

    if request.form.get('remove_image') and image_path:
        old_file = os.path.join(UPLOAD_FOLDER, image_path)
        if os.path.exists(old_file):
            os.remove(old_file)
        image_path = None

    db.execute(
        'UPDATE notices SET type=?, title=?, content=?, image_path=?, is_active=?, display_order=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
        (ntype, title, content or None, image_path, active, order, nid)
    )
    db.commit()
    return redirect(url_for('admin_notices') + '?msg=Notice+updated')


@app.route('/admin/notices/delete/<int:nid>', methods=['POST'])
def delete_notice(nid):
    if admin_required(): return redirect(url_for('index'))
    db     = get_db()
    notice = db.execute('SELECT image_path FROM notices WHERE id=?', (nid,)).fetchone()
    if notice and notice['image_path']:
        img_file = os.path.join(UPLOAD_FOLDER, notice['image_path'])
        if os.path.exists(img_file):
            os.remove(img_file)
    db.execute('DELETE FROM notices WHERE id=?', (nid,))
    db.commit()
    return redirect(url_for('admin_notices') + '?msg=Notice+deleted')


@app.route('/admin/notices/toggle/<int:nid>', methods=['POST'])
def toggle_notice(nid):
    if admin_required(): return redirect(url_for('index'))
    db = get_db()
    db.execute(
        'UPDATE notices SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?',
        (nid,)
    )
    db.commit()
    return redirect(url_for('admin_notices') + '?msg=Status+updated')


# ─────────────────────────────────────────────
# NOTICE BOARD — API
# ─────────────────────────────────────────────
@app.route('/api/notices')
def api_notices():
    if not session.get('role'):
        return jsonify([])
    notices = _get_notices_active()
    result  = []
    for n in notices:
        result.append({
            'id':         n['id'],
            'type':       n['type'],
            'title':      n['title'],
            'content':    n['content'] or '',
            'image_url':  f"/static/uploads/notices/{n['image_path']}" if n['image_path'] else None,
            'created_at': n['created_at'],
        })
    return jsonify(result)


if __name__ == '__main__':
    #app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    app.run(debug=False, host='0.0.0.0', port=5000)