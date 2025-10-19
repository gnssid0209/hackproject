from flask import Flask, request, render_template, redirect, url_for, session
import os, json, time
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "findit_secret"  # 세션 사용

# 업로드 설정
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {'png','jpg','jpeg','gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

# JSON 파일 경로
USER_JSON = 'users.json'
ITEM_JSON = 'lost_items.json'

# JSON 읽기/쓰기
def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 사용자, 분실물 불러오기
user_data = load_json(USER_JSON)
lost_items = load_json(ITEM_JSON)

# ------------------- 라우트 -------------------

@app.route('/')
def start():
    return render_template('start.html')

# 회원가입
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in user_data:
            return render_template('register.html', error="이미 존재하는 아이디입니다.")
        user_data[username] = {"password": password, "point": 100}  # 기본 100포인트
        save_json(user_data, USER_JSON)
        session['username'] = username
        return redirect(url_for('lost'))
    return render_template('register.html')

# 로그인
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in user_data and user_data[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('lost'))
        else:
            return render_template('login.html', error="아이디 또는 비밀번호가 잘못되었습니다.")
    return render_template('login.html')

# 로그아웃
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('start'))

# 분실물 등록
@app.route('/lost', methods=['GET','POST'])
def lost():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('lost.html', username=session['username'], point=user_data[session['username']]['point'])

@app.route('/find', methods=['GET', 'POST'])
def find():
    return render_template('find.html')

# 분실물 리스트
@app.route('/list')
def show_list():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('list.html', items=lost_items, username=session['username'], user_point=user_data[session['username']]['point'])

# 내 분실물만 보기
@app.route('/my_items')
def my_items():
    if 'username' not in session:
        return redirect(url_for('login'))
    my_items = [i for i in lost_items if i['owner']==session['username']]
    return render_template('my_items.html', items=my_items, username=session['username'], user_point=user_data[session['username']]['point'])

# 분실물 등록 처리
@app.route('/register_item', methods=['POST'])
def register_item():
    if 'username' not in session:
        return redirect(url_for('login'))
    item = request.form.get('item')
    point = int(request.form.get('point'))
    characteristic = request.form.get('item_characteristic')
    start_lat = request.form.get('start_lat')
    start_lng = request.form.get('start_lng')
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    start_address = request.form.get('start_address')
    end_address = request.form.get('end_address')

    # 파일 처리
    file = request.files.get('photo')
    photo_filename = ''
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(time.time())}{ext}"
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        photo_filename = filename

    item_data = {
        'id': int(time.time()),  # 간단한 고유 id
        'owner': session['username'],
        'item': item,
        'point': point,
        'characteristic': characteristic,
        'start_lat': start_lat,
        'start_lng': start_lng,
        'lat': lat,
        'lng': lng,
        'start_address': start_address,
        'end_address': end_address,
        'photo': photo_filename,
        'reports': []  # 신고자 정보
    }
    lost_items.append(item_data)
    save_json(lost_items, ITEM_JSON)
    return redirect(url_for('show_list'))

# 신고 제출 (기능3)
@app.route('/report/<int:item_id>', methods=['POST'])
def report_item(item_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    reporter = session['username']
    for item in lost_items:
        if item['id'] == item_id:
            item.setdefault('reports', []).append({'reporter': reporter, 'status': 'pending'})
            break
    save_json(lost_items, ITEM_JSON)
    return redirect(url_for('show_list'))

# 신고 처리 (Yes/No, 기능4)
@app.route('/my_items/action', methods=['POST'])
def handle_report():
    if 'username' not in session:
        return redirect(url_for('login'))
    item_id = int(request.form['item_id'])
    reporter = request.form['reporter']
    decision = request.form['decision']  # yes or no

    for item in lost_items:
        if item['id']==item_id and item['owner']==session['username']:
            for r in item.get('reports', []):
                if r['reporter']==reporter:
                    if decision=='yes':
                        user_data[reporter]['point'] += int(item['point'])
                        user_data[item['owner']]['point'] -= int(item['point'])
                        r['status'] = 'yes'
                    else:
                        item['reports'].remove(r)
                    break
            break
    save_json(lost_items, ITEM_JSON)
    save_json(user_data, USER_JSON)
    return redirect(url_for('my_items'))

# 서버 실행
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)
