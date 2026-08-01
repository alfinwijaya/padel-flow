#!/bin/bash
#
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ============================================================
# Google Cloud Workshop - Project Setup Script
# ============================================================
# This script helps workshop participants:
# 1. Check if a project already exists in .env (safeguard)
# 2. List projects with active billing and recommend to user
# 3. Verify trial billing account exists (only if creating new project)
# 4. Create a new GCP project if needed
# 5. Link trial billing account automatically
# 6. Set as default project
# 7. Save the project ID to .env file
# ============================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Google Cloud Workshop - Project Setup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# ============================================================
# Step 0: Check if gcloud is authenticated
# ============================================================
echo -e "${YELLOW}Step 0: Checking gcloud authentication${NC}"
echo -e "Verifying you are logged in to Google Cloud...\n"

# Check if user is authenticated by trying to get the active account
ACTIVE_ACCOUNT=$(gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>/dev/null)

if [ -z "$ACTIVE_ACCOUNT" ]; then
    echo -e "${RED}ERROR: You are not authenticated with Google Cloud!${NC}"
    echo ""
    echo "Please authenticate first by running one of the following commands:"
    echo ""
    echo -e "  ${YELLOW}Option 1 - If using Cloud Shell:${NC}"
    echo -e "    gcloud auth login --no-launch-browser"
    echo ""
    echo -e "  ${YELLOW}Option 2 - For local development:${NC}"
    echo -e "    gcloud auth login"
    echo ""
    echo "After authenticating, run this script again."
    exit 1
fi

echo -e "${GREEN}✓ Authenticated as: ${ACTIVE_ACCOUNT}${NC}"
echo ""

# ============================================================
# Step 1: Check if project already exists in .env
# ============================================================
ENV_FILE=".env"

