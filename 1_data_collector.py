import pandas as pd
import requests
from datetime import datetime
import io

urls = {
    "Premier League": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "Bundesliga": "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
    "La Liga": "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    "Serie A": "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
    "Ligue 1": "https://www.football-data.co.uk/mmz4281/2526/F1.csv"
}

all_data = []
cutoff = datetime(2025, 9, 25)

print("Скачиваем полную базу сезона 2025/26 (сентябрь–ноябрь 2025)...")

for league, url in urls.items():
    print(f"  → {league}", end="")
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        content = r.content.decode('utf-8-sig')
        df = pd.read_csv(io.StringIO(content))
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df[df['Date'] >= cutoff]
        df = df.dropna(subset=['FTHG', 'FTAG'])  # Завершённые

        added = 0
        for _, row in df.iterrows():
            all_data.append({
                "league": league,
                "date": row['Date'].strftime("%Y-%m-%d"),
                "home_team": row['HomeTeam'],
                "away_team": row['AwayTeam'],
                "score_home": int(row['FTHG']),
                "score_away": int(row['FTAG']),
                "events": [],
                "stats": {
                    "corners_home": int(row['HC']) if 'HC' in row and pd.notna(row['HC']) else 0,
                    "corners_away": int(row['AC']) if 'AC' in row and pd.notna(row['AC']) else 0,
                    "yellow_home": int(row['HY']) if 'HY' in row and pd.notna(row['HY']) else 0,
                    "yellow_away": int(row['AY']) if 'AY' in row and pd.notna(row['AY']) else 0,
                    "red_home": int(row['HR']) if 'HR' in row and pd.notna(row['HR']) else 0,
                    "red_away": int(row['AR']) if 'AR' in row and pd.notna(row['AR']) else 0
                }
            })
            added += 1
        print(f"  → {added} матчей")
    except Exception as e:
        print(f"  → ошибка: {e}")

final_df = pd.DataFrame(all_data)
final_df.to_csv("football_stats_last_2_months.csv", index=False, encoding='utf-8')

print(f"\nГОТОВО! Скачано {len(all_data)} матчей (сентябрь–ноябрь 2025)")
print("Запускай: python elite_trend_predictor.py")