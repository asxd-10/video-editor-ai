#!/usr/bin/env python3
"""
Verification script for Phase 1 dependencies.
Run this after installing requirements.txt to verify everything works.
"""

import sys

def verify_import(module_name, package_name=None):
    """Try to import a module and report success/failure"""
    if package_name is None:
        package_name = module_name
    
    try:
        __import__(module_name)
        print(f"✅ {package_name} - OK")
        return True
    except ImportError as e:
        print(f"❌ {package_name} - FAILED: {e}")
        return False

def main():
    print("=" * 60)
    print("Phase 1: Dependency Verification")
    print("=" * 60)
    print()
    
    results = []
    
    # Core dependencies (should already be installed)
    print("Core Dependencies:")
    print("-" * 60)
    results.append(verify_import("fastapi", "FastAPI"))
    results.append(verify_import("celery", "Celery"))
    results.append(verify_import("sqlalchemy", "SQLAlchemy"))
    results.append(verify_import("ffmpeg", "ffmpeg-python"))
    print()
    
    # Transcription
    print("Transcription & Speech Processing:")
    print("-" * 60)
    results.append(verify_import("faster_whisper", "faster-whisper"))
    results.append(verify_import("torch", "PyTorch"))
    print()
    
    # Audio Analysis
    print("Audio Analysis:")
    print("-" * 60)
    results.append(verify_import("librosa", "librosa"))
    results.append(verify_import("soundfile", "soundfile"))
    try:
        import silero_vad
        print("✅ silero-vad - OK")
        results.append(True)
    except ImportError as e:
        print(f"❌ silero-vad - FAILED: {e}")
        results.append(False)
    results.append(verify_import("pydub", "pydub"))
    print()
    
    # Scene Detection
    print("Scene Detection:")
    print("-" * 60)
    try:
        import scenedetect
        print("✅ scenedetect - OK")
        results.append(True)
    except ImportError as e:
        print(f"❌ scenedetect - FAILED: {e}")
        results.append(False)
    print()
    
    # Face Detection
    print("Face Detection:")
    print("-" * 60)
    results.append(verify_import("mediapipe", "mediapipe"))
    print()
    
    # LLM
    print("LLM Integration:")
    print("-" * 60)
    results.append(verify_import("transformers", "transformers"))
    print()
    
    # Summary
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Summary: {passed}/{total} dependencies verified")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All dependencies installed successfully!")
        return 0
    else:
        print("⚠️  Some dependencies failed. Please check the errors above.")
        print("   Run: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())

