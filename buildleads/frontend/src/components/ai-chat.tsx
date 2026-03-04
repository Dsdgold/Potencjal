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
        className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-br from-[#0ea5e9] to-[#a855f7] hover:from-[#38bdf8] hover:to-[#c084fc] text-white rounded-2xl shadow-xl shadow-[#0ea5e9]/25 flex items-center justify-center transition-all z-50 hover:scale-105 active:scale-95"
        title="Claude Haiku AI"
      >
        {open ? (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
          </svg>
        )}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 w-[420px] max-h-[560px] bg-[#0a1014] border border-[rgba(14,165,233,0.12)] rounded-2xl shadow-2xl shadow-black/60 flex flex-col z-50 overflow-hidden animate-slide-up">
          {/* Header */}
          <div className="bg-[#0f171e] border-b border-[rgba(14,165,233,0.08)] px-4 py-3 flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-[#0ea5e9] to-[#a855f7] rounded-xl flex items-center justify-center shadow-lg shadow-[#0ea5e9]/15">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4.5 h-4.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-[#e8edf2]">Claude Haiku + Web</p>
              <p className="text-[10px] text-[#455566] truncate">{leadName}</p>
            </div>
            <div className="flex items-center gap-2">
              {usageLabel && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                  limitReached
                    ? "text-[#ef4444] bg-[#ef4444]/10 border-[#ef4444]/20"
                    : "text-[#455566] bg-[#162028] border-[rgba(14,165,233,0.08)]"
                }`}>
                  {usageLabel}
                </span>
              )}
              <span className="text-[10px] px-2 py-0.5 rounded-full border text-[#7dd3fc] bg-[#0ea5e9]/10 border-[#0ea5e9]/20">
                Claude
              </span>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px] max-h-[380px]">
            {messages.length === 0 && (
              <div className="text-center py-4">
                <p className="text-[#455566] text-sm mb-3">Zapytaj o firme (szukam tez w internecie):</p>
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
                      className="block w-full text-left px-3 py-2 bg-[#162028] hover:bg-[#1e2d3a] border border-[rgba(14,165,233,0.06)] rounded-xl text-xs text-[#7b8fa0] transition-all disabled:opacity-40 hover:border-[rgba(14,165,233,0.15)]"
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
                    className={`max-w-[85%] px-3.5 py-2.5 rounded-xl text-sm whitespace-pre-wrap ${
                      msg.role === "user"
                        ? "bg-gradient-to-r from-[#0ea5e9] to-[#38bdf8] text-white"
                        : msg.role === "system"
                        ? "bg-[#ef4444]/8 text-[#ef4444] border border-[#ef4444]/20"
                        : "bg-[#162028] text-[#e8edf2] border border-[rgba(14,165,233,0.08)]"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-1.5 ml-1">
                    <p className="text-[10px] text-[#455566] mb-1">Zrodla:</p>
                    <div className="flex flex-wrap gap-1">
                      {msg.sources.slice(0, 3).map((url, j) => {
                        let domain = "";
                        try { domain = new URL(url).hostname.replace("www.", ""); } catch { domain = url.slice(0, 30); }
                        return (
                          <a key={j} href={url} target="_blank" rel="noopener noreferrer"
                            className="text-[10px] text-[#7dd3fc] hover:text-[#bae6fd] bg-[#0ea5e9]/10 px-2 py-0.5 rounded-lg border border-[#0ea5e9]/20 truncate max-w-[140px] transition-colors">
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
                <div className="bg-[#162028] border border-[rgba(14,165,233,0.08)] rounded-xl px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-[#0ea5e9] rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <div className="w-2 h-2 bg-[#0ea5e9] rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <div className="w-2 h-2 bg-[#0ea5e9] rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                    <span className="text-xs text-[#455566]">Claude analizuje...</span>
                  </div>
                </div>
              </div>
            )}

            {/* Limit reached banner */}
            {limitReached && (
              <div className="bg-[#f59e0b]/5 border border-[#f59e0b]/20 rounded-xl p-3 text-center">
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
          <div className="border-t border-[rgba(14,165,233,0.08)] p-3 bg-[#0f171e]">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder={limitReached ? "Limit zapytan wyczerpany..." : "Zapytaj o firme..."}
                className="flex-1 px-3 py-2.5 bg-[#020709] border border-[rgba(14,165,233,0.08)] rounded-xl text-sm text-[#e8edf2] placeholder-[#455566] focus:ring-2 focus:ring-[#0ea5e9]/30 focus:outline-none transition-all"
                disabled={loading || limitReached}
              />
              <button
                onClick={() => send()}
                disabled={loading || !input.trim() || limitReached}
                className="px-3 py-2.5 bg-gradient-to-r from-[#0ea5e9] to-[#38bdf8] hover:from-[#38bdf8] hover:to-[#7dd3fc] disabled:opacity-40 text-white rounded-xl transition-all"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
            <p className="text-[10px] text-[#1e2d3a] mt-1.5 text-center">
              Claude Haiku + Web Search
            </p>
          </div>
        </div>
      )}
    </>
  );
}
