"use client";

import { useEffect, useState } from "react";
import { useIsSignedIn } from "@/components/RequireAuth";
import { getFestivalPreferences, type OnboardingStatus } from "./api";

export type FestivalPreferenceState = OnboardingStatus | "signed_out" | "loading";

export function useFestivalPreferenceStatus(): FestivalPreferenceState {
  const signedIn = useIsSignedIn();
  const [state, setState] = useState<FestivalPreferenceState>("loading");

  useEffect(() => {
    if (!signedIn) {
      return;
    }

    const controller = new AbortController();
    getFestivalPreferences(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setState(result.onboarding_status);
      })
      .catch(() => {
        if (!controller.signal.aborted) setState("pending");
      });
    return () => controller.abort();
  }, [signedIn]);

  return signedIn ? state : "signed_out";
}
