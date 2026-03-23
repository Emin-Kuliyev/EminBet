import React, { useState } from 'react';

const translations = {
    ru: {
        win_streak: (n) => `Выигрывает ${n} ${declension(n, ['матч', 'матча', 'матчей'])} подряд`,
        no_loss_streak: (n) => `Не проигрывает ${n} ${declension(n, ['матч', 'матча', 'матчей'])} подряд`,
        loss_streak: (n) => `Проигрывает ${n} ${declension(n, ['матч', 'матча', 'матчей'])} подряд`,
        no_win_streak: (n) => `Не побеждает ${n} ${declension(n, ['матч', 'матча', 'матчей'])} подряд`,
        score_streak: (n) => `Забивает в ${n} ${declension(n, ['матче', 'матчах', 'матчах'])} подряд`,
        concede_streak: (n) => `Пропускает в ${n} ${declension(n, ['матче', 'матчах', 'матчах'])} подряд`,
        tb25_streak: (n) => `ТБ 2.5 в ${n} ${declension(n, ['матче', 'матчах', 'матчах'])} подряд`,
        
        win_1h_streak: (n) => `Выигрывает 1-й тайм в ${n} играх подряд`,
        no_loss_1h_streak: (n) => `Не проигрывает 1-й тайм в ${n} играх подряд`,
        score_1h_streak: (n) => `Гол в 1-м тайме в ${n} играх подряд`,
        score_2h_streak: (n) => `Гол во 2-м тайме в ${n} играх подряд`,

        win_100: "Победа (100% форма)",
        win_1h_100: "Победа в 1-м тайме (100%)",
        no_loss_100: "Не проиграет (1X/X2)",
        score_100: "Забьет гол (100%)",
        score_2h_100: "Гол во 2-м тайме (100%)",
        tb15_100: "ТБ 1.5 (100%)",
        
        no_pred: "",
        show_stat: "📊 Статистика ▼",
        hide_stat: "Скрыть ▲",
        home: "Дома",
        away: "В гостях"
    },
    en: {
        win_streak: (n) => `Wins ${n} matches in a row`,
        no_loss_streak: (n) => `No loss in ${n} matches in a row`,
        loss_streak: (n) => `Loses ${n} matches in a row`,
        no_win_streak: (n) => `No wins in ${n} matches in a row`,
        score_streak: (n) => `Scores in ${n} matches in a row`,
        concede_streak: (n) => `Concedes in ${n} matches in a row`,
        tb25_streak: (n) => `Over 2.5 goals in ${n} matches in a row`,
        
        win_1h_streak: (n) => `Wins 1st Half in ${n} matches in a row`,
        no_loss_1h_streak: (n) => `No loss 1st Half in ${n} matches in a row`,
        score_1h_streak: (n) => `Goal 1st Half in ${n} matches in a row`,
        score_2h_streak: (n) => `Goal 2nd Half in ${n} matches in a row`,

        win_100: "Win (100% form)",
        win_1h_100: "Win 1st Half (100%)",
        no_loss_100: "No loss (1X/X2)",
        score_100: "Will score (100%)",
        score_2h_100: "Score 2nd Half (100%)",
        tb15_100: "Over 1.5 (100%)",
        no_pred: "",
        show_stat: "📊 Stats ▼",
        hide_stat: "Hide ▲",
        home: "Home",
        away: "Away"
    }
};

const declension = (n, forms) => {
    if (n % 100 > 10 && n % 100 < 15) return forms[2];
    if (n % 10 === 1) return forms[0];
    if (n % 10 > 1 && n % 10 < 5) return forms[1];
    return forms[2];
};