if [ -f "$ENV_FILE" ]; then
    # Check if GOOGLE_CLOUD_PROJECT is set in .env
    EXISTING_PROJECT=$(grep "^GOOGLE_CLOUD_PROJECT=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2)

    if [ -n "$EXISTING_PROJECT" ]; then
        echo -e "${YELLOW}Step 1: Found existing project in .env${NC}"
        echo -e "Project ID: ${GREEN}${EXISTING_PROJECT}${NC}"
        echo -e "Validating project setup...\n"
        
        # Check if project exists in GCP
        if gcloud projects describe "$EXISTING_PROJECT" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Project exists in Google Cloud"

            # Check if project has billing linked (disable exit on error for this check)
            set +e
            BILLING_INFO=$(gcloud billing projects describe "$EXISTING_PROJECT" --format="value(billingAccountName)" 2>/dev/null)
            BILLING_CHECK_EXIT_CODE=$?
            set -e

            if [ $BILLING_CHECK_EXIT_CODE -eq 0 ] && [ -n "$BILLING_INFO" ]; then
                # Extract billing account ID
                BILLING_ACCOUNT_ID=$(echo "$BILLING_INFO" | sed 's|billingAccounts/||')

                # Check if the billing account is active (disable exit on error)
                set +e
                BILLING_NAME=$(gcloud billing accounts describe "$BILLING_ACCOUNT_ID" --format="value(displayName)" 2>/dev/null)
                BILLING_OPEN=$(gcloud billing accounts describe "$BILLING_ACCOUNT_ID" --format="value(open)" 2>/dev/null)
                BILLING_ACCOUNT_CHECK_EXIT_CODE=$?
                set -e

                if [ $BILLING_ACCOUNT_CHECK_EXIT_CODE -eq 0 ] && [ "$BILLING_OPEN" = "True" ]; then
                    echo -e "  ${GREEN}✓${NC} Linked to active billing account: ${BILLING_NAME}"
                    echo ""
                    echo -e "${BLUE}============================================${NC}"
                    echo -e "${GREEN}  Project Already Set Up! ✓${NC}"
                    echo -e "${BLUE}============================================${NC}"
                    echo -e "  Project ID:      ${GREEN}${EXISTING_PROJECT}${NC}"
                    echo -e "  Billing Account: ${GREEN}${BILLING_ACCOUNT_ID}${NC}"
                    echo -e "${BLUE}============================================${NC}"
                    echo ""
                    echo -e "Your environment is ready. No action needed!"
                    echo -e "To use a different project, remove GOOGLE_CLOUD_PROJECT from .env and re-run this script."
                    echo ""

                    # Activate the project
                    echo -e "Activating project..."
                    gcloud config set project "$EXISTING_PROJECT"
                    echo -e "${GREEN}✓ Project activated: ${EXISTING_PROJECT}${NC}"
                    exit 0
                elif [ $BILLING_ACCOUNT_CHECK_EXIT_CODE -ne 0 ]; then
                    echo -e "  ${YELLOW}⚠${NC} Unable to verify billing account status"
                    echo -e "  You may not have permission to view billing accounts."
                    echo -e "  Proceeding to activate the project anyway...\n"

                    # Activate the project even if we can't verify billing
                    echo -e "Activating project..."
                    gcloud config set project "$EXISTING_PROJECT"
                    echo -e "${GREEN}✓ Project activated: ${EXISTING_PROJECT}${NC}"
                    exit 0
                else
                    echo -e "  ${YELLOW}⚠${NC} Project is linked to inactive billing account: ${BILLING_NAME}"
                    echo -e "  The billing account is closed or suspended (OPEN: False)."
                    echo -e "  Creating a new project with trial billing...\n"
                fi
            else
                echo -e "  ${YELLOW}⚠${NC} Project exists but has no billing account linked"
                echo -e "  Linking trial billing account to this project...\n"
                # Skip project creation, just link billing
                PROJECT_ID="$EXISTING_PROJECT"
                SKIP_PROJECT_CREATION=true
            fi
        else
            echo -e "  ${RED}✗${NC} Project does not exist in Google Cloud"
            echo -e "  The project ID in .env is invalid or has been deleted."
            echo -e "  Creating a new project...\n"
        fi
        echo ""
    fi
fi

# ============================================================
# Step 2: List projects with active billing (recommend existing)
# ============================================================
echo -e "${YELLOW}Step 2: Checking for existing projects with active billing${NC}"
echo -e "Searching for projects you can reuse...\n"

PROJECTS_WITH_BILLING=()
PROJECTS_BILLING_NAMES=()

if [[ "$ACTIVE_ACCOUNT" == *"@gcplab.me" ]]; then
    # gcplab.me users may lack billing list permission — list projects directly
    GCPLAB_PROJECTS=$(gcloud projects list --format="value(projectId)" 2>/dev/null)
    while IFS= read -r proj_id; do
        if [ -n "$proj_id" ]; then
            PROJECTS_WITH_BILLING+=("$proj_id")
            PROJECTS_BILLING_NAMES+=("gcplab")
        fi
    done <<< "$GCPLAB_PROJECTS"
else
    # Get all active billing accounts and find their linked projects
    ACTIVE_BILLING=$(gcloud billing accounts list --filter="open=true" --format="csv[no-heading](ACCOUNT_ID,NAME)" 2>/dev/null)

    if [ -n "$ACTIVE_BILLING" ]; then
        while IFS=',' read -r ba_id ba_name; do
            [ -z "$ba_id" ] && continue
            LINKED=$(gcloud billing projects list --billing-account="$ba_id" --format="value(projectId)" 2>/dev/null)
            while IFS= read -r proj_id; do
                if [ -n "$proj_id" ]; then
                    PROJECTS_WITH_BILLING+=("$proj_id")
                    PROJECTS_BILLING_NAMES+=("$ba_name")
                fi
            done <<< "$LINKED"
        done <<< "$ACTIVE_BILLING"
    fi
fi

if [ ${#PROJECTS_WITH_BILLING[@]} -gt 0 ]; then
    echo -e "Found ${GREEN}${#PROJECTS_WITH_BILLING[@]}${NC} project(s) with active billing:"
    echo "-------------------------------------------"
    for i in "${!PROJECTS_WITH_BILLING[@]}"; do
        echo -e "  ${GREEN}[$((i+1))]${NC} ${PROJECTS_WITH_BILLING[$i]}"
        echo -e "       Billing: ${PROJECTS_BILLING_NAMES[$i]}"
    done
    echo "-------------------------------------------"
    echo ""

    SELECTED_PROJECT=""

    # Auto-select first project for @gcplab.me users
    if [[ "$ACTIVE_ACCOUNT" == *"@gcplab.me" ]]; then
        SELECTED_PROJECT="${PROJECTS_WITH_BILLING[0]}"
        echo -e "${GREEN}✓ Detected gcplab.me account — auto-selecting: ${SELECTED_PROJECT}${NC}"
    else
        echo -e "You can reuse one of these projects instead of creating a new one."
        read -p "Enter number to select (or press Enter to skip and use trial billing): " PROJ_SELECTION

        if [ -n "$PROJ_SELECTION" ] && [ "$PROJ_SELECTION" -ge 1 ] 2>/dev/null && [ "$PROJ_SELECTION" -le ${#PROJECTS_WITH_BILLING[@]} ] 2>/dev/null; then
            SELECTED_PROJECT="${PROJECTS_WITH_BILLING[$((PROJ_SELECTION-1))]}"
        else
            echo -e "\nSkipping. Will proceed with trial billing setup.\n"
        fi
    fi

    if [ -n "$SELECTED_PROJECT" ]; then
        echo ""
        echo -e "${GREEN}✓ Selected project: ${SELECTED_PROJECT}${NC}"

        # Activate project
        echo -e "Activating project..."
        gcloud config set project "$SELECTED_PROJECT"
        echo -e "${GREEN}✓ Project activated: ${SELECTED_PROJECT}${NC}"
        echo ""

        # Save to .env
        ENV_FILE=".env"
        ENV_EXAMPLE=".env.example"
        if [ -f "$ENV_FILE" ]; then
            if grep -q "^GOOGLE_CLOUD_PROJECT=" "$ENV_FILE"; then
                sed -i "s/^GOOGLE_CLOUD_PROJECT=.*/GOOGLE_CLOUD_PROJECT=${SELECTED_PROJECT}/" "$ENV_FILE"
            else
                echo "GOOGLE_CLOUD_PROJECT=${SELECTED_PROJECT}" >> "$ENV_FILE"
            fi
        elif [ -f "$ENV_EXAMPLE" ]; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            if grep -q "^GOOGLE_CLOUD_PROJECT=" "$ENV_FILE"; then
                sed -i "s/^GOOGLE_CLOUD_PROJECT=.*/GOOGLE_CLOUD_PROJECT=${SELECTED_PROJECT}/" "$ENV_FILE"
            else
                echo "GOOGLE_CLOUD_PROJECT=${SELECTED_PROJECT}" >> "$ENV_FILE"
            fi
        else
            echo "GOOGLE_CLOUD_PROJECT=${SELECTED_PROJECT}" > "$ENV_FILE"
        fi
        echo -e "${GREEN}✓ Project ID saved to .env file!${NC}"
        echo ""

        echo -e "${BLUE}============================================${NC}"
        echo -e "${GREEN}  Setup Complete! ✓${NC}"
        echo -e "${BLUE}============================================${NC}"
        echo -e "  Project ID:      ${GREEN}${SELECTED_PROJECT}${NC}"
        echo -e "  Billing:         ${GREEN}Active${NC}"
        echo -e "  Environment:     ${GREEN}.env${NC}"
        echo -e "${BLUE}============================================${NC}"
        echo ""
        echo -e "You can now proceed with the workshop!"
        echo -e "To verify, run: ${YELLOW}gcloud config get-value project${NC}"
        exit 0
    fi
else
    echo -e "No existing projects with active billing found."
    echo -e "Proceeding with trial billing setup.\n"
fi

# ============================================================
# Step 3: Check for Trial Billing Account (only if creating new project)
# ============================================================
# Skip this check if we already validated an existing project
if [ "$SKIP_PROJECT_CREATION" != "true" ] && [ -z "$EXISTING_PROJECT" ]; then
    echo -e "${YELLOW}Step 3: Checking for Trial Billing Account${NC}"
    echo -e "Searching for trial billing accounts...\n"

    # Get all billing accounts
    BILLING_ACCOUNTS=$(gcloud billing accounts list --format="csv[no-heading](ACCOUNT_ID,NAME,OPEN)" 2>/dev/null)

    if [ -z "$BILLING_ACCOUNTS" ]; then
        echo -e "${RED}ERROR: No billing accounts found!${NC}"
        echo ""
        echo "This workshop requires a Google Cloud trial billing account."
        echo "Please ensure you have claimed your trial credit first."
        exit 1
    fi

    # Filter for trial billing accounts only (accounts with "Trial" in the name)
    # Store the last one found (most recently added)
    SELECTED_ACCOUNT=""
    SELECTED_NAME=""
    TRIAL_COUNT=0

    echo -e "Found trial billing accounts:"
    echo "-------------------------------------------"
    while IFS=',' read -r account_id name open; do
        # Check if it's a trial account (contains "Trial" in name) and is open
        if [[ "$name" == *"Trial"* ]] && [ "$open" = "True" ]; then
            TRIAL_COUNT=$((TRIAL_COUNT + 1))
            # Keep updating to get the last (latest) one
            SELECTED_ACCOUNT="$account_id"
            SELECTED_NAME="$name"
            echo -e "  ${GREEN}[$TRIAL_COUNT]${NC} $name"
            echo "       ID: $account_id"
        fi
    done <<< "$BILLING_ACCOUNTS"
    echo "-------------------------------------------"

    # Error if no trial billing account found - EXIT EARLY before anything else
    if [ $TRIAL_COUNT -eq 0 ]; then
        echo -e "${RED}ERROR: No active trial billing account found!${NC}"
        echo ""
        echo "This workshop requires an active Google Cloud trial billing account."
        echo ""
        echo "Possible reasons:"
        echo "  - You haven't claimed your free trial credit yet"
        echo "  - Your trial billing account is closed/expired (OPEN: False)"
        echo ""
        echo "Your current billing accounts:"
        gcloud billing accounts list
        echo ""
        echo -e "${YELLOW}Note: Trial accounts with OPEN: False are expired and cannot be used.${NC}"
        exit 1
    fi

    # Auto-select the latest (last) trial billing account
    echo -e "\n${GREEN}✓ Trial billing account found!${NC}"
    echo -e "  Name: ${GREEN}${SELECTED_NAME}${NC}"
    echo -e "  ID:   ${GREEN}${SELECTED_ACCOUNT}${NC}"
    echo ""
fi

# ============================================================
# Step 4: Create a new GCP Project (skip if linking billing to existing project)
# ============================================================
if [ "$SKIP_PROJECT_CREATION" != "true" ]; then
    DEFAULT_PROJECT_ID="workshop-$(head -c 6 /dev/urandom | od -An -tx1 | tr -d ' \n')"
    echo -e "${YELLOW}Step 4: Create a new GCP Project${NC}"
    echo -e "Suggested project ID: ${GREEN}${DEFAULT_PROJECT_ID}${NC}"
    read -p "Enter project ID (press Enter for suggested): " PROJECT_ID
    PROJECT_ID=${PROJECT_ID:-$DEFAULT_PROJECT_ID}

    # Validate project ID format (lowercase letters, digits, hyphens only)
    if [[ ! "$PROJECT_ID" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]]; then
        echo -e "${RED}Error: Project ID must:${NC}"
        echo "  - Be 6 to 30 characters"
        echo "  - Start with a lowercase letter"
        echo "  - Contain only lowercase letters, digits, and hyphens"
        echo "  - Not end with a hyphen"
        exit 1
    fi

    echo -e "\nCreating project: ${GREEN}${PROJECT_ID}${NC}..."
    gcloud projects create "$PROJECT_ID" --name="$PROJECT_ID"

    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create project. The ID might already be taken.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Project created successfully!${NC}"
    echo ""
else
    echo -e "${YELLOW}Step 4: Using existing project${NC}"
    echo -e "Project ID: ${GREEN}${PROJECT_ID}${NC}"
    echo -e "${GREEN}✓ Skipping project creation${NC}"
    echo ""
fi

# ============================================================
# Step 5: Link Trial Billing Account to Project
# ============================================================
echo -e "${YELLOW}Step 5: Link Trial Billing Account${NC}"
echo -e "Linking billing account to project..."
gcloud billing projects link "$PROJECT_ID" --billing-account="$SELECTED_ACCOUNT"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to link billing account.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Billing account linked successfully!${NC}"
echo ""

# ============================================================
# Step 6: Set as default project
# ============================================================
echo -e "${YELLOW}Step 6: Setting as Default Project${NC}"
gcloud config set project "$PROJECT_ID"
echo -e "${GREEN}✓ Default project set to: ${PROJECT_ID}${NC}"
echo ""

# ============================================================
# Step 7: Write to .env file
# ============================================================
echo -e "${YELLOW}Step 7: Saving to .env file${NC}"
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

# Check if .env exists
if [ -f "$ENV_FILE" ]; then
    # .env exists - update or append GOOGLE_CLOUD_PROJECT
    if grep -q "^GOOGLE_CLOUD_PROJECT=" "$ENV_FILE"; then
        # Update existing value
        sed -i "s/^GOOGLE_CLOUD_PROJECT=.*/GOOGLE_CLOUD_PROJECT=${PROJECT_ID}/" "$ENV_FILE"
        echo -e "Updated GOOGLE_CLOUD_PROJECT in existing ${ENV_FILE}"
    else
        # Append to existing file
        echo "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" >> "$ENV_FILE"
        echo -e "Appended GOOGLE_CLOUD_PROJECT to existing ${ENV_FILE}"
    fi
elif [ -f "$ENV_EXAMPLE" ]; then
    # .env doesn't exist but .env.example does - use it as template
    echo -e "Using ${ENV_EXAMPLE} as template..."
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    # Update the project ID in the copied file
    if grep -q "^GOOGLE_CLOUD_PROJECT=" "$ENV_FILE"; then
        sed -i "s/^GOOGLE_CLOUD_PROJECT=.*/GOOGLE_CLOUD_PROJECT=${PROJECT_ID}/" "$ENV_FILE"
    else
        echo "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" >> "$ENV_FILE"
    fi
    echo -e "Created ${ENV_FILE} from ${ENV_EXAMPLE} template"
else
    # Neither .env nor .env.example exists - create new .env file
    echo "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" > "$ENV_FILE"
    echo -e "Created new ${ENV_FILE}"
fi

echo -e "${GREEN}✓ Project ID saved to .env file!${NC}"
echo ""

# ============================================================
# Summary
# ============================================================
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}  Setup Complete! 🎉${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "  Project ID:      ${GREEN}${PROJECT_ID}${NC}"
echo -e "  Billing Account: ${GREEN}${SELECTED_ACCOUNT}${NC}"
echo -e "  Environment:     ${GREEN}.env${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "You can now proceed with the workshop!"
echo -e "To verify, run: ${YELLOW}gcloud config get-value project${NC}"
