const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const error = new Error(
      data?.detail || data?.message || `Request failed with status ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }

  return data;
}

export async function sendMessage(message) {
  // Return the full response so callers can consume answer + trace.
  return requestJson(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  });
}
