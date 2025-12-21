import pandas as pd
import requests
import os
import time
from datetime import datetime, timedelta, timezone

# ==============================================================================
# НАСТРОЙКИ
# ==============================================================================

# 🔴 ВСТАВЬ СЮДА СВОЙ КЛЮЧ
API_KEY = '0da5c9f2e19a455faca817cd5699b78f' 

TARGET_LEAGUES = 'PL,BL1,SA,PD,FL1,CL,PPL,DED,ELC'

LEAGUE_PRIORITY = {
    'CL': 1, 'PL': 2, 'BL1': 3, 'PD': 4, 'SA': 5, 
    'FL1': 6, 'PPL': 7, 'DED': 8, 'ELC': 9
}

CACHE_FILE = "football_history_cache.csv"

# ==============================================================================
# 0. ЦВЕТА И ФОРМАТИРОВАНИЕ
# ==============================================================================
class Col:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    GREY = '\033[90m'

def declension(n, forms):
    if n % 100 in [11, 12, 13, 14]: return forms[2]
    if n % 10 == 1: return forms[0]
    if n % 10 in [2, 3, 4]: return forms[1]
    return forms[2]

def fmt_trend(text, count):
    word = declension(count, ['матч', 'матча', 'матчей'])
    return f"{text} {count} {word} подряд"

# ==============================================================================
# 1. ЗАГРУЗКА ИСТОРИИ
# ==============================================================================
def load_history():
    print(f"1. Проверяю базу данных...")
    if os.path.exists(CACHE_FILE):
        if (time.time() - os.path.getmtime(CACHE_FILE)) < 12 * 3600:
            print(f"   {Col.GREEN}✅ Кэш актуален. Загружаю...{Col.END}")
            return pd.read_csv(CACHE_FILE)
    
    print(f"   {Col.CYAN}🔄 Обновляю статистику через API...{Col.END}")
    headers = {'X-Auth-Token': API_KEY}
    leagues_list = TARGET_LEAGUES.split(',')
    all_matches = []

    for league_code in leagues_list:
        url = f"https://api.football-data.org/v4/competitions/{league_code}/matches?status=FINISHED"
        try:
            print(f"      ⏳ Лига {league_code}...", end=" ")
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                matches = resp.json().get('matches', [])
                print(f"OK ({len(matches)})")
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
            else:
                print(f"{Col.FAIL}Err {resp.status_code}{Col.END}")
        except: print(f"{Col.FAIL}Err Connect{Col.END}")

    df = pd.DataFrame(all_matches)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date', ascending=False).reset_index(drop=True)
        df.to_csv(CACHE_FILE, index=False)
        return df
    return pd.DataFrame() if not os.path.exists(CACHE_FILE) else pd.read_csv(CACHE_FILE)

