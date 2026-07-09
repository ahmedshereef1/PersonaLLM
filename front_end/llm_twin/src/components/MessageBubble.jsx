import ReactMarkdown from 'react-markdown'
import styles from './MessageBubble.module.css'

const BotAvatar = () => (
  <div className={styles.avatar}>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="11" width="18" height="10" rx="2"/>
      <circle cx="12" cy="5" r="2"/>
      <path d="M12 7v4"/>
    </svg>
  </div>
)

const UserAvatar = () => (
  <div className={`${styles.avatar} ${styles.userAvatar}`}>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  </div>
)

function formatTime(isoString) {
  if (!isoString) return ''
  return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isEmpty = !message.content

  return (
    <div className={`${styles.row} ${isUser ? styles.userRow : ''}`}>
      {!isUser && <BotAvatar />}
      <div className={`${styles.bubble} ${isUser ? styles.userBubble : styles.aiBubble}`}>
        {isEmpty ? (
          <span className={styles.cursor} />
        ) : isUser ? (
          <p className={styles.content}>{message.content}</p>
        ) : (
          <div className={styles.markdown}>
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
        {message.created_at && (
          <span className={styles.time}>{formatTime(message.created_at)}</span>
        )}
      </div>
      {isUser && <UserAvatar />}
    </div>
  )
}

