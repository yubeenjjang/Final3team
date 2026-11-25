"use client";

import { AssistantPrompt } from "@/features/assistant/chatbot/AssistantPrompt";

export interface FestivalAiPromptProps {
  festivalId: string;
}

export function FestivalAiPrompt({ festivalId }: FestivalAiPromptProps) {
  return <AssistantPrompt key={festivalId} festivalId={festivalId} />;
}
