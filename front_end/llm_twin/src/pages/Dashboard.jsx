import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { getUser, clearAuth, authHeaders } from '../auth'
import styles from './Dashboard.module.css'

const Icons = {
  messages: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
    </svg>
  ),
  sessions: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
    </svg>
  ),
  user: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>
    </svg>
  ),
  bot: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/>
    </svg>
  ),
  chat: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
    </svg>
  ),
  logout: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
    </svg>
  ),
}

function StatCard({ icon, label, value, color }) {
  return (
    <div className={`${styles.statCard} glass`}>
      <div className={styles.statIcon} style={{ background: color }}>{icon}</div>
      <div>
        <p className={styles.statValue}>{value}</p>
        <p className={styles.statLabel}>{label}</p>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const nav = useNavigate()
  const user = getUser()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/dashboard/stats', { headers: authHeaders() })
      .then(r => { if (r.status === 401) { clearAuth(); nav('/login') } return r.json() })
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [nav])

  const logout = () => { clearAuth(); nav('/login') }

  return (
    <div className={styles.page}>
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarLogo}>
          <div className={styles.logoIcon}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/>
            </svg>
          </div>
          <span className={styles.logoText}>LLM Twin</span>
        </div>

        <nav className={styles.nav}>
          <div className={`${styles.navItem} ${styles.navActive}`}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/>
              <rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>
            </svg>
            Dashboard
          </div>
          <Link to="/chat" className={styles.navItem}>
            {Icons.chat}
            Chat
          </Link>
        </nav>

        <div className={styles.sidebarBottom}>
          <div className={styles.userInfo}>
            <div className={styles.userAvatar}>{user?.username?.[0]?.toUpperCase()}</div>
            <div>
              <p className={styles.userName}>{user?.username}</p>
              <p className={styles.userEmail}>{user?.email}</p>
            </div>
          </div>
          <button className={styles.logoutBtn} onClick={logout}>{Icons.logout}</button>
        </div>
      </aside>

      {/* Main content */}
      <main className={styles.main}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.pageTitle}>Dashboard</h1>
            <p className={styles.pageSub}>Welcome back, <span className={styles.accent}>{user?.username}</span></p>
          </div>
          <Link to="/chat" className="btn-primary">{Icons.chat} Start chatting</Link>
        </header>

        {loading ? (
          <div className={styles.loadingGrid}>
            {[1,2,3,4].map(i => <div key={i} className={`${styles.skeletonCard} glass`} />)}
          </div>
        ) : (
          <>
            <div className={styles.statsGrid}>
              <StatCard icon={Icons.messages} label="Total messages" value={stats?.total_messages ?? 0} color="rgba(124,58,237,.25)" />
              <StatCard icon={Icons.sessions} label="Chat sessions"  value={stats?.total_sessions ?? 0} color="rgba(16,185,129,.2)" />
              <StatCard icon={Icons.user}     label="Your messages"  value={stats?.user_messages ?? 0}  color="rgba(59,130,246,.2)" />
              <StatCard icon={Icons.bot}      label="AI responses"   value={stats?.ai_messages ?? 0}    color="rgba(236,72,153,.2)" />
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>Recent conversations</h2>
                <span className={styles.memberSince}>Member since {stats?.member_since}</span>
              </div>

              {stats?.recent_messages?.length === 0 ? (
                <div className={`${styles.emptyState} glass`}>
                  <p>No conversations yet. <Link to="/chat" className={styles.accentLink}>Start your first chat →</Link></p>
                </div>
              ) : (
                <div className={styles.messageList}>
                  {stats?.recent_messages?.map((m, i) => (
                    <div key={i} className={`${styles.messageRow} glass`}>
                      <span className={`${styles.roleBadge} ${m.role === 'user' ? styles.userBadge : styles.aiBadge}`}>
                        {m.role === 'user' ? 'You' : 'AI'}
                      </span>
                      <p className={styles.messageContent}>{m.content.slice(0, 120)}{m.content.length > 120 ? '…' : ''}</p>
                      <span className={styles.messageTime}>
                        {new Date(m.created_at).toLocaleDateString([], { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' })}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}
