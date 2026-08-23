"use server";

import { ApiError, queryAssistant } from "@/lib/api";
import type { AssistantResponse } from "@/types/domain";

export type AssistantActionResult =
  | { ok: true; response: AssistantResponse }
  | { ok: false; message: string };

export async function askAssistantAction(
  message: string,
  conversationId?: string,
): Promise<AssistantActionResult> {
  const cleanMessage = message.trim();
  if (!cleanMessage) return { ok: false, message: "Enter an operational question." };
  try {
    return {
      ok: true,
      response: await queryAssistant(cleanMessage, conversationId),
    };
  } catch (error) {
    return {
      ok: false,
      message:
        error instanceof ApiError
          ? error.message
          : "The assistant could not complete this request.",
    };
  }
}
