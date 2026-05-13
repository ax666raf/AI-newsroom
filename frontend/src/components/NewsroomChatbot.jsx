import { useState, useRef, useEffect } from "react";
import { askNewsroomQuestion } from "../services/api";
import { FiMessageSquare } from "react-icons/fi";

// Inject Google Fonts
const fontLink = document.createElement("link");
fontLink.rel = "stylesheet";
fontLink.href = "https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap";
document.head.appendChild(fontLink);

const globalStyle = document.createElement("style");
globalStyle.textContent = `
  * { font-family: 'DM Sans', sans-serif; }
  h1, h2, h3, .serif { font-family: 'DM Serif Display', serif; }
`;
document.head.appendChild(globalStyle);

const SUGGESTED_TOPICS = [
  {
    id: 1,
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/></svg>
      ),
      title: "Latest Breaking News",
      description: "Get a summary of today's top breaking stories",
      prompt: "What are today's top breaking news stories?",
    },
    {
      id: 2,
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
      ),
      title: "Global Affairs",
      description: "Explore international events and geopolitics",
      prompt: "Give me an overview of the latest global affairs and international events.",
    },
    
];

const HISTORY = []

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-2">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-2 h-2 rounded-full bg-stone-500 inline-block animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 mb-6 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-bold"
          style={{ backgroundColor: "#4a5240", color: "#f5f0e8" }}>
          N
        </div>
      )}
      <div className={`max-w-xl text-sm leading-relaxed ${isUser ? "rounded-2xl rounded-tr-sm px-4 py-3" : "rounded-2xl rounded-tl-sm px-4 py-3"}`}
        style={{
          backgroundColor: isUser ? "#4a5240" : "#ede8dc",
          color: isUser ? "#f5f0e8" : "#2d2a22",
        }}>
        {msg.typing ? <TypingDots /> : (
          <div dangerouslySetInnerHTML={{ __html: msg.content }} />
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-bold"
          style={{ backgroundColor: "#9b8e7a", color: "#f5f0e8" }}>
          A
        </div>
      )}
    </div>
  );
}

