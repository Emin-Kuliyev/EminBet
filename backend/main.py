from flask import Flask, jsonify
from flask_cors import CORS
import pandas as pd
import requests
import os
import time
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Разрешаем сайту обращаться к серверу

# ==============================================================================
# НАСТРОЙКИ
# ==============================================================================
API_KEY = '0da5c9f2e19a455faca817cd5699b78f'

TARGET_LEAGUES = 'PL,BL1,SA,PD,FL1,CL,PPL,DED,ELC'
LEAGUE_PRIORITY = {'CL': 1, 'PL': 2, 'BL1': 3, 'PD': 4, 'SA': 5, 'FL1': 6, 'PPL': 7, 'DED': 8, 'ELC': 9}
CACHE_FILE = "football_history_cache.csv"

# ==============================================================================
# ЛОГИКА (Твоя, но адаптированная под JSON)
# ==============================================================================
def load_history():
    if os.path.exists(CACHE_FILE):
        if (time.time() - os.path.getmtime(CACHE_FILE)) < 12 * 3600:
            return pd.read_csv(CACHE_FILE)
    
    headers = {'X-Auth-Token': API_KEY}
    leagues_list = TARGET_LEAGUES.split(',')
    all_matches = []

    for league_code in leagues_list:
        url = f"https://api.football-data.org/v4/competitions/{league_code}/matches?status=FINISHED"
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                matches = resp.json().get('matches', [])
                for m in matches:
                    if m['score']['fullTime']['home'] is None: continue
                    ht_home = m['score']['halfTime']['home'] if m['score']['halfTime']['home'] is not None else 0
                    ht_away = m['score']['halfTime']['away'] if m['score']['halfTime']['away'] is not None else 0
                    all_matches.append({
                        'date': m['utcDate'][:10],
                        'league': m['competition']['name'],
                        'home_team': m['homeTeam']['name'],
                        'away_team': m['awayTeam']['name'],
                        'score_home': m['score']['fullTime']['home'],
                        'score_away': m['score']['fullTime']['away'],
                        'ht_home': ht_home, 'ht_away': ht_away
                    })
        except: pass

    df = pd.DataFrame(all_matches)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date', ascending=False).reset_index(drop=True)
        df.to_csv(CACHE_FILE, index=False)
        return df
    return pd.DataFrame() if not os.path.exists(CACHE_FILE) else pd.read_csv(CACHE_FILE)

def declension(n, forms):
    if n % 100 in [11, 12, 13, 14]: return forms[2]
    if n % 10 == 1: return forms[0]
    if n % 10 in [2, 3, 4]: return forms[1]
    return forms[2]

def fmt_trend(text, count, context=""):
    word = declension(count, ['матч', 'матча', 'матчей'])
    suffix = f" {context}" if context else ""
    return f"{text} {count} {word} подряд{suffix}"

