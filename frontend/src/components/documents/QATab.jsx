import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, AlertTriangle, Info, ChevronDown, ChevronUp, Scale } from 'lucide-react';
import { askDocumentQuestion } from '../../lib/api';

/* ─── Text Formatter (bold + critical) ─── */
function formatText(text) {
  const parts = text.split(/(\*\*\[CRITICAL\]\*\*)/g);
  return parts.map((part, i) => {
    if (part === '**[CRITICAL]**') {
      return <span key={i} className="font-bold text-red-600 bg-red-50 px-1 rounded mx-1 inline-flex items-center gap-1"><AlertTriangle className="w-3 h-3"/> CRITICAL:</span>;
    }
    const boldParts = part.split(/\*\*(.*?)\*\*/g);
    return boldParts.map((bp, j) => {
      if (j % 2 === 1) return <strong key={`${i}-${j}`}>{bp}</strong>;
      return bp;
    });
  });
}

/* ─── Confidence Badge (only for retrieval intents) ─── */
function ConfidenceBadge({ confidence, intent }) {
  if (confidence == null || !['document_qa', 'legal_analysis'].includes(intent)) return null;
  const pct = Math.round(confidence * 100);
  const color = pct >= 75 ? 'text-emerald-600' : pct >= 50 ? 'text-amber-600' : 'text-red-500';
  return (
    <span className={`text-[10px] font-semibold ${color}`}>
      {pct}% confidence
    </span>
  );
}

/* ─── Expandable Sources ─── */
function ExpandableSources({ msg }) {
  const [isOpen, setIsOpen] = useState(false);
  const intent = msg.intent;

  // Only show sources for retrieval-based intents
  if (!['document_qa', 'legal_analysis'].includes(intent)) return null;
  if (!msg.sources?.length) return null;

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg text-xs mt-2 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between font-medium text-slate-500 p-2.5 hover:bg-slate-100 transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5"/>
          Supporting clauses ({msg.sources.length})
        </span>
        <div className="flex items-center gap-2">
          <ConfidenceBadge confidence={msg.confidence} intent={intent} />
          {isOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-2.5 border-t border-slate-200 space-y-2 max-h-48 overflow-y-auto">
          {msg.sources.map((s, i) => (
            <div key={i} className="bg-white p-2.5 rounded-lg border border-slate-100">
               <div className="flex justify-between items-center mb-1">
                 <span className="font-bold text-indigo-600 uppercase text-[10px] tracking-wide">{s.clause_type || 'clause'}</span>
                 {s.party && <span className="text-[10px] text-slate-400">{s.party}</span>}
               </div>
               <div className="text-slate-600 leading-relaxed">"{s.text}"</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Suggested Prompts ─── */
const SUGGESTED_PROMPTS = [
  { text: 'What are the payment obligations?', icon: '💰' },
  { text: 'What are the major risks?', icon: '⚠️' },
  { text: 'Can this agreement be terminated?', icon: '🔚' },
  { text: 'What penalties exist?', icon: '⚖️' },
  { text: 'Who bears liability?', icon: '🛡️' },
];

function SuggestedPrompts({ onSelect, visible }) {
  if (!visible) return null;
  return (
    <div className="px-4 pb-3">
      <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-2">Suggested questions</p>
      <div className="flex flex-wrap gap-1.5">
        {SUGGESTED_PROMPTS.map((prompt, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onSelect(prompt.text)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-full hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 transition-all shadow-sm"
          >
            <span>{prompt.icon}</span>
            {prompt.text}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ─── Main QATab Component ─── */
export default function QATab({ documentId }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      intent: 'greeting',
      content: "Hello! I'm your AI legal assistant. I've analyzed this document and can help you understand its clauses, obligations, risks, payment terms, and legal implications.\n\nAsk me anything about this document to get started."
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const showSuggestions = messages.length <= 1 && !isLoading;

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || !documentId || isLoading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    try {
      const response = await askDocumentQuestion(documentId, userMsg);

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.answer,
        confidence: response.confidence,
        sources: response.sources,
        risks: response.related_risks,
        intent: response.intent || 'document_qa',
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'error', content: 'Failed to get answer. Please try again.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestedPrompt = (text) => {
    setInput(text);
    // Auto-submit after a tick so the input state is set
    setTimeout(() => {
      const form = document.getElementById('qa-form');
      if (form) form.requestSubmit();
    }, 50);
  };

  return (
    <div className="flex flex-col h-[600px] bg-gradient-to-b from-slate-50 to-white border border-slate-200 rounded-xl overflow-hidden relative">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur border-b border-slate-200 px-4 py-2.5 flex items-center gap-2 z-10">
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-sm">
          <Scale className="w-3.5 h-3.5 text-white" />
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-800">AI Legal Assistant</p>
          <p className="text-[10px] text-slate-400">Document-aware analysis</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 max-w-[90%] ${msg.role === 'user' ? 'ml-auto' : ''}`}>
            {msg.role !== 'user' && (
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 ${
                msg.role === 'error' ? 'bg-red-100' : 'bg-gradient-to-br from-blue-100 to-indigo-100'
              }`}>
                <Bot className={`w-4.5 h-4.5 ${msg.role === 'error' ? 'text-red-500' : 'text-blue-600'}`} />
              </div>
            )}

            <div className={`flex flex-col gap-1.5 ${msg.role === 'user' ? 'items-end' : 'items-start'} w-full`}>
              <div className={`p-3.5 rounded-2xl text-sm leading-relaxed whitespace-pre-line ${
                msg.role === 'user' ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-br-sm shadow-md' :
                msg.role === 'error' ? 'bg-red-50 text-red-600 border border-red-200 rounded-bl-sm' :
                'bg-white border border-slate-200 text-slate-700 rounded-bl-sm shadow-sm w-full'
              }`}>
                {msg.role === 'assistant' ? formatText(msg.content) : msg.content}
              </div>

              {/* Risks + Sources */}
              {msg.role === 'assistant' && (msg.risks?.length > 0 || msg.sources?.length > 0) && (
                <div className="flex flex-col gap-2 mt-0.5 w-full">
                  {msg.risks?.map((risk, rIdx) => (
                    <div key={rIdx} className="flex items-start gap-1.5 bg-red-50 border border-red-100 text-red-700 p-2.5 rounded-lg text-xs">
                      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold uppercase">{risk.severity} Risk: </span>
                        {risk.explanation}
                      </div>
                    </div>
                  ))}
                  <ExpandableSources msg={msg} />
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center shrink-0 mt-1">
                <User className="w-4.5 h-4.5 text-slate-600" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-100 to-indigo-100 flex items-center justify-center shrink-0">
              <Bot className="w-4.5 h-4.5 text-blue-600" />
            </div>
            <div className="bg-white border border-slate-200 p-3.5 rounded-2xl rounded-bl-sm shadow-sm">
              <div className="flex gap-1.5">
                <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" />
                <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{animationDelay: '0.15s'}} />
                <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{animationDelay: '0.3s'}} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompts */}
      <SuggestedPrompts visible={showSuggestions} onSelect={handleSuggestedPrompt} />

      {/* Input */}
      <div className="p-3 border-t border-slate-200 bg-white">
        <form id="qa-form" onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about clauses, risks, obligations, payments..."
            className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all placeholder:text-slate-400"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-slate-300 disabled:to-slate-300 text-white px-4 py-2.5 rounded-xl transition-all flex items-center justify-center shadow-sm"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
