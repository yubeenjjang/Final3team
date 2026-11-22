"use client";

import Link from "next/link";
import { ArrowRight, ArrowUp, Sparkles } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { storeRouteAccess } from "@/features/routes/return/api";
import { askAssistant, type AssistantAnswer } from "./api";

type ChatState =
  | { status: "idle" | "running" }
  | { status: "succeeded"; answer: AssistantAnswer }
  | { status: "failed"; message: string; question: string };

export function AssistantPrompt({ festivalId }: { festivalId?: string }) {
  const isHome = festivalId === undefined;
  const defaultQuestion = isHome
    ? "밤에 교통이 편한 축제를 추천해줘!"
    : "이 축제, 지금 가도 괜찮을까?";
  const [question, setQuestion] = useState("");
  const [state, setState] = useState<ChatState>({ status: "idle" });
  const activeRequest = useRef<AbortController | null>(null);
  const running = state.status === "running";

  useEffect(() => () => activeRequest.current?.abort(), []);

  async function runQuery(message: string) {
    if (activeRequest.current && !activeRequest.current.signal.aborted) {
      return;
    }
    const controller = new AbortController();
    activeRequest.current = controller;
    setState({ status: "running" });
    try {
      const answer = await askAssistant(message, festivalId, controller.signal);
      if (!controller.signal.aborted) {
        if (answer.route) storeRouteAccess(answer.route);
        setState({ status: "succeeded", answer });
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setState({
          status: "failed",
          message: error instanceof Error ? error.message : "질문을 처리하지 못했어요.",
          question: message,
        });
      }
    } finally {
      if (activeRequest.current === controller) {
        activeRequest.current = null;
      }
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = question.trim() || defaultQuestion;
    setQuestion(message);
    void runQuery(message);
  }

  const bubbleClass = isHome
    ? "border-line-dark bg-dark-surface text-surface"
    : "border-line-light bg-surface-soft/50 text-ink";

  return (
    <div className="space-y-2">
      <form
        onSubmit={submit}
        className={`flex items-center gap-2 rounded-input border p-1.5 pl-3.5 focus-within:ring-2 focus-within:ring-accent ${
          isHome ? "border-dark-muted bg-dark-surface" : "border-accent/35 bg-surface shadow-sm"
        }`}
      >
        <Sparkles className={`${isHome ? "h-6 w-6" : "h-4 w-4"} shrink-0 text-accent`} aria-hidden="true" />
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={isHome ? `예시) ${defaultQuestion}` : defaultQuestion}
          maxLength={500}
          disabled={running}
          aria-label="AI 질문 입력"
          className={`min-w-0 flex-1 bg-transparent text-sm focus:outline-none ${
            isHome ? "text-surface placeholder:text-surface/90" : "text-ink placeholder:text-muted"
          }`}
        />
        <button
          type="submit"
          disabled={running}
          aria-label="AI에게 질문하기"
          className={`grid shrink-0 place-items-center rounded-chip disabled:opacity-60 ${
            isHome ? "h-9 w-9 bg-neon text-ink" : "h-8 w-8 bg-accent text-surface"
          }`}
        >
          {isHome ? <ArrowRight size={19} aria-hidden="true" /> : <ArrowUp size={16} aria-hidden="true" />}
        </button>
      </form>

      {running && (
        <p role="status" className={`rounded-card border px-3.5 py-2.5 text-sm ${bubbleClass}`}>생각 중…</p>
      )}
      {state.status === "succeeded" && (
        <div className={`space-y-2 rounded-card border px-3.5 py-3 text-sm ${bubbleClass}`}>
          <p role="status" className="whitespace-pre-wrap">{state.answer.text}</p>
          {state.answer.route && (
            <Link
              href={`/routes/return?${new URLSearchParams({ id: state.answer.route.id })}`}
              prefetch={false}
              className={`inline-flex items-center gap-1 rounded-chip px-3 py-1.5 text-xs font-bold ${
                isHome ? "bg-neon text-ink" : "bg-accent text-surface"
              }`}
            >
              귀가 경로 보기 <ArrowRight size={14} aria-hidden="true" />
            </Link>
          )}
        </div>
      )}
      {state.status === "failed" && (
        <div className={`flex items-center justify-between gap-2 rounded-card border px-3.5 py-2.5 text-sm ${bubbleClass}`}>
          <p role="alert">{state.message}</p>
          <button
            type="button"
            onClick={() => {
              setQuestion(state.question);
              void runQuery(state.question);
            }}
            className="shrink-0 rounded-chip bg-brand px-3 py-1.5 text-xs font-bold text-surface"
          >
            다시 묻기
          </button>
        </div>
      )}
    </div>
  );
}
