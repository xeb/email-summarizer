#!/bin/bash
#
# create_skill.sh - Package the upcoming-school-events skill into a zip file
#
# This script creates a distributable zip file containing:
# - SKILL.md (skill documentation)
# - scripts/ folder (email_summarizer.py and email_summarizer_auth.py)
# - credentials.json (OAuth2 credentials, if exists)
# - token.json (authentication token, if exists)
#

set -e  # Exit on error

SKILL_NAME="upcoming-school-events"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ZIP_FILE="${SKILL_NAME}_${TIMESTAMP}.zip"

echo "=========================================="
echo "Creating Skill Package"
echo "=========================================="
echo ""

# Check if SKILL.md exists
if [ ! -f "SKILL.md" ]; then
    echo "Error: SKILL.md not found in current directory"
    exit 1
fi

# Check if scripts/ folder exists
if [ ! -d "scripts" ]; then
    echo "Error: scripts/ folder not found in current directory"
    exit 1
fi

echo "✓ Found SKILL.md"
echo "✓ Found scripts/ folder"
echo ""

# Create temporary directory for packaging
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="${TEMP_DIR}/${SKILL_NAME}"
mkdir -p "${PACKAGE_DIR}"

echo "Packaging files..."
echo ""

# Copy SKILL.md
cp SKILL.md "${PACKAGE_DIR}/"
echo "  [✓] SKILL.md"

# Copy scripts/ folder
cp -r scripts "${PACKAGE_DIR}/"
echo "  [✓] scripts/"
echo "      - scripts/email_summarizer.py"
echo "      - scripts/email_summarizer_auth.py"

# Copy credentials.json if it exists
if [ -f "credentials.json" ]; then
    cp credentials.json "${PACKAGE_DIR}/"
    echo "  [✓] credentials.json (OAuth2 credentials)"
else
    echo "  [⚠] credentials.json not found (user will need to provide their own)"
fi

# Copy token.json if it exists
if [ -f "token.json" ]; then
    cp token.json "${PACKAGE_DIR}/"
    echo "  [✓] token.json (authentication token)"
else
    echo "  [⚠] token.json not found (will be created on first authentication)"
fi

echo ""
echo "Creating zip file: ${ZIP_FILE}"

# Create zip file from the temp directory
cd "${TEMP_DIR}"
zip -r "${ZIP_FILE}" "${SKILL_NAME}" > /dev/null 2>&1
cd - > /dev/null

# Move zip to current directory
mv "${TEMP_DIR}/${ZIP_FILE}" .

# Clean up temp directory
rm -rf "${TEMP_DIR}"

echo ""
echo "=========================================="
echo "Package Created Successfully!"
echo "=========================================="
echo ""
echo "File: ${ZIP_FILE}"
echo "Size: $(du -h "${ZIP_FILE}" | cut -f1)"
echo ""
echo "Contents:"
unzip -l "${ZIP_FILE}"
echo ""
echo "To use this skill:"
echo "  1. Unzip the package: unzip ${ZIP_FILE}"
echo "  2. cd ${SKILL_NAME}"
echo "  3. If credentials.json is missing, add your OAuth2 credentials"
echo "  4. Run: uv run scripts/email_summarizer_auth.py"
echo "  5. Then use: uv run scripts/email_summarizer.py --query \"...\""
echo ""
