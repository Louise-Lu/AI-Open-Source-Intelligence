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
  try {
    return await requestJson(`${API_BASE_URL}/comparison`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ repo1, repo2 }),
    });
  } catch (error) {
    if (error?.status !== 404 && error?.status !== 405) {
      throw error;
    }

    const params = new URLSearchParams({ repo1, repo2 });
    return requestJson(`${API_BASE_URL}/compare?${params.toString()}`);
  }
}
