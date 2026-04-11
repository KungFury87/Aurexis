#!/usr/bin/env python3
"""Quick test: verify IP Webcam feed is reachable and grab one frame."""

import sys
import cv2
import numpy as np

FEED_URL = "http://192.168.12.251:8080/video"
SHOT_URL = "http://192.168.12.251:8080/shot.jpg"

print(f"Testing IP Webcam connection...")
print(f"  Video stream: {FEED_URL}")
print(f"  Snapshot URL: {SHOT_URL}")
print()

# Method 1: Try snapshot (single JPEG grab — most reliable)
import urllib.request
try:
    print("Grabbing snapshot...")
    resp = urllib.request.urlopen(SHOT_URL, timeout=5)
    img_array = np.frombuffer(resp.read(), dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if frame is not None:
        h, w = frame.shape[:2]
        print(f"  SUCCESS — snapshot grabbed: {w}x{h}")
        cv2.imwrite("test_live_frame.jpg", frame)
        print(f"  Saved to test_live_frame.jpg")
    else:
        print("  FAIL — got response but couldn't decode image")
except Exception as e:
    print(f"  Snapshot failed: {e}")

# Method 2: Try video stream (MJPEG — for continuous feed)
print()
print("Testing video stream (grabbing 3 frames)...")
cap = cv2.VideoCapture(FEED_URL)
if cap.isOpened():
    for i in range(3):
        ret, frame = cap.read()
        if ret:
            h, w = frame.shape[:2]
            print(f"  Frame {i+1}: {w}x{h} — OK")
        else:
            print(f"  Frame {i+1}: read failed")
    cap.release()
    print("  Video stream works!")
else:
    print("  Could not open video stream.")
    print("  (This is OK — snapshot mode will work fine)")

print()
print("If you see SUCCESS above, the feed is working.")
print("You can close this and run the live pipeline.")
