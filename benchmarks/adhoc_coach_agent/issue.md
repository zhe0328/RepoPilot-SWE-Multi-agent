### ISSUE-001: Duplicate, unauthenticated chat API routes (potential privilege escalation)

**Location:** `backend/app/api/main.py` L238–300 (authenticated) and L302–328 (unauthenticated duplicates)

**Problem:**
- `/v1/chat/sessions/{user_id}` and `/v1/chat/history/{session_id}` are each registered twice.
- The second set of handlers has **no** `Depends(get_current_user)` — anyone could fetch any user's session list and chat history.
- Starlette matches routes in registration order; the first (authenticated) group may win today, leaving the second as **latent dead code**. If route order is reversed during a refactor, data is exposed immediately.
- The unauthenticated handlers also have obvious bugs: 404 messages reference undefined variable `id` (should be `user_id` / `session_id`), and they use `print()` instead of the project's `logger`.

**Suggested fix:**
1. Delete the duplicate routes at L302–328.
2. Add tests: requests without JWT to these endpoints should return 401.

**Acceptance criteria:**
- Each chat-related GET endpoint in `main.py` is defined exactly once and requires JWT.
- `pytest` or API smoke tests cover unauthorized access returning 401.
