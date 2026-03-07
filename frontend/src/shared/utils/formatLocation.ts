import type { OregonCity, UsaState } from "../../types/models";

/**
 * Formats a city and state into a human-readable location string.
 *
 * @returns A display string like "Portland, OR", "OR", or "" if both are null.
 */
function formatLocation(
  city: OregonCity | null | undefined,
  state: UsaState | null | undefined,
): string {
  const cityDisplay = city
    ? city.charAt(0).toUpperCase() + city.slice(1)
    : null;
  const stateDisplay = state && state !== "other" ? state.toUpperCase() : null;

  return [cityDisplay, stateDisplay].filter(Boolean).join(", ");
}

export { formatLocation };
