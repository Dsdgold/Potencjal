"use client";

import { useState, useRef, useEffect } from "react";
import { apiFetch } from "@/lib/api";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

interface AiChatProps {
  leadId: string;
  leadName: string;
}

export default function AiChat({ leadId, leadName }: AiChatProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [available, setAvailable] = useState<boolean | null>(null);
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch("/api/v1/ai/status")
      .then((r) => r.json())
      .then((d) => setAvailable(d.available))
      .catch(() => setAvailable(false));
  }, []);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const res = await apiFetch("/api/v1/ai/chat", {
        method: "POST",
        body: JSON.stringify({ message: userMsg, lead_id: leadId }),
      });
      if (res.ok) {
        const data = await res.json();
        setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      } else {
        const err = await res.json().catch(() => ({ detail: "Błąd połączenia" }));
        setMessages((prev) => [
          ...prev,
          { role: "system", content: err.detail || "Błąd AI" },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: "Nie udało się połączyć z AI" },
      ]);
    }
    setLoading(false);
  };

  if (available === false) return null;

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-purple-600 hover:bg-purple-500 text-white rounded-full shadow-xl shadow-purple-900/40 flex items-center justify-center transition-all z-50"
        title="Asystent AI"
      >
        {open ? (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        )}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 w-96 max-h-[500px] bg-slate-900 border border-slate-700 rounded-xl shadow-2xl flex flex-col z-50 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-900/50 to-blue-900/50 border-b border-slate-700 px-4 py-3 flex items-center gap-3">
            <div className="w-8 h-8 bg-purple-500/20 rounded-full flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a3.768 3.768 0 01-2.28.88H9.75a3.768 3.768 0 01-2.28-.88L5 14.5m14 0V17a2 2 0 01-2 2H7a2 2 0 01-2-2v-2.5" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-white">Asystent AI</p>
              <p className="text-xs text-slate-400 truncate">Analiza: {leadName}</p>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px] max-h-[340px]">
            {messages.length === 0 && (
              <div className="text-center py-6">
                <p className="text-slate-500 text-sm mb-3">Zapytaj o firmę, np.:</p>
                <div className="space-y-2">
                  {[
                    "Jaki jest potencjał tej firmy?",
                    "Jaką strategię kontaktu proponujesz?",
                    "Jakie produkty budowlane pasują?",
                    "Podsumuj kluczowe dane",
                  ].map((q, i) => (
                    <button
                      key={i}
                      onClick={() => { setInput(q); }}
                      className="block w-full text-left px-3 py-2 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 rounded-lg text-xs text-slate-300 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap ${
                    msg.role === "user"
                      ? "bg-purple-600 text-white"
                      : msg.role === "system"
                      ? "bg-red-500/20 text-red-400 border border-red-500/20"
                      : "bg-slate-800 text-slate-200 border border-slate-700"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEnd} />
          </div>

          {/* Input */}
          <div className="border-t border-slate-700 p-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Zapytaj o firmę..."
                className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:ring-2 focus:ring-purple-500 focus:outline-none"
                disabled={loading}
              />
              <button
                onClick={send}
                disabled={loading || !input.trim()}
                className="px-3 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-purple-600/50 text-white rounded-lg transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
            <p className="text-xs text-slate-600 mt-1 text-center">AI Ollama (lokalne, darmowe)</p>
          </div>
        </div>
      )}
    </>
  );
}
