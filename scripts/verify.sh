#!/usr/bin/env bash
# ==============================================================================
# babylon_features Comprehensive Verification Gate
#
# Enforces code quality, static typing, unit testing, secret scanning,
# path privacy, and mandatory documentation synchronization.
# ==============================================================================

set -eo pipefail

DOCS_ONLY=false
STRICT_MODE=false

for arg in "$@"; do
    case "$arg" in
        --docs-only)
            DOCS_ONLY=true
            ;;
        --strict)
            STRICT_MODE=true
            ;;
        *)
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1" >&2
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo "======================================================================"
echo " Starting babylon_features Quality & Verification Gate"
echo "======================================================================"

# ------------------------------------------------------------------------------
# Gate 1: Code Formatting (Black)
# ------------------------------------------------------------------------------
if [ "$DOCS_ONLY" = false ]; then
    info "Gate 1: Checking PEP-8 code formatting via black..."
    if poetry run black features --check; then
        pass "Code formatting complies with PEP-8 (black)."
    else
        fail "Code formatting failed. Run 'make fmt' or 'poetry run black features' to reformat."
    fi
fi

# ------------------------------------------------------------------------------
# Gate 2: Static Analysis & Linting (Pylint)
# ------------------------------------------------------------------------------
if [ "$DOCS_ONLY" = false ]; then
    info "Gate 2: Running static analysis via pylint..."
    PYLINT_TARGETS="features/datalake features/processor.py features/vectorstore"
    if compgen -G "features/tools/*.py" > /dev/null; then
        PYLINT_TARGETS="$PYLINT_TARGETS features/tools"
    fi
    if poetry run pylint $PYLINT_TARGETS; then
        pass "Static analysis passed with zero errors (pylint)."
    else
        fail "Pylint reported issues. Please fix lint errors before proceeding."
    fi
fi

# ------------------------------------------------------------------------------
# Gate 3: Static Type Checking (Mypy)
# ------------------------------------------------------------------------------
if [ "$DOCS_ONLY" = false ]; then
    info "Gate 3: Running static type checking via mypy..."
    MYPY_TARGETS="features/datalake"
    if compgen -G "features/tools/*.py" > /dev/null; then
        MYPY_TARGETS="$MYPY_TARGETS features/tools"
    fi
    if poetry run mypy $MYPY_TARGETS; then
        pass "Type checking passed with zero errors (mypy)."
    else
        fail "Mypy type checking reported errors."
    fi
fi

# ------------------------------------------------------------------------------
# Gate 4: Unit Test Suite (Pytest)
# ------------------------------------------------------------------------------
if [ "$DOCS_ONLY" = false ]; then
    info "Gate 4: Executing unit test suite via pytest..."
    if poetry run pytest tests/datalake/test_repository.py -v; then
        pass "Unit test suite passed."
    else
        fail "Unit tests failed."
    fi
fi

# ------------------------------------------------------------------------------
# Gate 5: Documentation & Spec Audit Gate
# ------------------------------------------------------------------------------
info "Gate 5: Auditing documentation, specs, and path privacy..."

# 5A: Path Privacy Audit (No absolute home/user paths)
info "Checking for forbidden personal/home directory paths..."
FORBIDDEN_PATHS=$(git grep -E "(/Users/[a-zA-Z0-9]|/home/[a-zA-Z0-9]|~/[a-zA-Z0-9])" -- '*.py' '*.md' '*.yaml' '*.yml' '*.toml' ':!scripts/verify.sh' ':!poetry.lock' 2>/dev/null || true)
if [ -n "$FORBIDDEN_PATHS" ]; then
    echo "$FORBIDDEN_PATHS"
    fail "Path privacy violation: absolute personal/home directory paths found. Use repository-relative paths only."
else
    pass "Path privacy audit passed: zero absolute personal/home directory paths detected."
fi

# 5B: Documentation Synchronization Check
info "Checking synchronization between code changes and documentation..."
CHANGED_PROD_FILES=$(git diff --name-only main...HEAD 2>/dev/null | grep -E '^features/' || true)
CHANGED_DOC_FILES=$(git diff --name-only main...HEAD 2>/dev/null | grep -E '^(docs/|agent-docs/|AGENTS\.md|README\.md)' || true)

if [ -n "$CHANGED_PROD_FILES" ]; then
    if [ -z "$CHANGED_DOC_FILES" ]; then
        if [ "$STRICT_MODE" = true ]; then
            fail "Documentation Gate: Production code in features/ was modified without accompanying documentation updates in docs/specs/ or AGENTS.md."
        else
            warn "Production code in features/ was modified, but no documentation changes were detected in docs/specs/ or AGENTS.md."
            warn "Please verify whether architectural specifications or AGENTS.md require updates."
        fi
    else
        pass "Documentation synchronization check passed: accompanying documentation updates detected."
    fi
else
    pass "Documentation synchronization check passed: no unreviewed production changes."
fi

# 5C: Relative Link Verification in docs/specs/
info "Verifying relative links in docs/specs/..."
BROKEN_LINKS=0
for spec in docs/specs/*.md; do
    if [ -f "$spec" ]; then
        # Check referenced markdown files in the same directory
        for link in $(grep -oE '\(\./[a-zA-Z0-9_-]+\.md\)' "$spec" 2>/dev/null | tr -d '()'); do
            TARGET_FILE="docs/specs/${link#./}"
            if [ ! -f "$TARGET_FILE" ]; then
                warn "Broken relative link in $spec: $link (Target not found: $TARGET_FILE)"
                BROKEN_LINKS=$((BROKEN_LINKS + 1))
            fi
        done
    fi
done

if [ "$BROKEN_LINKS" -eq 0 ]; then
    pass "All specification relative links resolved successfully."
else
    fail "Detected $BROKEN_LINKS broken relative specification link(s)."
fi

# ------------------------------------------------------------------------------
# Gate 6: Secret & Sensitive File Scan
# ------------------------------------------------------------------------------
info "Gate 6: Scanning working tree and diff for sensitive keys or credentials..."
SUSPICIOUS_SECRETS=$(git diff --cached 2>/dev/null | grep -E '(BEGIN PRIVATE KEY|AWS_SECRET_ACCESS_KEY|ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36})' || true)
if [ -n "$SUSPICIOUS_SECRETS" ]; then
    fail "Secret scan detected potential private key or unmasked API token staged in git diff!"
else
    pass "Secret scanning passed: no hardcoded credentials or private keys detected."
fi

echo "======================================================================"
echo -e "${GREEN} All Verification Gates Passed Successfully!${NC}"
echo "======================================================================"