const MatchCard = ({ match, onTeamClick, lang, favTeams, onToggleFav, openLeagueModal }) => {
  const [showStats, setShowStats] = useState(false);
  const t = translations[lang];

  const dateObj = new Date(match.utcDate);
  const timeStr = dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  const dateStr = dateObj.toLocaleDateString([], {day: 'numeric', month: 'numeric'});
  const isLive = match.status === 'IN_PLAY' || match.status === 'PAUSED';

  const getTrendText = (trendObj) => {
      const func = t[trendObj.code];
      if (typeof func === 'function') return func(trendObj.count);
      return "";
  };
  const getPredText = (code) => t[code] || "";

  const renderForm = (form) => {
      if(!form || form.length === 0) return null;
      return (
          <div className="form-row">
              {form.map((res, i) => (
                  <span key={i} className={`form-badge f-${res} ${i===0?'latest':''}`} title={i===0?'Последний матч':''}>{res}</span>
              ))}
          </div>
      );
  };

  // ЗАЩИТА ОТ ОШИБКИ: (favTeams || [])
  const StarBtn = ({ id }) => (
      <button 
        className={`fav-btn-card ${(favTeams || []).includes(id) ? 'active' : ''}`} 
        onClick={(e) => {e.stopPropagation(); onToggleFav(id);}}
      >
        {(favTeams || []).includes(id) ? '★' : '☆'}
      </button>
  );

  const isCL = (match.league || "").includes('Champions') || ((match.league_flag || "").includes('Champions'));

  return (
    <div id={`match-${match.id}`} className="match-card">
      <div className="card-header">
        <div className="league-info">
            {match.league_flag && 
                <img 
                    src={match.league_flag} 
                    className={`card-flag ${isCL ? 'white-bg' : ''}`} 
                    alt="" 
                    onClick={() => openLeagueModal(match.league_code, match.league)}
                    style={{cursor: 'pointer'}}
                />
            }
            <span 
                className="league-label" 
                onClick={() => openLeagueModal(match.league_code, match.league)}
                style={{cursor: 'pointer'}}
            >
                {match.league}
            </span>
        </div>
        <div className="match-time">
            <span>{dateStr}</span> 
            <span className="time-val">{timeStr}</span>
            {isLive && <span className="live-indicator">🔴 LIVE</span>}
        </div>
      </div>

      <div className="teams-grid">
        {/* HOME */}
        <div className="team-column home-col">
          <div className="team-identity home clickable" onClick={() => onTeamClick(match.home.id, match.home.name)}>
             <StarBtn id={match.home.id} />
             <div className="logo-wrapper">
                <img src={match.home.logo} alt={match.home.name} />
             </div>
             <div className="name-form-box">
                <span className="team-name">
                    {match.home.name}
                    {match.home.is_top && <span className="top-badge">TOP</span>}
                </span>
                {renderForm(match.home.form)}
             </div>
          </div>
          <div className="prediction-box home">
             {match.home.prediction ? <div className="pred-item good">🎯 {getPredText(match.home.prediction)}</div> : <div className="pred-item neutral">{t.no_pred}</div>}
          </div>
        </div>

        <div className="vs-column">VS</div>

        {/* AWAY */}
        <div className="team-column away-col">
          <div className="team-identity away clickable" onClick={() => onTeamClick(match.away.id, match.away.name)}>
             <div className="name-form-box end">
                <span className="team-name">
                    {match.away.name}
                    {match.away.is_top && <span className="top-badge">TOP</span>}
                </span>
                {renderForm(match.away.form)}
             </div>
             <div className="logo-wrapper">
                <img src={match.away.logo} alt={match.away.name} />
             </div>
             <StarBtn id={match.away.id} />
          </div>
          <div className="prediction-box away">
             {match.away.prediction ? <div className="pred-item good">🎯 {getPredText(match.away.prediction)}</div> : <div className="pred-item neutral">{t.no_pred}</div>}
          </div>
        </div>
      </div>

      <div className="stats-toggle-row">
          <button className="stats-btn" onClick={() => setShowStats(!showStats)}>
              {showStats ? t.hide_stat : t.show_stat}
          </button>
      </div>

      {showStats && (
          <div className="stats-wrapper">
              
              {/* H2H */}
              {match.h2h && match.h2h.length > 0 && (
                  <div className="h2h-section">
                      <div className="h2h-title">H2H (Last 5)</div>
                      <div className="h2h-list">
                          {match.h2h.map((h, i) => (
                              <div key={i} className="h2h-item">
                                  <span className="h2h-date">{h.date}</span>
                                  <span className="h2h-teams">{h.home} - {h.away}</span>
                                  <span className="h2h-score">{h.score}</span>
                              </div>
                          ))}
                      </div>
                  </div>
              )}

              {/* GOALSCORERS */}
              {match.goals_info && match.goals_info.length > 0 && (
                   <div className="h2h-section">
                      <div className="h2h-title">Голы</div>
                      <div className="h2h-list">
                          {match.goals_info.map((g, i) => (
                              <div key={i} className="h2h-item" style={{color:'#fff'}}>{g}</div>
                          ))}
                      </div>
                   </div>
              )}

              <div className="stats-dropdown">
                  <div className="stats-col">
                      {match.home.trends_all?.length > 0 && (
                          <div className="trends-group">
                              {match.home.trends_all.map((t, i) => <div key={i} className="stat-item">🔹 {getTrendText(t)}</div>)}
                          </div>
                      )}
                      {match.home.trends_context?.length > 0 && (
                          <div className="trends-group context">
                              <div className="context-label">{t.home}:</div>
                              {match.home.trends_context.map((t, i) => <div key={i} className="stat-item context-item">🔸 {getTrendText(t)}</div>)}
                          </div>
                      )}
                      {(!match.home.trends_all?.length && !match.home.trends_context?.length) && <div className="stat-empty">-</div>}
                  </div>

                  <div className="stats-col right">
                      {match.away.trends_all?.length > 0 && (
                          <div className="trends-group">
                              {match.away.trends_all.map((t, i) => <div key={i} className="stat-item">🔹 {getTrendText(t)}</div>)}
                          </div>
                      )}
                      {match.away.trends_context?.length > 0 && (
                          <div className="trends-group context">
                              <div className="context-label">{t.away}:</div>
                              {match.away.trends_context.map((t, i) => <div key={i} className="stat-item context-item">🔸 {getTrendText(t)}</div>)}
                          </div>
                      )}
                      {(!match.away.trends_all?.length && !match.away.trends_context?.length) && <div className="stat-empty">-</div>}
                  </div>
              </div>
          </div>
      )}
    </div>
  );
};

export default MatchCard;