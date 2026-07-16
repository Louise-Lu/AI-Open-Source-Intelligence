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

export async function getRoadmap(owner, repo) {
  return requestJson(`${API_BASE_URL}/repositories/${owner}/${repo}/roadmap`);
}
