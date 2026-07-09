import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { v4 as uuidv4 } from 'uuid'
import ReactMarkdown from 'react-markdown'
import { getUser, clearAuth, authHeaders } from '../auth'
import styles from './Chat.module.css'

const SESSION_KEY = 'llm_twin_session_id'

function getOrCreateSession() {
  let id = localStorage.getItem(SESSION_KEY)
  if (!id) { id = uuidv4(); localStorage.setItem(SESSION_KEY, id) }
  return id
}

// ── Icons ──────────────────────────────────────────────────────────────────
const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
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
const SendIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
)
const BotIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/>
    <path d="M12 7v4"/>
  </svg>
)
const UserIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>
  </svg>
)
const GridIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/>
    <rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>
  </svg>
)
const LogoutIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
    <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
  </svg>
)

// ── Message bubble ──────────────────────────────────────────────────────────
function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isEmpty = !message.content
  return (
    <div className={`${styles.msgRow} ${isUser ? styles.userRow : ''}`}>
      <div className={`${styles.avatar} ${isUser ? styles.avatarUser : styles.avatarBot}`}>
        {isUser ? <UserIcon /> : <BotIcon />}
      </div>
      <div className={`${styles.bubble} ${isUser ? styles.bubbleUser : styles.bubbleBot}`}>
        {isEmpty
          ? <span className={styles.cursor} />
          : isUser
            ? <p className={styles.plainText}>{message.content}</p>
            : <div className={styles.markdown}><ReactMarkdown>{message.content}</ReactMarkdown></div>
        }
        {message.created_at && (
          <span className={styles.time}>
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
    </div>
  )
}

// ── Chat input ──────────────────────────────────────────────────────────────
function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('')
  const ref = useRef(null)

  const submit = () => {
    const text = value.trim()
    if (!text || disabled) return
    setValue('')
    ref.current.style.height = 'auto'
    onSend(text)
  }

  return (
    <div className={styles.inputArea}>
      <div className={`${styles.inputBox} ${disabled ? styles.inputDisabled : ''}`}>
        <textarea
          ref={ref}
          className={styles.textarea}
          placeholder="Ask your LLM Twin anything…"
          value={value}
          rows={1}
          disabled={disabled}
          onChange={e => {
            setValue(e.target.value)
            e.target.style.height = 'auto'
            e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
          }}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
        />
        <button className={styles.sendBtn} onClick={submit} disabled={disabled || !value.trim()}>
          <SendIcon />
        </button>
      </div>
      <p className={styles.hint}>Enter to send · Shift+Enter for new line</p>
    </div>
  )
}

