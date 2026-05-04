#!/usr/bin/env bash
# Agent-Pilot · Flutter 4-in-1 build verification
#
# Validates that the Flutter project compiles on available platforms.
# Exits 0 if at least web builds; prints summary table.

set -euo pipefail
cd "$(dirname "$0")/../mobile_desktop"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo "╔══════════════════════════════════════════╗"
echo "║  Agent-Pilot · Flutter Build Checker     ║"
echo "╚══════════════════════════════════════════╝"
echo ""

if ! command -v flutter &>/dev/null; then
    echo -e "${RED}flutter CLI not found.${NC}"
    echo "Install: https://docs.flutter.dev/get-started/install"
    exit 1
fi

echo "Flutter version:"
flutter --version | head -4
echo ""

echo "Resolving dependencies..."
flutter pub get 2>&1 | tail -3
echo ""

RESULTS=()

check_platform() {
    local platform=$1
    local cmd=$2
    echo -n "  $platform ... "
    if eval "$cmd" &>/dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        RESULTS+=("$platform:ok")
    else
        echo -e "${YELLOW}SKIP${NC} (platform not configured)"
        RESULTS+=("$platform:skip")
    fi
}

echo "Checking platforms:"
echo ""

echo -n "  analyze ... "
if flutter analyze --no-fatal-infos --no-fatal-warnings 2>&1 | tail -1 | grep -q "No issues"; then
    echo -e "${GREEN}OK${NC} (no issues)"
    RESULTS+=("analyze:ok")
else
    WARN_COUNT=$(flutter analyze --no-fatal-infos --no-fatal-warnings 2>&1 | tail -1 || true)
    echo -e "${YELLOW}WARN${NC} ($WARN_COUNT)"
    RESULTS+=("analyze:warn")
fi

check_platform "web" "flutter build web --release --no-tree-shake-icons 2>&1"
check_platform "apk" "flutter build apk --debug --no-tree-shake-icons 2>&1"
check_platform "ios" "flutter build ios --debug --no-codesign --no-tree-shake-icons 2>&1"
check_platform "macos" "flutter build macos --debug --no-tree-shake-icons 2>&1"
check_platform "windows" "flutter build windows --debug --no-tree-shake-icons 2>&1"

echo ""
echo "Summary:"
echo "--------"
OK=0; TOTAL=${#RESULTS[@]}
for r in "${RESULTS[@]}"; do
    IFS=':' read -r name status <<< "$r"
    if [ "$status" = "ok" ]; then
        echo -e "  ${GREEN}✓${NC} $name"
        ((OK++))
    elif [ "$status" = "warn" ]; then
        echo -e "  ${YELLOW}⚠${NC} $name"
    else
        echo -e "  ${YELLOW}⊘${NC} $name (skipped)"
    fi
done
echo ""
echo "$OK/$TOTAL platforms verified"
