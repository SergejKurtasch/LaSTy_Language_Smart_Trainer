#!/usr/bin/env python3
"""
Test script for LaSTy Language Smart Trainer connections
This script tests all external connections before running the main app
"""

import os
import sys
import time
from dotenv import load_dotenv

def test_env_file():
    """Test if .env file exists and is readable"""
    print("🔧 Testing .env file...")
    start_time = time.time()
    
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        return False, 0
    
    try:
        load_dotenv()
        elapsed_time = time.time() - start_time
        print(f"✅ .env file loaded successfully ({elapsed_time:.3f}s)")
        return True, elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ Failed to load .env file: {e} ({elapsed_time:.3f}s)")
        return False, elapsed_time

def test_supabase_connection():
    """Test Supabase connection"""
    print("🔧 Testing Supabase connection...")
    start_time = time.time()
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    if not SUPABASE_URL or SUPABASE_URL == "your_supabase_url_here":
        elapsed_time = time.time() - start_time
        print(f"❌ SUPABASE_URL not set or using default value ({elapsed_time:.3f}s)")
        return False, elapsed_time
    
    if not SUPABASE_KEY or SUPABASE_KEY == "your_supabase_key_here":
        elapsed_time = time.time() - start_time
        print(f"❌ SUPABASE_KEY not set or using default value ({elapsed_time:.3f}s)")
        return False, elapsed_time
    
    try:
        from supabase import create_client
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Test connection
        result = client.table("users").select("user_id").limit(1).execute()
        elapsed_time = time.time() - start_time
        print(f"✅ Supabase connection successful ({elapsed_time:.3f}s)")
        return True, elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ Supabase connection failed: {e} ({elapsed_time:.3f}s)")
        return False, elapsed_time

def test_openai_connection():
    """Test OpenAI connection"""
    print("🔧 Testing OpenAI connection...")
    start_time = time.time()
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
        elapsed_time = time.time() - start_time
        print(f"❌ OPENAI_API_KEY not set or using default value ({elapsed_time:.3f}s)")
        return False, elapsed_time
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Test connection with a simple request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        elapsed_time = time.time() - start_time
        print(f"✅ OpenAI connection successful ({elapsed_time:.3f}s)")
        return True, elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ OpenAI connection failed: {e} ({elapsed_time:.3f}s)")
        return False, elapsed_time

def main():
    """Run all connection tests"""
    print("🚀 Starting connection tests for LaSTy Language Smart Trainer...")
    print("=" * 60)
    
    tests = [
        ("Environment File", test_env_file),
        ("Supabase Connection", test_supabase_connection),
        ("OpenAI Connection", test_openai_connection)
    ]
    
    results = []
    total_start_time = time.time()
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        try:
            result, elapsed_time = test_func()
            results.append((test_name, result, elapsed_time))
        except Exception as e:
            elapsed_time = time.time() - time.time()  # 0 for crashed tests
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False, elapsed_time))
    
    total_elapsed_time = time.time() - total_start_time
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    
    all_passed = True
    for test_name, result, elapsed_time in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status} ({elapsed_time:.3f}s)")
        if not result:
            all_passed = False
    
    print(f"\n⏱️  Total execution time: {total_elapsed_time:.3f}s")
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! The application should work correctly.")
    else:
        print("⚠️  Some tests failed. Please check the configuration.")
        print("\n📝 Next steps:")
        print("1. Create/update .env file with real API keys")
        print("2. Ensure Supabase database is set up")
        print("3. Verify OpenAI API key is valid")
        print("4. Run this test again")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
