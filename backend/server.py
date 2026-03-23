from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import requests
import os
import time
import json
import threading
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)
api_lock = threading.Lock()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    avatar = db.Column(db.String(10), default='👤')
    fav_leagues = db.Column(db.Text, default='[]')
    fav_teams = db.Column(db.Text, default='[]')

with app.app_context():
    db.create_all()

API_KEY = '0da5c9f2e19a455faca817cd5699b78f' 
TARGET_LEAGUES = 'PL,BL1,SA,PD,FL1,CL,PPL,DED,ELC,BSA' 
LEAGUE_PRIORITY = {'CL': 1, 'PL': 2, 'BL1': 3, 'PD': 4, 'SA': 5, 'FL1': 6, 'PPL': 7, 'DED': 8, 'ELC': 9, 'BSA': 10}

CACHE_FILE = "football_history_cache.csv"
LEAGUE_DATA_FILE = "league_details.json"
TOP_TEAMS_FILE = "top_teams.json"
TOP_POSITIONS = 4 

LEAGUE_FLAGS = {
    'PL': 'https://flagcdn.com/h240/gb-eng.png',
    'ELC': 'https://flagcdn.com/h240/gb-eng.png',
    'PD': 'https://flagcdn.com/h240/es.png',
    'BL1': 'https://flagcdn.com/h240/de.png',
    'SA': 'https://flagcdn.com/h240/it.png',
    'FL1': 'https://flagcdn.com/h240/fr.png',
    'PPL': 'https://flagcdn.com/h240/pt.png',
    'DED': 'https://flagcdn.com/h240/nl.png',
    'BSA': 'https://flagcdn.com/h240/br.png',
    'CL': 'https://crests.football-data.org/CL.png'
}

