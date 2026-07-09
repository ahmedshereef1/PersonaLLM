import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import styles from './ChatWindow.module.css'

const EmptyState = () => (
  <div className={styles.empty}>
    <div className={styles.emptyIcon}>
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
      </svg>
    </div>
    <h2>Ask your LLM Twin</h2>
    <p>Start a conversation — your AI twin will answer using your own knowledge base.</p>
    <div className={styles.suggestions}>
      {['Who are you?', 'What are your skills?', 'Tell me about your projects'].map(s => (
        <div key={s} className={styles.suggestionChip}>{s}</div>
      ))}
    </div>
  </div>
)

const TypingIndicator = () => (
  <div className={styles.typing}>
    <span /><span /><span />
  </div>
)

export default function ChatWindow({ messages, loading, historyLoading, onSend }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // The last message is streaming if it's an assistant bubble with empty content
  const lastMsg = messages[messages.length - 1]
  const isStreaming = lastMsg?.role === 'assistant' && lastMsg?.content === '' && !loading

  return (
    <main className={styles.window}>
      <header className={styles.header}>
        <div className={styles.headerTitle}>
          <div className={styles.onlineDot} />
          LLM Twin Chat
        </div>
        <span className={styles.headerSub}>RAG-powered • SageMaker inference</span>
      </header>

      <div className={styles.messages}>
        {historyLoading ? (
          <div className={styles.loadingHistory}>Loading history…</div>
        ) : messages.length === 0 ? (
          <EmptyState />
        ) : (
          messages.map((m) => <MessageBubble key={m.id} message={m} />)
        )}
        {/* Show dots only while waiting for the first token */}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={onSend} disabled={loading || isStreaming} />
    </main>
  )
}