# ==============================================================================
# 2. АЛГОРИТМ АНАЛИЗА
# ==============================================================================
def get_current_streaks(df, team, side='all'):
    if side == 'home':
        games = df[df['home_team'] == team].copy()
    elif side == 'away':
        games = df[df['away_team'] == team].copy()
    else:
        games = df[(df['home_team'] == team) | (df['away_team'] == team)].copy()

    games = games.sort_values('date', ascending=False).reset_index(drop=True)
    if len(games) == 0: return []

    is_only_cup = False
    if side == 'all':
        played_leagues = games['league'].unique()
        domestic = ['Premier', 'Bundesliga', 'Ligue 1', 'Serie A', 'Primera', 'Eredivisie', 'Championship', 'Liga']
        is_only_cup = not any(any(k in l for k in domestic) for l in played_leagues)

    # Счетчики
    c_win, c_no_loss, c_loss, c_no_win = 0, 0, 0, 0
    c_score, c_concede = 0, 0
    c_concede_15, c_concede_25 = 0, 0
    c_tb15, c_tb25, c_tm25, c_tb35 = 0, 0, 0, 0
    c_win_1h = 0

    # Флаги
    a_win, a_no_loss, a_loss, a_no_win = True, True, True, True
    a_score, a_concede = True, True
    a_concede_15, a_concede_25 = True, True
    a_tb15, a_tb25, a_tm25, a_tb35 = True, True, True, True
    a_win_1h = True

    for _, row in games.iterrows():
        is_home = row['home_team'] == team
        gf = row['score_home'] if is_home else row['score_away']
        ga = row['score_away'] if is_home else row['score_home']
        tot = gf + ga
        hh = row['ht_home'] if is_home else row['ht_away']
        ha = row['ht_away'] if is_home else row['ht_home']

        if a_win: (c_win, a_win) = (c_win+1, True) if gf > ga else (c_win, False)
        if a_no_loss: (c_no_loss, a_no_loss) = (c_no_loss+1, True) if gf >= ga else (c_no_loss, False)
        if a_loss: (c_loss, a_loss) = (c_loss+1, True) if gf < ga else (c_loss, False)
        if a_no_win: (c_no_win, a_no_win) = (c_no_win+1, True) if gf <= ga else (c_no_win, False)

        if a_score: (c_score, a_score) = (c_score+1, True) if gf > 0 else (c_score, False)
        if a_concede: (c_concede, a_concede) = (c_concede+1, True) if ga > 0 else (c_concede, False)
        
        if a_concede_15: (c_concede_15, a_concede_15) = (c_concede_15+1, True) if ga > 1 else (c_concede_15, False)
        if a_concede_25: (c_concede_25, a_concede_25) = (c_concede_25+1, True) if ga > 2 else (c_concede_25, False)

        if a_tb15: (c_tb15, a_tb15) = (c_tb15+1, True) if tot > 1 else (c_tb15, False)
        if a_tb25: (c_tb25, a_tb25) = (c_tb25+1, True) if tot > 2 else (c_tb25, False)
        if a_tb35: (c_tb35, a_tb35) = (c_tb35+1, True) if tot > 3 else (c_tb35, False)
        if a_tm25: (c_tm25, a_tm25) = (c_tm25+1, True) if tot < 3 else (c_tm25, False)
        
        if a_win_1h: (c_win_1h, a_win_1h) = (c_win_1h+1, True) if hh > ha else (c_win_1h, False)

        if not any([a_win, a_no_loss, a_loss, a_no_win, a_concede, a_score, a_tb25]): break

    trends = []

    # Исходы
    if c_win >= 3:       trends.append({"text": fmt_trend("Выигрывает", c_win), "type": "good"})
    elif c_no_loss >= 5: trends.append({"text": fmt_trend("Не проигрывает", c_no_loss), "type": "good"})
    
    if c_loss >= 3:      trends.append({"text": fmt_trend("Проигрывает", c_loss), "type": "bad"})
    elif c_no_win >= 5:  trends.append({"text": fmt_trend("Не может выиграть", c_no_win), "type": "bad"})
    
    # Оборона
    if c_concede >= 4:
         trends.append({"text": fmt_trend("Пропускает", c_concede), "type": "bad"})

    if c_concede >= 5:
        if c_concede_25 >= 3:
            trends.append({"text": fmt_trend("Пропускает > 2.5", c_concede_25), "type": "bad"})
        elif c_concede_15 >= 3:
            trends.append({"text": fmt_trend("Пропускает > 1.5", c_concede_15), "type": "bad"})
    
    if c_score >= 6: trends.append({"text": f"Забивает в {c_score} {declension(c_score, ['матче', 'матчах', 'матчах'])} подряд", "type": "good"})
    
    # Тоталы
    if c_tb35 >= 3:     trends.append({"text": f"ТБ 3.5 в {c_tb35} играх подряд", "type": "neutral"})
    elif c_tb25 >= 3:   trends.append({"text": f"ТБ 2.5 в {c_tb25} играх подряд", "type": "neutral"})
    elif c_tb15 >= 6:   trends.append({"text": f"ТБ 1.5 в {c_tb15} играх подряд", "type": "neutral"})
    
    if c_tm25 >= 4:     trends.append({"text": f"ТМ 2.5 в {c_tm25} играх подряд", "type": "neutral"})
    if c_win_1h >= 2:   trends.append({"text": f"Выигрывает 1-й тайм в {c_win_1h} играх подряд", "type": "good"})

    if trends and is_only_cup:
        trends.insert(0, {"text": "ℹ️ Статистика только в ЛЧ", "type": "info"})

    return trends

# ==============================================================================
# 3. ПОЛУЧЕНИЕ РАСПИСАНИЯ
# ==============================================================================
def get_upcoming_matches():
    print("2. Скачиваю расписание (на 48ч)...")
    headers = {'X-Auth-Token': API_KEY}
    date_from = datetime.now().strftime('%Y-%m-%d')
    date_to = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    url = f"https://api.football-data.org/v4/matches?dateFrom={date_from}&dateTo={date_to}&competitions={TARGET_LEAGUES}"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('matches', [])
        return []
    except: return []

# ==============================================================================
# 4. ГЛАВНЫЙ БЛОК
# ==============================================================================
df_history = load_history()
if df_history.empty: exit()

print("3. Анализ трендов...")

upcoming = get_upcoming_matches()
future_matches = []
for m in upcoming:
    if m['status'] in ['FINISHED', 'AWARDED']: continue
    future_matches.append(m)

future_matches.sort(key=lambda x: (LEAGUE_PRIORITY.get(x['competition']['code'], 99), x['utcDate']))