def get_current_streaks(df, team, side='all', is_home_team_in_match=True):
    # side: 'home', 'away', 'all'
    if side == 'home':
        games = df[df['home_team'] == team].copy()
        context_str = "(дома)"
    elif side == 'away':
        games = df[df['away_team'] == team].copy()
        context_str = "(в гостях)"
    else:
        games = df[(df['home_team'] == team) | (df['away_team'] == team)].copy()
        context_str = ""

    games = games.sort_values('date', ascending=False).reset_index(drop=True)
    if len(games) == 0: return []

    # ЛЧ проверка
    is_only_cup = False
    if side == 'all':
        domestic = ['Premier', 'Bundesliga', 'Ligue 1', 'Serie A', 'Primera', 'Eredivisie', 'Championship', 'Liga']
        is_only_cup = not any(any(k in l for k in domestic) for l in games['league'].unique())

    c = {'win':0, 'no_loss':0, 'loss':0, 'no_win':0, 'clean':0, 'score':0, 'tb35':0, 'tb25':0, 'tb15':0, 'tm25':0, 'win1h':0, 'c15':0, 'c25':0}
    a = {k: True for k in c}
    c_concede = 0; a_concede = True

    for _, row in games.iterrows():
        is_home = row['home_team'] == team
        gf = row['score_home'] if is_home else row['score_away']
        ga = row['score_away'] if is_home else row['score_home']
        tot = gf + ga
        hh = row['ht_home'] if is_home else row['ht_away']
        ha = row['ht_away'] if is_home else row['ht_home']

        if a['win']: (c['win'], a['win']) = (c['win']+1, True) if gf > ga else (c['win'], False)
        if a['no_loss']: (c['no_loss'], a['no_loss']) = (c['no_loss']+1, True) if gf >= ga else (c['no_loss'], False)
        if a['loss']: (c['loss'], a['loss']) = (c['loss']+1, True) if gf < ga else (c['loss'], False)
        if a['no_win']: (c['no_win'], a['no_win']) = (c['no_win']+1, True) if gf <= ga else (c['no_win'], False)
        
        if a_concede: (c_concede, a_concede) = (c_concede+1, True) if ga > 0 else (c_concede, False)
        if a['c15']: (c['c15'], a['c15']) = (c['c15']+1, True) if ga > 1 else (c['c15'], False)
        if a['c25']: (c['c25'], a['c25']) = (c['c25']+1, True) if ga > 2 else (c['c25'], False)
        
        if a['score']: (c['score'], a['score']) = (c['score']+1, True) if gf > 0 else (c['score'], False)
        if a['tb35']: (c['tb35'], a['tb35']) = (c['tb35']+1, True) if tot > 3 else (c['tb35'], False)
        if a['tb25']: (c['tb25'], a['tb25']) = (c['tb25']+1, True) if tot > 2 else (c['tb25'], False)
        if a['tb15']: (c['tb15'], a['tb15']) = (c['tb15']+1, True) if tot > 1 else (c['tb15'], False)
        if a['tm25']: (c['tm25'], a['tm25']) = (c['tm25']+1, True) if tot < 3 else (c['tm25'], False)
        if a['win1h']: (c['win1h'], a['win1h']) = (c['win1h']+1, True) if hh > ha else (c['win1h'], False)
        
        if not any(a.values()) and not a_concede: break

    trends = []
    
    # ФУНКЦИЯ ДЛЯ ДОБАВЛЕНИЯ ТРЕНДА С РЕКОМЕНДАЦИЕЙ
    def add_tr(text, type_t, rec_code):
        rec = ""
        # Логика рекомендаций (твоя исправленная)
        if rec_code == "WIN": rec = "П1" if is_home_team_in_match else "П2"
        elif rec_code == "NO_LOSS": rec = "1X" if is_home_team_in_match else "X2"
        elif rec_code == "LOSS": rec = "Победа соп. (П2)" if is_home_team_in_match else "Победа соп. (П1)"
        elif rec_code == "NO_WIN": rec = "Против (X2)" if is_home_team_in_match else "Против (1X)"
        elif rec_code == "ITM": rec = "ИТМ соп."
        elif rec_code == "ITB_OPP_15": rec = "ИТБ соп 1.5"
        elif rec_code == "ITB_OPP_25": rec = "ИТБ соп 2.5"
        elif rec_code == "ITB": rec = "ИТБ 0.5"
        elif rec_code == "TB35": rec = "ТБ 3.5"
        elif rec_code == "TB25": rec = "ТБ 2.5"
        elif rec_code == "TB15": rec = "ТБ 1.5"
        elif rec_code == "TM25": rec = "ТМ 2.5"
        elif rec_code == "WIN1H": rec = "1 тайм Победа"
        
        trends.append({"text": text, "type": type_t, "recommendation": rec})

    if c['win'] >= 3:        add_tr(fmt_trend("Выигрывает", c['win'], context_str), "good", "WIN")
    elif c['no_loss'] >= 5:  add_tr(fmt_trend("Не проигрывает", c['no_loss'], context_str), "good", "NO_LOSS")
    
    if c['loss'] >= 3:       add_tr(fmt_trend("Проигрывает", c['loss'], context_str), "bad", "LOSS")
    elif c['no_win'] >= 5:   add_tr(fmt_trend("Не может выиграть", c['no_win'], context_str), "bad", "NO_WIN")
    
    if c_concede >= 4:       add_tr(fmt_trend("Пропускает", c_concede, context_str), "bad", "")
    if c['c25'] >= 3:        add_tr(fmt_trend("Пропускает > 2.5", c['c25'], context_str), "bad", "ITB_OPP_25")
    elif c['c15'] >= 3:      add_tr(fmt_trend("Пропускает > 1.5", c['c15'], context_str), "bad", "ITB_OPP_15")
    
    if c['clean'] >= 3:      add_tr(fmt_trend("Не пропускает", c['clean'], context_str), "good", "ITM")
    if c['score'] >= 6:      add_tr(f"Забивает в {c['score']} {declension(c['score'], ['матче', 'матчах', 'матчах'])} подряд {context_str}", "good", "ITB")
    
    if c['tb35'] >= 3:       add_tr(f"ТБ 3.5 в {c['tb35']} матчах подряд {context_str}", "neutral", "TB35")
    elif c['tb25'] >= 3:     add_tr(f"ТБ 2.5 в {c['tb25']} матчах подряд {context_str}", "neutral", "TB25")
    elif c['tb15'] >= 6:     add_tr(f"ТБ 1.5 в {c['tb15']} матчах подряд {context_str}", "neutral", "TB15")
    
    if c['tm25'] >= 4:       add_tr(f"ТМ 2.5 в {c['tm25']} матчах подряд {context_str}", "neutral", "TM25")
    if c['win1h'] >= 2:      add_tr(f"Выигрывает 1-й тайм в {c['win1h']} матчах подряд {context_str}", "good", "WIN1H")

    if trends and is_only_cup:
        trends.insert(0, {"text": "ℹ️ Статистика только в ЛЧ", "type": "info", "recommendation": ""})
        
    return trends

