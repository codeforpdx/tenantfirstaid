/**
 * Reads a localStorage value, returning null when the key is absent or when
 * storage access throws (e.g. blocked site data).
 */
export function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

/**
 * Writes a localStorage value as best-effort persistence.
 * Storage failures are ignored.
 */
export function writeStorage(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Ignored: callers treat persistence as best-effort.
  }
}

/**
 * Reads a sessionStorage value, returning null when the key is absent or when
 * storage access throws (e.g. blocked site data).
 */
export function readSessionStorage(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

/**
 * Writes a sessionStorage value as best-effort persistence.
 * Storage failures are ignored.
 */
export function writeSessionStorage(key: string, value: string): void {
  try {
    sessionStorage.setItem(key, value);
  } catch {
    // Ignored: callers treat persistence as best-effort.
  }
}

/**
 * Removes a sessionStorage value as best-effort persistence.
 * Storage failures are ignored.
 */
export function removeSessionStorage(key: string): void {
  try {
    sessionStorage.removeItem(key);
  } catch {
    // Ignored: callers treat persistence as best-effort.
  }
}

/**
 * Removes every sessionStorage key starting with the given prefix, as
 * best-effort persistence. Storage failures are ignored.
 */
export function removeSessionStorageByPrefix(prefix: string): void {
  try {
    const keysToRemove: string[] = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key?.startsWith(prefix)) keysToRemove.push(key);
    }
    keysToRemove.forEach((key) => sessionStorage.removeItem(key));
  } catch {
    // Ignored: callers treat persistence as best-effort.
  }
}
