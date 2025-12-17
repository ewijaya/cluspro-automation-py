# ClusPro CLI Workflow Guide

Step-by-step guide for automating protein docking with the ClusPro CLI.

## Prerequisites

- ClusPro CLI installed (`pip install -e .`)
- Firefox browser installed
- Internet connection
- PDB files for receptor and ligand proteins

## Single Job Workflow

This example uses the included sample PDB files.

### Step 1: Submit a Job

```bash
cluspro submit -n "my-docking-job" \
  -r examples/receptor.pdb \
  -l examples/ligand.pdb \
  -s gpu
```

**Options:**
- `-n, --name`: Job name (required)
- `-r, --receptor`: Path to receptor PDB file (required)
- `-l, --ligand`: Path to ligand PDB file (required)
- `-s, --server`: Server type - `gpu` (faster) or `cpu` (default: `gpu`)
- `--no-headless`: Show browser window for debugging

**Output:**
```
Job 'my-docking-job' submitted successfully
```

### Step 2: Monitor Queue Status

Check if your job is still processing:

```bash
cluspro queue --pattern "my-.*"
```

**Output while processing:**
```
Found 1 jobs in queue:

  job_id    job_name        user   status
  1375534   my-docking-job  piper  in queue on supercomputer
```

Jobs typically take 15-60 minutes depending on server load.

### Step 3: Check Results

Once the job completes, it moves from queue to results:

```bash
cluspro results --pattern "my-.*"
```

**Output when finished:**
```
Found 1 finished jobs:

  job_name        job_id   status    submitted
  my-docking-job  1375534  finished  2025-12-17 14:47
```

### Step 4: Download Results

Download the docking results:

```bash
# Download with PDB model files
cluspro download --job-id 1375534 --pdb

# Download without PDB files (just scores)
cluspro download --job-id 1375534 --no-pdb
```

**Output:**
```
Downloaded results for job 1375534 to ~/Desktop/ClusPro_results/
```

### Step 5: View Downloaded Files

Results are saved to your configured output directory (default: `~/Desktop/ClusPro_results/`):

```
ClusPro_results/
└── 1375534/
    ├── model.000.00.pdb    # Best docking pose
    ├── model.001.00.pdb    # 2nd best pose
    ├── ...
    └── scores.csv          # Energy scores
```

## Batch Job Workflow

For multiple docking jobs, use batch processing.

### Step 1: Prepare Jobs CSV

Create a CSV file with your jobs (`jobs.csv`):

```csv
job_name,receptor_pdb,ligand_pdb,server
dock-peptide1-receptor1,/path/to/receptor1.pdb,/path/to/peptide1.pdb,gpu
dock-peptide2-receptor1,/path/to/receptor1.pdb,/path/to/peptide2.pdb,gpu
dock-peptide1-receptor2,/path/to/receptor2.pdb,/path/to/peptide1.pdb,gpu
```

See `examples/sample_jobs.csv` for a template.

### Step 2: Validate Jobs (Optional)

Check your CSV for errors before submitting:

```bash
cluspro dry-run -i jobs.csv
```

### Step 3: Submit Batch

```bash
cluspro submit-batch -i jobs.csv -o submitted_jobs.csv
```

**Options:**
- `-i, --input`: Input CSV file (required)
- `-o, --output`: Output CSV with job IDs
- `--stop-on-error`: Stop if any job fails

### Step 4: Monitor All Jobs

```bash
# Check queue for jobs matching pattern
cluspro queue --pattern "dock-.*"

# Get summary of all matching jobs
cluspro summary --pattern "dock-.*"
```

**Summary output:**
```
Summary for pattern 'dock-.*':
  Total: 3
  Finished: 2
  Running: 1
  Error: 0
```

### Step 5: Download Batch Results

Once jobs finish, download all results:

```bash
# Get finished job IDs
cluspro results --pattern "dock-.*" --output job_ids.txt

# Download all (using compressed notation)
cluspro download-batch --ids "1375534:1375536" --pdb
```

