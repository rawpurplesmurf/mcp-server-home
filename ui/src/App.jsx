import { useState, useRef, useEffect } from 'react'
import './App.css'
import { WavEncoder } from './wavEncoder'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId] = useState(`session-${Date.now()}`)
  const [clientUrl, setClientUrl] = useState(null)
  const messagesEndRef = useRef(null)
  
  // Audio recording state
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const audioContextRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const processorRef = useRef(null)
  const audioChunksRef = useRef([])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Fetch client URL configuration on mount
  useEffect(() => {
    const fetchConfig = async () => {
      // Determine the correct client URL based on environment
      const getClientUrl = () => {
        const hostname = window.location.hostname
        
        // Local development
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
          return 'http://localhost:8001'
        }
        
        // Kubernetes deployment - replace mcp-ui with mcp-client
        if (hostname.includes('mcp-ui')) {
          return `http://${hostname.replace('mcp-ui', 'mcp-client')}`
        }
        
        // Default fallback - assume client is on same host, port 8001
        return `http://${hostname}:8001`
      }
      
      const fallbackUrl = getClientUrl()
      
      try {
        // Try to fetch config from the backend
        const response = await fetch(`${fallbackUrl}/config`)
        if (response.ok) {
          const config = await response.json()
          setClientUrl(config.client_url)
          return
        }
      } catch (error) {
        console.warn('Failed to fetch config from backend, using fallback URL:', error)
      }
      
      // Use fallback if config fetch fails
      setClientUrl(fallbackUrl)
    }
    fetchConfig()
  }, [])

  const sendMessage = async (e, transcribedText = null) => {
    if (e) e.preventDefault()
    
    // Use transcribed text if provided, otherwise use input field
    const messageText = transcribedText || input.trim()
    if (!messageText || isLoading || !clientUrl) return

    const userMessage = messageText
    if (!transcribedText) {
      setInput('')
    }
    
    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      const response = await fetch(`${clientUrl}/chat`, {
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
    if (!clientUrl) return
    
    try {
      const response = await fetch(`${clientUrl}/feedback`, {
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

  const startRecording = async () => {
    try {
      // Create AudioContext with 16kHz sample rate for Wyoming
      const AudioContext = window.AudioContext || window.webkitAudioContext
      const audioContext = new AudioContext({ sampleRate: 16000 })
      audioContextRef.current = audioContext

      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true
        }
      })
      mediaStreamRef.current = stream

      const source = audioContext.createMediaStreamSource(stream)
      
      // Use ScriptProcessorNode to capture raw PCM data
      const bufferSize = 4096
      const processor = audioContext.createScriptProcessor(bufferSize, 1, 1)
      processorRef.current = processor

      audioChunksRef.current = []

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0)
        // Copy the Float32Array data
        const chunk = new Float32Array(inputData)
        audioChunksRef.current.push(chunk)
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      setIsRecording(true)
    } catch (error) {
      console.error('Error accessing microphone:', error)
      alert('Failed to access microphone. Please check permissions.')
    }
  }

  const stopRecording = async () => {
    if (!isRecording) return

    // Stop audio processing
    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }

    if (audioContextRef.current) {
      await audioContextRef.current.close()
      audioContextRef.current = null
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop())
      mediaStreamRef.current = null
    }

    setIsRecording(false)

    // Combine all audio chunks
    const totalLength = audioChunksRef.current.reduce((acc, chunk) => acc + chunk.length, 0)
    const combined = new Float32Array(totalLength)
    let offset = 0
    for (const chunk of audioChunksRef.current) {
      combined.set(chunk, offset)
      offset += chunk.length
    }

    // Encode to WAV
    const encoder = new WavEncoder(16000, 1, 16)
    const wavBlob = encoder.encodeWAV(combined)

    // Send to transcription
    await transcribeAudio(wavBlob, 'wav')
  }

  const transcribeAudio = async (audioBlob, extension = 'webm') => {
    if (!clientUrl) return
    
    setIsTranscribing(true)
    
    try {
      // Create form data with audio file
      const formData = new FormData()
      formData.append('file', audioBlob, `audio.${extension}`)
      
      const response = await fetch(`${clientUrl}/transcribe`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      // Set the transcribed text and auto-send
      if (data.text && data.text.trim()) {
        const transcribedText = data.text
        setInput(transcribedText)
        
        // Auto-send the transcribed text
        setIsTranscribing(false)
        await sendMessage(null, transcribedText)
      } else {
        // Show warning if provided, otherwise generic message
        const message = data.warning || 'No speech detected. Please speak clearly and try recording again.'
        alert(message)
        setIsTranscribing(false)
      }
    } catch (error) {
      console.error('Transcription error:', error)
      alert(`Transcription failed: ${error.message}. Make sure the Whisper service is running.`)
      setIsTranscribing(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>🤖 MCP Chat</h1>
          <p>Model Context Protocol - Network Tools & Voice Assistant</p>
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
            <p className="hint">Start typing or use the 🎤 button to speak your message!</p>
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
          disabled={isLoading || isRecording || isTranscribing}
          autoFocus
        />
        <button 
          type="button"
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isLoading || isTranscribing}
          className={`record-btn ${isRecording ? 'recording' : ''}`}
          title={isRecording ? 'Stop recording' : 'Start voice input'}
        >
          {isTranscribing ? '⏳' : isRecording ? '⏹️' : '🎤'}
        </button>
      </form>
    </div>
  )
}

export default App

