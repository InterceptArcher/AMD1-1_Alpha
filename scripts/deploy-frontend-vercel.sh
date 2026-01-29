#!/usr/bin/env bash
# Deploy frontend to Vercel
# Non-interactive, CI-safe deployment script
# Reads credentials from environment variables only

set -euo pipefail

echo "=== Vercel Frontend Deployment ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Verify required environment variables
if [[ -z "${VERCEL_TOKEN:-}" ]]; then
    echo "ERROR: VERCEL_TOKEN environment variable is required"
    exit 1
fi

# Optional: Use existing project IDs if available
VERCEL_ORG_ID="${VERCEL_ORG_ID:-}"
VERCEL_PROJECT_ID="${VERCEL_PROJECT_ID:-}"

cd "$(dirname "$0")/../frontend"

echo "Working directory: $(pwd)"

# Install dependencies
echo "Installing dependencies..."
npm ci --silent

# Run tests before deployment
echo "Running tests..."
npm test -- --passWithNoTests --silent

# Build the application
echo "Building application..."
npm run build

# Deploy to Vercel
echo "Deploying to Vercel..."

DEPLOY_ARGS="--token=$VERCEL_TOKEN --yes --prod"

if [[ -n "$VERCEL_ORG_ID" ]]; then
    DEPLOY_ARGS="$DEPLOY_ARGS --scope=$VERCEL_ORG_ID"
fi

# Run deployment and capture output
DEPLOY_OUTPUT=$(npx vercel deploy $DEPLOY_ARGS 2>&1) || {
    echo "ERROR: Vercel deployment failed"
    echo "$DEPLOY_OUTPUT"
    exit 1
}

# Extract deployed URL
DEPLOYED_URL=$(echo "$DEPLOY_OUTPUT" | grep -oE 'https://[a-zA-Z0-9.-]+\.vercel\.app' | tail -1)

if [[ -z "$DEPLOYED_URL" ]]; then
    echo "WARNING: Could not extract deployed URL from output"
    echo "$DEPLOY_OUTPUT"
else
    echo ""
    echo "=== Deployment Successful ==="
    echo "Frontend URL: $DEPLOYED_URL"
fi

# If this is a new project, output the project info for .env
if [[ -z "$VERCEL_PROJECT_ID" ]]; then
    echo ""
    echo "NOTE: To avoid creating duplicate projects, add these to your .env:"
    echo "  VERCEL_PROJECT_ID=<check vercel dashboard>"
    echo "  VERCEL_ORG_ID=<check vercel dashboard>"
fi

echo ""
echo "Deployment complete at $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
