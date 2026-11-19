#!/bin/bash
# Development installation script for ddoc-full
# This script installs all packages in editable mode from local paths

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🔧 Installing ddoc-full in development mode..."
echo "Project root: $PROJECT_ROOT"

# Install core
echo "📦 Installing ddoc core..."
pip install -e "$PROJECT_ROOT/ddoc"

# Install plugins
echo "📦 Installing plugins..."
pip install -e "$PROJECT_ROOT/plugins/ddoc-plugin-vision"
pip install -e "$PROJECT_ROOT/plugins/ddoc-plugin-text"
pip install -e "$PROJECT_ROOT/plugins/ddoc-plugin-timeseries"
pip install -e "$PROJECT_ROOT/plugins/ddoc-plugin-audio"
pip install -e "$PROJECT_ROOT/plugins/ddoc-plugin-categorical"
pip install -e "$PROJECT_ROOT/plugins/ddoc-plugin-tabular"

echo "✅ ddoc-full development installation complete!"
echo ""
echo "Verify installation:"
echo "  ddoc plugin list"
echo "  ddoc --version"