print("\n" + "="*80)
print(f"{Col.BOLD}🚀 ПРОГНОЗЫ НА ПРЕДСТОЯЩИЕ МАТЧИ ({len(future_matches)} игр){Col.END}")
print("="*80)

found_any = False
current_league = ""

for match in future_matches:
    home_team = match['homeTeam']['name']
    away_team = match['awayTeam']['name']
    league_name = match['competition']['name']
    status = match['status']
    
    if league_name != current_league:
        print(f"\n{Col.HEADER}📌 {league_name.upper()}{Col.END}")
        print("-" * 40)
        current_league = league_name
    
    # Считаем тренды
    ht_all = get_current_streaks(df_history, home_team, side='all')
    ht_home = get_current_streaks(df_history, home_team, side='home')
    at_all = get_current_streaks(df_history, away_team, side='all')
    at_away = get_current_streaks(df_history, away_team, side='away')

    if ht_all or ht_home or at_all or at_away:
        found_any = True
        
        match_time_utc = datetime.strptime(match['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
        msk_time = (match_time_utc + timedelta(hours=3)).strftime('%H:%M')
        match_date = (match_time_utc + timedelta(hours=3)).strftime('%d.%m')
        
        live_tag = f"{Col.FAIL} 🔴 (LIVE){Col.END}" if status in ['IN_PLAY', 'PAUSED'] else ""
        print(f"⚽ {match_date} в {msk_time}{live_tag} | {Col.BOLD}{home_team} - {away_team}{Col.END}")
        
        def print_team_trends(team_name, trends_all, trends_context, icon, is_home):
            print(f"   {icon} {team_name}:")
            
            def print_list(trends_list):
                for item in trends_list:
                    t_text = item['text']
                    t_type = item['type']
                    
                    if t_type == 'good': colored_text = f"{Col.GREEN}{t_text}{Col.END}"
                    elif t_type == 'bad': colored_text = f"{Col.FAIL}{t_text}{Col.END}"
                    elif t_type == 'info': colored_text = f"{Col.CYAN}{t_text}{Col.END}"
                    else: colored_text = t_text

                    rec = ""
                    # --- ИСПРАВЛЕННАЯ ЛОГИКА СТАВОК ---
                    if "Статистика только" in t_text: pass
                    
                    elif "Не проигрывает" in t_text:
                        rec = "👉 1X" if is_home else "👉 X2"
                    
                    elif "Выигрывает" in t_text and "тайм" not in t_text:
                        rec = "👉 П1" if is_home else "👉 П2"
                    
                    # !!! ВАЖНОЕ ИЗМЕНЕНИЕ ЗДЕСЬ !!!
                    elif "Проигрывает" in t_text: 
                        # Если проигрывает серию - ставим на ЧИСТУЮ победу соперника
                        rec = "👉 Победа соперника (П2)" if is_home else "👉 Победа соперника (П1)"
                    
                    elif "Не может выиграть" in t_text:
                        # Если не может выиграть (ничьи/лузы) - ставим осторожно (Двойной шанс)
                        rec = "👉 Против (X2)" if is_home else "👉 Против (1X)"

                    elif "Пропускает > 1.5" in t_text: rec = "👉 ИТБ соп. 1.5"
                    elif "Пропускает > 2.5" in t_text: rec = "👉 ИТБ соп. 2.5"
                    elif "Не пропускает" in t_text:    rec = "👉 ИТМ соперника"
                    elif "Пропускает" in t_text:       rec = "👉 Гол соперника"

                    elif "ТБ 3.5" in t_text:           rec = "👉 ТБ 3.5"
                    elif "ТБ 2.5" in t_text:           rec = "👉 ТБ 2.5"
                    elif "ТБ 1.5" in t_text:           rec = "👉 ТБ 1.5"
                    elif "ТМ 2.5" in t_text:           rec = "👉 ТМ 2.5"
                    
                    elif "Забивает" in t_text:         rec = "👉 ИТБ 0.5"
                    elif "1-й тайм" in t_text:         rec = "👉 Победа в 1 тайме"
                    
                    rec_str = f"   {Col.BLUE}{rec}{Col.END}" if rec else ""
                    print(f"      🔹 {colored_text}{rec_str}")

            if trends_all:
                print(f"      {Col.GREY}🌍 Общая статистика:{Col.END}")
                print_list(trends_all)
            
            if trends_context:
                context_name = "🏠 Дома" if is_home else "✈️ В гостях"
                print(f"      {Col.GREY}{context_name}:{Col.END}")
                print_list(trends_context)

        if ht_all or ht_home:
            print_team_trends(home_team, ht_all, ht_home, "🏠", True)
        if at_all or at_away:
            print_team_trends(away_team, at_all, at_away, "✈️ ", False)
            
        print("")

if not found_any: print("\nАктивных серий не найдено.")
print("\n" + "="*80)