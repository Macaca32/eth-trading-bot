#!/bin/bash
# Push ETH Trading Bot to GitHub
# Run this from your local machine after cloning or copying the project

set -e

REPO="Macaca32/eth-trading-bot"
REMOTE="https://github.com/${REPO}.git"

echo "============================================="
echo "  ETH Trading Bot - GitHub Push Script"
echo "============================================="
echo ""

# Check if gh CLI is available
if command -v gh &> /dev/null; then
    echo "Using GitHub CLI..."
    if gh auth status &> /dev/null; then
        echo "Already authenticated!"
    else
        echo "Please authenticate with: gh auth login"
        exit 1
    fi
    gh repo create ${REPO} --public --source=. --remote=origin --push
else
    echo "Using git with HTTPS..."
    echo ""
    echo "1. First, create the repo on GitHub:"
    echo "   Go to https://github.com/new"
    echo "   Repository name: eth-trading-bot"
    echo "   Make it PUBLIC"
    echo "   Do NOT initialize with README"
    echo ""
    echo "2. Then run:"
    echo "   git remote add origin ${REMOTE}"
    echo "   git push -u origin main"
fi

echo ""
echo "Done! Your repo is at: https://github.com/${REPO}"
