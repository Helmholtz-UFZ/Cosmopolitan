#!/bin/bash
#
# Test script to fill object storage bucket to verify behavior when full
# This helps test the hypothesis that rclone sync fails silently when bucket is full
#
# Usage: ./fill_bucket_test.sh
# Stop with Ctrl+C when done

set -e

# Configuration
TEMP_DIR="${HOME}/tmp"
REMOTE="cosmopolitan-remote:cosmopolitan-prod"
FILE_SIZE_MB=300

# Create temp directory if it doesn't exist
mkdir -p "${TEMP_DIR}"

echo "Starting bucket fill test..."
echo "Temp directory: ${TEMP_DIR}"
echo "Remote: ${REMOTE}"
echo "File size: ${FILE_SIZE_MB} MB"
echo ""
echo "Press Ctrl+C to stop"
echo ""

counter=1

while true; do
    # Generate unique filename using timestamp and random number
    timestamp=$(date +%Y%m%d_%H%M%S)
    random=$(head -c 8 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 8)
    filename="test_${timestamp}_${random}_${counter}.bin"
    filepath="${TEMP_DIR}/${filename}"

    echo "[${counter}] Creating ${filename} (${FILE_SIZE_MB}MB)..."

    # Create 100MB file with random data
    dd if=/dev/urandom of="${filepath}" bs=1M count="${FILE_SIZE_MB}" 2>/dev/null

    echo "[${counter}] Uploading to ${REMOTE}/${filename}..."

    # Try to copy to remote and capture exit code
    if rclone copy "${filepath}" "${REMOTE}" --s3-no-check-bucket; then
        echo "[${counter}] ✓ Upload successful"

        # Remove local file to save disk space
        rm -f "${filepath}"
        echo "[${counter}] Local file removed"
    else
        exit_code=$?
        echo "[${counter}] ✗ Upload FAILED with exit code: ${exit_code}"
        echo ""
        echo "==================================="
        echo "BUCKET APPEARS TO BE FULL!"
        echo "Exit code: ${exit_code}"
        echo "Failed on file: ${filename}"
        echo "File still at: ${filepath}"
        echo "==================================="

        # Keep the failed file for inspection
        break
    fi

    echo "[${counter}] Total uploaded: $((counter * FILE_SIZE_MB)) MB"
    echo ""

    counter=$((counter + 1))

    # Small delay to avoid hammering the service
    sleep 1
done

echo ""
echo "Test stopped after ${counter} files"
echo "Total uploaded: $(((counter - 1) * FILE_SIZE_MB)) MB"
