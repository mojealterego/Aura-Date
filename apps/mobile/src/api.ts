import * as SecureStore from 'expo-secure-store';

export const BASE_URL =
  (process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

const SESSION_KEY = 'aura_session_v1';

export type Person = {
  id: string;
  display_name: string;
  age: number;
  bio: string;
  values: string[];
};
export type Me = Person & {
  email: string;
  min_age: number;
  max_age: number;
  ready: boolean;
};
export type Intro = {
  id: string | null;
  day: string;
  person: Person | null;
  owner_accepted?: boolean;
  candidate_accepted?: boolean;
  declined?: boolean;
};
export type Conversation = { id: string; person: Person };
export type ChatMessage = {
  id: string;
  author_id: string;
  content: string;
  created_at: string;
};
export type ChatHistory = {
  reveal_stage: 'hidden' | 'unlocked';
  meaningful_messages: number;
  items: ChatMessage[];
};

export async function getSession(): Promise<string | null> {
  return SecureStore.getItemAsync(SESSION_KEY);
}
export async function saveSession(token: string): Promise<void> {
  await SecureStore.setItemAsync(SESSION_KEY, token);
}
export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(SESSION_KEY);
}

export async function api<T>(
  route: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  body?: unknown,
  token?: string | null,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}${route}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) {
      let detail = `Serwer odpowiedział kodem ${res.status}`;
      try {
        const data = await res.json();
        if (typeof data.detail === 'string') detail = data.detail;
      } catch {
        // Keep the HTTP status if response has no JSON body.
      }
      throw new Error(detail);
    }
    if (res.status === 204) return undefined as T;
    return await res.json() as T;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Przekroczono czas oczekiwania na serwer');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
