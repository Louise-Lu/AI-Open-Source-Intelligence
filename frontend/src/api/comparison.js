const API_BASE_URL = 'http://127.0.0.1:8000';

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

export async function getComparison(repo1, repo2) {
  const params = new URLSearchParams({ repo1, repo2 });
  return requestJson(`${API_BASE_URL}/repositories/compare?${params.toString()}`);
}
