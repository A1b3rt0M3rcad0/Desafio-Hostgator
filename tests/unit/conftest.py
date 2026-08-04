import os


_TEST_SECRET = "unit-tests-only-secret-value-with-at-least-32-characters"

for variable_name in (
    "JWT_SECRET_KEY",
    "REFRESH_TOKEN_PEPPER",
    "CSRF_SECRET_KEY",
):
    os.environ.setdefault(variable_name, _TEST_SECRET)
