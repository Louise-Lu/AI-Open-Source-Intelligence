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

/**
 * 一次请求获取 Profile + Roadmap + Analysis（后端只收集一次证据）。
 * @param {string} owner
 * @param {string} repo
 * @returns {Promise<{profile: object, roadmap: object, analysis: string, _errors?: object}>}
 */
export async function getInsights(owner, repo) {
  return requestJson(`${API_BASE_URL}/repositories/${owner}/${repo}/insights`);
}
