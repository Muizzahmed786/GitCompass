import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from '../lib/api';

export default function AIChatDrawer({ isOpen, onClose, repoId }) {
  const [history, setHistory] = useState([
    {
      role: 'assistant',
      content: 'Hello! I am the GitCompass AI. I can answer questions about this repository based on its codebase, architecture, and git history.\n\n**Note:** I am still in development, so my results may not be perfectly consistent yet, and many more features are yet to come!'
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pageContext, setPageContext] = useState(null);
  
  const messagesEndRef = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [history, isLoading]);

  // Listen for global page context updates
  useEffect(() => {
    const handleSetContext = (e) => setPageContext(e.detail);
    window.addEventListener('gitcompass:set_page_context', handleSetContext);
    return () => window.removeEventListener('gitcompass:set_page_context', handleSetContext);
  }, []);

  // Reset chat if repo changes
  useEffect(() => {
    setHistory([
      {
        role: 'assistant',
        content: 'Hello! I am the GitCompass AI. I can answer questions about this repository based on its codebase, architecture, and git history.\n\n**Note:** I am still in development, so my results may not be perfectly consistent yet, and many more features are yet to come!'
      }
    ]);
    setError(null);
  }, [repoId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage = { role: 'user', content: inputValue.trim() };
    const updatedHistory = [...history, userMessage];
    
    setHistory(updatedHistory);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const payload = updatedHistory.filter(msg => msg.role === 'user' || msg.role === 'assistant').map(m => ({ role: m.role, content: m.content }));
      const response = await api.askAIChat(repoId, payload, pageContext);
      
      setHistory(prev => [...prev, { role: 'assistant', content: response.answer, citations: response.citations }]);
    } catch (err) {
      console.error("AI Chat Error:", err);
      setError("Something went wrong while analyzing the repository. Try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/20 z-40 transition-opacity"
          onClick={onClose}
        ></div>
      )}

      {/* Drawer */}
      <aside className={`
        fixed top-0 right-0 h-full w-full max-w-md bg-[var(--color-surface-raised)] border-l-4 border-[var(--color-border)] shadow-[-8px_0px_0px_rgba(0,0,0,0.1)] z-50 transform transition-transform duration-300 ease-in-out flex flex-col
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}
      `}>
        {/* Header */}
        <div className="h-16 border-b-4 border-[var(--color-border)] bg-[var(--color-primary)] text-[#121212] flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-3">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="square" strokeLinejoin="miter" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <h2 className="font-black uppercase tracking-wider">Ask GitCompass</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-1 hover:bg-[#121212] hover:text-[#E2FF32] transition-colors"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="square" strokeLinejoin="miter" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Message List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {history.map((msg, idx) => (
            <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className="text-xs font-black uppercase text-[var(--color-text-tertiary)] mb-1 px-1">
                {msg.role === 'user' ? 'You' : 'GitCompass AI'}
              </div>
              <div className={`
                max-w-[85%] p-4 border-2 border-[var(--color-border)]
                ${msg.role === 'user' 
                  ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)] shadow-[4px_4px_0px_var(--color-border)]' 
                  : 'bg-[var(--color-surface)] text-[var(--color-text-secondary)] shadow-[4px_4px_0px_var(--color-border)]'
                }
              `}>
                {msg.role === 'user' ? (
                  <p className="whitespace-pre-wrap font-mono text-sm">{msg.content}</p>
                ) : (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-4 flex flex-wrap gap-2 border-t-2 border-[var(--color-border)] pt-4">
                        <span className="text-xs font-black uppercase text-[var(--color-text-tertiary)] w-full block mb-1 tracking-widest">Evidence</span>
                        {msg.citations.map((cit, cIdx) => (
                          <div key={cIdx} className="px-2 py-1 bg-[var(--color-surface-raised)] border-2 border-[var(--color-border)] shadow-[2px_2px_0px_var(--color-border)] text-xs font-mono flex items-center gap-2 text-[var(--color-text-primary)]">
                            {cit.type === 'file' ? '📄' : '📌'} {cit.path}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex flex-col items-start">
              <div className="text-xs font-black uppercase text-[var(--color-text-tertiary)] mb-1 px-1">
                GitCompass AI
              </div>
              <div className="max-w-[85%] p-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] shadow-[4px_4px_0px_var(--color-border)] flex items-center gap-2">
                <span className="font-mono text-sm">AI is thinking</span>
                <span className="animate-pulse">●</span>
                <span className="animate-pulse delay-75">●</span>
                <span className="animate-pulse delay-150">●</span>
              </div>
            </div>
          )}
          
          {error && (
            <div className="p-4 border-2 border-[var(--color-danger)] bg-[var(--color-danger)] text-white font-bold text-sm shadow-[4px_4px_0px_var(--color-border)] mt-4">
              {error}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t-4 border-[var(--color-border)] bg-[var(--color-surface)]">
          <form onSubmit={handleSubmit} className="relative">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask about the architecture..."
              disabled={isLoading || !repoId}
              className="w-full bg-[var(--color-surface-raised)] border-2 border-[var(--color-border)] p-4 pr-12 font-mono text-sm text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)] focus:outline-none focus:border-[var(--color-primary)] focus:shadow-[4px_4px_0px_var(--color-primary)] transition-all disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading || !repoId}
              className="absolute right-2 top-2 bottom-2 aspect-square bg-[var(--color-primary)] border-2 border-[var(--color-border)] text-[#121212] flex items-center justify-center hover:bg-[#E2FF32] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="square" strokeLinejoin="miter" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </form>
          <div className="mt-2 text-center">
             <span className="text-[10px] uppercase font-black tracking-widest text-[var(--color-text-tertiary)] block">
               AI uses repository evidence to answer questions
             </span>
             {pageContext && pageContext.page && (
               <span className="text-[10px] uppercase font-black tracking-widest text-[var(--color-primary)] mt-1 block">
                 Context: {pageContext.page} {pageContext.selected_file && `- ${pageContext.selected_file}`}
               </span>
             )}
          </div>
        </div>
      </aside>
    </>
  );
}
