"""
Main entry point for Lasty Language Smart Trainer
Run this file to start the Streamlit application
"""
import streamlit as st
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the main application
from app import main

if __name__ == "__main__":
    main()
