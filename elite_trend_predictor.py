import pandas as pd
import io

# ---------------------------------------------------------------------------
# 1. ЗАГРУЗКА ИСТОРИЧЕСКИХ ДАННЫХ (Твоя часть)
# ---------------------------------------------------------------------------
try:
    # Если файл есть, читаем его
    df = pd.read_csv("football_stats_last_2_months.csv")
except FileNotFoundError:
    # Для демонстрации (если файла нет), создадим маленький датафрейм
    # В реальной работе этот блок else можно убрать
    print("Файл не найден, использую тестовые данные для примера...")
    data = """league,date,home_team,away_team,score_home,score_away
Bundesliga,2025-11-20,Bayern Munich,Augsburg,3,0
Bundesliga,2025-11-10,St Pauli,Bayern Munich,0,1
Bundesliga,2025-11-02,Bayern Munich,Union Berlin,3,0
Champions League,2025-11-06,Bayern Munich,Benfica,1,0
Bundesliga,2025-10-27,Bochum,Bayern Munich,0,5
Champions League,2025-10-23,Barcelona,Bayern Munich,4,1
Bundesliga,2025-10-19,Bayern Munich,Stuttgart,4,0
Premier League,2025-11-23,Arsenal,Nottm Forest,3,0
Premier League,2025-11-10,Chelsea,Arsenal,1,1
Champions League,2025-11-06,Inter,Arsenal,1,0
Premier League,2025-11-02,Newcastle,Arsenal,1,0
"""
    df = pd.read_csv(io.StringIO(data))

# Предобработка
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date', ascending=False).reset_index(drop=True)

# ---------------------------------------------------------------------------
# 2. ФУНКЦИЯ АНАЛИЗА (Твоя логика, без изменений)
# ---------------------------------------------------------------------------
def get_current_streaks(team):
    games = df[(df['home_team'] == team) | (df['away_team'] == team)].copy()
    games = games.sort_values('date', ascending=False).reset_index(drop=True)
    
    if len(games) == 0:
        return []

    cnt_wins = 0
    cnt_no_loss = 0
    cnt_clean_sheet = 0
    cnt_over25 = 0
    cnt_total_loss = 0

    alive_win = True
    alive_no_loss = True
    alive_clean_sheet = True
    alive_over25 = True
    alive_loss = True

    for _, row in games.iterrows():
        if not (alive_win or alive_no_loss or alive_clean_sheet or alive_over25 or alive_loss):
            break
            
        is_home = row['home_team'] == team
        team_goals = row['score_home'] if is_home else row['score_away']
        opp_goals  = row['score_away'] if is_home else row['score_home']
        total_goals = row['score_home'] + row['score_away']
        
        # 1. Победы
        if alive_win:
            if team_goals > opp_goals: cnt_wins += 1
            else: alive_win = False
        
        # 2. Без поражений
        if alive_no_loss:
            if team_goals >= opp_goals: cnt_no_loss += 1
            else: alive_no_loss = False
        
        # 3. Сухая серия
        if alive_clean_sheet:
            if opp_goals == 0: cnt_clean_sheet += 1
            else: alive_clean_sheet = False
                
        # 4. ТБ 2.5
        if alive_over25:
            if total_goals > 2: cnt_over25 += 1
            else: alive_over25 = False

        # 5. Поражения
        if alive_loss:
            if team_goals < opp_goals: cnt_total_loss += 1
            else: alive_loss = False

    trends = []
    # Пороги (можно менять)
    if cnt_wins >= 3:        trends.append(f"Выигрывает {cnt_wins} матчей подряд")
    elif cnt_no_loss >= 4:   trends.append(f"Не проигрывает {cnt_no_loss} матчей подряд")
    
    if cnt_total_loss >= 3:  trends.append(f"Проигрывает {cnt_total_loss} матчей подряд")
    if cnt_clean_sheet >= 3: trends.append(f"Не пропускает {cnt_clean_sheet} матчей подряд")
    if cnt_over25 >= 3:      trends.append(f"ТБ 2.5 в {cnt_over25} последних матчах") # Снизил порог до 3 для теста

    return trends

# ---------------------------------------------------------------------------
# 3. СОХРАНЯЕМ ВСЕ ТРЕНДЫ В ПАМЯТЬ
# ---------------------------------------------------------------------------
# Создаем словарь: { "Название команды": ["тренд 1", "тренд 2"] }
team_trends_db = {}
all_teams = pd.concat([df['home_team'], df['away_team']]).unique()

for team in all_teams:
    trends = get_current_streaks(team)
    if trends:
        team_trends_db[team] = trends

# ---------------------------------------------------------------------------
# 4. СПИСОК БУДУЩИХ МАТЧЕЙ (ВВОД РАСПИСАНИЯ)
# ---------------------------------------------------------------------------
# Здесь ты вручную вбиваешь матчи на завтра/сегодня.
# В будущем этот список можно подгружать через pd.read_csv("fixtures_tomorrow.csv")
upcoming_matches = [
    {"home": "Bayern Munich", "away": "Paris SG", "league": "Champions League"},
    {"home": "Barcelona", "away": "Brest", "league": "Champions League"},
    {"home": "Man City", "away": "Feyenoord", "league": "Champions League"},
    {"home": "Inter", "away": "RB Leipzig", "league": "Champions League"},
    {"home": "Arsenal", "away": "Man United", "league": "Premier League"}, # Пример вымышленного матча
]

print("="*80)
print(f"ПРОГНОЗЫ НА ПРЕДСТОЯЩИЕ МАТЧИ ({len(upcoming_matches)} игр)")
print("="*80)

found_predictions = 0

for match in upcoming_matches:
    home = match['home']
    away = match['away']
    league = match['league']
    
    # Проверяем, есть ли тренды у Домашней или Гостевой команды
    home_has_trends = home in team_trends_db
    away_has_trends = away in team_trends_db
    
    if home_has_trends or away_has_trends:
        print(f"\n⚽ Матч: {home} - {away} ({league})")
        found_predictions += 1
        
        # Вывод для хозяев
        if home_has_trends:
            print(f"   🏠 {home} (Тренды):")
            for t in team_trends_db[home]:
                # Добавляем "ставку" на основе текста тренда
                prediction = ""
                if "Выигрывает" in t: prediction = "П1"
                elif "Не проигрывает" in t: prediction = "1X"
                elif "Проигрывает" in t: prediction = "Против (X2 или П2)"
                elif "Не пропускает" in t: prediction = "ИТМ2 0.5 (Сухая победа)"
                elif "ТБ 2.5" in t: prediction = "Тотал Больше 2.5"
                
                print(f"      🔸 {t} -> Рекомендуем: {prediction}")
                
        # Вывод для гостей
        if away_has_trends:
            print(f"   ✈️  {away} (Тренды):")
            for t in team_trends_db[away]:
                prediction = ""
                if "Выигрывает" in t: prediction = "П2"
                elif "Не проигрывает" in t: prediction = "X2"
                elif "Проигрывает" in t: prediction = "Против (1X или П1)"
                elif "Не пропускает" in t: prediction = "ИТМ1 0.5"
                elif "ТБ 2.5" in t: prediction = "Тотал Больше 2.5"

                print(f"      🔸 {t} -> Рекомендуем: {prediction}")
    else:
        # Если трендов нет, можно пропустить или написать, что матч без явных серий
        # print(f"Матч {home}-{away}: Явных статистических серий нет.")
        pass

if found_predictions == 0:
    print("\nНа указанные матчи активных серий (трендов) не найдено.")