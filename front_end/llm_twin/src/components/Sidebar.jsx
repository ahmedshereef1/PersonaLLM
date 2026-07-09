import styles from './Sidebar.module.css'

const BotIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="11" width="18" height="10" rx="2"/>
    <circle cx="12" cy="5" r="2"/>
    <path d="M12 7v4"/>
    <line x1="8" y1="16" x2="8" y2="16"/>
    <line x1="16" y1="16" x2="16" y2="16"/>
  </svg>
)

const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <line x1="12" y1="5" x2="12" y2="19"/>
    <line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
)

const TrashIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
    <path d="M10 11v6M14 11v6"/>
    <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
  </svg>
)

export default function Sidebar({ onNewChat, onClear, sessionId }) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <div className={styles.logoIcon}><BotIcon /></div>
        <span className={styles.logoText}>LLM Twin</span>
      </div>

      <button className={styles.newChat} onClick={onNewChat}>
        <PlusIcon />
        New chat
      </button>

      <div className={styles.section}>
        <span className={styles.sectionLabel}>Current session</span>
        <div className={styles.sessionId}>{sessionId.slice(0, 8)}…</div>
      </div>

      <div className={styles.spacer} />

      <button className={styles.clearBtn} onClick={onClear} title="Clear history for this session">
        <TrashIcon />
        Clear history
      </button>

      <div className={styles.footer}>
        <span>Powered by SageMaker + RAG</span>
      </div>
    </aside>
  )
}