@app.route('/api/matches')
def get_matches():
    df = load_history()
    if df.empty: return jsonify([])

    # 1. Скачиваем расписание
    headers = {'X-Auth-Token': API_KEY}
    date_from = datetime.now().strftime('%Y-%m-%d')
    date_to = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    url = f"https://api.football-data.org/v4/matches?dateFrom={date_from}&dateTo={date_to}&competitions={TARGET_LEAGUES}"
    
    result = []
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            raw_matches = resp.json().get('matches', [])
            
            for m in raw_matches:
                if m['status'] in ['FINISHED', 'AWARDED']: continue
                
                home = m['homeTeam']['name']
                away = m['awayTeam']['name']
                
                # Тренды (Общие + Дома/Выезд)
                ht_all = get_current_streaks(df, home, 'all', True)
                ht_side = get_current_streaks(df, home, 'home', True)
                
                at_all = get_current_streaks(df, away, 'all', False)
                at_side = get_current_streaks(df, away, 'away', False)
                
                if ht_all or ht_side or at_all or at_side:
                    match_data = {
                        "id": m['id'],
                        "date": m['utcDate'],
                        "status": m['status'],
                        "league": m['competition']['name'],
                        "priority": LEAGUE_PRIORITY.get(m['competition']['code'], 99),
                        "home": {
                            "name": home,
                            "logo": m['homeTeam']['crest'],
                            "trends": ht_all,
                            "trends_side": ht_side
                        },
                        "away": {
                            "name": away,
                            "logo": m['awayTeam']['crest'],
                            "trends": at_all,
                            "trends_side": at_side
                        }
                    }
                    result.append(match_data)
    except Exception as e:
        print("Error:", e)

    # Сортировка
    result.sort(key=lambda x: (x['priority'], x['date']))
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)