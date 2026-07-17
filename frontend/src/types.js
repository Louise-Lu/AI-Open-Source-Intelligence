/**
 * @typedef {Object} EnterpriseReadiness
 * @property {string} level - Readiness level, e.g. "mature", "developing", "nascent"
 * @property {string} explanation - Human-readable explanation of enterprise readiness
 */

/**
 * @typedef {Object} ProfileResponse
 * @property {string} project_type
 * @property {string[]} target_users
 * @property {string[]} core_features
 * @property {string[]} technical_stack
 * @property {string[]} strengths
 * @property {string[]} weaknesses
 * @property {EnterpriseReadiness} enterprise_readiness
 * @property {string} summary
 */

export {};
