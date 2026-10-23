let counter = 0;

/**
 * Returns an id that is unique within the page session, even for calls in the same millisecond.
 * Unlike crypto.randomUUID, it works outside secure contexts (e.g. plain-HTTP LAN testing).
 */
export function createId(): string {
  counter += 1;
  return `${Date.now()}-${counter}`;
}
