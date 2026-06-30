# Product Overview

git-metrics is a CLI tool that gathers commit metrics from a Git repository and generates XLSX spreadsheets.

## Core Capabilities

- Parses `git log` output to count unique commits per author (deduplicated by Change-Id)
- Generates XLSX reports with author names, emails, and commit counts for a given time period
- Supports grouping authors by email pattern and calculating group subtotals
- Merges multiple period reports into a single multi-column spreadsheet
- Provides a config file workflow for recurring report generation with auto-advancing dates
- Includes a helper script to pull multiple remote branches locally before analysis
