# Bandit Security Testing

Bandit is a security linter for Python code that identifies common security issues.

**Note**: Using bandit development version (1.8.7.dev16+) for Python 3.14 support. Will switch to stable release when available.

## Quick Links

- **[Vulnerability Tracking](./VULNERABILITIES.md)** - Current security issues and remediation status
- **[Testing Guide](./TESTING.md)** - Complete test suite documentation
- **[Changelog](./CHANGELOG.md)** - Version history including security fixes
- **[Bandit Documentation](https://bandit.readthedocs.io/)** - Official Bandit reference

## Running Bandit

**Standalone security scan:**
```bash
npm run test:security
# Or: bash scripts/security-check.sh
```

**As part of full test suite:**
```bash
npm test
# Or: bash scripts/run-tests.sh
```

**Manual execution:**
```bash
source .venv/bin/activate
bandit -c .bandit -r server.py client.py
```

## Configuration

Bandit configuration is in `.bandit`:

- **Targets**: `server.py`, `client.py`
- **Excluded**: `tests/`, `.venv/`, `ui/`, etc.
- **Severity**: MEDIUM and above
- **Confidence**: MEDIUM and above

## Common Security Issues Detected

### B201-B703: Various Security Checks

Bandit checks for:

1. **Hardcoded Passwords** (B105, B106, B107)
   - Passwords, secrets, tokens in source code
   - Use environment variables instead

2. **SQL Injection** (B608)
   - Unsafe SQL query construction
   - Use parameterized queries

3. **Shell Injection** (B602, B603, B605)
   - `subprocess.call()` with shell=True
   - User input in shell commands

4. **Insecure Crypto** (B303, B304, B305)
   - Weak hashing (MD5, SHA1)
   - Use SHA256 or better

5. **Assert Used** (B101)
   - `assert` statements can be optimized away
   - Use explicit checks in production

6. **Try/Except/Pass** (B110)
   - Silent exception swallowing
   - Log errors properly

7. **Insecure Random** (B311)
   - `random` module for security purposes
   - Use `secrets` module instead

## Suppressing False Positives

Add `# nosec` comment to suppress specific warnings:

```python
# Suppress specific check
password = os.getenv("PASSWORD", "default")  # nosec B105

# Suppress with reason
subprocess.run(["ping", hostname])  # nosec B603 - hostname is validated
```

## Exit Codes

- **0**: No issues found
- **1**: Security issues detected

Note: Bandit warnings don't fail the overall test suite, but should be reviewed.

## Integration with CI/CD

The test runner (`run-tests.sh`) includes bandit as step 2 of 5:

1. Install dependencies
2. **Bandit security scan** ⬅️ 
3. Pytest backend tests
4. Playwright UI tests
5. Summary

Bandit warnings are shown but don't block the build (exit code 0 even with warnings).

## Best Practices

1. **Review all findings**: Even low-confidence issues can be real
2. **Don't ignore warnings**: Understand why each issue was flagged
3. **Use environment variables**: Never hardcode secrets
4. **Parameterize queries**: Always use prepared statements for SQL
5. **Validate input**: Sanitize all user-provided data
6. **Document suppressions**: Always add comments explaining why

## Example Output

```
[main]  INFO     profile include tests: None
[main]  INFO     profile exclude tests: None
[main]  INFO     cli include tests: None
[main]  INFO     cli exclude tests: None
[main]  INFO     running on Python 3.14.0

Run started:2025-11-11 10:30:00.000000

Test results:
>> Issue: [B201:flask_debug_true] A Flask app appears to be run with debug=True
   Severity: High   Confidence: Medium
   Location: server.py:100
   More Info: https://bandit.readthedocs.io/en/latest/plugins/b201_flask_debug_true.html

Code scanned:
        Total lines of code: 2500
        Total lines skipped (#nosec): 5

Run metrics:
        Total issues (by severity):
                Undefined: 0
                Low: 0
                Medium: 2
                High: 1
        Total issues (by confidence):
                Undefined: 0
                Low: 0
                Medium: 2
                High: 1
```

## Further Reading

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [OWASP Security Guidelines](https://owasp.org/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
