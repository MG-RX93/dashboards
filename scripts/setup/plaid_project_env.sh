#!/bin/bash

################################################################################
# Setup Script for Plaid Data Fetching Project
# 
# This script sets up a Python environment for fetching financial data using
# the Plaid API. It creates the necessary directory structure, virtual
# environment, and configuration files.
################################################################################

# =============================================================================
# Color Definitions for Terminal Output
# =============================================================================
GREEN='\033[0;32m'  # Success messages
BLUE='\033[0;34m'   # Information messages
NC='\033[0m'        # No Color (resets formatting)

# =============================================================================
# Initial Setup Message
# =============================================================================
echo -e "${BLUE}Setting up Plaid Project Environment...${NC}"

# =============================================================================
# Path Configurations
# =============================================================================
# Base environment file path - this will store all our configuration
ENV_FILE="/Users/jrk/Documents/Git/GitHub/dashboards/scripts/.env"

# Create parent directories if they don't exist
echo -e "${GREEN}Creating parent directories...${NC}"
mkdir -p "$(dirname "$ENV_FILE")"

# =============================================================================
# Environment Configuration
# =============================================================================
echo -e "${GREEN}Creating .env file with configuration...${NC}"
# Create .env file with initial configuration
cat > "$ENV_FILE" << EOL
# Project Base Directory
BASE_DIR=/Users/jrk/Documents/Git/GitHub/dashboards/scripts

# Plaid API Credentials
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret_key
PLAID_ENV=https://development.plaid.com
EOL

# Load BASE_DIR from .env file
export $(cat "$ENV_FILE" | grep BASE_DIR)

# Define dependent paths
PYTHON_SCRIPT="$BASE_DIR/plaid_fetcher.py"
REQUIREMENTS_FILE="$BASE_DIR/requirements.txt"

# =============================================================================
# Directory Structure Creation
# =============================================================================
echo -e "${GREEN}Creating project directory structure...${NC}"
# Create directories for different components
mkdir -p "$BASE_DIR/transactions"  # For storing financial transaction data
mkdir -p "$BASE_DIR/logs"         # For application logs

# =============================================================================
# Python Environment Setup
# =============================================================================
echo -e "${GREEN}Setting up Python virtual environment...${NC}"
# Create isolated Python environment
python3 -m venv "$BASE_DIR/venv"

# =============================================================================
# Project Files Creation
# =============================================================================
# Create empty Python script file
echo -e "${GREEN}Creating Python script file...${NC}"
touch "$PYTHON_SCRIPT"

# Create requirements.txt with necessary dependencies
echo -e "${GREEN}Creating requirements.txt...${NC}"
cat > "$REQUIREMENTS_FILE" << EOL
# Plaid API client library
plaid-python

# Environment variable management
python-dotenv

# Data manipulation and analysis
pandas
EOL

# =============================================================================
# File Permissions
# =============================================================================
echo -e "${GREEN}Setting file permissions...${NC}"
chmod +x "$PYTHON_SCRIPT"

# =============================================================================
# Setup Completion
# =============================================================================
echo -e "${BLUE}Setup complete! Your directory structure is ready.${NC}"
echo -e "Project created at: $BASE_DIR"
echo -e "\nNext steps:"
echo -e "1. cd $BASE_DIR"
echo -e "2. source venv/bin/activate"
echo -e "3. pip install -r requirements.txt"
echo -e "4. Add your code to plaid_fetcher.py"