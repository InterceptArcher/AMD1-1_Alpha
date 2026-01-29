#!/usr/bin/env bash
# Setup Supabase database and run migrations
# Non-interactive, CI-safe script
# Reads credentials from environment variables only

set -euo pipefail

echo "=== Supabase Database Setup ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Verify required environment variables
if [[ -z "${SUPABASE_ACCESS_TOKEN:-}" ]]; then
    echo "ERROR: SUPABASE_ACCESS_TOKEN environment variable is required"
    exit 1
fi

if [[ -z "${SUPABASE_PROJECT_REF:-}" ]]; then
    echo "ERROR: SUPABASE_PROJECT_REF environment variable is required"
    echo "You can find this in your Supabase dashboard URL: https://supabase.com/dashboard/project/<PROJECT_REF>"
    exit 1
fi

cd "$(dirname "$0")/.."

echo "Working directory: $(pwd)"

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "Installing Supabase CLI..."
    npm install -g supabase
fi

# Link to project
echo "Linking to Supabase project..."
supabase link --project-ref "$SUPABASE_PROJECT_REF"

# Check for migrations
MIGRATIONS_DIR="supabase/migrations"
if [[ ! -d "$MIGRATIONS_DIR" ]]; then
    echo "ERROR: Migrations directory not found: $MIGRATIONS_DIR"
    exit 1
fi

MIGRATION_COUNT=$(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | wc -l)
echo "Found $MIGRATION_COUNT migration(s)"

# Run migrations
echo "Running database migrations..."
supabase db push || {
    echo "ERROR: Migration failed"
    exit 1
}

echo ""
echo "=== Database Setup Complete ==="
echo "Project: $SUPABASE_PROJECT_REF"
echo "Migrations applied: $MIGRATION_COUNT"

# Output connection info (without secrets)
echo ""
echo "Connection details (set these in your backend):"
echo "  SUPABASE_URL=https://$SUPABASE_PROJECT_REF.supabase.co"
echo "  SUPABASE_KEY=<get from Supabase dashboard: Settings > API>"

echo ""
echo "Setup complete at $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
