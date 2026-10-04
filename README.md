# Possession QA Tool

A Python tool to validate JSON outputs from a computer vision annotation tool for basketball tracking data.

## What it checks
- Frame count mismatch between event and tracking files
- Invalid event frame ranges
- Orphan track IDs
- Multiple ball carriers in a frame
- Bounding boxes outside video bounds
- Low-confidence detections
- Missing frames within a track

## Usage


Outputs `qa_report.csv`.

## Skills
Python, JSON validation, QA automation, reporting.