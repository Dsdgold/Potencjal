"use client";

import { useState, useRef, useEffect } from "react";
import { apiFetch } from "@/lib/api";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  sources?: string[];
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
  const [provider, setProvider] = useState<string | null>(null);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [queriesUsed, setQueriesUsed] = useState(0);
  const [queriesLimit, setQueriesLimit] = useState(0);
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch("/api/v1/ai/status")
      .then((r) => r.json())
      .then((d) => {
        setAvailable(d.available);
        setProvider(d.provider || "ollama");
        setQueriesUsed(d.queries_used ?? 0);
        setQueriesLimit(d.queries_limit ?? 0);
      })
      .catch(() => setAvailable(false));
  }, []);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const limitReached = queriesLimit > 0 && queriesUsed >= queriesLimit;

  const send = async (text?: string) => {
    const userMsg = (text || input).trim();
    if (!userMsg || loading) return;

    if (limitReached) {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: userMsg },
        {
          role: "system",
          content: `Osiagnieto dzienny limit ${queriesLimit} zapytan AI. Zmien pakiet na wyzszy, aby uzyskac wiecej zapytan dziennie.`,
        },
      ]);
      setInput("");
      return;
    }

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
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.reply, sources: data.web_sources },
        ]);
        if (data.queries_used != null) setQueriesUsed(data.queries_used);
        if (data.queries_limit != null) setQueriesLimit(data.queries_limit);
      } else if (res.status === 429) {
        const err = await res.json().catch(() => ({ detail: "Limit zapytan AI" }));
        setMessages((prev) => [
          ...prev,
          { role: "system", content: err.detail || "Limit zapytan AI wyczerpany" },
        ]);
        setQueriesUsed(queriesLimit); // mark as exhausted
      } else {
        const err = await res.json().catch(() => ({ detail: "Blad polaczenia" }));
        setMessages((prev) => [
          ...prev,
          { role: "system", content: err.detail || "Blad AI" },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: "Nie udalo sie polaczyc z AI" },
      ]);
    }
    setLoading(false);
  };

  if (available === false) return null;

  const isClaude = provider === "claude";

  // Colors based on provider
  const accent = isClaude ? "bg-orange-600 hover:bg-orange-500" : "bg-purple-600 hover:bg-purple-500";
  const accentShadow = isClaude ? "shadow-orange-900/40" : "shadow-purple-900/40";
  const headerGrad = isClaude
    ? "bg-gradient-to-r from-orange-900/50 to-amber-900/50"
    : "bg-gradient-to-r from-purple-900/50 to-blue-900/50";
  const userBubble = isClaude ? "bg-orange-600" : "bg-purple-600";
  const dotColor = isClaude ? "bg-orange-400" : "bg-purple-400";
  const inputRing = isClaude ? "focus:ring-orange-500" : "focus:ring-purple-500";

  // Usage display
  const remaining = queriesLimit > 0 ? queriesLimit - queriesUsed : null;
  const usageLabel =
    queriesLimit === -1
      ? null // unlimited — don't show
      : remaining !== null
      ? `${remaining}/${queriesLimit}`
      : null;

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(!open)}
        className={`fixed bottom-6 right-6 w-14 h-14 ${accent} text-white rounded-full shadow-xl ${accentShadow} flex items-center justify-center transition-all z-50`}
        title={isClaude ? "Claude AI" : "Asystent AI"}
      >
        {open ? (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : isClaude ? (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        )}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 w-[420px] max-h-[560px] bg-slate-900 border border-slate-700 rounded-xl shadow-2xl flex flex-col z-50 overflow-hidden">
          {/* Header */}
          <div className={`${headerGrad} border-b border-slate-700 px-4 py-3 flex items-center gap-3`}>
            <div className={`w-8 h-8 ${isClaude ? "bg-orange-500/20" : "bg-purple-500/20"} rounded-full flex items-center justify-center`}>
              {isClaude ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-orange-400" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a3.768 3.768 0 01-2.28.88H9.75a3.768 3.768 0 01-2.28-.88L5 14.5m14 0V17a2 2 0 01-2 2H7a2 2 0 01-2-2v-2.5" />
                </svg>
              )}
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-white">
                {isClaude ? "Claude AI + Web" : "Asystent AI + Web"}
              </p>
              <p className="text-xs text-slate-400 truncate">{leadName}</p>
            </div>
            <div className="flex items-center gap-2">
              {usageLabel && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                  limitReached
                    ? "text-red-400 bg-red-400/10 border-red-400/20"
                    : "text-slate-400 bg-slate-400/10 border-slate-400/20"
                }`}>
                  {usageLabel}
                </span>
              )}
              <span className={`text-[10px] px-2 py-0.5 rounded-full border ${isClaude ? "text-orange-400 bg-orange-400/10 border-orange-400/20" : "text-green-400 bg-green-400/10 border-green-400/20"}`}>
                {isClaude ? "Claude" : "Ollama"}
              </span>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px] max-h-[380px]">
            {messages.length === 0 && (
              <div className="text-center py-4">
                <p className="text-slate-500 text-sm mb-3">Zapytaj o firme (szukam tez w internecie):</p>
                <div className="space-y-2">
                  {[
                    "Jaki jest potencjal tej firmy?",
                    "Znajdz najnowsze informacje o tej firmie",
                    "Jaka strategie kontaktu proponujesz?",
                    "Jakie produkty budowlane pasuja do tej firmy?",
                  ].map((q, i) => (
                    <button
                      key={i}
                      onClick={() => send(q)}
                      disabled={limitReached}
                      className="block w-full text-left px-3 py-2 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 rounded-lg text-xs text-slate-300 transition-colors disabled:opacity-40"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i}>
                <div className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[85%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap ${
                      msg.role === "user"
                        ? `${userBubble} text-white`
                        : msg.role === "system"
                        ? "bg-red-500/20 text-red-400 border border-red-500/20"
                        : "bg-slate-800 text-slate-200 border border-slate-700"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-1 ml-1">
                    <p className="text-[10px] text-slate-500 mb-1">Zrodla:</p>
                    <div className="flex flex-wrap gap-1">
                      {msg.sources.slice(0, 3).map((url, j) => {
                        let domain = "";
                        try { domain = new URL(url).hostname.replace("www.", ""); } catch { domain = url.slice(0, 30); }
                        return (
                          <a key={j} href={url} target="_blank" rel="noopener noreferrer"
                            className="text-[10px] text-blue-400 hover:text-blue-300 bg-blue-400/10 px-2 py-0.5 rounded border border-blue-400/20 truncate max-w-[140px]">
                            {domain}
                          </a>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <div className={`w-2 h-2 ${dotColor} rounded-full animate-bounce`} style={{ animationDelay: "0ms" }} />
                      <div className={`w-2 h-2 ${dotColor} rounded-full animate-bounce`} style={{ animationDelay: "150ms" }} />
                      <div className={`w-2 h-2 ${dotColor} rounded-full animate-bounce`} style={{ animationDelay: "300ms" }} />
                    </div>
                    <span className="text-xs text-slate-500">
                      {isClaude ? "Claude analizuje..." : "szukam w internecie..."}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Limit reached banner */}
            {limitReached && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-center">
                <p className="text-xs text-amber-400 font-medium mb-1">
                  Wykorzystano limit {queriesLimit} zapytan AI na dzis
                </p>
                <p className="text-[10px] text-amber-400/70">
                  Zmien pakiet na wyzszy, aby uzyskac wiecej zapytan dziennie
                </p>
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
                placeholder={limitReached ? "Limit zapytan wyczerpany..." : "Zapytaj o firme..."}
                className={`flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:ring-2 ${inputRing} focus:outline-none`}
                disabled={loading || limitReached}
              />
              <button
                onClick={() => send()}
                disabled={loading || !input.trim() || limitReached}
                className={`px-3 py-2 ${isClaude ? "bg-orange-600 hover:bg-orange-500" : "bg-purple-600 hover:bg-purple-500"} disabled:opacity-40 text-white rounded-lg transition-colors`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
            <p className="text-[10px] text-slate-600 mt-1 text-center">
              {isClaude ? "Claude Haiku + Web Search" : "Ollama + Web Search (lokalne)"}
            </p>
          </div>
        </div>
      )}
    </>
  );
}
