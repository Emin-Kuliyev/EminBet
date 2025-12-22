import React, { useEffect, useState } from 'react';
import axios from 'axios';
import MatchCard from './MatchCard';
import './App.css';

const translations = {
  ru: {
    title: "EminBet",
    predictions: "Прогнозы",
    leagues: "Чемпионаты",
    refresh: "Обновить",
    loading: "Загрузка...",
    noData: "Матчей не найдено",
    byLeague: "По Лигам",
    byTime: "По Времени",
    history: "История",
    home: "Дома",
    away: "В гостях",
    noHistory: "Нет данных",
    login: "Вход",
    register: "Регистрация",
    username: "Имя пользователя",
    password: "Пароль",
    submit: "Продолжить",
    logout: "Выйти",
    back: "Назад",
    profile: "Профиль",
    guest: "Гость",
    regSuccess: "Регистрация успешна! Теперь войдите.",
    loginTitle: "Авторизация",
    settings: "Настройки профиля",
    save: "Сохранить",
    newUsername: "Новое имя",
    newPassword: "Новый пароль",
    avatar: "Аватар",
    authRequired: "Войдите, чтобы добавлять в избранное!"
  },
  en: {
    title: "EminBet",
    predictions: "Predictions",
    leagues: "Leagues",
    refresh: "Refresh",
    loading: "Loading...",
    noData: "No matches found",
    byLeague: "By League",
    byTime: "By Time",
    history: "History",
    home: "Home",
    away: "Away",
    noHistory: "No data",
    login: "Login",
    register: "Register",
    username: "Username",
    password: "Password",
    submit: "Continue",
    logout: "Logout",
    back: "Back",
    profile: "Profile",
    guest: "Guest",
    regSuccess: "Registered! Please login.",
    loginTitle: "Authorization",
    settings: "Profile Settings",
    save: "Save",
    newUsername: "New Username",
    newPassword: "New Password",
    avatar: "Avatar",
    authRequired: "Login to use favorites!"
  }
};

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(localStorage.getItem('user'));
  const [avatar, setAvatar] = useState(localStorage.getItem('avatar') || ''); 
  const [theme, setTheme] = useState('dark');
  const [lang, setLang] = useState('ru');
  
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedLeague, setExpandedLeague] = useState(null);
  const [sortMode, setSortMode] = useState('league');

  // FAVORITES
  const [favLeagues, setFavLeagues] = useState([]);
  const [favTeams, setFavTeams] = useState([]);

  const [historyStack, setHistoryStack] = useState([]); 
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  const t = translations[lang];

  useEffect(() => {
    document.body.className = theme === 'light' ? 'light-mode' : '';
  }, [theme]);

  useEffect(() => { fetchData(); }, []);

  // Синхронизация при загрузке (если есть токен)
  useEffect(() => {
      if(token) {
          const storedFavL = JSON.parse(localStorage.getItem('favLeagues') || '[]');
          const storedFavT = JSON.parse(localStorage.getItem('favTeams') || '[]');
          setFavLeagues(storedFavL);
          setFavTeams(storedFavT);
      } else {
          setFavLeagues([]);
          setFavTeams([]);
      }
  }, [token]);

  // --- FAVORITES LOGIC (SERVER SYNC) ---
  const syncFav = async (type, id) => {
      try {
          await axios.post('http://127.0.0.1:5000/api/favorites', {
              username: user, type, id
          });
      } catch(e) { console.error(e); }
  }

  const toggleFavLeague = (leagueName, e) => {
      e.stopPropagation();
      if (!token) return alert(t.authRequired);
      
      let newFavs;
      if(favLeagues.includes(leagueName)) newFavs = favLeagues.filter(l => l !== leagueName);
      else newFavs = [...favLeagues, leagueName];
      
      setFavLeagues(newFavs);
      localStorage.setItem('favLeagues', JSON.stringify(newFavs));
      syncFav('league', leagueName);
  };

  const toggleFavTeam = (teamId) => {
      if (!token) return alert(t.authRequired);
      
      let newFavs;
      if(favTeams.includes(teamId)) newFavs = favTeams.filter(id => id !== teamId);
      else newFavs = [...favTeams, teamId];
      
      setFavTeams(newFavs);
      localStorage.setItem('favTeams', JSON.stringify(newFavs));
      syncFav('team', teamId);
  }

  // --- AUTH ---
  const handleAuth = async (isLogin, username, password) => {
    const endpoint = isLogin ? '/api/login' : '/api/register';
    try {
      const res = await axios.post(`http://127.0.0.1:5000${endpoint}`, { username, password });
      if (res.data.token) {
        setToken(res.data.token);
        setUser(res.data.username);
        setAvatar(res.data.avatar || '');
        
        if (res.data.favLeagues) {
            setFavLeagues(res.data.favLeagues);
            localStorage.setItem('favLeagues', JSON.stringify(res.data.favLeagues));
        }
        if (res.data.favTeams) {
            setFavTeams(res.data.favTeams);
            localStorage.setItem('favTeams', JSON.stringify(res.data.favTeams));
        }

        localStorage.setItem('token', res.data.token);
        localStorage.setItem('user', res.data.username);
        localStorage.setItem('avatar', res.data.avatar || '');
        setShowAuthModal(false);
      } else if (!isLogin) {
        alert(t.regSuccess);
      }
    } catch (e) { alert("Error: " + (e.response?.data?.error || "Auth failed")); }
  };

  const logout = () => {
    if (window.confirm("Выйти?")) {
        setToken(null); setUser(null); setAvatar('');
        setFavLeagues([]); setFavTeams([]);
        localStorage.removeItem('token'); 
        localStorage.removeItem('user'); 
        localStorage.removeItem('avatar');
        localStorage.removeItem('favLeagues'); 
        localStorage.removeItem('favTeams');
    }
  };

  const handleUpdateProfile = async (newUsername, newPassword, newAvatar) => {
      try {
          const res = await axios.put('http://127.0.0.1:5000/api/update_profile', {
              oldUsername: user, newUsername, newPassword, newAvatar
          });
          setUser(res.data.username);
          setAvatar(res.data.avatar);
          localStorage.setItem('user', res.data.username);
          localStorage.setItem('avatar', res.data.avatar);
          setShowSettingsModal(false);
          alert("Профиль обновлен!");
      } catch (e) { alert("Ошибка: " + e.response?.data?.error); }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const ts = new Date().getTime();
      const response = await axios.get(`http://127.0.0.1:5000/api/matches?t=${ts}`);
      setMatches(response.data);
    } catch (error) { console.error(error); }
    setLoading(false);
  };

  const pushTeamToHistory = async (teamId, teamName) => {
    setLoadingHistory(true);
    try {
      const res = await axios.get(`http://127.0.0.1:5000/api/team/${teamId}/history`);
      setHistoryStack(prev => [...prev, { name: teamName, matches: res.data }]);
    } catch (e) { console.error(e); }
    setLoadingHistory(false);
  };

  const popHistory = () => setHistoryStack(prev => prev.slice(0, -1));
  const closeModal = () => setHistoryStack([]);

  // --- SORTING ---
  const sortedMatches = [...matches];
  if (sortMode === 'time') sortedMatches.sort((a, b) => new Date(a.utcDate) - new Date(b.utcDate));

  const groupedMatches = matches.reduce((acc, m) => {
    const l = m.league; if (!acc[l]) acc[l] = []; acc[l].push(m); return acc;
  }, {});

  // Сортировка ЛИГ (Избранные -> Вверх)
  const sortedLeagueKeys = Object.keys(groupedMatches).sort((a, b) => {
      const aFav = favLeagues.includes(a);
      const bFav = favLeagues.includes(b);
      if (aFav && !bFav) return -1;
      if (!aFav && bFav) return 1;
      return 0;
  });

  const displayGroups = {};
  if (sortMode === 'league') {
      sortedLeagueKeys.forEach(league => {
          // Сортировка МАТЧЕЙ (Избранные команды -> Вверх)
          const leagueMatches = groupedMatches[league].sort((a, b) => {
              const aHasFav = favTeams.includes(a.home.id) || favTeams.includes(a.away.id);
              const bHasFav = favTeams.includes(b.home.id) || favTeams.includes(b.away.id);
              if (aHasFav && !bHasFav) return -1;
              if (!aHasFav && bHasFav) return 1;
              return 0;
          });
          displayGroups[league] = leagueMatches;
      });
  } else {
      displayGroups["All"] = sortedMatches;
  }

  const currentModalData = historyStack.length > 0 ? historyStack[historyStack.length - 1] : null;

  return (
    <div className={`app-wrapper ${theme}`}>
      <aside className="sidebar">
        <div className="logo-area"><h2>🏆 {t.title}</h2></div>
        <div className="settings-row">
           <button onClick={() => setTheme(theme==='dark'?'light':'dark')}>{theme==='dark'?'☀️':'🌙'}</button>
           <button onClick={() => setLang(lang==='ru'?'en':'ru')}>{lang.toUpperCase()}</button>
        </div>
        <nav className="league-nav">
          <div className="nav-title">{t.leagues}</div>
          {sortedLeagueKeys.map(league => {
             const isFav = favLeagues.includes(league);
             
             // --- ПРОВЕРКА ДЛЯ БЕЛОГО ФОНА В МЕНЮ ---
             const flagUrl = groupedMatches[league][0].league_flag;
             const isCL = league.includes('Champions') || (flagUrl && flagUrl.includes('Champions'));

             return (
                <div key={league} className="nav-group">
                  <button className={`nav-item ${expandedLeague === league ? 'active' : ''}`} onClick={() => setExpandedLeague(expandedLeague === league ? null : league)}>
                    <div className="nav-left">
                        <button className={`fav-btn-sidebar ${isFav ? 'active' : ''}`} onClick={(e) => toggleFavLeague(league, e)}>
                            {isFav ? '★' : '☆'}
                        </button>
                        {flagUrl && <img src={flagUrl} className={`nav-flag ${isCL ? 'white-bg' : ''}`} alt="" />}
                        <span>{league}</span>
                    </div>
                    <span className="count-badge">{groupedMatches[league].length}</span>
                  </button>
                  {expandedLeague === league && (
                    <div className="nav-submenu">
                      {groupedMatches[league].map(m => (
                        <button key={m.id} className="nav-subitem" onClick={() => {
                            const el = document.getElementById(`match-${m.id}`);
                            if(el) el.scrollIntoView({behavior: 'smooth', block: 'center'});
                        }}>
                          {m.home.name} - {m.away.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
             );
          })}
        </nav>
      </aside>

      <main className="main-content">
        <header className="header">
          <div className="header-controls">
            <h1 className="page-title">{t.predictions}</h1>
            <div className="sort-controls">
                <button className={`sort-btn ${sortMode === 'league' ? 'active' : ''}`} onClick={() => setSortMode('league')}>{t.byLeague}</button>
                <button className={`sort-btn ${sortMode === 'time' ? 'active' : ''}`} onClick={() => setSortMode('time')}>{t.byTime}</button>
            </div>
          </div>
          <div className="header-right">
             <button className="refresh-btn" onClick={fetchData}>🔄</button>
             <div className="profile-widget" onClick={token ? () => setShowSettingsModal(true) : () => setShowAuthModal(true)}>
                <div className="avatar-circle">
                    {avatar ? avatar : (
                        <svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                    )}
                </div>
                <span className="profile-name">{token ? user : t.login}</span>
             </div>
          </div>
        </header>

        <div className="content-container">
          {loading ? <div className="loading"><div className="spinner"></div>{t.loading}</div> : 
           matches.length === 0 ? <div className="no-data">{t.noData}</div> : 
           Object.keys(displayGroups).map(groupName => (
              <div key={groupName} className="league-section">
                {sortMode === 'league' && (
                    <div className="league-header-wrapper">
                        {(() => {
                            // --- ПРОВЕРКА ДЛЯ БЕЛОГО ФОНА В ЗАГОЛОВКЕ ---
                            const flagUrl = displayGroups[groupName][0].league_flag;
                            const isCL = groupName.includes('Champions') || (flagUrl && flagUrl.includes('Champions'));
                            
                            return flagUrl && <img src={flagUrl} className={`league-flag ${isCL ? 'white-bg' : ''}`} alt="" />;
                        })()}
                        <h3 className="league-header">{groupName}</h3>
                        {favLeagues.includes(groupName) && <span style={{color:'var(--gold)', fontSize:'1.2rem', marginLeft:'auto'}}>★</span>}
                    </div>
                )}
                <div className="matches-grid">
                  {displayGroups[groupName].map(match => (
                    <MatchCard 
                        key={match.id} 
                        match={match} 
                        onTeamClick={pushTeamToHistory} 
                        lang={lang} 
                        favTeams={favTeams}
                        onToggleFav={toggleFavTeam}
                    />
                  ))}
                </div>
              </div>
            ))
          }
        </div>
      </main>

      {/* MODALS */}
      {currentModalData && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content history-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div className="mh-left">
                  {historyStack.length > 1 && <button className="back-btn" onClick={popHistory}>⬅ {t.back}</button>}
                  <h3>{t.history}: <span className="highlight">{currentModalData.name}</span></h3>
              </div>
              <button className="close-btn" onClick={closeModal}>×</button>
            </div>
            <div className="modal-body">
              {loadingHistory ? <div className="loading"><div className="spinner"></div></div> : 
               currentModalData.matches.length === 0 ? <p className="no-hist">{t.noHistory}</p> : (
                <div className="history-list">
                  {currentModalData.matches.map((h, idx) => {
                    // --- ПРОВЕРКА ДЛЯ БЕЛОГО ФОНА В ИСТОРИИ ---
                    const isCL = h.competition.includes('Champions');
                    return (
                        <div key={idx} className={`history-item result-${h.result}`}>
                        <div className="h-left">
                            <span className="h-date">{h.date.slice(5)}</span>
                            <div className="h-league-row">
                                {h.league_flag && <img src={h.league_flag} className={`h-mini-flag ${isCL ? 'white-bg' : ''}`} alt="" />}
                            </div>
                        </div>
                        <div className="h-mid">
                            <div className="h-opp-row clickable" onClick={() => pushTeamToHistory(h.opponent_id, h.opponent)}>
                                <img src={h.opponent_logo} alt="" className="h-opp-logo"/>
                                <span className="h-opp-name">{h.opponent}</span>
                            </div>
                            <span className="h-side">{h.is_home ? `(${t.home})` : `(${t.away})`}</span>
                        </div>
                        <div className="h-score">{h.score}</div>
                        </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {showAuthModal && (
          <div className="modal-overlay" onClick={() => setShowAuthModal(false)}>
             <div className="modal-content auth-modal" onClick={e => e.stopPropagation()}>
                 <AuthForm onAuth={handleAuth} t={t} />
             </div>
          </div>
      )}

      {showSettingsModal && (
          <div className="modal-overlay" onClick={() => setShowSettingsModal(false)}>
             <div className="modal-content auth-modal" onClick={e => e.stopPropagation()}>
                 <SettingsForm 
                    t={t} currentAvatar={avatar} currentUser={user}
                    onUpdate={handleUpdateProfile} 
                    onLogout={() => {logout(); setShowSettingsModal(false);}}
                 />
             </div>
          </div>
      )}
    </div>
  );
}

function AuthForm({ onAuth, t }) {
    const [isLogin, setIsLogin] = useState(true);
    const [u, setU] = useState('');
    const [p, setP] = useState('');
    return (
        <div className="auth-box-internal">
            <div className="auth-header-internal"><h2>{t.loginTitle}</h2></div>
            <div className="auth-tabs">
                <button className={isLogin?'active':''} onClick={()=>setIsLogin(true)}>{t.login}</button>
                <button className={!isLogin?'active':''} onClick={()=>setIsLogin(false)}>{t.register}</button>
            </div>
            <div className="auth-inputs">
                <label>{t.username}</label>
                <input value={u} onChange={e=>setU(e.target.value)} />
                <label>{t.password}</label>
                <input type="password" value={p} onChange={e=>setP(e.target.value)} />
            </div>
            <button className="submit-btn" onClick={()=>onAuth(isLogin, u, p)}>{t.submit}</button>
        </div>
    );
}

function SettingsForm({ t, currentAvatar, currentUser, onUpdate, onLogout }) {
    const [u, setU] = useState(currentUser);
    const [p, setP] = useState('');
    const [av, setAv] = useState(currentAvatar);
    const avatars = ['⚽', '🦁', '🐻', '🦅', '🦈', '🚀', '🔥', '👑', '😎', '💀', '👽', '🤖'];

    return (
        <div className="auth-box-internal">
            <div className="auth-header-internal"><h2>{t.settings}</h2></div>
            <div className="avatar-selector">
                {avatars.map(a => (<button key={a} className={av===a ? 'selected' : ''} onClick={() => setAv(a)}>{a}</button>))}
            </div>
            <div className="auth-inputs">
                <label>{t.username}</label>
                <input value={u} onChange={e=>setU(e.target.value)} />
                <label>{t.newPassword} (optional)</label>
                <input type="password" value={p} onChange={e=>setP(e.target.value)} />
            </div>
            <button className="submit-btn" onClick={() => onUpdate(u, p, av)}>{t.save}</button>
            <button className="logout-full-btn" onClick={onLogout}>{t.logout}</button>
        </div>
    );
}

export default App;