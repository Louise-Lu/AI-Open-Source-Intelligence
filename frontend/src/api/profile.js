/** @typedef {import('../types.js').ProfileResponse} ProfileResponse */

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
 * Fetch repository profile. Returns the API payload as-is without field mapping.
 * @param {string} owner
 * @param {string} repo
 * @returns {Promise<ProfileResponse>}
 */
export async function getProfile(owner, repo) {
  return requestJson(`${API_BASE_URL}/repositories/${owner}/${repo}/profile`);
}
