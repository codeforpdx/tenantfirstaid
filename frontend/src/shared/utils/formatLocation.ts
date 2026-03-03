import type { TOregonCity, TUsaState } from "../../types/LocationTypes";

/**
 * Formats a city and state into a human-readable location string.
 *
 * @returns A display string like "Portland, OR", "OR", or "" if both are null.
 */
function formatLocation(
  city: TOregonCity | null,
  state: TUsaState | null,
): string {
  const cityDisplay = city
    ? city.charAt(0).toUpperCase() + city.slice(1)
    : null;
  const stateDisplay = state?.toUpperCase() ?? null;

  if (cityDisplay && stateDisplay) return `${cityDisplay}, ${stateDisplay}`;
  return cityDisplay || stateDisplay || "";
}

export { formatLocation };
