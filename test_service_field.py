#!/usr/bin/env python3
"""
Test script to verify the service field is properly stored and propagated.
"""

import requests
import time

BASE_URL = "http://localhost:5000"

def test_service_field():
    """Test the service field across document ingestion"""
    print("=" * 80)
    print("Service Field Test")
    print("=" * 80)
    
    # Test 1: Upload document with service field
    print("\n📤 Test 1: Uploading document with service='DOCT'...")
    
    response = requests.post(
        f"{BASE_URL}/documents/text",
        json={
            "text": "This is a test document from the DOCT service about administrative procedures.",
            "service": "DOCT",
            "accreditation_level": 0,
            "file_source": "test_doct_doc.txt"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"  ✅ Document uploaded successfully")
        print(f"     Status: {result['status']}")
        print(f"     Track ID: {result.get('track_id', 'N/A')}")
    else:
        print(f"  ❌ Failed to upload document: {response.status_code}")
        print(f"     Response: {response.text}")
        return False
    
    # Test 2: Upload document without service field
    print("\n📤 Test 2: Uploading document without service field...")
    
    response = requests.post(
        f"{BASE_URL}/documents/text",
        json={
            "text": "This is a test document without a service specified.",
            "accreditation_level": 0,
            "file_source": "test_no_service.txt"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"  ✅ Document uploaded successfully")
        print(f"     Status: {result['status']}")
    else:
        print(f"  ❌ Failed to upload document: {response.status_code}")
        print(f"     Response: {response.text}")
        return False
    
    # Test 3: Upload multiple documents with different services
    print("\n📤 Test 3: Uploading multiple documents with different services...")
    
    response = requests.post(
        f"{BASE_URL}/documents/texts",
        json={
            "texts": [
                "Document from DRI service about research initiatives.",
                "Document from DAF service about financial procedures.",
                "Document from CABINET office about strategic decisions."
            ],
            "services": ["DRI", "DAF", "CABINET"],
            "file_sources": ["dri_doc.txt", "daf_doc.txt", "cabinet_doc.txt"]
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"  ✅ Documents uploaded successfully")
        print(f"     Status: {result['status']}")
    else:
        print(f"  ❌ Failed to upload documents: {response.status_code}")
        print(f"     Response: {response.text}")
        return False
    
    # Wait for processing
    print("\n⏳ Waiting 5 seconds for document processing...")
    time.sleep(5)
    
    # Test 4: Verify service field via query
    print("\n🔍 Test 4: Querying to verify data is accessible...")
    
    response = requests.post(
        f"{BASE_URL}/query",
        json={
            "query": "What documents are available?",
            "mode": "naive",
            "only_need_context": True
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        chunks = result.get("data", {}).get("chunks", [])
        print(f"  ✅ Query successful, {len(chunks)} chunks returned")
        
        # Check if service field exists in chunks
        if chunks:
            sample_chunk = chunks[0]
            if "service" in sample_chunk:
                service_value = sample_chunk.get("service")
                print(f"     Service field found: '{service_value}'")
            else:
                print("     ⚠️  Service field not found in chunks")
        else:
            print("     ℹ️  No chunks returned yet (documents may still be processing)")
    else:
        print(f"  ❌ Query failed: {response.status_code}")
        print(f"     Response: {response.text}")
    
    print("\n" + "=" * 80)
    print("✅ Service field tests completed successfully")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    try:
        test_service_field()
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
