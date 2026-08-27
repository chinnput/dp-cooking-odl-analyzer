# Onboarding & Project Handover Summary: DP Cooking ODL Analyzer

**New Owner:** Chinnput  
**Update Date:** August 25, 2026  
**Primary Scope (Current Phase):** Focus on Line 2 | Integration with PI System via MI Cube API & SharePoint | "Just Visualize, Not Optimize"

---

## 1. Project Overview & Historical Baseline

The **DP Cooking ODL Analyzer** project aims to analyze and minimize process variation across the **DP Cooking (Digesters 1–4)** process and the **ODL (Oxygen Delignification)** washing & bleaching stage.

### Historical Work Completed
* **Batch Extraction & Classification:** Analyzed 30,529 rows of sensor data to extract 1,168 batches. Utilized **PCA + Unsupervised Clustering** to classify batches into **Normal (1,109 batches)** and **Abnormal (59 batches, top 5%)**.
* **Root Cause of Abnormal Batches:** Identified that abnormal batches are primarily driven by severe process slowdowns, with production dropping by **38–43%**.
* **Specific Consumption Spikes:** Discovered massive resource waste during abnormal batches—Specific Steam Consumption spiked by **+3,165%** and Oxygen feed spiked by **+3,693%**. This occurs because production drops near zero while steam and chemical feeding rates remain active.
* **Digester Performance Breakdown (D1–D4):**
  * **Digester 3:** Most stable and reliable with the highest production rate (~284 ADT/D).
  * **Digester 1:** Suffers from **Trip / Sudden Shutdowns** (production drops to zero).
  * **Digester 4:** Suffers from **Control Loop Drift**, causing the highest SOP violation rate (23.4%).
  * **Digester 2:** Displays high within-batch volatility but features effective interlock logic to throttle chemical flows during process upsets.

---

## 2. Latest Guidance & Architectural Updates

1. **Line 2 Scope Concentration:** Focus primary analytical efforts specifically on **Line 2**.
2. **Key Metrics Integration:**
   * **Kappa Value** (pulp quality and delignification metric).
   * **Pulp Consistency Value** (pulp fiber concentration percentage).
3. **Current Phase Philosophy:** **"Just Visualize, Not Optimize"** — Focus on extracting data, establishing pipelines, and displaying process variation clearly before attempting process optimization.
4. **Data Source & Direct Integration Architecture:**
   * Transitioning from manual OneDrive Excel files to direct automated push into the **AVEVA PI System**.
   * **No Intermediate Database Required:** Data will be pushed directly from Python to PI Server tags.
   * **MI Cube API Wrapper:** Writing to PI Tags will be executed via the **MI Cube API** endpoint (`https://micube.scg.com/v2/api/Datacenter/PIServer/WriteValue/ByTag/`) using payload parameters (`token`, `server`, `tag`, `value`, `timestamp`).
5. **SharePoint Lab Data Pipeline:** Connect time-series lab data (Kappa & Consistency) stored on SharePoint/OneDrive into the active pipeline.
6. **Rule-Based Time Matching Problem:** Lab samples are recorded at fixed intervals (e.g., 10:00, 11:00), whereas batch execution times vary (e.g., 10:30). Develop rule-based matching logic to align lab values with corresponding batch windows.
7. **Digester 4 / Batch 4 Variation Tracking:** Focus on Digester 4 due to its high process variation. Aggregate batch ranges over a monthly period to analyze variation distributions and patterns.
8. **Folder Organization:** Designated sync scripts folder: `onedrive_to_pi` (or `pi_sync`).

---

## 3. Step-by-Step Action Plan for New Owner

Execution Process Workflow:
Windows Task Scheduler / `.bat` script --> Python Script Execution --> Read Excel from OneDrive / SharePoint --> Filter New Data & Rule-Based Time Matching --> Post JSON Payload to MI Cube API --> Write Values to PI Tags in PI Server --> Save Last Sync Timestamp

### Step 1: Pipeline Setup & MI Cube API Integration (`onedrive_to_pi`)
* **Objective:** Connect lab metrics (Kappa, Consistency) from SharePoint/OneDrive and push directly to **PI Server** via **MI Cube API**.
* **Execution:**
  * Create folder `onedrive_to_pi` to store automation scripts and batch files.
  * Develop Python script using `requests` to read Excel rows, format timestamps, and invoke `https://micube.scg.com/v2/api/Datacenter/PIServer/WriteValue/ByTag/`.
  * Set up `run_pi_sync.bat` and schedule automated execution via Windows Task Scheduler.

### Step 2: Rule-Based Time Matching Logic
* **Objective:** Resolve the timestamp mismatch between fixed lab sampling times (10:00, 11:00) and active batch execution windows (e.g., 10:30).
* **Execution:**
  * Develop rule-based Python logic (e.g., Nearest Neighbor or Forward-Fill interpolation) to map lab sample values to their corresponding batch ID based on batch start and end timestamps.

### Step 3: Line 2 Visualization & Monthly Analytics
* **Objective:** Fulfill the "Just Visualize, Not Optimize" objective.
* **Execution:**
  * Build dedicated visualization dashboards/plots for **Line 2**.
  * Plot interactions between `Production Rate`, `Pulp Consistency`, `Kappa Value`, and `Specific Consumption`.
  * Aggregate batch ranges across the entire month to visualize monthly distribution patterns.
  * Create detailed visual charts focusing on **Digester 4 / Batch 4** to highlight its high process variation.

### Step 4: Phase Analyze & Optimization (Future Phase)
* **Objective:** Transition to in-depth root cause analysis and process optimization once visualization is complete.
* **Execution:**
  * Build Predictive Early Warning models to detect upcoming abnormal batch conditions.
  * Collaborate with Process & Automation engineers to propose **Ratio Control / Interlock Tuning** for steam and chemical valves during production slowdowns.

---

## 4. Workspace Quick Reference & File Guide

* `summary.md`: Complete archive of past statistical and cluster analysis findings.
* `summaryUpdate.md`: (This file) Project update, onboarding handover, and step-by-step action plan.
* `onedrive_to_pi/`: Dedicated directory for OneDrive-to-PI sync scripts (`.py` and `.bat`).
* `clean_data.py`: Preprocesses raw data and handles missing/string sensor errors.
* `extract_signatures.py`: Extracts batch windows and calculates specific resource consumption metrics.
* `cluster_analysis.py`: Performs PCA + Unsupervised Clustering to classify Normal vs Abnormal batches.
* `generate_sop_reference.py`: Derives data-driven SOP limits (5th–95th percentiles).
* `main_analysis.py`: Calculates SOP violation rates and identifies worst-offending batches.
* `analyze_digester_performance.py`: Compares statistical performance across Digesters 1–4.
* `visualize_*.py`: Plotting scripts for boxplots, KDE density bell curves, heatmaps, and scatter plots.


