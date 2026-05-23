# Reference: Semantic Duplicate Detection (Documents)

## When to Use

Semantic dedup is for **document collections** where files may be reformatted, paraphrased, or slightly modified versions of each other — not byte-identical.

Use cases:
- Large PDF/document archives
- Training data deduplication
- Knowledge base cleanup
- Research paper collections

**Not for:** typical file cleanup (use exact dedup instead).

## semhash

Python library. Uses Model2Vec embeddings (fast, local) + Vicinity (ANN search).

### Install

```bash
python3 -m pip install --user semhash
```

### Usage

```python
from semhash import SemHash
import os

def scan_document_duplicates(directory: str, threshold: float = 0.85) -> list:
    """Find semantically similar documents.
    Returns list of (keep, remove) pairs.
    """
    # 1. Collect documents
    records = []
    text_exts = {'.txt', '.md', '.pdf', '.docx', '.rtf', '.html'}

    for root, _, files in os.walk(directory):
        for f in files:
            if os.path.splitext(f)[1].lower() not in text_exts:
                continue
            path = os.path.join(root, f)
            try:
                # For text files, read directly
                if f.endswith(('.txt', '.md', '.html')):
                    with open(path, 'r', errors='ignore') as fh:
                        text = fh.read(50000)  # First 50KB
                else:
                    text = f"[File: {f}]"  # Placeholder for binary formats
                records.append({"path": path, "text": text, "filename": f})
            except Exception as e:
                print(f"Error reading {path}: {e}")

    if len(records) < 2:
        return []

    # 2. Deduplicate
    semhash = SemHash.from_records(records, columns=["text"])
    result = semhash.self_deduplicate(threshold=threshold)

    # 3. Extract pairs
    duplicates = []
    for record in result.duplicates:
        dup_path = record["path"]
        # Find the original it matches
        for selected in result.selected:
            if selected["path"] != dup_path:
                duplicates.append((selected["path"], dup_path))
                break

    return duplicates
```

### Threshold Guide

| Threshold | Meaning | Use When |
|-----------|---------|----------|
| 0.95 | Near-identical content | Removing copies with minor edits |
| 0.85 | Similar topic/structure | Dedup a document archive |
| 0.75 | Related content | Aggressive dedup (more false positives) |

**Default: 0.85** — good balance of precision/recall.

### Limitations

- Requires text extraction (PDFs need `pymupdf` or similar)
- Slower than hash-based dedup (embedding computation)
- Not suitable for binary files (images, videos, archives)
- Model2Vec is fast but less accurate than full transformer models

## Alternative: sentence-transformers

For higher accuracy (at cost of speed):

```bash
python3 -m pip install --user sentence-transformers
```

```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode([r["text"] for r in records])
sim_matrix = cosine_similarity(embeddings)

# Find pairs above threshold
duplicates = []
for i in range(len(records)):
    for j in range(i + 1, len(records)):
        if sim_matrix[i][j] > 0.85:
            duplicates.append((records[i]["path"], records[j]["path"]))
```

This is more accurate but 10–50x slower than semhash. Use for < 10K documents.
