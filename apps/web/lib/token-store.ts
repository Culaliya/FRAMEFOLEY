const PREFIX = "framefoley:project-token:";

export function storeProjectToken(projectId: string, token: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(`${PREFIX}${projectId}`, token);
}

export function readProjectToken(projectId: string): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(`${PREFIX}${projectId}`);
}

export function removeProjectToken(projectId: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(`${PREFIX}${projectId}`);
}
