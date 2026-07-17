/** @typedef {import('../types.js').ProfileResponse} ProfileResponse */

/**
 * Extract star count from summary or strengths text.
 * Matches patterns like "37,489 Stars" or "37k+ Stars".
 * @param {ProfileResponse} profile
 * @returns {string}
 */
export function extractStars(profile) {
  const sources = [profile.summary, ...(profile.strengths || [])].filter(Boolean);

  for (const text of sources) {
    const commaMatch = text.match(/([\d,]+)\s*Stars/i);
    if (commaMatch) {
      return commaMatch[1];
    }

    const kMatch = text.match(/(\d+)k\+?\s*Stars/i);
    if (kMatch) {
      return `${kMatch[1]}k+`;
    }
  }

  return 'N/A';
}

/**
 * Parse star count as integer for score heuristics.
 * @param {ProfileResponse} profile
 * @returns {number|null}
 */
export function parseStarsCount(profile) {
  const sources = [profile.summary, ...(profile.strengths || [])].filter(Boolean);

  for (const text of sources) {
    const commaMatch = text.match(/([\d,]+)(?=\s*Stars)/i);
    if (commaMatch) {
      const parsed = parseInt(commaMatch[1].replace(/,/g, ''), 10);
      return Number.isNaN(parsed) ? null : parsed;
    }

    const kMatch = text.match(/(\d+)k\+?\s*Stars/i);
    if (kMatch) {
      return parseInt(kMatch[1], 10) * 1000;
    }
  }

  return null;
}

/**
 * @param {string[]} strengths
 * @returns {string}
 */
export function extractLicense(strengths) {
  const items = Array.isArray(strengths) ? strengths : [];
  const entry = items.find((item) => /MIT|许可/i.test(item));

  if (!entry) {
    return 'N/A';
  }

  if (/MIT/i.test(entry)) {
    return 'MIT';
  }

  return entry;
}

/**
 * @param {string[]} technicalStack
 * @returns {string}
 */
export function extractPrimaryLanguage(technicalStack) {
  const stack = Array.isArray(technicalStack) ? technicalStack : [];
  return stack[0] || 'N/A';
}

const ENTERPRISE_SCORE_MAP = {
  mature: 10,
  developing: 6,
  nascent: 3,
};

/**
 * @param {ProfileResponse} profile
 * @returns {number | 'N/A'}
 */
export function computeEnterpriseScore(profile) {
  const level = profile.enterprise_readiness?.level?.toLowerCase();
  if (!level || !(level in ENTERPRISE_SCORE_MAP)) {
    return 'N/A';
  }
  return ENTERPRISE_SCORE_MAP[level];
}

/**
 * TODO: Derive maintenance score dynamically from release cadence,
 * commit frequency, and issue response time instead of static heuristics.
 * @param {ProfileResponse} profile
 * @returns {number}
 */
export function computeMaintenanceScore(profile) {
  const stars = parseStarsCount(profile);
  const hasRecentVersion = /v?\d+\.\d+(\.\d+)?/.test(
    [profile.summary, ...(profile.strengths || [])].join(' '),
  );

  if (stars !== null && stars >= 10000 && hasRecentVersion) {
    return 9;
  }

  if (stars !== null && stars >= 1000 && hasRecentVersion) {
    return 7;
  }

  if (hasRecentVersion) {
    return 6;
  }

  return 5;
}

/**
 * TODO: Derive community score dynamically from contributor count,
 * issue engagement, and discussion activity instead of static heuristics.
 * @param {ProfileResponse} profile
 * @returns {number}
 */
export function computeCommunityScore(profile) {
  const stars = parseStarsCount(profile);
  const adoptedByEnterprises = (profile.strengths || []).some((item) =>
    /Klarna|Replit|Elastic|企业|知名/i.test(item),
  );

  if (stars !== null && stars >= 30000 && adoptedByEnterprises) {
    return 9;
  }

  if (stars !== null && stars >= 10000) {
    return 8;
  }

  if (stars !== null && stars >= 1000) {
    return 6;
  }

  return adoptedByEnterprises ? 7 : 5;
}
