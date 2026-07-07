import { useQuery } from "@tanstack/react-query";
import type { ReferralList } from "../types/models";

async function fetchReferrals(): Promise<ReferralList> {
  const response = await fetch("/api/referrals");
  if (!response.ok) {
    throw new Error(`Failed to load referrals: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetches the legal-aid referral catalog served by the backend, which is the
 * same source of truth the agent's get_legal_aid_referrals tool reads from.
 */
export default function useReferrals() {
  return useQuery({
    queryKey: ["referrals"],
    queryFn: fetchReferrals,
  });
}