function WelcomeScreen({ onSelectTopic }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-8 pb-16">
      <div className="mb-3 w-14 h-14 rounded-2xl flex items-center justify-center"
        style={{ backgroundColor: "#4a5240", color: "#f5f0e8" }}>
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/></svg>
      </div>
      <h1 className="text-2xl font-bold mb-1 serif" style={{ color: "#2d2a22" }}>
        Automated Newsroom
      </h1>
      <p className="text-sm mb-10 text-center max-w-xs" style={{ color: "#7a7060" }}>
        Your AI-powered journalism assistant. Ask me about any news topic.
      </p>
      <p className="text-xs font-semibold tracking-widest uppercase mb-4" style={{ color: "#9b8e7a" }}>
        Suggested Topics
      </p>
      <div className="flex flex-col gap-3 w-full max-w-md">
        {SUGGESTED_TOPICS.map((topic) => (
          <button
            key={topic.id}
            onClick={() => onSelectTopic(topic)}
            className="flex items-center gap-4 px-5 py-4 rounded-2xl text-left transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] border"
            style={{
              backgroundColor: "#ede8dc",
              borderColor: "#d5cfc2",
              color: "#2d2a22",
            }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = "#e3ddd0"}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = "#ede8dc"}
          >
            <span className="text-2xl">{topic.icon}</span>
            <div>
              <p className="text-sm font-semibold" style={{ color: "#2d2a22" }}>{topic.title}</p>
              <p className="text-xs mt-0.5" style={{ color: "#7a7060" }}>{topic.description}</p>
            </div>
            <span className="ml-auto text-lg" style={{ color: "#9b8e7a" }}>›</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function NewsroomChatbot() {
  const [chats, setChats] = useState([{ id: 1, title: "New Chat", messages: [] }]);
  const [activeChatId, setActiveChatId] = useState(1);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);

  const activeChat = chats.find((c) => c.id === activeChatId);
  const hasMessages = activeChat?.messages?.length > 0;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeChat?.messages]);

  const formatResponse = (text) => {
    // Convert numbered lists and bold
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/^\d+\.\s+\*\*(.*?)\*\*:/gm, (_, t) => `<br/><strong>${t}:</strong>`)
      .replace(/\n\n/g, "<br/><br/>")
      .replace(/\n/g, "<br/>");
  };

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;
    setInput("");

    const userMsg = { role: "user", content: text };
    const thinkingMsg = { role: "assistant", content: "", typing: true, id: Date.now() };

    setChats((prev) =>
      prev.map((c) =>
        c.id === activeChatId
          ? {
              ...c,
              title: c.messages.length === 0 ? text.slice(0, 32) + (text.length > 32 ? "…" : "") : c.title,
              messages: [...c.messages, userMsg, thinkingMsg],
            }
          : c
      )
    );
    setLoading(true);

    try {
      const history = (activeChat?.messages || []).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Automatically detect Arabic or French text to set the language parameter
      const isArabic = /[\u0600-\u06FF]/.test(text);
      const isFrench = /\b(le|la|les|un|une|des|est|sont|que|qui|pourquoi|comment|quand|où|quel|quelle|bonjour)\b/i.test(text);
      const language = isArabic ? "ar" : (isFrench ? "fr" : "en");

      const data = await askNewsroomQuestion({
        question: text,
        history,
        language: language
      });

      const raw = data.answer || "I couldn't retrieve that information right now.";
      const formatted = formatResponse(raw);

      setChats((prev) =>
        prev.map((c) =>
          c.id === activeChatId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === thinkingMsg.id ? { role: "assistant", content: formatted } : m
                ),
              }
            : c
        )
      );
    } catch {
      setChats((prev) =>
        prev.map((c) =>
          c.id === activeChatId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === thinkingMsg.id
                    ? { role: "assistant", content: "Sorry, something went wrong. Please try again." }
                    : m
                ),
              }
            : c
        )
      );
    }
    setLoading(false);
  };

  const newChat = () => {
    const id = Date.now();
    setChats((prev) => [...prev, { id, title: "New Chat", messages: [] }]);
    setActiveChatId(id);
  };

  return (
    <div className="flex h-screen w-full overflow-hidden" style={{ backgroundColor: "#f5f0e8" }}>
      {/* Sidebar */}
      {sidebarOpen && (
        <aside className="w-56 flex-shrink-0 flex flex-col py-4 px-3 overflow-y-auto"
          style={{ backgroundColor: "#2d2a22", color: "#c8bfaa" }}>
          <button
            onClick={newChat}
            className="flex items-center gap-2 px-3 py-2 rounded-xl mb-5 text-sm font-semibold transition-colors"
            style={{ backgroundColor: "#4a5240", color: "#f5f0e8" }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = "#5a6350"}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = "#4a5240"}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
            New Chat
          </button>

          {/* Active chats */}
          {chats.filter(c => c.messages.length > 0).length > 0 && (
            <div className="mb-4">
              <p className="text-xs uppercase tracking-widest mb-2 px-1 font-semibold" style={{ color: "#6b6250" }}>Recent</p>
              {chats.filter(c => c.messages.length > 0).map((c) => (
                <button key={c.id} onClick={() => setActiveChatId(c.id)}
                  className="w-full text-left px-3 py-2 rounded-lg text-xs mb-1 truncate transition-colors"
                  style={{
                    backgroundColor: activeChatId === c.id ? "#4a5240" : "transparent",
                    color: activeChatId === c.id ? "#f5f0e8" : "#c8bfaa",
                  }}
                  onMouseEnter={e => { if (activeChatId !== c.id) e.currentTarget.style.backgroundColor = "#3a3628"; }}
                  onMouseLeave={e => { if (activeChatId !== c.id) e.currentTarget.style.backgroundColor = "transparent"; }}
                >
                  <FiMessageSquare className="w-4 h-4 inline-block mr-2 opacity-70" /> {c.title}
                </button>
              ))}
            </div>
          )}

          {/* Static history */}
          {HISTORY.map((group) => (
            <div key={group.section} className="mb-4">
              <p className="text-xs uppercase tracking-widest mb-2 px-1 font-semibold" style={{ color: "#6b6250" }}>
                {group.section}
              </p>
              {group.items.map((item, i) => (
                <button key={i}
                  className="w-full text-left px-3 py-2 rounded-lg text-xs mb-1 truncate flex items-center gap-2 transition-colors"
                  style={{ color: "#9b8e7a" }}
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = "#3a3628"}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = "transparent"}
                >
                  <FiMessageSquare className="w-4 h-4 inline-block flex-shrink-0 opacity-70" /> 
                  <span className="truncate">{item}</span>
                </button>
              ))}
            </div>
          ))}

        </aside>
      )}

      {/* Main */}
      <main className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b"
          style={{ backgroundColor: "#f5f0e8", borderColor: "#ddd8cc" }}>
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(o => !o)}
              className="p-2 rounded-lg transition-colors text-sm"
              style={{ color: "#7a7060" }}
              onMouseEnter={e => e.currentTarget.style.backgroundColor = "#ede8dc"}
              onMouseLeave={e => e.currentTarget.style.backgroundColor = "transparent"}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>
            </button>
            {hasMessages && (
              <span className="text-sm font-semibold truncate max-w-xs" style={{ color: "#2d2a22" }}>
                {activeChat?.title}
              </span>
            )}
          </div>
          
        </div>

        {/* Chat / Welcome */}
        <div className="flex-1 overflow-y-auto">
          {!hasMessages ? (
            <WelcomeScreen onSelectTopic={(t) => sendMessage(t.prompt)} />
          ) : (
            <div className="max-w-2xl mx-auto px-4 py-6">
              {activeChat.messages.map((msg, i) => (
                <Message key={i} msg={msg} />
              ))}
              {/* Quick actions after last assistant message */}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="px-4 pb-4 pt-2" style={{ backgroundColor: "#f5f0e8" }}>
          <div className="max-w-2xl mx-auto flex items-center gap-2 rounded-2xl border px-4 py-3"
            style={{ backgroundColor: "#fff", borderColor: "#d5cfc2" }}>
            <input
              className="flex-1 text-sm bg-transparent outline-none"
              style={{ color: "#2d2a22" }}
              placeholder="Ask me anything about the news…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage(input)}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={loading || !input.trim()}
              className="w-8 h-8 rounded-xl flex items-center justify-center transition-all"
              style={{
                backgroundColor: input.trim() && !loading ? "#4a5240" : "#c8bfaa",
                color: "#f5f0e8",
              }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
            </button>
          </div>
        </div>
      </main>
    </div>
  );}