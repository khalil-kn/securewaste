#!/usr/bin/env python
"""Run tests programmatically."""

import sys
import os

os.chdir(r'C:\Users\medkh\projects\securewaste')
sys.path.insert(0, '.')

import pytest

# Run unit tests for upload
print("Running upload unit tests...")
result = pytest.main(['-v', 'tests/unit/test_upload.py'])
print(f"Unit tests exit code: {result}")

print("\nRunning upload security tests...")
result = pytest.main(['-v', 'tests/security/test_upload_security.py'])
print(f"Security tests exit code: {result}")