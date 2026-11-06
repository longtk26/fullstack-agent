/** The signed-in user's token in the `local` mode (Story 22.7, decision P8), and on the mock API in both modes (MSW
 *  cannot set httpOnly cookies). The only place the token touches localStorage; `cookie` mode never calls these. */
const KEY = "bga.session";

export function readToken(): string | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function storeToken(token: string): void {
  try {
    window.localStorage.setItem(KEY, token);
  } catch {
    // private mode: the session lasts as long as the page
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // nothing stored
  }
}
