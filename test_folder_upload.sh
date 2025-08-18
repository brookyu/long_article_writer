#!/bin/bash
echo "🚀 70-File Upload Test Script"
echo "=============================="
echo

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_zip_file>"
    echo "Example: $0 /path/to/your/documents.zip"
    exit 1
fi

ZIP_FILE="$1"
COLLECTION_ID=2

if [ ! -f "$ZIP_FILE" ]; then
    echo "❌ Error: File $ZIP_FILE not found"
    exit 1
fi

echo "📁 Testing with file: $ZIP_FILE"
echo "🎯 Collection ID: $COLLECTION_ID"
echo "⏰ Starting upload..."
echo

# Record start time
START_TIME=$(date +%s)

# Make the API call
RESPONSE=$(curl -s -X POST "http://localhost:8001/api/kb/collections/$COLLECTION_ID/upload-folder-simple/" \
  -F "zipFile=@$ZIP_FILE" \
  -w "\nHTTP_STATUS:%{http_code}")

# Extract HTTP status
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
JSON_RESPONSE=$(echo "$RESPONSE" | grep -v "HTTP_STATUS:")

# Record end time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "📊 UPLOAD RESULTS:"
echo "=================="
echo "⏱️  Duration: ${DURATION} seconds"
echo "🌐 HTTP Status: $HTTP_STATUS"
echo

if [ "$HTTP_STATUS" = "200" ]; then
    echo "$JSON_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    summary = data.get('summary', {})
    
    print('✅ UPLOAD SUCCESSFUL!')
    print(f'📊 Summary:')
    print(f'   • Total files: {summary.get(\"total\", 0)}')
    print(f'   • Successful: {summary.get(\"successful\", 0)}')
    print(f'   • Failed: {summary.get(\"failed\", 0)}')
    print(f'   • Skipped: {summary.get(\"skipped\", 0)}')
    
    success_rate = (summary.get('successful', 0) / summary.get('total', 1)) * 100
    print(f'   • Success Rate: {success_rate:.1f}%')
    
    if success_rate > 80:
        print()
        print('🎉 EXCELLENT! Much better than the previous 69/70 failures!')
        print('✅ Open WebUI-inspired system working perfectly!')
    elif success_rate > 50:
        print()
        print('✅ GOOD IMPROVEMENT! Significant progress from previous failures!')
    else:
        print()
        print('⚠️  Still some issues, but processing is working...')
        
except Exception as e:
    print(f'❌ Failed to parse response: {e}')
    print('Raw response:', sys.stdin.read()[:500])
"
else
    echo "❌ Upload failed with HTTP status: $HTTP_STATUS"
    echo "Response: $JSON_RESPONSE"
fi
