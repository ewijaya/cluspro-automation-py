# ClusPro Automation - Python

Python automation tool for the [ClusPro](https://cluspro.bu.edu/) protein docking web server.

Automates job submission, queue monitoring, results parsing, and file downloading for protein-protein docking experiments.

## Features

- **Job Submission**: Submit single or batch docking jobs
- **Queue Monitoring**: Check job queue status in real-time
- **Results Parsing**: Parse completed jobs across multiple result pages
- **Download**: Download PDB models and energy scores
- **File Organization**: Organize results into meaningful directory structures
- **CLI Interface**: Full command-line interface for all operations
- **No External Server**: Uses `webdriver-manager` - no need to manually run Selenium server

## Installation

### Prerequisites

- Python 3.10 or higher
- Firefox browser installed

### Install from source

```bash
git clone <repo-url>
cd cluspro-automation-py

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

## Quick Start

For a complete step-by-step guide, see [docs/WORKFLOW.md](docs/WORKFLOW.md).

### Verify Installation

Test the installation using the included example PDB files:

```bash
# Submit a test job
cluspro submit -n "test-job" \
  -r examples/receptor.pdb \
  -l examples/ligand.pdb \
  -s gpu

# Verify submission
cluspro queue --pattern "test-.*"
```

### CLI Usage

```bash
# Submit a single job
cluspro submit -n "test-dock" -r receptor.pdb -l ligand.pdb

# Submit batch jobs from CSV
cluspro submit-batch -i jobs.csv -o results.csv

# Check queue status
cluspro queue --pattern "bb-.*"

# Get finished job results
cluspro results --pattern "pad-.*" --output job_ids.txt

# Download results
cluspro download --job-id 1154309 --pdb
cluspro download-batch --ids "1154309:1154320" --pdb

# Organize downloaded files
cluspro organize -i mapping.csv --pdb
```

### Python API Usage

```python
from cluspro import submit_job, download_results, get_finished_jobs

# Submit a job
submit_job(
    job_name="my-docking-job",
    receptor_pdb="/path/to/receptor.pdb",
    ligand_pdb="/path/to/ligand.pdb",
    server="gpu"
)

# Get finished jobs
df = get_finished_jobs(filter_pattern="my-.*")
print(df[["job_name", "job_id", "status"]])

# Download results
download_results(job_id=1154309, download_pdb=True)
```

## CLI Commands

### Submit Commands

```bash
# Submit single job
cluspro submit -n NAME -r RECEPTOR.pdb -l LIGAND.pdb [-s gpu|cpu]

# Submit batch from CSV
cluspro submit-batch -i jobs.csv [-o results.csv] [--stop-on-error]

# Validate without submitting
cluspro dry-run -i jobs.csv
```

**CSV format for batch submission:**
```csv
job_name,receptor_pdb,ligand_pdb,server
job-1,/path/to/rec1.pdb,/path/to/lig1.pdb,gpu
job-2,/path/to/rec2.pdb,/path/to/lig2.pdb,gpu
```

### Queue Commands

```bash
# Check queue status
cluspro queue [-u USER] [-p PATTERN] [-o output.csv]

# Examples
cluspro queue --user piper
cluspro queue --pattern "bb-.*"
```

### Results Commands

```bash
# Get finished jobs
cluspro results [-p PATTERN] [--max-pages N] [-o job_ids.txt] [--csv results.csv]

# Get summary statistics
cluspro summary [-p PATTERN]
```

### Download Commands

```bash
# Download single job
cluspro download --job-id 1154309 [--pdb|--no-pdb] [-o OUTPUT_DIR]

# Download batch
cluspro download-batch --ids "1154309:1154320,1154325" [--pdb]
```

### Organize Commands

```bash
# Organize with mapping file
cluspro organize -i mapping.csv [--pdb|--no-pdb]

# List organized results
cluspro list [-d DIRECTORY]
```

**CSV format for organization:**
```csv
job_name,peptide_name,receptor_name
bb-1,hmgb1.144,mLrp1
bb-2,hmgb1.144,hLrp1
```

### Utility Commands

```bash
# Expand job ID sequence
cluspro expand "1154309:1154312,1154315"
# Output: 1154309,1154310,1154311,1154312,1154315

# Compress job IDs
cluspro compress 1154309 1154310 1154311 1154315
# Output: 1154309:1154311,1154315

# Show configuration
cluspro config
```

## Configuration

Default configuration is in `config/settings.yaml`.

For user-specific settings, copy to `~/.cluspro/settings.yaml`:

```bash
mkdir -p ~/.cluspro
cp config/settings.yaml ~/.cluspro/settings.yaml
```

### Key Configuration Options

```yaml
browser:
  headless: true          # Run without visible browser
  type: "firefox"         # Browser type

paths:
  output_dir: "~/Desktop/ClusPro_results"
  organized_dir: "~/Desktop/ClusPro_results/full_names"

timeouts:
  submission_wait: 10     # Wait after submission
  download_wait: 10       # Wait for downloads
  between_jobs: 10        # Delay between batch jobs

batch:
  max_pages_to_parse: 50  # Max result pages to scan
```

## Python API Reference

### Submit Module

```python
from cluspro import submit_job, submit_batch

# Single job
job_id = submit_job(
    job_name="test",
    receptor_pdb="/path/to/receptor.pdb",
    ligand_pdb="/path/to/ligand.pdb",
    server="gpu",
    headless=True
)

# Batch submission
import pandas as pd
jobs = pd.DataFrame({
    "job_name": ["job1", "job2"],
    "receptor_pdb": ["/path/rec1.pdb", "/path/rec2.pdb"],
    "ligand_pdb": ["/path/lig1.pdb", "/path/lig2.pdb"]
})
results = submit_batch(jobs, continue_on_error=True)
```

### Queue Module

```python
from cluspro import get_queue_status

df = get_queue_status(
    filter_user="piper",
    filter_pattern="bb-.*"
)
print(df[["job_name", "status"]])
```

### Results Module

```python
from cluspro import get_finished_jobs, group_sequences

df = get_finished_jobs(filter_pattern="pad-.*", max_pages=50)

# Get compressed job IDs for batch download
job_ids = group_sequences(df["job_id"].tolist())
print(job_ids)  # "1154309:1154320,1154325"
```

### Download Module

```python
from cluspro import download_results, download_batch

# Single job
path = download_results(job_id=1154309, download_pdb=True)

# Batch download
results = download_batch(
    job_ids="1154309:1154320",
    download_pdb=True,
    continue_on_error=True
)
```

### Organize Module

```python
from cluspro import organize_results

mapping = [
    {"job_name": "bb-1", "peptide_name": "hmgb1.144", "receptor_name": "mLrp1"},
    {"job_name": "bb-2", "peptide_name": "hmgb1.144", "receptor_name": "hLrp1"},
]
organize_results(mapping, include_pdb=True)
```

### Utility Functions

```python
from cluspro import expand_sequences, group_sequences

# Expand: "1:3,5" -> [1, 2, 3, 5]
ids = expand_sequences("1154309:1154312,1154315")

# Compress: [1, 2, 3, 5] -> "1:3,5"
compressed = group_sequences([1154309, 1154310, 1154311, 1154315])
```

## Complete Workflow Example

```python
from cluspro import (
    submit_batch,
    get_finished_jobs,
    download_batch,
    organize_results,
    group_sequences
)
import pandas as pd
import time

# 1. Prepare jobs
jobs = pd.DataFrame({
    "job_name": ["dock-1", "dock-2", "dock-3"],
    "receptor_pdb": ["rec.pdb"] * 3,
    "ligand_pdb": ["lig1.pdb", "lig2.pdb", "lig3.pdb"],
    "peptide_name": ["peptide1", "peptide2", "peptide3"],
    "receptor_name": ["receptor"] * 3
})

# 2. Submit jobs
submit_results = submit_batch(jobs[["job_name", "receptor_pdb", "ligand_pdb"]])
print(f"Submitted {len(submit_results)} jobs")

# 3. Wait for completion (check periodically)
while True:
    finished = get_finished_jobs(filter_pattern="dock-.*")
    if len(finished) == len(jobs):
        break
    print(f"Waiting... {len(finished)}/{len(jobs)} complete")
    time.sleep(300)  # Check every 5 minutes

# 4. Download results
job_ids = group_sequences(finished["job_id"].tolist())
download_batch(job_ids, download_pdb=True)

# 5. Organize files
mapping = jobs[["job_name", "peptide_name", "receptor_name"]]
organize_results(mapping, include_pdb=True)

print("Workflow complete!")
```

## Troubleshooting

### Browser Issues

If you encounter browser-related errors:

```bash
# Update webdriver
pip install --upgrade webdriver-manager

# Clear webdriver cache
rm -rf ~/.wdm
```

**macOS**: If Firefox isn't detected, specify the binary path in `~/.cluspro/settings.yaml`:

```yaml
browser:
  firefox_binary: /Applications/Firefox.app/Contents/MacOS/firefox
```

### Download Failures

If downloads fail or timeout:

1. Increase timeout in config:
   ```yaml
   timeouts:
     download_wait: 30
   ```

2. Run with visible browser to debug:
   ```bash
   cluspro download --job-id 123 --no-headless
   ```

### Network Issues

For slow or unreliable connections:

```yaml
timeouts:
  page_load_wait: 10
  between_jobs: 30

browser:
  page_load_timeout: 60
```

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

### Code Formatting

```bash
black src/
ruff check src/
```

## License

MIT License

## Acknowledgments

- [ClusPro](https://cluspro.bu.edu/) - Protein docking web server
- Original R implementation using RSelenium
