"use client";

import { useSession, signIn, signOut } from "next-auth/react";

export default function AuthButton() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return <div className="h-10 w-44 animate-pulse rounded-xl bg-[#142c54]/15" />;
  }

  if (session) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-[#142c54]/20 bg-white/70 px-3 py-2 shadow-sm backdrop-blur-sm">
        <span className="hidden max-w-52 truncate text-sm text-[#142c54]/80 sm:block">
          {session.user?.email}
        </span>
        {session.error === "RefreshAccessTokenError" && (
          <span className="inline-flex items-center gap-1 rounded-full bg-[#f43126]/10 px-2 py-1 text-xs text-[#f43126]">
            <i className="ph ph-warning-circle" aria-hidden="true" /> Re-auth needed
          </span>
        )}
        <button
          onClick={() => signOut()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#142c54]/30 px-3 py-1.5 text-sm text-[#142c54] transition hover:bg-[#142c54]/5"
        >
          <i className="ph ph-sign-out" aria-hidden="true" /> Sign out
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => signIn("google", { callbackUrl: window.location.href })}
      className="inline-flex items-center gap-2 rounded-xl border border-[#142c54]/20 bg-white px-4 py-2 text-sm font-medium text-[#142c54] shadow-sm transition hover:-translate-y-0.5 hover:shadow"
    >
      <i className="ph ph-google-logo text-base" aria-hidden="true" />
      Sign in with Google
    </button>
  );
}
