"use client";

import Link from "next/link";
import { ArrowRight, ArrowUp, RotateCw, Sparkles } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { storeRouteAccess } from "@/features/routes/return/api";
import { askAssistant, type AssistantAnswer } from "./api";

type ChatState =
  | { status: "idle" | "running" }
  | { status: "succeeded"; answer: AssistantAnswer }
  | { status: "failed"; message: string; question: string };

const HOME_EXAMPLE_SETS = [
  ["이번 주 서울 축제 알려줘", "친구와 함께 가기 좋은 축제는?"],
  ["야간에 볼거리 많은 축제 추천해줘", "서울역으로 귀가하는 길 알려줘"],
] as const;
const FESTIVAL_EXAMPLES = ["이 축제 혼잡도 알려줘", "귀가하기 편한 길 알려줘"] as const;

export function AssistantPrompt({ festivalId }: { festivalId?: string }) {
  const isHome = festivalId === undefined;
  const defaultQuestion = isHome
    ? "밤에 교통이 편한 축제를 추천해줘!"
    : "이 축제, 지금 가도 괜찮을까?";
  const [question, setQuestion] = useState("");
  const [exampleSetIndex, setExampleSetIndex] = useState(0);
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

  function selectExample(example: string) {
    if (running) return;
    setQuestion(example);
    void runQuery(example);
  }

  const examples = isHome
    ? HOME_EXAMPLE_SETS[exampleSetIndex % HOME_EXAMPLE_SETS.length]
    : FESTIVAL_EXAMPLES;

  return (
    <div className="space-y-2.5">
      <form
        onSubmit={submit}
        className="flex min-h-14 items-center gap-2 rounded-input border-2 border-brand/35 bg-surface p-1.5 pl-4 shadow-card focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/20"
      >
        <Sparkles className="h-5 w-5 shrink-0 fill-brand text-brand" aria-hidden="true" />
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={isHome ? `“(예시) ${defaultQuestion}”` : `“${defaultQuestion}”`}
          maxLength={500}
          disabled={running}
          aria-label="AI 질문 입력"
          className="min-w-0 flex-1 bg-transparent text-sm font-medium text-ink placeholder:text-ink/70 focus:outline-none"
        />
        <button
          type="submit"
          disabled={running}
          aria-label="AI에게 질문하기"
          className="grid h-11 w-11 shrink-0 place-items-center rounded-chip bg-brand text-surface shadow-sm transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          <ArrowUp size={18} strokeWidth={2.4} aria-hidden="true" />
        </button>
      </form>

      <div className="no-scrollbar flex touch-pan-x items-center gap-1.5 overflow-x-auto pb-0.5">
        {isHome ? (
          <button
            type="button"
            disabled={running}
            onClick={() => setExampleSetIndex((prev) => (prev + 1) % HOME_EXAMPLE_SETS.length)}
            aria-label="예시 질문 새로고침"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-chip bg-surface-muted text-ink/70 transition-colors hover:bg-surface-soft hover:text-brand disabled:opacity-50"
          >
            <RotateCw size={16} aria-hidden="true" />
          </button>
        ) : null}
        {examples.map((example) => (
          <button
            key={example}
            type="button"
            disabled={running}
            onClick={() => selectExample(example)}
            className="shrink-0 rounded-chip bg-surface-muted px-4 py-2 text-xs font-semibold text-ink/85 transition-colors hover:bg-surface-soft hover:text-brand disabled:opacity-50"
          >
            {example}
          </button>
        ))}
      </div>
      {running && (
        <p role="status" className="rounded-card border border-line-light bg-surface-soft/60 px-3.5 py-2.5 text-sm font-medium text-ink">
          생각 중…
        </p>
      )}
      {state.status === "succeeded" && (
        <div className="space-y-2 rounded-card border border-brand/20 bg-surface-soft/50 px-3.5 py-3 text-sm text-ink shadow-sm">
          <p role="status" className="whitespace-pre-wrap leading-relaxed">{state.answer.text}</p>
          {state.answer.route && (
            <Link
              href={`/routes/return?${new URLSearchParams({ id: state.answer.route.id })}`}
              prefetch={false}
              className="inline-flex items-center gap-1 rounded-chip bg-brand px-3.5 py-1.5 text-xs font-bold text-surface shadow-sm hover:opacity-90"
            >
              귀가 경로 보기 <ArrowRight size={14} aria-hidden="true" />
            </Link>
          )}
        </div>
      )}
      {state.status === "failed" && (
        <div className="flex items-center justify-between gap-2 rounded-card border border-brand/30 bg-surface-soft px-3.5 py-2.5 text-sm text-ink">
          <p role="alert" className="font-medium">{state.message}</p>
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
