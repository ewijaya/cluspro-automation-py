# ClusPro Automation - Python

Python automation tool for the [ClusPro](https://cluspro.bu.edu/) protein docking web server.

Automates job submission, queue monitoring, results parsing, and file downloading for protein-protein docking experiments.

## Features

- **Job Submission**: Submit single or batch docking jobs
- **Queue Monitoring**: Check job queue status in real-time
- **Results Parsing**: Parse completed jobs across multiple result pages
- **Download**: Download PDB models and energy scores
- **File Organization**: Organize results into meaningful directory structures
- **Docking Validation**: Validate docking poses against receptor topology (GPCR extracellular/TM/IC regions)
- **Job Persistence**: SQLite database for tracking jobs and resuming interrupted batches
- **Retry Logic**: Automatic retry with exponential backoff for flaky operations
- **Authentication**: Guest mode (default) or account login with multiple credential sources
- **CLI Interface**: Full command-line interface for all operations
- **No External Server**: Uses `webdriver-manager` - no need to manually run Selenium server

[![CI](https://github.com/ewijaya/cluspro-automation-py/actions/workflows/ci.yml/badge.svg)](https://github.com/ewijaya/cluspro-automation-py/actions/workflows/ci.yml)

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

### Validate Commands

Validate docking poses against receptor topology (requires `pip install cluspro-automation-py[validate]`):

```bash
# Validate docking results
cluspro validate -r receptor.pdb -d ./results -t topology.json

# With output directory
cluspro validate -r receptor.pdb -d ./results -t topology.json -o ./validation

# Validate all models (not just min-clash per target)
cluspro validate -r receptor.pdb -d ./results -t topology.json --all-models
```

**Topology JSON format** (see `examples/MRGX2_MOUSE_topology.json`):
```json
{
  "extracellular": [[1, 45], [97, 107], [177, 195], [261, 275]],
  "transmembrane": [[46, 66], [76, 96], [108, 128], [156, 176]],
  "intracellular": [[67, 75], [129, 155], [217, 239], [297, 352]],
  "alignment_residues": [97, 107]
}
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

### Jobs Commands (Database)

Track and resume batch submissions using the built-in job database:

```bash
# List all tracked jobs
cluspro jobs list

# List jobs by status
cluspro jobs list --status pending
cluspro jobs list --status failed

# List jobs in a specific batch
cluspro jobs list --batch my-batch-001

# Show batch summary
cluspro jobs status --batch my-batch-001

# Resume interrupted batch submission
cluspro jobs resume --batch my-batch-001

# Resume including failed jobs (retry)
cluspro jobs resume --batch my-batch-001 --include-failed
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
  geckodriver_path: ""    # Optional: direct path to geckodriver (bypasses GitHub API)

paths:
  output_dir: "~/Desktop/ClusPro_results"
  organized_dir: "~/Desktop/ClusPro_results/full_names"

timeouts:
  submission_wait: 10     # Wait after submission
  download_wait: 10       # Wait for downloads
  between_jobs: 10        # Delay between batch jobs

batch:
  max_pages_to_parse: 50  # Max result pages to scan

retry:
  max_attempts: 3         # Retry attempts for failed operations
  min_wait: 2             # Min wait between retries (seconds)
  max_wait: 60            # Max wait between retries (seconds)
  multiplier: 2           # Exponential backoff multiplier

database:
  # path: "~/.cluspro/jobs.db"  # Job tracking database location
```

## Authentication

By default, the tool uses **guest mode** (no account required). To use your ClusPro account, configure credentials using one of these methods (in priority order):

### 1. Environment Variables (Recommended)

```bash
export CLUSPRO_USERNAME="your_username"
export CLUSPRO_PASSWORD="your_password"

# Now all commands will use account login automatically
cluspro submit -n "my-job" -r receptor.pdb -l ligand.pdb
```

### 2. Configuration File

Add credentials to `~/.cluspro/settings.yaml`:

```yaml
credentials:
  username: "your_username"
  password: "your_password"
  default_mode: "auto"  # auto, guest, or account
```

### 3. Interactive Prompt

Use `--login` flag to prompt for credentials:

```bash
cluspro --login submit -n "my-job" -r receptor.pdb -l ligand.pdb
# Prompts: Username: _
# Prompts: Password: _
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--guest` | Force guest mode (ignore any configured credentials) |
| `--login` | Force account login (prompts if no credentials found) |
| (none) | Auto mode: uses account if credentials available, otherwise guest |

```bash
# Force guest mode even with credentials configured
cluspro --guest submit -n "my-job" -r receptor.pdb -l ligand.pdb

# Force account login
cluspro --login download --job-id 123456 --pdb
```

### Python API

```python
from cluspro import submit_job, get_credentials, Credentials, CredentialSource

# Auto mode (uses credentials if available)
submit_job("my-job", "receptor.pdb", "ligand.pdb")

# Get credentials from env/config
creds = get_credentials()
if creds:
    print(f"Using {creds.source.value} credentials")

# Force guest mode
submit_job("my-job", "receptor.pdb", "ligand.pdb", force_guest=True)

# With explicit credentials
creds = Credentials(
    username="user",
    password="pass",
    source=CredentialSource.CONFIG
)
submit_job("my-job", "receptor.pdb", "ligand.pdb", credentials=creds)
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

### Database Module

```python
from cluspro import JobDatabase, JobStatus, Job

# Initialize database (creates ~/.cluspro/jobs.db if needed)
db = JobDatabase()

# Create a job record
job = db.create_job(
    job_name="my-job",
    receptor_pdb="/path/to/receptor.pdb",
    ligand_pdb="/path/to/ligand.pdb",
    batch_id="batch-001"
)

# Update job status after submission
db.update_status(job.id, JobStatus.SUBMITTED, cluspro_id=1154309)

# Get all pending jobs in a batch
pending = db.get_pending_jobs(batch_id="batch-001")

# Get failed jobs for retry
failed = db.get_failed_jobs(batch_id="batch-001")

# Get batch summary
summary = db.get_batch_summary("batch-001")
print(f"Completed: {summary['completed']}/{summary['total']}")
```

### Retry Module

```python
from cluspro import retry_browser, retry_download, with_retry

# Use pre-configured decorators
@retry_browser
def my_selenium_operation(driver):
    """Retries on WebDriverException, TimeoutException, etc."""
    driver.find_element(By.ID, "submit").click()

@retry_download
def my_download_operation():
    """Retries on network and file errors."""
    download_file(url, path)

# Custom retry configuration
@with_retry(max_attempts=5, min_wait=1, max_wait=30)
def my_custom_operation():
    """Custom retry logic."""
    pass
```

### Validate Module

Validate docking poses against receptor topology (requires `pip install cluspro-automation-py[validate]`):

```python
from cluspro.validate import validate_docking, load_topology_from_json, Topology

# Load topology from JSON
topology = load_topology_from_json("examples/MRGX2_MOUSE_topology.json")

# Or define programmatically
topology = Topology(
    extracellular=[(1, 45), (97, 107), (177, 195), (261, 275)],
    transmembrane=[(46, 66), (76, 96), (108, 128), (156, 176)],
    intracellular=[(67, 75), (129, 155), (217, 239), (297, 352)],
    alignment_residues=(97, 107)
)

# Validate docking results (finds min-clash model per target)
results = validate_docking(
    receptor_pdb="receptor.pdb",
    results_dir="./cluspro_results",
    topology=topology,
    output_dir="./validation"
)

# Access results
for r in results:
    print(f"{r.target}: {r.clashes} clashes, {r.ec_pct}% extracellular")
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

### GitHub API Rate Limits

The tool automatically handles GitHub API rate limits. When webdriver-manager hits a rate limit, it falls back to using a cached geckodriver from `~/.wdm/drivers/geckodriver/`.

**Manual options** (if automatic fallback doesn't work):

**Option 1**: Specify a geckodriver path directly (bypasses GitHub API entirely):

```yaml
# ~/.cluspro/settings.yaml
browser:
  geckodriver_path: "~/.wdm/drivers/geckodriver/mac64/v0.36.0/geckodriver"
```

To find your cached geckodriver path:
```bash
ls ~/.wdm/drivers/geckodriver/
```

**Option 2**: Set a GitHub token for higher rate limits:
```bash
export GH_TOKEN=your_github_personal_access_token
```

**Option 3**: Download geckodriver manually:
1. Download from [Mozilla geckodriver releases](https://github.com/mozilla/geckodriver/releases)
2. Extract and place in a known location (e.g., `~/.local/bin/geckodriver`)
3. Add to config:
   ```yaml
   browser:
     geckodriver_path: "~/.local/bin/geckodriver"
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
