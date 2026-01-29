#!/usr/bin/env bash
# Deploy backend to Railway
# Non-interactive, CI-safe deployment script
# Reads credentials from environment variables only

set -euo pipefail

echo "=== Railway Backend Deployment ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Verify required environment variables
if [[ -z "${RAILWAY_TOKEN:-}" ]]; then
    echo "ERROR: RAILWAY_TOKEN environment variable is required"
    exit 1
fi

cd "$(dirname "$0")/../backend"

echo "Working directory: $(pwd)"

# Verify Python dependencies file exists
if [[ ! -f "requirements.txt" ]]; then
    echo "ERROR: requirements.txt not found"
    exit 1
fi

# Run tests before deployment (if pytest available)
echo "Running tests..."
if command -v pytest &> /dev/null; then
    pytest --tb=short -q || {
        echo "ERROR: Tests failed, aborting deployment"
        exit 1
    }
else
    echo "WARNING: pytest not found, skipping tests"
fi

# Deploy to Railway
echo "Deploying to Railway..."

# Set Railway token for CLI
export RAILWAY_TOKEN

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Deploy
DEPLOY_OUTPUT=$(railway up --detach 2>&1) || {
    echo "ERROR: Railway deployment failed"
    echo "$DEPLOY_OUTPUT"
    exit 1
}

echo "$DEPLOY_OUTPUT"

# Get deployment URL
echo ""
echo "Fetching deployment URL..."
sleep 5  # Give Railway a moment to provision

DEPLOY_URL=$(railway status --json 2>/dev/null | grep -oE '"url":\s*"[^"]+' | cut -d'"' -f4 || echo "")

if [[ -n "$DEPLOY_URL" ]]; then
    echo ""
    echo "=== Deployment Successful ==="
    echo "Backend URL: $DEPLOY_URL"
else
    echo ""
    echo "=== Deployment Initiated ==="
    echo "Check Railway dashboard for deployment URL"
    echo "Dashboard: https://railway.app/dashboard"
fi

echo ""
echo "Deployment complete at $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
