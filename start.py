#!/usr/bin/env python3
"""
Frankfurt Flight Tracker - Startup Script
This script installs dependencies and starts the backend server.
"""

import subprocess
import sys
import os
import webbrowser
import time
from pathlib import Path

def install_dependencies():
    """Install required Python packages"""
    print("Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False
    return True

def create_data_directory():
    """Create the data directory if it doesn't exist"""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print("✅ Data directory ready")

def start_backend():
    """Start the Flask backend server"""
    print("Starting backend server...")
    try:
        # Change to backend directory and start the server
        os.chdir("backend")
        subprocess.Popen([sys.executable, "app.py"])
        print("✅ Backend server started on http://localhost:8081")
        return True
    except Exception as e:
        print(f"❌ Error starting backend server: {e}")
        return False

def open_frontend():
    """Open the frontend in the default browser"""
    # Get the project root directory (go back from backend directory)
    project_root = Path.cwd().parent
    frontend_path = project_root / "frontend" / "index.html"
    print(f"Opening frontend at: {frontend_path}")
    
    # Wait a moment for the backend to start
    time.sleep(3)
    
    try:
        webbrowser.open(f"file://{frontend_path}")
        print("✅ Frontend opened in browser")
    except Exception as e:
        print(f"❌ Error opening frontend: {e}")
        print(f"Please manually open: {frontend_path}")

def main():
    print("🚀 Frankfurt Flight Tracker - Starting up...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("backend/app.py").exists():
        print("❌ Error: Please run this script from the flight-tracker directory")
        return
    
    # Install dependencies
    if not install_dependencies():
        return
    
    # Create data directory
    create_data_directory()
    
    # Start backend
    if not start_backend():
        return
    
    # Open frontend
    open_frontend()
    
    print("\n" + "=" * 50)
    print("🎉 Flight Tracker is now running!")
    print("\nBackend API: http://localhost:8081")
    print("Frontend: Open frontend/index.html in your browser")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down Flight Tracker...")

if __name__ == "__main__":
    main() 