# Docking Validation Guide

Validate ClusPro docking results for **membrane proteins** by checking if ligands contact biologically appropriate regions.

## Applicability

This validation works for **any membrane protein** with defined topology:

- **GPCRs** (G protein-coupled receptors)
- **Ion channels** (voltage-gated, ligand-gated)
- **Transporters** (ABC transporters, solute carriers)
- **Single-pass transmembrane receptors** (receptor tyrosine kinases, cytokine receptors)
- **Any protein with UniProt topology annotations**

The key requirement: your receptor must have distinct extracellular, transmembrane, and intracellular regions.

## Table of Contents

- [Motivation](#motivation)
- [Background: Membrane Protein Topology](#background-membrane-protein-topology)
- [How Validation Works](#how-validation-works)
- [Getting Topology Data](#getting-topology-data)
- [Usage Guide](#usage-guide)
- [Interpreting Results](#interpreting-results)
- [Worked Example](#worked-example)
- [References](#references)

## Motivation

### The Problem

ClusPro is a powerful protein-protein docking server that ranks models primarily by **cluster size** and **energy scores** ([Kozakov et al., 2017](https://pubmed.ncbi.nlm.nih.gov/28079879/)). While these metrics effectively identify energetically favorable poses, they don't inherently account for **biological validity** when docking to membrane proteins.

For membrane proteins (GPCRs, ion channels, transporters, etc.):

- **Ligands bind from the extracellular side** - they cannot penetrate the lipid bilayer
- **Transmembrane regions are embedded in the membrane** - inaccessible to soluble ligands
- **Intracellular regions face the cytoplasm** - unreachable from outside the cell

A docking pose might have an excellent energy score but be biologically impossible if the ligand contacts transmembrane or intracellular regions.

### Why Validate?

This validation module addresses a critical gap. As noted for GPCRs (which applies to all membrane proteins):

> "In the case of GPCRs, a large hydrophobic surface is responsible for positioning the protein in the membrane and this part does not interact with bound ligands. Therefore, docking simulations should limit the peptide conformational sampling space to the broad neighborhood of the extracellular receptor domain."
> — [Ciemny et al., 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8138832/)

By analyzing which receptor regions each docked peptide contacts, we can:

1. **Filter out impossible poses** - those penetrating the membrane
2. **Rank poses by biological validity** - not just energy
3. **Identify the best candidates** - minimal clashes, maximal extracellular contacts

## Background: Membrane Protein Topology

### General Principle

All membrane proteins share a common organization:

| Region | Location | Ligand Accessible? |
|--------|----------|-------------------|
| **Extracellular** | Above membrane (or lumenal) | ✅ Yes |
| **Transmembrane** | Within lipid bilayer | ❌ No |
| **Intracellular** | Below membrane (cytoplasmic) | ❌ No |

UniProt annotates these regions as "Topological domain" features, which this tool parses automatically.

### Example: GPCR 7-Transmembrane Structure

GPCRs are characterized by seven transmembrane (7-TM) α-helices that span the plasma membrane ([Weis & Kobilka, 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6535338/)):

```
                    EXTRACELLULAR
                         │
     N-term ─────────────┼─────────────────────────
                         │
         ECL1    ECL2    │    ECL3
          ↓      ↓       │      ↓
    ┌──┐  │  ┌──┐│┌──┐   │  ┌──┐│┌──┐  │  ┌──┐
    │  │  │  │  │││  │   │  │  │││  │  │  │  │
    │T │  │  │T │││T │   │  │T │││T │  │  │T │
    │M │  │  │M │││M │   │  │M │││M │  │  │M │
    │1 │  │  │3 │││4 │   │  │5 │││6 │  │  │7 │
    │  │  │  │  │││  │   │  │  │││  │  │  │  │
    │  │  │  │  │││  │   │  │  │││  │  │  │  │
    └──┘  │  └──┘│└──┘   │  └──┘│└──┘  │  └──┘
          │      │       │      │      │
        ICL1   ICL2      │    ICL3   C-term
                         │
  ═══════════════════════╪════════════════════════
         MEMBRANE        │        MEMBRANE
  ═══════════════════════╪════════════════════════
                         │
                    INTRACELLULAR
```

### GPCR Region Definitions

| Region Type | Components | Location | Ligand Accessible? |
|-------------|-----------|----------|-------------------|
| **Extracellular** | N-terminus, ECL1, ECL2, ECL3 | Above membrane | ✅ Yes |
| **Transmembrane** | TM1-TM7 | Within membrane | ❌ No |
| **Intracellular** | ICL1, ICL2, ICL3, C-terminus | Below membrane | ❌ No |

### Other Membrane Protein Types

The same principle applies to all membrane proteins:

| Protein Type | Example Extracellular Regions |
|--------------|------------------------------|
| **Ion channels** | Pore loops, selectivity filter, outer vestibule |
| **Transporters** | Substrate binding domains, periplasmic loops |
| **Single-pass TM** | Entire ectodomain (N-terminal for type I) |
| **Multi-pass TM** | Extracellular loops between TM helices |

### Why This Matters for Docking

For GPCRs, the ligand binding site is located in the cavity formed by the seven α-helices, accessible from the extracellular side. Larger ligands like peptides can also interact with extracellular loops (ECLs) and the N-terminal domain ([Wheatley et al., 2012](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3372823/)).

The same logic applies to other membrane proteins - ligands can only access regions exposed to the extracellular space.

**A valid docking pose should:**
- Contact primarily extracellular regions
- Have minimal or no transmembrane contacts
- Have zero intracellular contacts
- Show no steric clashes with the receptor

## How Validation Works

### Overview

The validation process:

1. **Load the full receptor structure** with all regions (not just the docking fragment)
2. **Superimpose docked complexes** onto the full receptor
3. **Calculate contacts** between peptide and receptor atoms
4. **Classify contacts** by region type (EC/TM/IC)
5. **Detect clashes** (atoms too close together)
6. **Rank poses** by biological validity

### Step 1: Structure Superposition

ClusPro may dock against a receptor fragment (e.g., only extracellular regions). To check for membrane clashes, we superimpose the docked complex onto the full receptor using the Kabsch algorithm on a conserved extracellular region (the first extracellular region by default, or a user-specified region).

**Receptor fragment detection:** When parsing docked complexes, only extracellular loop (ECL) regions with residue numbers > 50 are used to identify receptor atoms. This excludes the N-terminus to prevent misclassifying peptide residues (which typically start at residue 1) as receptor atoms.

### Step 2: Contact Calculation

Contacts are identified using a **KD-tree spatial query** with a 4.5 Å distance threshold:

```
Contact: Any peptide atom within 4.5 Å of a receptor atom
```

This threshold captures van der Waals interactions (3.3-4.0 Å) and hydrogen bonds (2.6-3.1 Å) while excluding distant atoms ([Nussinov et al., 2017](https://www.nature.com/articles/s41598-017-01498-6)).

### Step 3: Clash Detection

Clashes indicate steric overlap - atoms that would physically collide:

```
Clash: Any atom pair with distance < 2.0 Å
```

High clash counts suggest the pose is geometrically impossible.

### Step 4: Region Classification

Each contact is classified based on the receptor residue's position in the topology:

```python
if residue in extracellular_ranges:
    region = "extracellular"
elif residue in transmembrane_ranges:
    region = "transmembrane"
elif residue in intracellular_ranges:
    region = "intracellular"
```

### Step 5: Model Selection

For each target, the model with **minimum clashes** is selected. Among models with equal clashes, higher extracellular contact percentage is preferred.

## Getting Topology Data

### Option 1: UniProt API (Recommended)

Fetch topology directly from UniProt using the receptor's accession ID:

```bash
cluspro validate -r receptor.pdb -d ./results --uniprot Q3UG50
```

The tool automatically retrieves:
- Topological domain annotations (extracellular/cytoplasmic)
- Transmembrane helix positions
- Region boundaries

**Finding your UniProt accession:**
1. Go to [UniProt](https://www.uniprot.org/)
2. Search for your protein name or gene
3. Copy the accession ID (e.g., Q3UG50, P25025)

### Option 2: JSON Topology File

For custom receptors or modified topologies, provide a JSON file:

```bash
cluspro validate -r receptor.pdb -d ./results -t topology.json
```

**JSON format:**

```json
{
  "extracellular": [[1, 45], [97, 107], [177, 195], [261, 275]],
  "transmembrane": [[46, 66], [76, 96], [108, 128], [156, 176], [196, 216], [240, 260], [276, 296]],
  "intracellular": [[67, 75], [129, 155], [217, 239], [297, 352]],
  "alignment_residues": [97, 107]
}
```

Each array contains `[start_residue, end_residue]` pairs defining regions.

See `examples/MRGX2_MOUSE_topology.json` for a complete example.

## Usage Guide

### Prerequisites

Install validation dependencies:

```bash
pip install cluspro-automation-py[validate]
```

This adds BioPython and SciPy for structure manipulation and spatial queries.

### CLI Usage

**Basic validation with UniProt:**

```bash
cluspro validate \
  -r /path/to/receptor.pdb \
  -d /path/to/cluspro_results \
  --uniprot Q3UG50
```

**With output directory:**

```bash
cluspro validate \
  -r receptor.pdb \
  -d ./results \
  --uniprot Q3UG50 \
  -o ./validation
```

**With custom topology:**

```bash
cluspro validate \
  -r receptor.pdb \
  -d ./results \
  -t topology.json \
  -o ./validation
```

**Validate all models (not just minimum clash):**

```bash
cluspro validate \
  -r receptor.pdb \
  -d ./results \
  --uniprot Q3UG50 \
  --all-models
```

### Python API

```python
from cluspro.validate import (
    validate_docking,
    fetch_topology_from_uniprot,
    load_topology_from_json,
    Topology
)

# Option 1: Fetch from UniProt
topology = fetch_topology_from_uniprot("Q3UG50")

# Option 2: Load from JSON
topology = load_topology_from_json("topology.json")

# Option 3: Define programmatically
topology = Topology(
    extracellular=[(1, 45), (97, 107), (177, 195), (261, 275)],
    transmembrane=[(46, 66), (76, 96), (108, 128), (156, 176)],
    intracellular=[(67, 75), (129, 155), (217, 239), (297, 352)],
    alignment_residues=(97, 107)
)

# Run validation
results = validate_docking(
    receptor_pdb="receptor.pdb",
    results_dir="./cluspro_results",
    topology=topology,
    output_dir="./validation"
)

# Access results
for r in results:
    print(f"{r.target}: {r.clashes} clashes, {r.ec_pct}% EC, score={r.validity_score}")
```

### Output Columns

| Column | Description |
|--------|-------------|
| `rank` | Ranking by minimum clashes (1 = best) |
| `target` | Peptide/ligand identifier |
| `model` | ClusPro model filename (format: `model.{coefficient}.{cluster}.pdb`) |
| `cluster` | ClusPro cluster number (extracted from filename) |
| `center_score` | ClusPro weighted score (kcal/mol) |
| `clashes` | Number of atom pairs < 2.0 Å |
| `ec_contacts` | Contacts with extracellular regions |
| `tm_contacts` | Contacts with transmembrane regions |
| `ic_contacts` | Contacts with intracellular regions |
| `ec_pct` | Percentage of contacts that are extracellular |
| `validity_score` | Composite validity score (0-100), higher = more valid |

**ClusPro Model Naming Convention:**

The model filename encodes both the scoring function (coefficient) and cluster number:
- `model.000.XX.pdb` - Balanced scoring, cluster XX
- `model.002.XX.pdb` - Electrostatic-favored, cluster XX
- `model.004.XX.pdb` - Hydrophobic-favored, cluster XX
- `model.006.XX.pdb` - Van der Waals + Electrostatics, cluster XX

Source: [Kozakov et al., Nature Protocols 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5540229/)

## Interpreting Results

### Good Pose Indicators

| Metric | Ideal Value | Interpretation |
|--------|-------------|----------------|
| `clashes` | 0 | No steric collisions |
| `ec_pct` | 90-100% | Contacts primarily extracellular |
| `tm_contacts` | 0 or low | Minimal membrane penetration |
| `ic_contacts` | 0 | No intracellular contacts |
| `validity_score` | > 80 | High biological validity |

### Warning Signs

| Observation | Concern |
|-------------|---------|
| `clashes` > 10 | Severe steric overlap, geometrically impossible |
| `ec_pct` < 50% | Most contacts are TM/IC, likely invalid pose |
| `ic_contacts` > 0 | Peptide reaching inside the cell (impossible) |
| `tm_contacts` high | Peptide penetrating membrane |

### EC% Interpretation

- **100%**: All contacts are extracellular - ideal
- **90-99%**: Minor TM contacts, likely from loop boundaries - acceptable
- **70-89%**: Significant TM contacts - review carefully
- **< 70%**: Majority non-extracellular contacts - likely invalid

### Validity Score

The validity score is a simple metric combining EC% and clashes:

```
validity_score = ec_pct - clashes
```

The score is clamped to the range 0-100.

**Rationale:** TM/IC contacts are already reflected in lower ec_pct, so we don't
double-penalize them. Only clashes get an additional penalty since they represent
physically impossible steric collisions.

**Score interpretation:**

| Score | Interpretation |
|-------|----------------|
| **80-100** | Excellent - high EC%, few clashes |
| **50-79** | Moderate - review manually |
| **20-49** | Poor - low EC% or many clashes |
| **0-19** | Invalid - significant problems |

### Best Practices

1. **Prioritize low clashes** over high EC% - a clash-free pose with 90% EC is better than 10 clashes with 100% EC
2. **Zero IC contacts is mandatory** - any intracellular contact indicates an impossible pose
3. **Consider cluster scores** - among similar validation metrics, prefer better ClusPro scores
4. **Visualize top candidates** in PyMOL to confirm validity

## Worked Example

### GPCR Example: MRGX2_MOUSE Peptide Docking

**Receptor:** MRGPRX2 (mouse), UniProt Q3UG50 - a GPCR

MRGPRX2 is a mast cell receptor involved in pseudo-allergic reactions. Its structure has been resolved by cryo-EM ([PDB: 7VV6](https://www.rcsb.org/structure/7VV6)).

**Command:**

```bash
cluspro validate \
  -r MRGX2_MOUSE.pdb \
  -d ./cluspro_results \
  --uniprot Q3UG50 \
  -o ./validation
```

**Sample output:**

```
Fetching topology from UniProt: Q3UG50
Loaded topology: 4 EC, 7 TM, 4 IC regions

Validated 33 targets:
--------------------------------------------------------------------------------
Rank  Target              Model              Clashes   EC%     Score
--------------------------------------------------------------------------------
1     1r10_MF21_20        model.002.00.pdb   0         97.4    89.4
2     SR-5_1-110          model.006.13.pdb   0         100.0   100.0
3     NPM_208             model.000.21.pdb   1         75.5    0.0
4     RF0012              model.004.03.pdb   1         98.0    81.0
5     test_20aa           model.006.03.pdb   1         100.0   95.0
...

Summary:
  Average EC%: 90.4%
  Zero clashes: 2/33
  EC% >= 90%: 21/33
```

**Interpretation:**

- **Top 2 poses (1r10_MF21_20, SR-5_1-110)** have zero clashes and high validity scores (89.4, 100.0) - excellent candidates
- **SR-5_1-110** achieved a perfect validity score of 100 (100% EC, 0 clashes)
- **Most peptides (21/33)** achieved ≥90% extracellular contacts
- **Coefficient 006 (VdW+Elec)** dominated the best models - this scoring function may work better for peptide docking

## Tips

1. **Use UniProt when possible** - it ensures accurate, curated topology data
2. **Check AlphaFold models** - if using AF structures, residue numbering should match UniProt
3. **Compare across clusters** - the best ClusPro cluster by score isn't always the most valid
4. **Run early in your workflow** - validate before detailed analysis to avoid wasted effort
5. **Combine with visual inspection** - automated metrics should guide, not replace, expert review

## References

### ClusPro Server & Methodology

1. Kozakov D, Hall DR, Xia B, et al. (2017). "The ClusPro web server for protein-protein docking." *Nature Protocols* 12:255-278. [PubMed](https://pubmed.ncbi.nlm.nih.gov/28079879/) | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5540229/)

2. Comeau SR, Gatchell DW, Vajda S, Camacho CJ (2004). "ClusPro: a fully automated algorithm for protein-protein docking." *Nucleic Acids Res* 32:W96-99. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC441492/)

3. Kozakov D, Beglov D, Bohnuud T, et al. (2013). "How good is automated protein docking?" *Proteins* 81(12):2159-66. [PubMed](https://pubmed.ncbi.nlm.nih.gov/23996272/)

### Membrane Protein Docking (GPCR examples)

4. Ciemny M, Kurcinski M, Kamel K, et al. (2021). "Docking of peptides to GPCRs using a combination of CABS-dock with FlexPepDock refinement." *Brief Bioinform* 22(3):bbaa109. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8138832/)

5. Pándy-Szekeres G, Caroli J, Mamyrbekov A, et al. (2023). "Evaluating GPCR modeling and docking strategies in the era of deep learning-based protein structure prediction." *Comput Struct Biotechnol J* 21:757-769. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9747351/)

### Membrane Protein Structure & Topology

6. Wheatley M, Wootten D, Conner MT, et al. (2012). "Lifting the lid on GPCRs: the role of extracellular loops." *Br J Pharmacol* 165(6):1688-1703. [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3372823/)

7. Weis WI, Kobilka BK (2018). "The Molecular Basis of G Protein-Coupled Receptor Activation." *Annu Rev Biochem* 87:897-919. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6535338/)

### MRGPRX2 (Worked Example)

8. Cao C, et al. (2022). "Cryo-EM structure of MRGPRX2 complex with compound 48/80." [PDB: 7VV6](https://www.rcsb.org/structure/7VV6)

9. Thapaliya M, et al. (2025). "MRGPRX2 ligandome: Molecular simulations reveal three categories of ligand-receptor interactions." *J Struct Biol*. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1047847725000280)

### Contact Analysis

10. Vijayabaskar MS, Vishveshwara S (2017). "An optimal distance cutoff for contact-based Protein Structure Networks using side-chain centers of mass." *Sci Rep* 7:2838. [Nature](https://www.nature.com/articles/s41598-017-01498-6)

### AlphaFold & GPCR Modeling

11. Hollingsworth SA, et al. (2023). "Using AlphaFold and Experimental Structures for the Prediction of GPCR Complexes via Induced Fit Docking and Free Energy Perturbation." *J Chem Theory Comput*. [ACS](https://pubs.acs.org/doi/10.1021/acs.jctc.3c00839)

### UniProt

12. UniProt Consortium. "UniProt: the Universal Protein Knowledgebase." [Topology domain documentation](https://www.uniprot.org/help/topo_dom)
