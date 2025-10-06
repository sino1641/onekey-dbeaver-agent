#!/bin/bash

# DBeaver License Generator Script
# Usage: ./gen-license.sh [OPTIONS] [DBeaver_Path]
#
# Arguments:
#   DBeaver_Path    Path to DBeaver installation directory or executable (optional, will prompt if not provided)
#
# Options:
#   -h, --help                Show help message
#   -t, --type=<type>         License type: le (Lite), ee (Enterprise), ue (Ultimate)
#                             If not specified, will read from .eclipseproduct or prompt
#   -v, --version=<version>   Product version (e.g., 25)
#                             If not specified, will read from .eclipseproduct or prompt
#
# Examples:
#   ./gen-license.sh                                              # Interactive mode
#   ./gen-license.sh "/Applications/DBeaver.app"
#   ./gen-license.sh "C:\Program Files\DBeaver\dbeaver.exe"
#   ./gen-license.sh -t ee -v 24 "/usr/share/dbeaver"

set -e

# Default values (empty means will be determined later)
LICENSE_TYPE=""
VERSION=""
DBEAVER_PATH=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            echo "Usage: $0 [OPTIONS] [DBeaver_Path]"
            echo ""
            echo "Arguments:"
            echo "  DBeaver_Path              Path to DBeaver installation directory or executable (optional)"
            echo "                            If not provided, will prompt for input"
            echo ""
            echo "Options:"
            echo "  -h, --help                Show this help message"
            echo "  -t, --type=<type>         License type: le (Lite), ee (Enterprise), ue (Ultimate)"
            echo "                            If not specified, will read from .eclipseproduct or prompt"
            echo "  -v, --version=<version>   Product version (e.g., 25)"
            echo "                            If not specified, will read from .eclipseproduct or prompt"
            echo ""
            echo "Examples:"
            echo "  $0                                              # Interactive mode"
            echo "  $0 \"/Applications/DBeaver.app\""
            echo "  $0 \"C:\\Program Files\\DBeaver\\dbeaver.exe\""
            echo "  $0 -t ee -v 24 \"/usr/share/dbeaver\""
            exit 0
            ;;
        -t|--type)
            LICENSE_TYPE="$2"
            shift 2
            ;;
        --type=*)
            LICENSE_TYPE="${1#*=}"
            shift
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        --version=*)
            VERSION="${1#*=}"
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
        *)
            DBEAVER_PATH="$1"
            shift
            ;;
    esac
done

# If DBeaver path is not provided, prompt for it
if [ -z "$DBEAVER_PATH" ]; then
    echo "=========================================="
    echo "DBeaver License Generator"
    echo "=========================================="
    echo ""
    echo "Please enter DBeaver installation path:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  - macOS: /Applications/DBeaver.app"
    else
        echo "  - Linux: /usr/share/dbeaver or /opt/dbeaver"
        echo "  - Executable: /path/to/dbeaver (or dbeaver.exe on Windows)"
    fi
    echo ""
    read -p "Path: " DBEAVER_PATH

    # Trim whitespace and quotes
    DBEAVER_PATH=$(echo "$DBEAVER_PATH" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^["'\'']//' -e 's/["'\'']$//')

    if [ -z "$DBEAVER_PATH" ]; then
        echo "Error: No path provided"
        exit 1
    fi
fi

# Normalize path - if it's an executable, get the directory
INSTALL_DIR="$DBEAVER_PATH"
if [[ "$DBEAVER_PATH" == *.exe ]] || [[ "$DBEAVER_PATH" == */dbeaver ]] || [[ "$DBEAVER_PATH" == */DBeaverEE ]] || [[ "$DBEAVER_PATH" == */DBeaverUE ]]; then
    INSTALL_DIR=$(dirname "$DBEAVER_PATH")
fi

# Determine plugins directory based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if [[ "$INSTALL_DIR" == *.app ]]; then
        PLUGINS_DIR="$INSTALL_DIR/Contents/Eclipse/plugins"
        PRODUCT_FILE="$INSTALL_DIR/Contents/Eclipse/.eclipseproduct"
    else
        echo "Error: On macOS, please provide path to .app bundle (e.g., /Applications/DBeaver.app)"
        exit 1
    fi
else
    # Linux/Windows
    PLUGINS_DIR="$INSTALL_DIR/plugins"
    PRODUCT_FILE="$INSTALL_DIR/.eclipseproduct"
fi

# Check if plugins directory exists
if [ ! -d "$PLUGINS_DIR" ]; then
    echo "Error: Plugins directory not found: $PLUGINS_DIR"
    echo "Please check the DBeaver installation path"
    exit 1
fi

# Check if dbeaver-agent.jar exists
AGENT_JAR="$PLUGINS_DIR/dbeaver-agent.jar"
if [ ! -f "$AGENT_JAR" ]; then
    echo "Error: dbeaver-agent.jar not found: $AGENT_JAR"
    echo "Please deploy the agent first using onekey.py or manually"
    exit 1
fi

# Read product information from .eclipseproduct if not specified
if [ -z "$LICENSE_TYPE" ] || [ -z "$VERSION" ]; then
    if [ -f "$PRODUCT_FILE" ]; then
        echo "Reading product information from .eclipseproduct..."

        # Read product ID to determine license type
        if [ -z "$LICENSE_TYPE" ]; then
            PRODUCT_ID=$(grep "^id=" "$PRODUCT_FILE" | cut -d'=' -f2)
            case "$PRODUCT_ID" in
                *lite*)
                    LICENSE_TYPE="le"
                    ;;
                *ultimate*)
                    LICENSE_TYPE="ue"
                    ;;
                *enterprise*)
                    LICENSE_TYPE="ee"
                    ;;
                *)
                    echo "Warning: Could not determine license type from product ID: $PRODUCT_ID"
                    ;;
            esac
        fi

        # Read version
        if [ -z "$VERSION" ]; then
            FULL_VERSION=$(grep "^version=" "$PRODUCT_FILE" | cut -d'=' -f2)
            # Extract major version (e.g., "25.2.0" -> "25")
            VERSION=$(echo "$FULL_VERSION" | cut -d'.' -f1)
        fi
    else
        echo "Warning: .eclipseproduct file not found: $PRODUCT_FILE"
    fi
fi

# Prompt for missing values
if [ -z "$LICENSE_TYPE" ]; then
    echo ""
    echo "Please enter License Type:"
    echo "  - le: Lite Edition"
    echo "  - ee: Enterprise Edition"
    echo "  - ue: Ultimate Edition"
    read -p "License Type (le/ee/ue): " LICENSE_TYPE

    if [ -z "$LICENSE_TYPE" ]; then
        echo "Error: License type is required"
        exit 1
    fi
fi

if [ -z "$VERSION" ]; then
    echo ""
    read -p "Please enter Product Version (e.g., 25): " VERSION

    if [ -z "$VERSION" ]; then
        echo "Error: Version is required"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "Generating DBeaver License"
echo "=========================================="
echo "DBeaver Path: $DBEAVER_PATH"
echo "Install Dir:  $INSTALL_DIR"
echo "Plugins Dir:  $PLUGINS_DIR"
echo "License Type: $LICENSE_TYPE"
echo "Version:      $VERSION"
echo "=========================================="
echo ""

# Change to plugins directory and run License generator
cd "$PLUGINS_DIR" || exit 1

# Run java command with all jars in plugins directory
java -cp "*" com.dbeaver.agent.License -t "$LICENSE_TYPE" -v "$VERSION"