# --- AUTH ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "User exists"}), 400
    try:
        new_user = User(username=data['username'], password=data['password'])
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "Success", "token": f"token-{new_user.id}", "username": new_user.username, "avatar": new_user.avatar})
    except: return jsonify({"error": "DB Error"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username'], password=data['password']).first()
    if user:
        try: fl = json.loads(user.fav_leagues)
        except: fl = []
        try: ft = json.loads(user.fav_teams)
        except: ft = []
        return jsonify({"username": user.username, "token": f"token-{user.id}", "avatar": user.avatar, "favLeagues": fl, "favTeams": ft})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/update_profile', methods=['PUT'])
def update_profile():
    data = request.json
    user = User.query.filter_by(username=data.get('oldUsername')).first()
    if not user: return jsonify({"error": "Not found"}), 404
    if data.get('newUsername') and data['newUsername'] != user.username:
        if User.query.filter_by(username=data['newUsername']).first(): return jsonify({"error": "Taken"}), 400
        user.username = data['newUsername']
    if data.get('newPassword'): 
        if data['newPassword'] == user.password: return jsonify({"error": "Same password"}), 400
        user.password = data['newPassword']
    if data.get('newAvatar'): user.avatar = data['newAvatar']
    db.session.commit()
    return jsonify({"message": "OK", "username": user.username, "avatar": user.avatar})

@app.route('/api/favorites', methods=['POST'])
def update_favorites():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    if not user: return jsonify({"error": "User not found"}), 404
    tid = data.get('id')
    ftype = data.get('type')
    if ftype == 'league':
        cur = json.loads(user.fav_leagues)
        if tid in cur: cur.remove(tid)
        else: cur.append(tid)
        user.fav_leagues = json.dumps(cur)
        res = cur
    elif ftype == 'team':
        cur = json.loads(user.fav_teams)
        if int(tid) in cur: cur.remove(int(tid))
        else: cur.append(int(tid))
        user.fav_teams = json.dumps(cur)
        res = cur
    db.session.commit()
    return jsonify({"success": True, "list": res})

# --- DATA LOADERS ---
def is_valid(path, h=24):
    return os.path.exists(path) and (time.time() - os.path.getmtime(path)) < h * 3600

def load_league_details():
    if is_valid(LEAGUE_DATA_FILE, 24):
        try:
            with open(LEAGUE_DATA_FILE, 'r') as f: return json.load(f)
        except: pass
    
    with api_lock:
        if is_valid(LEAGUE_DATA_FILE, 24):
            try:
                with open(LEAGUE_DATA_FILE, 'r') as f: return json.load(f)
            except: pass

        print("\n--- ЗАГРУЗКА ТАБЛИЦ И БОМБАРДИРОВ ---")
        headers = {'X-Auth-Token': API_KEY}
        combined_data = {}
        for code in TARGET_LEAGUES.split(','):
            league_info = {"standings": [], "scorers": []}
            if code != 'CL':
                print(f"Table {code}...", end=" ", flush=True)
                attempts = 0
                success = False
                while attempts < 3 and not success:
                    try:
                        r = requests.get(f"https://api.football-data.org/v4/competitions/{code}/standings", headers=headers)
                        if r.status_code == 200:
                            data = r.json()
                            st = data.get('standings', [])
                            if st: league_info["standings"] = st[0].get('table', [])
                            print("OK", end=" | ", flush=True)
                            success = True
                        elif r.status_code == 429:
                            print("Wait 30s...", end=" ", flush=True)
                            time.sleep(30); attempts += 1
                        else:
                            print(f"Err {r.status_code}", end=" | ", flush=True)
                            success = True
                    except: break
                time.sleep(2)

            print(f"Scorers...", end=" ", flush=True)
            attempts = 0
            success = False
            while attempts < 3 and not success:
                try:
                    r = requests.get(f"https://api.football-data.org/v4/competitions/{code}/scorers", headers=headers)
                    if r.status_code == 200:
                        league_info["scorers"] = r.json().get('scorers', [])
                        print("OK")
                        success = True
                    elif r.status_code == 429:
                        print("Wait 30s...", end=" ", flush=True)
                        time.sleep(30); attempts += 1
                    else:
                        print(f"Err {r.status_code}")
                        success = True
                except: break
            combined_data[code] = league_info
            time.sleep(2)

        with open(LEAGUE_DATA_FILE, 'w') as f: json.dump(combined_data, f)
        return combined_data

def get_top_teams_ids():
    data = load_league_details()
    ids = set()
    for code, info in data.items():
        if code == 'CL': continue
        standings = info.get("standings", [])
        for row in standings[:TOP_POSITIONS]:
            ids.add(row['team']['id'])
    with open(TOP_TEAMS_FILE, 'w') as f: json.dump(list(ids), f)
    return ids

def load_history():
    if is_valid(CACHE_FILE, 12):
        try:
            df = pd.read_csv(CACHE_FILE)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['home_id'] = df['home_id'].astype(int)
                df['away_id'] = df['away_id'].astype(int)
                return df
        except: pass

    with api_lock:
        if is_valid(CACHE_FILE, 12):
            try:
                df = pd.read_csv(CACHE_FILE)
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df['home_id'] = df['home_id'].astype(int)
                    df['away_id'] = df['away_id'].astype(int)
                    return df
            except: pass
        
        print("\n--- ЗАГРУЗКА ИСТОРИИ ---")
        headers = {'X-Auth-Token': API_KEY}
        matches = []
        for code in TARGET_LEAGUES.split(','):
            print(f"[{code}]...", end=" ", flush=True)
            url = f"https://api.football-data.org/v4/competitions/{code}/matches?status=FINISHED"
            attempts = 0
            success = False
            while attempts < 3 and not success:
                try:
                    r = requests.get(url, headers=headers)
                    if r.status_code == 200:
                        data = r.json().get('matches', [])
                        print(f"OK ({len(data)})")
                        for m in data:
                            if m['score']['fullTime']['home'] is None: continue
                            ht_h = m['score']['halfTime']['home'] if m['score']['halfTime']['home'] is not None else 0
                            ht_a = m['score']['halfTime']['away'] if m['score']['halfTime']['away'] is not None else 0
                            matches.append({
                                'date': m['utcDate'][:10], 'league': m['competition']['name'],
                                'league_code': code,
                                'home_id': m['homeTeam']['id'], 'home_team': m['homeTeam']['name'],
                                'home_logo': m['homeTeam']['crest'],
                                'away_id': m['awayTeam']['id'], 'away_team': m['awayTeam']['name'],
                                'away_logo': m['awayTeam']['crest'],
                                'score_home': m['score']['fullTime']['home'], 'score_away': m['score']['fullTime']['away'],
                                'ht_home': ht_h, 'ht_away': ht_a
                            })
                        success = True
                    elif r.status_code == 429:
                        print("Limit 20s...", end=" ", flush=True)
                        time.sleep(20); attempts += 1
                    else:
                        print(f"Err {r.status_code}")
                        success = True
                except: break
            time.sleep(3)
        
        df = pd.DataFrame(matches)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df['home_id'] = df['home_id'].astype(int)
            df['away_id'] = df['away_id'].astype(int)
            df = df.sort_values('date', ascending=False).reset_index(drop=True)
            df.to_csv(CACHE_FILE, index=False)
            return df
        return pd.DataFrame()

# --- ANALYTICS ---
def declension(n, f): return f[2] if n%100 in[11,12,13,14] else f[0] if n%10==1 else f[1] if n%10 in[2,3,4] else f[2]
def fmt_trend(text, count): word = declension(count, ['матч', 'матча', 'матчей']); return f"{text} {count} {word} подряд"

def get_h2h_history(df, h_id, a_id):
    if df.empty: return []
    if not pd.api.types.is_datetime64_any_dtype(df['date']): df['date'] = pd.to_datetime(df['date'])
    mask = ((df['home_id'] == h_id) & (df['away_id'] == a_id)) | \
           ((df['home_id'] == a_id) & (df['away_id'] == h_id))
    h2h = df[mask].sort_values('date', ascending=False).head(5)
    res = []
    for _, row in h2h.iterrows():
        d_val = row['date']
        d_str = d_val.strftime('%d.%m.%Y') if isinstance(d_val, pd.Timestamp) else str(d_val)[:10]
        res.append({
            'date': d_str, 'home': row['home_team'], 'away': row['away_team'], 'score': f"{row['score_home']} : {row['score_away']}"
        })
    return res

def get_stat_trends(df, team_id, side='all'):
    if side=='home': games = df[df['home_id']==team_id].copy()
    elif side=='away': games = df[df['away_id']==team_id].copy()
    else: games = df[(df['home_id']==team_id)|(df['away_id']==team_id)].copy()
    games = games.sort_values('date', ascending=False).reset_index(drop=True)
    if len(games) == 0: return []

    c = {'win':0,'no_loss':0,'loss':0,'no_win':0,'score':0,'concede':0,'tb25':0,
         'win_1h':0, 'no_loss_1h':0, 'score_1h':0, 'concede_1h':0, 'score_2h':0}
    a = {k:True for k in c}

    for _, r in games.iterrows():
        is_h = r['home_id'] == team_id
        fs_h, fs_a = r['score_home'], r['score_away']
        hs_h, hs_a = r['ht_home'], r['ht_away']
        my_fs = fs_h if is_h else fs_a
        op_fs = fs_a if is_h else fs_h
        my_hs = hs_h if is_h else hs_a
        op_hs = hs_a if is_h else hs_h
        my_2h = my_fs - my_hs
        
        if a['win']: (c['win'], a['win']) = (c['win']+1, True) if my_fs > op_fs else (c['win'], False)
        if a['no_loss']: (c['no_loss'], a['no_loss']) = (c['no_loss']+1, True) if my_fs >= op_fs else (c['no_loss'], False)
        if a['loss']: (c['loss'], a['loss']) = (c['loss']+1, True) if my_fs < op_fs else (c['loss'], False)
        if a['no_win']: (c['no_win'], a['no_win']) = (c['no_win']+1, True) if my_fs <= op_fs else (c['no_win'], False)
        if a['score']: (c['score'], a['score']) = (c['score']+1, True) if my_fs > 0 else (c['score'], False)
        if a['concede']: (c['concede'], a['concede']) = (c['concede']+1, True) if op_fs > 0 else (c['concede'], False)
        if a['tb25']: (c['tb25'], a['tb25']) = (c['tb25']+1, True) if (my_fs+op_fs) > 2 else (c['tb25'], False)
        
        if a['win_1h']: (c['win_1h'], a['win_1h']) = (c['win_1h']+1, True) if my_hs > op_hs else (c['win_1h'], False)
        if a['no_loss_1h']: (c['no_loss_1h'], a['no_loss_1h']) = (c['no_loss_1h']+1, True) if my_hs >= op_hs else (c['no_loss_1h'], False)
        if a['score_1h']: (c['score_1h'], a['score_1h']) = (c['score_1h']+1, True) if my_hs > 0 else (c['score_1h'], False)
        if a['concede_1h']: (c['concede_1h'], a['concede_1h']) = (c['concede_1h']+1, True) if op_hs > 0 else (c['concede_1h'], False)
        if a['score_2h']: (c['score_2h'], a['score_2h']) = (c['score_2h']+1, True) if my_2h > 0 else (c['score_2h'], False)

        if not any(a.values()): break

    trends = []
    has_win = False
    if c['win']>=3: 
        trends.append({'code':'win_streak','count':c['win']})
        has_win = True
    elif c['no_loss']>=5: trends.append({'code':'no_loss_streak','count':c['no_loss']})
    if c['loss']>=3: trends.append({'code':'loss_streak','count':c['loss']})
    elif c['no_win']>=4: trends.append({'code':'no_win_streak','count':c['no_win']})
    if not has_win and c['score']>=3: trends.append({'code':'score_streak','count':c['score']})
    if c['concede']>=4: trends.append({'code':'concede_streak','count':c['concede']})
    if c['tb25']>=3: trends.append({'code':'tb25_streak','count':c['tb25']})
    if c['win_1h']>=2: trends.append({'code':'win_1h_streak','count':c['win_1h']})
    if c['no_loss_1h']>=4: trends.append({'code':'no_loss_1h_streak','count':c['no_loss_1h']})
    if c['score_1h']>=3: trends.append({'code':'score_1h_streak','count':c['score_1h']})
    if c['score_2h']>=3: trends.append({'code':'score_2h_streak','count':c['score_2h']})
    return trends

def get_strict_prediction(df, team_id, is_home, opponent_is_top, top_teams_ids):
    two_months = datetime.now() - timedelta(days=60)
    games = df[((df['home_id']==team_id)|(df['away_id']==team_id))&(pd.to_datetime(df['date'])>=two_months)].copy()
    if len(games)<3: return None
    am_i_top = team_id in top_teams_ids
    if am_i_top and not opponent_is_top:
        fg = []
        for _,r in games.iterrows():
            oid = r['away_id'] if r['home_id']==team_id else r['home_id']
            if oid not in top_teams_ids: fg.append(r)
        games = pd.DataFrame(fg)
    if len(games)<3: return None
    
    aw, anl, ascr, atb15, aw1h, ascr2h = True, True, True, True, True, True
    for _,r in games.iterrows():
        ih = r['home_id']==team_id
        ms = r['score_home'] if ih else r['score_away']
        os_ = r['score_away'] if ih else r['score_home']
        mhs = r['ht_home'] if ih else r['ht_away']
        ohs = r['ht_away'] if ih else r['ht_home']
        m2h = ms - mhs
        if ms<=os_: aw=False
        if ms<os_: anl=False
        if (ms+os_)<2: atb15=False
        if ms==0: ascr=False
        if mhs <= ohs: aw1h = False
        if m2h == 0: ascr2h = False
        
    if aw: return "win_100"
    if aw1h: return "win_1h_100"
    if anl: return "no_loss_100"
    if ascr: return "score_100"
    if ascr2h: return "score_2h_100"
    if atb15: return "tb15_100"
    return None

def get_recent_form(df, team_id):
    games = df[(df['home_id'] == team_id) | (df['away_id'] == team_id)].copy()
    games = games.sort_values('date', ascending=False).head(5)
    form = []
    for _, row in games.iterrows():
        is_home = row['home_id'] == team_id
        gf = row['score_home'] if is_home else row['score_away']
        ga = row['score_away'] if is_home else row['score_home']
        if gf > ga: form.append("W")
        elif gf < ga: form.append("L")
        else: form.append("D")
    return form

# --- ROUTES ---
@app.route('/api/matches')
def get_matches_endpoint():
    load_league_details()
    df = load_history()
    top_teams = get_top_teams_ids()
    if df.empty: return jsonify([])

    headers = {'X-Auth-Token': API_KEY}
    d1 = datetime.now().strftime('%Y-%m-%d')
    d2 = (datetime.now() + timedelta(hours=120)).strftime('%Y-%m-%d')
    
    try:
        r = requests.get(f"https://api.football-data.org/v4/matches?dateFrom={d1}&dateTo={d2}&competitions={TARGET_LEAGUES}", headers=headers)
        raw = r.json().get('matches', []) if r.status_code==200 else []
    except: raw = []

    res = []
    now = datetime.now(timezone.utc)
    for m in raw:
        if m['status'] in ['FINISHED', 'AWARDED']: continue
        mt = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if (now - mt).total_seconds()/3600 > 4: continue 

        hid, aid = m['homeTeam']['id'], m['awayTeam']['id']
        h2h = get_h2h_history(df, hid, aid)
        trends_h_all = get_stat_trends(df, hid, 'all')
        trends_h_ctx = get_stat_trends(df, hid, 'home')
        trends_a_all = get_stat_trends(df, aid, 'all')
        trends_a_ctx = get_stat_trends(df, aid, 'away')
        pred_h = get_strict_prediction(df, hid, True, aid in top_teams, top_teams)
        pred_a = get_strict_prediction(df, aid, False, hid in top_teams, top_teams)

        if pred_h or pred_a or trends_h_all or trends_a_all or h2h:
            furl = LEAGUE_FLAGS.get(m['competition']['code'], '')
            if m['competition']['code'] == 'CL': furl = LEAGUE_FLAGS['CL']
            
            goals_info = []
            if 'goals' in m:
                for g in m['goals']:
                    p_name = g.get('scorer', {}).get('name', 'Unknown')
                    minute = g.get('minute')
                    goals_info.append(f"{p_name} {minute}'")

            res.append({
                "id": m['id'], "utcDate": m['utcDate'], "status": m['status'],
                "league": m['competition']['name'], "league_code": m['competition']['code'], "league_flag": furl,
                "h2h": h2h, "goals_info": goals_info,
                "home": { 
                    "id": hid, "name": m['homeTeam']['name'], "logo": m['homeTeam']['crest'], 
                    "prediction": pred_h, "trends_all": trends_h_all, "trends_context": trends_h_ctx, 
                    "form": get_recent_form(df, hid), "is_top": hid in top_teams 
                },
                "away": { 
                    "id": aid, "name": m['awayTeam']['name'], "logo": m['awayTeam']['crest'], 
                    "prediction": pred_a, "trends_all": trends_a_all, "trends_context": trends_a_ctx, 
                    "form": get_recent_form(df, aid), "is_top": aid in top_teams }
            })
    res.sort(key=lambda x: (LEAGUE_PRIORITY.get(x['league_code'], 99), x['utcDate']))
    return jsonify(res)

@app.route('/api/league/<league_code>')
def get_league_info(league_code):
    data = load_league_details()
    lg_data = data.get(league_code, {"standings": [], "scorers": []})
    return jsonify(lg_data)

@app.route('/api/team/<int:tid>/history')
def get_hist(tid):
    df = load_history()
    if df.empty: return jsonify([])
    games = df[(df['home_id']==tid)|(df['away_id']==tid)].sort_values('date', ascending=False)
    
    hist = []
    for _, r in games.iterrows():
        ih = r['home_id'] == tid
        my_s, op_s = (r['score_home'], r['score_away']) if ih else (r['score_away'], r['score_home'])
        res = 'W' if my_s > op_s else 'L' if my_s < op_s else 'D'
        l_code = r.get('league_code', 'PL')
        flag = LEAGUE_FLAGS.get(l_code, '')
        if l_code == 'CL': flag = LEAGUE_FLAGS['CL']
        opp_logo = r['away_logo'] if ih else r['home_logo']

        hist.append({
            'date': r['date'].strftime('%Y-%m-%d'), # ОТДАЕМ ISO (YYYY-MM-DD), чтобы App.js мог красиво отформатировать
            'league_name': r['league'],
            'league_flag': flag,
            'opponent': r['away_team'] if ih else r['home_team'],
            'opponent_id': r['away_id'] if ih else r['home_id'],
            'opponent_logo': opp_logo,
            'score': f"{r['score_home']}:{r['score_away']}", 
            'result': res,
            'is_home': ih
        })
    return jsonify(hist)

if __name__ == '__main__':
    load_league_details() 
    app.run(debug=False, port=5000)