#!/bin/bash

# Gmail MCP + OpenWebUI Setup Script
# This script automates the setup process

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
║      Gmail MCP + OpenWebUI Setup                         ║
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
echo "1) Start services"
echo "2) Stop services"
echo "3) Restart services"
echo "4) View logs"
echo "5) Download LLM model"
echo "6) Check status"
echo "7) Update services"
echo "8) Clean up (remove all data)"
echo "9) Exit"
echo ""
read -p "Enter your choice (1-9): " choice

case $choice in
    1)
        print_info "Starting services..."
        docker-compose up -d
        print_success "Services started!"
        echo ""
        print_info "Waiting for services to be ready..."
        sleep 5
        
        print_info "Checking if services are running..."
        if docker-compose ps | grep -q "Up"; then
            print_success "Services are running!"
            echo ""
            print_info "OpenWebUI: http://localhost:3002"
            print_info "Ollama API: http://localhost:11434"
            echo ""
            print_warning "Don't forget to download a model!"
            print_info "Run: docker exec -it ollama ollama pull llama3.2"
        else
            print_error "Services failed to start. Check logs with: docker-compose logs"
        fi
        ;;
    
    2)
        print_info "Stopping services..."
        docker-compose down
        print_success "Services stopped!"
        ;;
    
    3)
        print_info "Restarting services..."
        docker-compose restart
        print_success "Services restarted!"
        ;;
    
    4)
        print_info "Showing logs (Ctrl+C to exit)..."
        docker-compose logs -f
        ;;
    
    5)
        print_info "Available models:"
        echo "1) llama3.2 (3B) - Fast, good for most tasks"
        echo "2) llama3.1 (8B) - Better quality, slower"
        echo "3) mistral (7B) - Good balance"
        echo "4) qwen2.5 (7B) - Strong function calling"
        echo ""
        read -p "Enter model number (1-4): " model_choice
        
        case $model_choice in
            1) MODEL="llama3.2";;
            2) MODEL="llama3.1";;
            3) MODEL="mistral";;
            4) MODEL="qwen2.5";;
            *) print_error "Invalid choice"; exit 1;;
        esac
        
        print_info "Downloading $MODEL..."
        docker exec -it ollama ollama pull $MODEL
        print_success "Model $MODEL downloaded!"
        ;;
    
    6)
        print_info "Service status:"
        docker-compose ps
        echo ""
        print_info "Resource usage:"
        docker stats --no-stream
        echo ""
        print_info "Available models:"
        docker exec -it ollama ollama list
        ;;
    
    7)
        print_info "Updating services..."
        docker-compose pull
        docker-compose up -d --force-recreate
        print_success "Services updated!"
        ;;
    
    8)
        print_warning "This will DELETE all data including models and conversations!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            print_info "Stopping and removing everything..."
            docker-compose down -v
            print_success "All data removed!"
        else
            print_info "Cancelled"
        fi
        ;;
    
    9)
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
