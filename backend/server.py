from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import requests
import os
import time
import json
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)

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
STANDINGS_FILE = "standings_cache.json"
TOP_POSITIONS = 4 

# СТАБИЛЬНЫЕ ЛОГОТИПЫ (FlagCDN + API)
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

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Пользователь уже существует"}), 400
    try:
        new_user = User(username=data['username'], password=data['password'])
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "Успешно", "token": f"token-{new_user.id}", "username": new_user.username, "avatar": new_user.avatar})
    except: return jsonify({"error": "Ошибка БД"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username'], password=data['password']).first()
    if user:
        try: fav_l = json.loads(user.fav_leagues)
        except: fav_l = []
        try: fav_t = json.loads(user.fav_teams)
        except: fav_t = []
        return jsonify({"username": user.username, "token": f"token-{user.id}", "avatar": user.avatar, "favLeagues": fav_l, "favTeams": fav_t})
    return jsonify({"error": "Неверный логин или пароль"}), 401

@app.route('/api/update_profile', methods=['PUT'])
def update_profile():
    data = request.json
    user = User.query.filter_by(username=data.get('oldUsername')).first()
    if not user: return jsonify({"error": "User not found"}), 404
    
    new_username = data.get('newUsername')
    if new_username and new_username != user.username:
        if User.query.filter_by(username=new_username).first():
            return jsonify({"error": "Имя занято"}), 400
        user.username = new_username
    
    new_password = data.get('newPassword')
    if new_password:
        if new_password == user.password:
            return jsonify({"error": "Новый пароль совпадает со старым"}), 400
        user.password = new_password
    
    if data.get('newAvatar'): user.avatar = data['newAvatar']
    db.session.commit()
    return jsonify({"message": "OK", "username": user.username, "avatar": user.avatar})

@app.route('/api/favorites', methods=['POST'])
def update_favorites():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    if not user: return jsonify({"error": "User not found"}), 404
    target_id = data.get('id')
    fav_type = data.get('type')
    if fav_type == 'league':
        current = json.loads(user.fav_leagues)
        if target_id in current: current.remove(target_id)
        else: current.append(target_id)
        user.fav_leagues = json.dumps(current)
        result_list = current
    elif fav_type == 'team':
        current = json.loads(user.fav_teams)
        if int(target_id) in current: current.remove(int(target_id))
        else: current.append(int(target_id))
        user.fav_teams = json.dumps(current)
        result_list = current
    db.session.commit()
    return jsonify({"success": True, "list": result_list})

def load_standings():
    if os.path.exists(STANDINGS_FILE):
        if (time.time() - os.path.getmtime(STANDINGS_FILE)) < 24 * 3600:
            with open(STANDINGS_FILE, 'r') as f:
                return set(json.load(f))
    
    print("\n--- ЗАГРУЗКА ТАБЛИЦ ---")
    headers = {'X-Auth-Token': API_KEY}
    top_teams_ids = set()
    leagues_list = TARGET_LEAGUES.split(',')

    for league_code in leagues_list:
        if league_code == 'CL': continue 
        print(f"Tab {league_code}...", end=" ", flush=True)
        url = f"https://api.football-data.org/v4/competitions/{league_code}/standings"
        attempts = 0
        success = False
        while attempts < 3 and not success:
            try:
                resp = requests.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    standings = data.get('standings', [])
                    if standings:
                        table = standings[0].get('table', [])
                        for row in table[:TOP_POSITIONS]:
                            top_teams_ids.add(row['team']['id'])
                    print("OK")
                    success = True
                elif resp.status_code == 429:
                    print("Wait 20s...", end=" ", flush=True)
                    time.sleep(20)
                    attempts += 1
                else:
                    print(f"Err {resp.status_code}")
                    success = True
            except: break
        time.sleep(2) 
    
    with open(STANDINGS_FILE, 'w') as f:
        json.dump(list(top_teams_ids), f)
    return top_teams_ids

def load_history():
    if os.path.exists(CACHE_FILE):
        if (time.time() - os.path.getmtime(CACHE_FILE)) < 12 * 3600:
            df = pd.read_csv(CACHE_FILE)
            if not df.empty:
                df['home_id'] = df['home_id'].astype(int)
                df['away_id'] = df['away_id'].astype(int)
            return df
    
    print("\n--- ЗАГРУЗКА ИСТОРИИ ---")
    headers = {'X-Auth-Token': API_KEY}
    leagues_list = TARGET_LEAGUES.split(',')
    all_matches = []

    for league_code in leagues_list:
        print(f"[{league_code}]...", end=" ", flush=True)
        url = f"https://api.football-data.org/v4/competitions/{league_code}/matches?status=FINISHED"
        attempts = 0
        success = False
        while attempts < 3 and not success:
            try:
                resp = requests.get(url, headers=headers)
                if resp.status_code == 200:
                    matches_data = resp.json().get('matches', [])
                    print(f"OK ({len(matches_data)})")
                    for m in matches_data:
                        if m['score']['fullTime']['home'] is None: continue
                        ht_home = m['score']['halfTime']['home'] if m['score']['halfTime']['home'] is not None else 0
                        ht_away = m['score']['halfTime']['away'] if m['score']['halfTime']['away'] is not None else 0
                        all_matches.append({
                            'date': m['utcDate'][:10],
                            'league': m['competition']['name'],
                            'home_id': m['homeTeam']['id'], 
                            'home_team': m['homeTeam']['name'],
                            'away_id': m['awayTeam']['id'], 
                            'away_team': m['awayTeam']['name'],
                            'score_home': m['score']['fullTime']['home'],
                            'score_away': m['score']['fullTime']['away'],
                            'ht_home': ht_home, 'ht_away': ht_away
                        })
                    success = True
                elif resp.status_code == 429:
                    print("Limit 20s...", end=" ", flush=True)
                    time.sleep(20)
                    attempts += 1
                else:
                    print(f"Err {resp.status_code}")
                    success = True
            except: break
        time.sleep(2) 

    df = pd.DataFrame(all_matches)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['home_id'] = df['home_id'].astype(int)
        df['away_id'] = df['away_id'].astype(int)
        df = df.sort_values('date', ascending=False).reset_index(drop=True)
        df.to_csv(CACHE_FILE, index=False)
        return df
    return pd.DataFrame() if not os.path.exists(CACHE_FILE) else pd.read_csv(CACHE_FILE)

# --- АНАЛИТИКА ---
def get_recent_form(df, team_id, limit=5):
    games = df[(df['home_id'] == team_id) | (df['away_id'] == team_id)].copy()
    games = games.sort_values('date', ascending=False).head(limit)
    form = []
    for _, row in games.iterrows():
        is_home = row['home_id'] == team_id
        gf = row['score_home'] if is_home else row['score_away']
        ga = row['score_away'] if is_home else row['score_home']
        if gf > ga: form.append("W")
        elif gf < ga: form.append("L")
        else: form.append("D")
    return form

# Обновленный алгоритм статистики (возвращает КОДЫ, а не текст)
def get_stat_trends(df, team_id, side='all'):
    if side == 'home': games = df[df['home_id'] == team_id].copy()
    elif side == 'away': games = df[df['away_id'] == team_id].copy()
    else: games = df[(df['home_id'] == team_id) | (df['away_id'] == team_id)].copy()
    games = games.sort_values('date', ascending=False).reset_index(drop=True)
    if len(games) == 0: return []

    c = {'win':0, 'no_loss':0, 'loss':0, 'no_win':0, 'score':0, 'concede':0, 'tb25':0}
    a = {k: True for k in c}

    for _, row in games.iterrows():
        is_home = row['home_id'] == team_id
        my_s = row['score_home'] if is_home else row['score_away']
        opp_s = row['score_away'] if is_home else row['score_home']
        tot = my_s + opp_s

        if a['win']: (c['win'], a['win']) = (c['win']+1, True) if my_s > opp_s else (c['win'], False)
        if a['no_loss']: (c['no_loss'], a['no_loss']) = (c['no_loss']+1, True) if my_s >= opp_s else (c['no_loss'], False)
        if a['loss']: (c['loss'], a['loss']) = (c['loss']+1, True) if my_s < opp_s else (c['loss'], False)
        if a['no_win']: (c['no_win'], a['no_win']) = (c['no_win']+1, True) if my_s <= opp_s else (c['no_win'], False)
        if a['score']: (c['score'], a['score']) = (c['score']+1, True) if my_s > 0 else (c['score'], False)
        if a['concede']: (c['concede'], a['concede']) = (c['concede']+1, True) if opp_s > 0 else (c['concede'], False)
        if a['tb25']: (c['tb25'], a['tb25']) = (c['tb25']+1, True) if tot > 2 else (c['tb25'], False)
        if not any(a.values()): break

    trends = []
    # Возвращаем ОБЪЕКТЫ, а не строки
    if c['win'] >= 3: trends.append({'code': 'win_streak', 'count': c['win']})
    elif c['no_loss'] >= 5: trends.append({'code': 'no_loss_streak', 'count': c['no_loss']})
    if c['loss'] >= 3: trends.append({'code': 'loss_streak', 'count': c['loss']})
    elif c['no_win'] >= 4: trends.append({'code': 'no_win_streak', 'count': c['no_win']})
    if c['score'] >= 3: trends.append({'code': 'score_streak', 'count': c['score']})
    if c['concede'] >= 4: trends.append({'code': 'concede_streak', 'count': c['concede']})
    if c['tb25'] >= 3: trends.append({'code': 'tb25_streak', 'count': c['tb25']})
    return trends

# Обновленный алгоритм прогноза (возвращает КОД)
def get_strict_prediction(df, team_id, is_home, opponent_is_top, top_teams_ids):
    two_months_ago = datetime.now() - timedelta(days=60)
    games = df[((df['home_id'] == team_id) | (df['away_id'] == team_id)) & (pd.to_datetime(df['date']) >= two_months_ago)].copy()
    
    if len(games) < 3: return None 
    am_i_top = team_id in top_teams_ids
    if am_i_top and not opponent_is_top:
        filtered_games = []
        for _, row in games.iterrows():
            hist_opp_id = row['away_id'] if row['home_id'] == team_id else row['home_id']
            if hist_opp_id not in top_teams_ids: filtered_games.append(row)
        games = pd.DataFrame(filtered_games)
    
    if len(games) < 3: return None

    all_win, all_no_loss, all_tb15, all_score = True, True, True, True
    for _, row in games.iterrows():
        is_h = row['home_id'] == team_id
        my_s = row['score_home'] if is_h else row['score_away']
        opp_s = row['score_away'] if is_h else row['score_home']
        tot = my_s + opp_s
        if my_s <= opp_s: all_win = False
        if my_s < opp_s: all_no_loss = False
        if tot < 2: all_tb15 = False
        if my_s == 0: all_score = False
        
    # Возвращаем КОДЫ
    if all_win: return "win_100"
    if all_no_loss: return "no_loss_100"
    if all_score: return "score_100"
    if all_tb15: return "tb15_100"
    return None 

@app.route('/api/matches')
def get_matches_endpoint():
    df = load_history()
    top_teams = load_standings()
    if df.empty: return jsonify([])

    headers = {'X-Auth-Token': API_KEY}
    date_from = datetime.now().strftime('%Y-%m-%d')
    date_to = (datetime.now() + timedelta(hours=60)).strftime('%Y-%m-%d')
    url = f"https://api.football-data.org/v4/matches?dateFrom={date_from}&dateTo={date_to}&competitions={TARGET_LEAGUES}"
    
    try:
        resp = requests.get(url, headers=headers)
        raw_matches = resp.json().get('matches', []) if resp.status_code == 200 else []
    except: raw_matches = []

    final_data = []
    now_utc = datetime.now(timezone.utc)

    for m in raw_matches:
        if m['status'] in ['FINISHED', 'AWARDED']: continue
        match_time = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if (now_utc - match_time).total_seconds() / 3600 > 4: continue 

        home_id = m['homeTeam']['id']
        away_id = m['awayTeam']['id']
        home_is_top = home_id in top_teams
        away_is_top = away_id in top_teams
        
        trends_h_all = get_stat_trends(df, home_id, 'all')
        trends_h_context = get_stat_trends(df, home_id, 'home')
        trends_a_all = get_stat_trends(df, away_id, 'all')
        trends_a_context = get_stat_trends(df, away_id, 'away')
        
        pred_h = get_strict_prediction(df, home_id, True, away_is_top, top_teams)
        pred_a = get_strict_prediction(df, away_id, False, home_is_top, top_teams)
        
        form_h = get_recent_form(df, home_id)
        form_a = get_recent_form(df, away_id)

        if pred_h or pred_a or trends_h_all or trends_a_all:
            flag_url = LEAGUE_FLAGS.get(m['competition']['code'], '')
            if m['competition']['code'] == 'CL': flag_url = LEAGUE_FLAGS['CL']

            final_data.append({
                "id": m['id'],
                "utcDate": m['utcDate'],
                "status": m['status'],
                "league": m['competition']['name'],
                "league_code": m['competition']['code'],
                "league_flag": flag_url,
                "home": { 
                    "id": home_id, "name": m['homeTeam']['name'], "logo": m['homeTeam']['crest'], 
                    "prediction": pred_h, "trends_all": trends_h_all, "trends_context": trends_h_context, "form": form_h, "is_top": home_is_top
                },
                "away": { 
                    "id": away_id, "name": m['awayTeam']['name'], "logo": m['awayTeam']['crest'], 
                    "prediction": pred_a, "trends_all": trends_a_all, "trends_context": trends_a_context, "form": form_a, "is_top": away_is_top
                }
            })

    final_data.sort(key=lambda x: (LEAGUE_PRIORITY.get(x['league_code'], 99), x['utcDate']))
    return jsonify(final_data)

@app.route('/api/team/<int:team_id>/history')
def get_team_history_endpoint(team_id):
    # Старый код истории (он работает и так)
    headers = {'X-Auth-Token': API_KEY}
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches?status=FINISHED"
    try:
        resp = requests.get(url, headers=headers)
        matches = resp.json().get('matches', []) if resp.status_code == 200 else []
        matches.sort(key=lambda x: x['utcDate'], reverse=True)
        history = []
        for m in matches:
            is_home = (m['homeTeam']['id'] == team_id)
            score_h = m['score']['fullTime']['home']
            score_a = m['score']['fullTime']['away']
            if score_h is None: continue 
            res = 'D'
            my_s = score_h if is_home else score_a
            opp_s = score_a if is_home else score_h
            if my_s > opp_s: res = 'W'
            elif my_s < opp_s: res = 'L'
            comp = m['competition']['code']
            flag = LEAGUE_FLAGS.get(comp, '')
            if comp == 'CL': flag = LEAGUE_FLAGS['CL']
            history.append({
                'date': m['utcDate'][:10],
                'competition': m['competition']['name'],
                'league_flag': flag,
                'opponent': m['awayTeam']['name'] if is_home else m['homeTeam']['name'],
                'opponent_id': m['awayTeam']['id'] if is_home else m['homeTeam']['id'],
                'opponent_logo': m['awayTeam']['crest'] if is_home else m['homeTeam']['crest'],
                'score': f"{score_h} - {score_a}",
                'result': res,
                'is_home': is_home
            })
        return jsonify(history)
    except: return jsonify([])

if __name__ == '__main__':
    app.run(debug=False, port=5000)