// ── Main Chat page ──────────────────────────────────────────────────────────
export default function Chat() {
  const nav = useNavigate()
  const user = getUser()
  const [sessionId, setSessionId] = useState(getOrCreateSession)
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [histLoading, setHistLoading] = useState(true)
  const bottomRef = useRef(null)

  useEffect(() => {
    setHistLoading(true)
    fetch(`/chat/history?session_id=${sessionId}`, { headers: authHeaders() })
      .then(r => { if (r.status === 401) { clearAuth(); nav('/login') } return r.json() })
      .then(d => setMessages((d.messages || []).map((m, i) => ({ id: i, ...m }))))
      .catch(() => setMessages([]))
      .finally(() => setHistLoading(false))
  }, [sessionId, nav])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = useCallback(async (text) => {
    const aiId = Date.now() + 1
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', content: text }])
    setLoading(true)

    try {
      const res = await fetch('/rag/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ query: text, session_id: sessionId }),
      })
      if (res.status === 401) { clearAuth(); nav('/login'); return }
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail ?? `HTTP ${res.status}`) }

      setMessages(prev => [...prev, { id: aiId, role: 'assistant', content: '' }])
      setLoading(false)

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const lines = buf.split('\n\n')
        buf = lines.pop()
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const chunk = line.slice(6)
          if (chunk === '[DONE]') break
          if (chunk.startsWith('[ERROR]')) {
            setMessages(prev => prev.map(m => m.id === aiId ? { ...m, content: chunk.slice(8) } : m))
            break
          }
          setMessages(prev => prev.map(m => m.id === aiId ? { ...m, content: m.content + chunk } : m))
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      setMessages(prev => {
        const errMsg = { id: aiId, role: 'assistant', content: `Error: ${err.message}` }
        return prev.some(m => m.id === aiId)
          ? prev.map(m => m.id === aiId ? errMsg : m)
          : [...prev, errMsg]
      })
    } finally {
      setLoading(false)
    }
  }, [sessionId, nav])

  const newChat = () => {
    const id = uuidv4()
    localStorage.setItem(SESSION_KEY, id)
    setSessionId(id)
  }

  const clearHistory = async () => {
    try {
      await fetch(`/chat/history?session_id=${sessionId}`, { method: 'DELETE', headers: authHeaders() })
      setMessages([])
    } catch {}
  }

  const logout = () => { clearAuth(); nav('/login') }

  const isStreaming = messages[messages.length - 1]?.role === 'assistant'
    && messages[messages.length - 1]?.content === '' && !loading

  return (
    <div className={styles.layout}>
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarTop}>
          <div className={styles.logo}>
            <div className={styles.logoIcon}><BotIcon /></div>
            <span className={styles.logoText}>LLM Twin</span>
          </div>

          <button className={styles.newChatBtn} onClick={newChat}>
            <PlusIcon /> New chat
          </button>

          <div className={styles.navSection}>
            <Link to="/dashboard" className={styles.navItem}><GridIcon /> Dashboard</Link>
            <div className={`${styles.navItem} ${styles.navActive}`}><BotIcon /> Chat</div>
          </div>

          <div className={styles.sessionBox}>
            <p className={styles.sessionLabel}>Session</p>
            <p className={styles.sessionId}>{sessionId.slice(0, 8)}…</p>
          </div>
        </div>

        <div className={styles.sidebarBottom}>
          <div className={styles.userRow}>
            <div className={styles.userAvatar}>{user?.username?.[0]?.toUpperCase()}</div>
            <div className={styles.userInfo}>
              <p className={styles.userName}>{user?.username}</p>
              <p className={styles.userEmail}>{user?.email}</p>
            </div>
          </div>
          <div className={styles.sidebarActions}>
            <button className={styles.iconBtn} onClick={clearHistory} title="Clear history"><TrashIcon /></button>
            <button className={styles.iconBtn} onClick={logout} title="Log out"><LogoutIcon /></button>
          </div>
        </div>
      </aside>

      {/* Chat area */}
      <main className={styles.chatArea}>
        <header className={styles.chatHeader}>
          <div className={styles.chatHeaderLeft}>
            <div className={styles.onlineDot} />
            <span className={styles.chatTitle}>LLM Twin</span>
          </div>
          <span className={styles.chatSub}>RAG-powered · SageMaker inference</span>
        </header>

        <div className={styles.messages}>
          {histLoading ? (
            <div className={styles.centerMsg}>Loading history…</div>
          ) : messages.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}><BotIcon /></div>
              <h2 className={styles.emptyTitle}>Ask your LLM Twin</h2>
              <p className={styles.emptySub}>Your AI twin answers using your personal knowledge base via RAG.</p>
              <div className={styles.chips}>
                {['Who are you?', 'What are your skills?', 'Tell me about your projects'].map(s => (
                  <button key={s} className={styles.chip} onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            </div>
          ) : (
            messages.map(m => <MessageBubble key={m.id} message={m} />)
          )}

          {/* Dots shown only while waiting for first token */}
          {loading && (
            <div className={styles.typingRow}>
              <div className={styles.avatarBot}><BotIcon /></div>
              <div className={styles.typingDots}>
                <span /><span /><span />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <ChatInput onSend={send} disabled={loading || isStreaming} />
      </main>
    </div>
  )
}
