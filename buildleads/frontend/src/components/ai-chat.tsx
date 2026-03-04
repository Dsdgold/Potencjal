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
        setQueriesUsed(queriesLimit);
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

  // Usage display
  const remaining = queriesLimit > 0 ? queriesLimit - queriesUsed : null;
  const usageLabel =
    queriesLimit === -1
      ? null
      : remaining !== null
      ? `${remaining}/${queriesLimit}`
      : null;

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-[#6366f1] hover:bg-[#818cf8] text-white rounded-full shadow-xl shadow-[#6366f1]/20 flex items-center justify-center transition-all z-50 glow-accent"
        title={isClaude ? "Claude AI" : "Asystent AI"}
      >
        {open ? (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" />
          </svg>
        )}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 w-[420px] max-h-[560px] bg-[#111118] border border-[#26263a] rounded-xl shadow-2xl shadow-black/50 flex flex-col z-50 overflow-hidden">
          {/* Header */}
          <div className="bg-[#16161f] border-b border-[#26263a] px-4 py-3 flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-[#6366f1] to-[#8b5cf6] rounded-lg flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-[#ededf0]">
                {isClaude ? "Claude AI + Web" : "Asystent AI + Web"}
              </p>
              <p className="text-xs text-[#5e5e73] truncate">{leadName}</p>
            </div>
            <div className="flex items-center gap-2">
              {usageLabel && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                  limitReached
                    ? "text-[#ef4444] bg-[#ef4444]/10 border-[#ef4444]/20"
                    : "text-[#5e5e73] bg-[#1c1c28] border-[#26263a]"
                }`}>
                  {usageLabel}
                </span>
              )}
              <span className={`text-[10px] px-2 py-0.5 rounded-full border ${isClaude ? "text-[#a5b4fc] bg-[#6366f1]/10 border-[#6366f1]/20" : "text-[#10b981] bg-[#10b981]/10 border-[#10b981]/20"}`}>
                {isClaude ? "Claude" : "Ollama"}
              </span>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px] max-h-[380px]">
            {messages.length === 0 && (
              <div className="text-center py-4">
                <p className="text-[#5e5e73] text-sm mb-3">Zapytaj o firme (szukam tez w internecie):</p>
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
                      className="block w-full text-left px-3 py-2 bg-[#1c1c28] hover:bg-[#26263a] border border-[#26263a] rounded-lg text-xs text-[#9494a8] transition-colors disabled:opacity-40"
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
                        ? "bg-[#6366f1] text-white"
                        : msg.role === "system"
                        ? "bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/20"
                        : "bg-[#1c1c28] text-[#ededf0] border border-[#26263a]"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-1 ml-1">
                    <p className="text-[10px] text-[#5e5e73] mb-1">Zrodla:</p>
                    <div className="flex flex-wrap gap-1">
                      {msg.sources.slice(0, 3).map((url, j) => {
                        let domain = "";
                        try { domain = new URL(url).hostname.replace("www.", ""); } catch { domain = url.slice(0, 30); }
                        return (
                          <a key={j} href={url} target="_blank" rel="noopener noreferrer"
                            className="text-[10px] text-[#a5b4fc] hover:text-[#c7d2fe] bg-[#6366f1]/10 px-2 py-0.5 rounded border border-[#6366f1]/20 truncate max-w-[140px]">
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
                <div className="bg-[#1c1c28] border border-[#26263a] rounded-lg px-4 py-2">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-[#6366f1] rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <div className="w-2 h-2 bg-[#6366f1] rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <div className="w-2 h-2 bg-[#6366f1] rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                    <span className="text-xs text-[#5e5e73]">
                      {isClaude ? "Claude analizuje..." : "szukam w internecie..."}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Limit reached banner */}
            {limitReached && (
              <div className="bg-[#f59e0b]/5 border border-[#f59e0b]/20 rounded-lg p-3 text-center">
                <p className="text-xs text-[#f59e0b] font-medium mb-1">
                  Wykorzystano limit {queriesLimit} zapytan AI na dzis
                </p>
                <p className="text-[10px] text-[#f59e0b]/70">
                  Zmien pakiet na wyzszy, aby uzyskac wiecej zapytan dziennie
                </p>
              </div>
            )}

            <div ref={messagesEnd} />
          </div>

          {/* Input */}
          <div className="border-t border-[#26263a] p-3 bg-[#16161f]">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder={limitReached ? "Limit zapytan wyczerpany..." : "Zapytaj o firme..."}
                className="flex-1 px-3 py-2 bg-[#0a0a0f] border border-[#26263a] rounded-lg text-sm text-[#ededf0] placeholder-[#5e5e73] focus:ring-2 focus:ring-[#6366f1]/50 focus:outline-none"
                disabled={loading || limitReached}
              />
              <button
                onClick={() => send()}
                disabled={loading || !input.trim() || limitReached}
                className="px-3 py-2 bg-[#6366f1] hover:bg-[#818cf8] disabled:opacity-40 text-white rounded-lg transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
            <p className="text-[10px] text-[#33334d] mt-1 text-center">
              {isClaude ? "Claude Haiku + Web Search" : "Ollama + Web Search (lokalne)"}
            </p>
          </div>
        </div>
      )}
    </>
  );
}
