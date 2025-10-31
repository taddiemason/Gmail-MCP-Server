#!/bin/bash

# Gmail MCP Server Setup Script
# This script automates the setup and management of the Gmail MCP Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Print banner
echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║      Gmail MCP Server Setup                              ║
║      Automated Deployment Script                         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check prerequisites
print_info "Checking prerequisites..."

if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi
print_success "Docker found: $(docker --version)"

if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
print_success "Docker Compose found"

# Check if .env exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success "Created .env from .env.example"
        print_warning "Please edit .env and add your GMAIL_ACCESS_TOKEN"
        print_info "Run: nano .env"
        exit 0
    else
        print_error ".env.example not found. Cannot create .env"
        exit 1
    fi
fi

# Check if GMAIL_ACCESS_TOKEN is set
if ! grep -q "GMAIL_ACCESS_TOKEN=.*[a-zA-Z0-9]" .env; then
    print_error "GMAIL_ACCESS_TOKEN not set in .env file"
    print_info "Please get your token from: https://developers.google.com/oauthplayground/"
    print_info "Then edit .env and add your token"
    exit 1
fi
print_success "Gmail access token found in .env"

# Ask user what to do
echo ""
print_info "What would you like to do?"
echo "1) Start Gmail MCP Server"
echo "2) Stop Gmail MCP Server"
echo "3) Restart Gmail MCP Server"
echo "4) View logs"
echo "5) Check status"
echo "6) Update server"
echo "7) Clean up (remove all data)"
echo "8) Exit"
echo ""
read -p "Enter your choice (1-8): " choice

case $choice in
    1)
        print_info "Starting Gmail MCP Server..."
        docker-compose up -d --build
        print_success "Server started!"
        echo ""
        print_info "Waiting for server to be ready..."
        sleep 3

        print_info "Checking if server is running..."
        if docker-compose ps | grep -q "Up"; then
            print_success "Gmail MCP Server is running!"
            echo ""
            print_info "Server is available at: http://localhost:3002"
            echo ""
            print_info "To connect from OpenWebUI:"
            print_info "1. Go to OpenWebUI Settings > Admin Panel > MCP Servers"
            print_info "2. Add a new MCP server with URL: http://gmail-mcp-server:3002"
            print_info "   (or http://localhost:3002 if OpenWebUI is not in Docker)"
        else
            print_error "Server failed to start. Check logs with: docker-compose logs"
        fi
        ;;

    2)
        print_info "Stopping Gmail MCP Server..."
        docker-compose down
        print_success "Server stopped!"
        ;;

    3)
        print_info "Restarting Gmail MCP Server..."
        docker-compose restart
        print_success "Server restarted!"
        ;;

    4)
        print_info "Showing logs (Ctrl+C to exit)..."
        docker-compose logs -f
        ;;

    5)
        print_info "Server status:"
        docker-compose ps
        echo ""
        print_info "Resource usage:"
        docker stats --no-stream gmail-mcp-server 2>/dev/null || print_warning "Server not running"
        ;;

    6)
        print_info "Updating Gmail MCP Server..."
        docker-compose pull
        docker-compose up -d --build --force-recreate
        print_success "Server updated!"
        ;;

    7)
        print_warning "This will STOP the server and remove all containers!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            print_info "Stopping and removing containers..."
            docker-compose down
            print_success "All containers removed!"
        else
            print_info "Cancelled"
        fi
        ;;

    8)
        print_info "Goodbye!"
        exit 0
        ;;

    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

echo ""
print_info "Done!"
