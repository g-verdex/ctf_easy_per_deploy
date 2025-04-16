#!/bin/bash

# Terminal colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== CTF Deployer Test Setup ===${NC}"
echo "This script will install required dependencies and set up the test environment."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    exit 1
fi

# Set up virtual environment
VENV_DIR="../.venv"
echo -e "\n${YELLOW}Creating virtual environment in ${VENV_DIR}...${NC}"

# Remove existing venv if requested
if [ "$1" == "--force" ] && [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Removing existing virtual environment...${NC}"
    rm -rf "$VENV_DIR"
fi

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create virtual environment. Do you have the venv module installed?${NC}"
        echo -e "${YELLOW}On Arch Linux, you may need to install it with:${NC} sudo pacman -S python-virtualenv"
        exit 1
    fi
else
    echo -e "${YELLOW}Using existing virtual environment at ${VENV_DIR}${NC}"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to activate virtual environment.${NC}"
    exit 1
fi
echo -e "${GREEN}Virtual environment activated.${NC}"

# Add .venv to .gitignore if not already there
if [ -f "../.gitignore" ]; then
    if ! grep -q "^\.venv/$" ../.gitignore; then
        echo -e "\n# Virtual environment" >> ../.gitignore
        echo ".venv/" >> ../.gitignore
        echo -e "${GREEN}Added .venv to .gitignore${NC}"
    fi
fi

# Install dependencies
echo -e "\n${YELLOW}Installing required packages...${NC}"
"$VENV_DIR/bin/pip" install psycopg2-binary python-dotenv pytest pytest-cov netifaces requests prometheus_client
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install dependencies in virtual environment.${NC}"
    exit 1
fi

echo -e "\n${GREEN}Dependencies installed successfully!${NC}"

# Create proper directory structure if needed
echo -e "\n${YELLOW}Setting up test directory structure...${NC}"

# Create __init__.py files in the tests directory
if [ ! -f "__init__.py" ]; then
    touch __init__.py
    echo -e "${GREEN}Created __init__.py${NC}"
fi

# Create environment directory if it doesn't exist
if [ ! -d "environment" ]; then
    mkdir -p environment
    touch environment/__init__.py
    echo -e "${GREEN}Created environment/ directory${NC}"
    
    # Move test files if they exist
    for test_file in test_*.py; do
        if [ -f "$test_file" ]; then
            # Skip test_database_minimal.py
            if [[ "$test_file" == *"test_database_minimal.py"* ]]; then
                continue
            fi
            
            mv "$test_file" "environment/$test_file"
            echo -e "${GREEN}Moved $test_file to environment directory${NC}"
        fi
    done
fi

# Create unit directory if it doesn't exist
if [ ! -d "unit" ]; then
    mkdir -p unit
    touch unit/__init__.py
    echo -e "${GREEN}Created unit/ directory${NC}"
    
    # Move test_database_minimal.py if it exists
    if [ -f "test_database_minimal.py" ]; then
        mv test_database_minimal.py unit/
        echo -e "${GREEN}Moved test_database_minimal.py to unit directory${NC}"
    fi
fi

# Create api directory if it doesn't exist
if [ ! -d "api" ]; then
    mkdir -p api
    touch api/__init__.py
    echo -e "${GREEN}Created api/ directory${NC}"
    
    # Move api_test.sh if it exists
    if [ -f "api_test.sh" ]; then
        mv api_test.sh api/
        chmod +x api/api_test.sh 2>/dev/null
        echo -e "${GREEN}Moved api_test.sh to api directory${NC}"
    fi
fi

# Create load directory if it doesn't exist
if [ ! -d "load" ]; then
    mkdir -p load
    touch load/__init__.py
    echo -e "${GREEN}Created load/ directory${NC}"
    
    # Move load_test_deploy.py if it exists
    if [ -f "load_test_deploy.py" ]; then
        mv load_test_deploy.py load/
        echo -e "${GREEN}Moved load_test_deploy.py to load directory${NC}"
    fi
fi

echo -e "\n${GREEN}Test environment setup complete!${NC}"
echo -e "${BLUE}The virtual environment is now ${GREEN}activated${NC} in this terminal session.${NC}"
echo -e "To deactivate it, run: ${YELLOW}deactivate${NC}"
exit 0
