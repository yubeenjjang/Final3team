"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowUp, Sparkles } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import {
  fetchAssistantRunStatus,
  submitFestivalAssistantQuery,
} from "./api";

export interface FestivalAiPromptProps {
  festivalId: string;
}

const MAX_POLL_ATTEMPTS = 10;
const POLL_INTERVAL_MS = 1000;

function generateRequestId(): string {
  if (typeof globalThis.crypto !== "undefined" && globalThis.crypto.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `fest_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export function FestivalAiPrompt({ festivalId }: FestivalAiPromptProps) {
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<
    "idle" | "running" | "succeeded" | "failed"
  >("idle");
  const [answer, setAnswer] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [routeLink, setRouteLink] = useState<{
    id: string;
    token: string;
  } | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  async function runQuery(text: string) {
    const trimmed = text.trim();
    if (!trimmed) {
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStatus("running");
    setAnswer(null);
    setErrorMessage(null);
    setRouteLink(null);

    try {
      const submitted = await submitFestivalAssistantQuery(
        {
          request_id: generateRequestId(),
          message: trimmed,
          context: { festival_id: festivalId },
        },
        controller.signal,
      );

      const runId = submitted.run_id;
      const runToken = submitted.run_access_token;

      for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt += 1) {
        if (controller.signal.aborted) {
          return;
        }
        if (attempt > 0) {
          await new Promise<void>((resolve, reject) => {
            const timer = setTimeout(resolve, POLL_INTERVAL_MS);
            controller.signal.addEventListener(
              "abort",
              () => {
                clearTimeout(timer);
                reject(new DOMException("Aborted", "AbortError"));
              },
              { once: true },
            );
          });
        }

        const run = await fetchAssistantRunStatus(
          runId,
          runToken,
          controller.signal,
        );

        if (run.status === "succeeded") {
          setAnswer(
            run.answer ?? run.reply ?? run.message ?? "답변을 확인했어요.",
          );
          if (run.route_request_id && run.route_access_token) {
            setRouteLink({
              id: run.route_request_id,
              token: run.route_access_token,
            });
          }
          setStatus("succeeded");
          return;
        }

        if (run.status === "failed") {
          setErrorMessage(
            run.error?.message ?? "답변을 생성하지 못했어요.",
          );
          setStatus("failed");
          return;
        }
      }

      setErrorMessage("응답이 지연되고 있어요. 잠시 후 다시 물어봐 주세요.");
      setStatus("failed");
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "질문을 처리하지 못했어요.",
      );
      setStatus("failed");
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const target = question.trim() || "이 축제, 지금 가도 괜찮을까?";
    if (!question.trim()) {
      setQuestion(target);
    }
    void runQuery(target);
  }

  return (
    <div className="space-y-2">
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 rounded-input border border-accent/35 bg-surface py-1.5 pl-3.5 pr-1.5 shadow-sm"
      >
        <Sparkles className="h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="이 축제, 지금 가도 괜찮을까?"
          aria-label="AI 질문 입력"
          className="min-w-0 flex-1 bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none"
        />
        <button
          type="submit"
          disabled={status === "running"}
          aria-label="AI에게 질문하기"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-chip bg-accent text-surface transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          <ArrowUp className="h-4 w-4" aria-hidden="true" />
        </button>
      </form>

      {status === "running" ? (
        <div className="rounded-card border border-line-light bg-surface-soft/50 px-3.5 py-2.5 text-xs font-medium text-ink">
          생각 중…
        </div>
      ) : null}

      {status === "succeeded" && answer ? (
        <div className="space-y-2 rounded-card border border-accent/25 bg-surface px-3.5 py-3 text-xs leading-relaxed text-ink">
          <p className="whitespace-pre-line">{answer}</p>
          {routeLink ? (
            <Link
              href={`/routes/return?id=${encodeURIComponent(
                routeLink.id,
              )}&token=${encodeURIComponent(routeLink.token)}`}
              className="inline-flex items-center rounded-chip bg-accent px-3 py-1.5 text-xs font-bold text-surface"
            >
              귀가 경로 보기 →
            </Link>
          ) : null}
        </div>
      ) : null}

      {status === "failed" && errorMessage ? (
        <div className="flex items-center justify-between gap-2 rounded-card border border-brand/30 bg-surface-soft/60 px-3.5 py-2.5 text-xs text-ink">
          <span>{errorMessage}</span>
          <button
            type="button"
            onClick={() => void runQuery(question)}
            className="shrink-0 rounded-chip bg-brand px-2.5 py-1 text-[11px] font-bold text-surface"
          >
            다시 묻기
          </button>
        </div>
      ) : null}
    </div>
  );
}
