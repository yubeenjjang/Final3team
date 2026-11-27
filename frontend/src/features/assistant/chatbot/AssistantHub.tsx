"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowUp,
  Bot,
  CalendarDays,
  CloudSun,
  MapPin,
  MessageCircleHeart,
  Route,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { BrandLogo } from "@/components/BrandLogo";
import { storeRouteAccess } from "@/features/routes/return/api";
import {
  askAssistant,
  type AssistantAnswer,
  type AssistantConversation,
} from "./api";

type Conversation =
  | { status: "intro" }
  | { status: "running"; question: string }
  | { status: "succeeded"; question: string; answer: AssistantAnswer }
  | { status: "failed"; question: string; message: string };

const QUICK_QUESTIONS = [
  { label: "이번 주말 축제 추천해줘", icon: CalendarDays },
  { label: "같이 갈 동행 찾아줘", icon: Users },
  { label: "축제 끝나고 귀가 방법 알려줘", icon: Route },
  { label: "지금 축제장 혼잡도 어때?", icon: ShieldCheck },
  { label: "지금 열리는 지역 축제 알려줘", icon: MapPin },
  { label: "축제 날씨는 어때?", icon: CloudSun },
] as const;

const CAPABILITIES = [
  "내 상황에 맞는 축제 추천",
  "동행 모집글·동행방 연결",
  "교통·귀가 경로 안내",
  "축제 일정·장소·유의사항 요약",
] as const;

