import { useState, useRef, useEffect } from 'react'
import './App.css'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId] = useState(`session-${Date.now()}`)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    
    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      // Use relative URL for Docker compatibility, fallback to localhost for development
      const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://localhost:8001' 
        : `http://${window.location.hostname}:8001`
      
      const response = await fetch(`${baseUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      // Add assistant response with debug info
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.response,
        tools_used: data.tools_used || [],
        debug: data.debug,
        interaction_id: data.interaction_id,
        session_id: data.session_id,
        feedback: null
      }])
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, { 
        role: 'error', 
        content: `Error: ${error.message}. Make sure the MCP client is running on port 8001.`
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const submitFeedback = async (interactionId, sessionId, feedback, messageIndex) => {
    try {
      const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://localhost:8001' 
        : `http://${window.location.hostname}:8001`
        
      const response = await fetch(`${baseUrl}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          interaction_id: interactionId,
          session_id: sessionId,
          feedback: feedback
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      // Update the message with feedback status
      setMessages(prev => prev.map((msg, idx) => 
        idx === messageIndex ? { ...msg, feedback: feedback } : msg
      ))
      
      console.log(data.message)
    } catch (error) {
      console.error('Feedback error:', error)
      alert(`Failed to submit feedback: ${error.message}`)
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>🤖 MCP Chat</h1>
          <p>Model Context Protocol - Network Tools Assistant</p>
        </div>
        {messages.length > 0 && (
          <button onClick={clearChat} className="clear-btn">
            Clear Chat
          </button>
        )}
      </header>

      <div className="chat-container">
        {messages.length === 0 && (
          <div className="welcome">
            <h2>Welcome to MCP Chat!</h2>
            <p>Ask me about:</p>
            <ul>
              <li>🕐 Current time (via NTP servers)</li>
              <li>🏓 Network connectivity (ping hosts)</li>
              <li>💬 General questions</li>
            </ul>
            <p className="hint">Try: "What time is it?" or "Can you ping google.com?"</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-header">
              <span className="message-role">
                {msg.role === 'user' ? '👤 You' : msg.role === 'error' ? '⚠️ Error' : '🤖 Assistant'}
              </span>
              {msg.tools_used && msg.tools_used.length > 0 && (
                <span className="tools-badge">
                  🔧 {msg.tools_used.join(', ')}
                </span>
              )}
              {msg.role === 'assistant' && msg.interaction_id && (
                <div className="feedback-buttons">
                  <button 
                    className={`feedback-btn ${msg.feedback === 'thumbs_up' ? 'active' : ''}`}
                    onClick={() => submitFeedback(msg.interaction_id, msg.session_id, 'thumbs_up', idx)}
                    title="Good response - keep this forever"
                  >
                    👍
                  </button>
                  <button 
                    className={`feedback-btn ${msg.feedback === 'thumbs_down' ? 'active' : ''}`}
                    onClick={() => submitFeedback(msg.interaction_id, msg.session_id, 'thumbs_down', idx)}
                    title="Bad response - remove from cache"
                  >
                    👎
                  </button>
                </div>
              )}
            </div>
            <div className="message-content">
              {msg.content}
            </div>
            
            {msg.debug && (
              <details className="debug-details">
                <summary>🔍 View Details</summary>
                <div className="debug-content">
                  <div className="debug-section">
                    <strong>Routing:</strong> {msg.debug.routing}
                  </div>
                  
                  <div className="debug-section">
                    <strong>Model:</strong> {msg.debug.model || 'N/A'}
                  </div>
                  
                  {msg.debug.routing === 'direct_shortcut' && (
                    <div className="debug-section" style={{backgroundColor: '#2a4a2a', padding: '10px', borderRadius: '5px', marginBottom: '10px'}}>
                      <strong>⚡ Direct Shortcut Explanation:</strong>
                      <p style={{margin: '5px 0', fontSize: '14px'}}>
                        This message was handled by a <strong>direct shortcut</strong> without using the LLM. 
                        The client detected specific keywords in your message and immediately routed it to the appropriate tool.
                        This is faster than LLM processing but only works for common, predictable patterns.
                      </p>
                    </div>
                  )}
                  
                  {msg.debug.prompt && (
                    <div className="debug-section">
                      <strong>📝 Full Prompt Sent to LLM:</strong>
                      <pre>{msg.debug.prompt}</pre>
                    </div>
                  )}
                  
                  {msg.debug.initial_prompt && (
                    <div className="debug-section">
                      <strong>📝 Initial Prompt (Tool Detection):</strong>
                      <pre>{msg.debug.initial_prompt}</pre>
                    </div>
                  )}
                  
                  {msg.debug.initial_llm_response && (
                    <div className="debug-section">
                      <strong>🤖 Initial LLM Response:</strong>
                      <pre>{msg.debug.initial_llm_response}</pre>
                    </div>
                  )}
                  
                  {msg.debug.pattern_matched && (
                    <div className="debug-section">
                      <strong>🎯 Pattern Matched:</strong>
                      <pre>{msg.debug.pattern_matched}</pre>
                    </div>
                  )}
                  
                  {msg.debug.keywords_detected && (
                    <div className="debug-section">
                      <strong>🔍 Keywords Detected:</strong>
                      <pre>{JSON.stringify(msg.debug.keywords_detected, null, 2)}</pre>
                    </div>
                  )}
                  
                  {msg.debug.extracted_params && (
                    <div className="debug-section">
                      <strong>⚙️ Extracted Parameters:</strong>
                      <pre>{JSON.stringify(msg.debug.extracted_params, null, 2)}</pre>
                    </div>
                  )}
                  
                  {msg.debug.tool_arguments && (
                    <div className="debug-section">
                      <strong>📦 Tool Arguments:</strong>
                      <pre>{JSON.stringify(msg.debug.tool_arguments, null, 2)}</pre>
                    </div>
                  )}
                  
                  {msg.debug.tool_results && (
                    <div className="debug-section">
                      <strong>🔧 Tool Results:</strong>
                      <pre>{JSON.stringify(msg.debug.tool_results, null, 2)}</pre>
                    </div>
                  )}
                  
                  {msg.debug.final_prompt && (
                    <div className="debug-section">
                      <strong>📝 Final Prompt (With Tool Results):</strong>
                      <pre>{msg.debug.final_prompt}</pre>
                    </div>
                  )}
                  
                  {msg.debug.final_llm_response && (
                    <div className="debug-section">
                      <strong>🤖 Final LLM Response:</strong>
                      <pre>{msg.debug.final_llm_response}</pre>
                    </div>
                  )}
                  
                  {msg.debug.llm_response && !msg.debug.initial_llm_response && (
                    <div className="debug-section">
                      <strong>🤖 LLM Response:</strong>
                      <pre>{msg.debug.llm_response}</pre>
                    </div>
                  )}
                </div>
              </details>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="message assistant loading">
            <div className="message-header">
              <span className="message-role">🤖 Assistant</span>
            </div>
            <div className="message-content">
              <span className="loading-dots">Thinking</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={sendMessage} className="input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me anything..."
          className="message-input"
          disabled={isLoading}
          autoFocus
        />
        <button 
          type="submit" 
          disabled={isLoading || !input.trim()}
          className="send-btn"
        >
          {isLoading ? '⏳' : '📤'}
        </button>
      </form>
    </div>
  )
}

export default App