**Compressed notation:**
- `1375534:1375536` = jobs 1375534, 1375535, 1375536
- `1375534:1375536,1375540` = jobs 1375534-1375536 and 1375540

### Step 6: Organize Results (Optional)

Rename downloaded folders with meaningful names using a mapping file.

Create `mapping.csv`:

```csv
job_name,peptide_name,receptor_name
dock-peptide1-receptor1,HMGB1,LRP1-mouse
dock-peptide2-receptor1,RAGE,LRP1-mouse
dock-peptide1-receptor2,HMGB1,LRP1-human
```

Organize:

```bash
cluspro organize -i mapping.csv --pdb
```

**Result:**
```
ClusPro_results/full_names/
├── HMGB1_LRP1-mouse/
├── RAGE_LRP1-mouse/
└── HMGB1_LRP1-human/
```

## Quick Reference

| Task | Command |
|------|---------|
| Submit single job | `cluspro submit -n NAME -r REC.pdb -l LIG.pdb` |
| Submit batch | `cluspro submit-batch -i jobs.csv --batch-id ID` |
| Check queue | `cluspro queue --pattern "PREFIX-.*"` |
| Check results | `cluspro results --pattern "PREFIX-.*"` |
| Download single | `cluspro download --job-id ID --pdb` |
| Download batch | `cluspro download-batch --ids "ID1:ID2" --pdb` |
| Organize files | `cluspro organize -i mapping.csv` |
| List tracked jobs | `cluspro jobs list --batch ID` |
| Resume batch | `cluspro jobs resume --batch ID` |
| Show config | `cluspro config` |

## Job Tracking Workflow

The CLI includes a job database for tracking submissions and resuming interrupted batches.

### Track Batch Submissions

When submitting jobs, they are automatically tracked in the database:

```bash
# Submit batch - jobs are tracked with batch ID
cluspro submit-batch -i jobs.csv --batch-id "experiment-001"
```

### View Tracked Jobs

```bash
# List all tracked jobs
cluspro jobs list

# List jobs by status
cluspro jobs list --status pending
cluspro jobs list --status failed
cluspro jobs list --status completed

# List jobs in a specific batch
cluspro jobs list --batch experiment-001
```

**Output:**
```
Jobs in batch 'experiment-001':

  ID  Name              Status     ClusPro ID
  1   dock-pep1-rec1    completed  1375534
  2   dock-pep2-rec1    completed  1375535
  3   dock-pep3-rec1    failed     -
```

### Check Batch Status

```bash
cluspro jobs status --batch experiment-001
```

**Output:**
```
Batch 'experiment-001' summary:
  Total: 10
  Pending: 0
  Submitted: 0
  Completed: 8
  Failed: 2
```

### Resume Interrupted Batches

If a batch submission is interrupted (network issue, timeout, etc.), resume it:

```bash
# Resume pending jobs only
cluspro jobs resume --batch experiment-001

# Resume including failed jobs (retry)
cluspro jobs resume --batch experiment-001 --include-failed
```

The database automatically tracks:
- Job submission status
- ClusPro job IDs
- Error messages for failed jobs
- Timestamps for all state changes

## Tips

1. **Use consistent naming**: Prefix job names (e.g., `exp1-`, `batch2-`) for easy filtering
2. **GPU vs CPU**: GPU server is faster but may have longer queues
3. **Batch delays**: Jobs are submitted with delays between them to avoid overwhelming the server
4. **Check queue first**: Before downloading, verify jobs are finished with `cluspro results`
5. **Organize early**: Create your mapping CSV before submitting to make organization easier later
6. **Use batch IDs**: Always specify `--batch-id` when submitting batches for easy tracking and resumption
7. **Retry failed jobs**: Use `cluspro jobs resume --include-failed` to retry jobs that failed due to transient errors