export function AssistantHub() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [conversation, setConversation] = useState<Conversation>({ status: "intro" });
  const activeRequest = useRef<AbortController | null>(null);
  const conversationAccess = useRef<AssistantConversation | undefined>(undefined);
  const running = conversation.status === "running";

  useEffect(() => () => activeRequest.current?.abort(), []);

  async function runQuery(rawQuestion: string) {
    const message = rawQuestion.trim();
    if (!message || running) return;

    const controller = new AbortController();
    activeRequest.current = controller;
    setQuestion(message);
    setConversation({ status: "running", question: message });

    try {
      const answer = await askAssistant(
        message,
        undefined,
        controller.signal,
        conversationAccess.current,
      );
      if (controller.signal.aborted) return;
      conversationAccess.current = answer.conversation;
      if (answer.route) storeRouteAccess(answer.route);
      setConversation({ status: "succeeded", question: message, answer });
    } catch (error) {
      if (controller.signal.aborted) return;
      setConversation({
        status: "failed",
        question: message,
        message: error instanceof Error ? error.message : "질문을 처리하지 못했어요.",
      });
    } finally {
      if (activeRequest.current === controller) activeRequest.current = null;
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runQuery(question);
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col bg-surface">
      <header className="flex h-[72px] shrink-0 items-center justify-between border-b border-line-light px-4 md:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            aria-label="이전 화면으로 돌아가기"
            className="grid h-10 w-10 place-items-center rounded-full text-ink transition-colors hover:bg-surface-soft hover:text-brand"
          >
            <ArrowLeft size={22} aria-hidden="true" />
          </button>
          <Link href="/" aria-label="놀다가 홈">
            <BrandLogo className="h-9 w-auto md:h-10" priority />
          </Link>
        </div>
      </header>

      <main className="flex-1 px-5 pb-28 pt-7 md:px-10 md:pt-10">
        <section className="relative overflow-hidden rounded-panel bg-gradient-to-br from-surface via-surface to-brand-soft/75 px-1 pb-5">
          <div className="relative z-10 max-w-[520px]">
            <h1 className="text-[30px] font-black tracking-[-0.045em] text-ink md:text-4xl">
              <span className="text-brand">AI</span>에게 물어보세요!
            </h1>
            <p className="mt-2 text-sm font-medium leading-6 text-ink/75 md:text-base">
              축제 추천부터 동행 찾기, 귀가 방법까지<br className="sm:hidden" /> 놀다가 AI가 한 번에 도와드려요.
            </p>
          </div>
          <div className="absolute -right-2 top-0 grid h-28 w-28 place-items-center rounded-full bg-brand-soft/80 text-brand md:right-6 md:h-32 md:w-32">
            <Bot size={68} strokeWidth={1.7} aria-hidden="true" />
            <Sparkles className="absolute -left-1 top-3 h-7 w-7" aria-hidden="true" />
          </div>
        </section>

        {conversation.status !== "intro" ? (
          <section aria-live="polite" className="mt-7 space-y-4">
            <div className="ml-auto max-w-[88%] rounded-[22px] rounded-br-md bg-brand-soft px-4 py-3 text-sm font-semibold leading-6 text-ink">
              {conversation.question}
            </div>
            <div className="flex items-start gap-2.5">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand text-surface">
                <Bot size={20} aria-hidden="true" />
              </span>
              <div className="max-w-[88%] rounded-[22px] rounded-tl-md bg-surface-muted px-4 py-3 text-sm leading-6 text-ink">
                {conversation.status === "running" ? (
                  <p role="status" className="font-semibold text-ink/70">답변을 준비하고 있어요…</p>
                ) : conversation.status === "succeeded" ? (
                  <p className="whitespace-pre-wrap">{conversation.answer.text}</p>
                ) : (
                  <div>
                    <p role="alert">{conversation.message}</p>
                    <button
                      type="button"
                      onClick={() => void runQuery(conversation.question)}
                      className="mt-2 font-bold text-brand"
                    >
                      다시 물어보기
                    </button>
                  </div>
                )}
              </div>
            </div>

            {conversation.status === "succeeded" ? (
              <div className="grid grid-cols-3 gap-2 pt-3">
                <Link href="/festivals" className="assistant-action-link">
                  <CalendarDays size={20} aria-hidden="true" />
                  축제 보기
                </Link>
                <Link href="/companions" className="assistant-action-link">
                  <Users size={20} aria-hidden="true" />
                  동행 찾기
                </Link>
                <Link
                  href={conversation.answer.route
                    ? `/routes/return?${new URLSearchParams({ id: conversation.answer.route.id })}`
                    : "/routes/return"}
                  prefetch={false}
                  className="assistant-action-link"
                >
                  <Route size={20} aria-hidden="true" />
                  귀가 보기
                </Link>
              </div>
            ) : null}
          </section>
        ) : (
          <>
            <section className="mt-7">
              <h2 className="text-xl font-black tracking-[-0.03em] text-ink">이런 질문을 많이 해요 👀</h2>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {QUICK_QUESTIONS.map(({ label, icon: Icon }) => (
                  <button
                    key={label}
                    type="button"
                    onClick={() => void runQuery(label)}
                    className="flex min-h-14 items-center gap-2.5 rounded-card bg-gradient-to-r from-brand-soft/75 to-surface-soft/55 px-3 text-left text-[13px] font-bold leading-5 text-ink transition-transform hover:-translate-y-0.5"
                  >
                    <Icon className="h-6 w-6 shrink-0 text-brand" strokeWidth={2.3} aria-hidden="true" />
                    {label}
                  </button>
                ))}
              </div>
            </section>

            <section className="mt-7 overflow-hidden rounded-card-lg bg-gradient-to-br from-surface-soft to-brand-soft px-5 py-5">
              <h2 className="flex items-center gap-2 text-lg font-black text-ink">
                <Sparkles className="h-6 w-6 fill-brand text-brand" aria-hidden="true" />
                <span><span className="text-brand">AI 검색</span>으로 이렇게 도와드려요!</span>
              </h2>
              <ul className="mt-3 space-y-2.5">
                {CAPABILITIES.map((item) => (
                  <li key={item} className="flex items-center gap-2.5 text-sm font-bold text-ink">
                    <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand text-surface">✓</span>
                    {item}
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </main>

      <form
        onSubmit={submit}
        className="assistant-chat-composer fixed inset-x-0 bottom-0 z-20 mx-auto flex items-center gap-2 border-t border-line-light bg-surface/95 px-4 pb-[calc(14px+var(--safe-area-bottom))] pt-3 backdrop-blur md:px-8"
      >
        <MessageCircleHeart className="h-6 w-6 shrink-0 text-brand" aria-hidden="true" />
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          disabled={running}
          maxLength={500}
          aria-label="AI 질문 입력"
          placeholder="추가로 궁금한 점을 물어보세요!"
          className="h-12 min-w-0 flex-1 rounded-input bg-surface-muted px-4 text-sm font-medium text-ink outline-none ring-brand/30 placeholder:text-muted focus:ring-2"
        />
        <button
          type="submit"
          disabled={running || !question.trim()}
          aria-label="AI에게 질문하기"
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-brand text-surface transition-opacity disabled:opacity-40"
        >
          <ArrowUp size={20} aria-hidden="true" />
        </button>
      </form>
    </div>
  );
}
