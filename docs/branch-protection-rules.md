# Suggested Branch Protection Rules

Apply on the default branch (`main`):

1. Require pull request before merging.
2. Require approvals: minimum 1.
3. Require status checks to pass before merging:
   - `openapi-validation`
   - `plugin-tests`
   - `contract-regression`
   - `security-scan`
4. Require branches to be up to date before merging.
5. Require conversation resolution before merging.
6. Restrict force pushes and branch deletions.
