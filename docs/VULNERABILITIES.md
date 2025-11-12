# Security Vulnerabilities Tracking

This document tracks security vulnerabilities identified by bandit and other security tools, along with their remediation status.

## Overview

Security scans are run automatically as part of the test suite. See [SECURITY_TESTING.md](SECURITY_TESTING.md) for details on running security scans.

**Last Scan**: 2025-11-12  
**Tool**: Bandit 1.8.7.dev16  
**Scan Command**: `npm run test:security`

---

## Active Vulnerabilities

### High Severity

| ID | Issue | Location | CWE | Status | Notes |
|----|-------|----------|-----|--------|-------|
| B324 | Weak MD5 hash usage | `client.py:279` | [CWE-327](https://cwe.mitre.org/data/definitions/327.html) | 🟡 **ACCEPTED** | Used only for generating non-security interaction IDs. Consider adding `usedforsecurity=False` parameter or switching to UUID. |

**Details**:
```python
# Line 279 in client.py
interaction_id = hashlib.md5(f"{session_id}:{message}:{datetime.now().isoformat()}".encode()).hexdigest()[:16]
```

**Recommendation**: Not used for cryptographic security (just unique IDs). Options:
1. Add `usedforsecurity=False` parameter: `hashlib.md5(..., usedforsecurity=False)`
2. Switch to `uuid.uuid4()` for better uniqueness guarantees
3. Use SHA256 if hash properties are needed

---

### Medium Severity

| ID | Issue | Location | CWE | Status | Notes |
|----|-------|----------|-----|--------|-------|
| B604 | Shell=True in subprocess | `server.py:422` | [CWE-78](https://cwe.mitre.org/data/definitions/78.html) | 🟡 **ACCEPTED** | Ping command uses shell=True for cross-platform compatibility. Hostname is not directly user-controlled and would require authenticated access. |

**Details**:
```python
# Lines 420-423 in server.py
result = subprocess.run(
    ping_cmd,
    capture_output=True,
    text=True,
    timeout=10,
    check=False,
    shell=True  # ← Security issue
)
```

**Recommendation**: The `ping_cmd` is constructed from a hostname parameter. Consider:
1. Strict input validation with regex: `^[a-zA-Z0-9.-]+$`
2. Use shell=False with proper argument splitting (may break cross-platform support)
3. Add `# nosec B604` with justification if accepting the risk

**Current Mitigation**: Tool requires MCP server access (internal API, no public exposure)

---

### Low Severity

| ID | Issue | Location | CWE | Status | Notes |
|----|-------|----------|-----|--------|-------|
| B110 | Try/Except/Pass | `client.py:894` | [CWE-703](https://cwe.mitre.org/data/definitions/703.html) | 🔴 **TO FIX** | Silent exception swallowing in health check. Should log errors. |
| B110 | Try/Except/Pass | `server.py:227` | [CWE-703](https://cwe.mitre.org/data/definitions/703.html) | 🔴 **TO FIX** | Silent exception in WebSocket state handler. Should log. |
| B110 | Try/Except/Pass | `server.py:258` | [CWE-703](https://cwe.mitre.org/data/definitions/703.html) | 🔴 **TO FIX** | Silent exception in Redis cache invalidation. Should log. |
| B110 | Try/Except/Pass | `server.py:642` | [CWE-703](https://cwe.mitre.org/data/definitions/703.html) | 🔴 **TO FIX** | Silent exception in light control cache invalidation. Should log. |
| B110 | Try/Except/Pass | `server.py:748` | [CWE-703](https://cwe.mitre.org/data/definitions/743.html) | 🔴 **TO FIX** | Silent exception in switch control cache invalidation. Should log. |
| B404 | Subprocess import | `server.py:4` | [CWE-78](https://cwe.mitre.org/data/definitions/78.html) | 🟢 **ACCEPTED** | Required for ping functionality. Documented use case. |

**Details - Try/Except/Pass Issues**:

All try/except/pass blocks should be replaced with proper error logging:

```python
# Bad (current)
try:
    await redis_client.delete(cache_key)
except Exception:
    pass

# Good (recommended)
try:
    await redis_client.delete(cache_key)
except Exception as e:
    logger.warning(f"Failed to invalidate cache for {cache_key}: {e}")
```

---

## Resolved Vulnerabilities

| Date Resolved | ID | Issue | Location | Resolution |
|---------------|----|----|----------|------------|
| - | - | - | - | _No resolved vulnerabilities yet_ |

---

## Status Legend

- 🔴 **TO FIX** - Needs remediation
- 🟡 **ACCEPTED** - Risk accepted with justification (document why)
- 🟢 **MITIGATED** - Controls in place to reduce risk
- ✅ **RESOLVED** - Fixed and moved to resolved section

---

## Risk Assessment

### Current Risk Level: **MEDIUM**

**Rationale**:
- 1 HIGH severity issue (MD5 hash) - non-security use case, low actual risk
- 1 MEDIUM severity issue (shell=True) - internal API with limited exposure
- 6 LOW severity issues (mostly logging gaps) - quality issues, minimal security impact

**Recommended Actions** (Priority Order):
1. **Add logging to all try/except/pass blocks** - Improves debugging and incident response
2. **Consider MD5 alternatives** - Switch to UUID or add `usedforsecurity=False`
3. **Add hostname validation to ping** - Strict regex or allowlist
4. **Document risk acceptance** - Formal security review and sign-off

---

## Scanning Process

Security scans are run:
1. **Automatically**: Part of `npm test` and `./scripts/run-tests.sh`
2. **On-demand**: `npm run test:security` or `./scripts/security-check.sh`
3. **Pre-commit**: Recommended as git pre-commit hook

### Running a Scan

```bash
# Quick scan
npm run test:security

# Full scan with debug output
source .venv/bin/activate
bandit --debug -c .bandit -r server.py client.py
```

### Updating This Document

After each security scan:
1. Run `npm run test:security`
2. Review new findings
3. Update vulnerability table
4. Assign status (TO FIX, ACCEPTED, etc.)
5. Document risk acceptance or mitigation plans
6. Commit changes with scan results

---

## References

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Database](https://cwe.mitre.org/)
- [Security Testing Guide](SECURITY_TESTING.md)
- [Changelog](CHANGELOG.md)

---

## Contact

For security concerns or to report vulnerabilities:
- File an issue (for non-sensitive findings)
- Contact maintainers directly (for critical/sensitive issues)

**Last Updated**: 2025-11-12
