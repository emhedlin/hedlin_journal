#!/usr/bin/env python3
"""
Generate embeddings for journal entries.

This script computes sentence embeddings for all entries using
sentence-transformers. These embeddings can be used for:
1. Timeline hover previews (finding related entries)
2. Semantic search
3. Clustering similar entries
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict

import numpy as np
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sentence_transformers import SentenceTransformer

console = Console()


def load_entries(data_file: Path) -> List[Dict]:
    """Load entries from journal_entries.json."""
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('entries', [])


def prepare_text_for_embedding(entry: Dict) -> str:
    """
    Prepare entry text for embedding.

    Combine the date display and first few paragraphs
    to create a representative text for the entry.
    """
    content = entry.get('content', '')

    # Take first 500 characters as preview
    preview = content[:500].replace('\n', ' ').strip()

    # Combine date and preview
    text = f"{entry.get('date_display', '')}. {preview}"

    return text


def generate_summaries(entries: List[Dict]) -> None:
    """
    Generate short summaries for each entry.

    This creates a 1-2 sentence summary by taking the first
    meaningful sentence(s) from the content.
    """
    import re

    for entry in entries:
        content = entry.get('content', '')

        # Split into sentences
        sentences = re.split(r'[.!?]+\s+', content)

        # Take first 1-2 sentences that have meaningful content
        summary_sentences = []
        for sent in sentences[:3]:
            sent = sent.strip()
            if len(sent) > 20 and not sent.lower().startswith(('we', 'i', 'cheryl', 'peter', 'matthew')):
                summary_sentences.append(sent)
            elif len(summary_sentences) == 0:
                summary_sentences.append(sent)
            if len(summary_sentences) >= 2:
                break

        summary = '. '.join(summary_sentences)[:150]
        if len(summary) < len(content):
            summary += '...'

        entry['summary'] = summary


def generate_embeddings(
    entries: List[Dict],
    model_name: str = 'all-MiniLM-L6-v2',
    batch_size: int = 32
) -> np.ndarray:
    """
    Generate embeddings for all entries.

    Args:
        entries: List of entry dictionaries
        model_name: Name of the sentence-transformers model
        batch_size: Batch size for encoding

    Returns:
        numpy array of embeddings
    """
    console.print(f"[bold]Loading model:[/bold] {model_name}")

    model = SentenceTransformer(model_name)

    # Prepare texts
    texts = [prepare_text_for_embedding(e) for e in entries]

    console.print(f"[bold]Generating embeddings for {len(texts)} entries...[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Encoding...", total=len(texts))

        # Generate embeddings
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        progress.update(task, completed=len(texts))

    console.print(f"[green]Embeddings shape:[/green] {embeddings.shape}")

    return embeddings


def save_embeddings(
    entries: List[Dict],
    embeddings: np.ndarray,
    output_file: Path
) -> None:
    """Save entries with embeddings to JSON file."""
    # Convert embeddings to list for JSON serialization
    output_data = {
        'model': 'all-MiniLM-L6-v2',
        'dimension': embeddings.shape[1],
        'count': len(entries),
        'entries': []
    }

    for i, entry in enumerate(entries):
        output_data['entries'].append({
            'date': entry.get('date'),
            'date_display': entry.get('date_display'),
            'title': entry.get('title'),
            'summary': entry.get('summary', ''),
            'preview': entry.get('summary', ''),
            'url': f"/entries/{entry['date'][:4]}/{entry['date'][5:7]}/{entry['date']}.html",
            'embedding': embeddings[i].tolist()
        })

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    console.print(f"[green]Embeddings saved to:[/green] {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate embeddings for journal entries"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=Path("data/journal_entries.json"),
        help="Input JSON file (default: data/journal_entries.json)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("output/static/js/embeddings.json"),
        help="Output file for embeddings (default: output/static/js/embeddings.json)"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="all-MiniLM-L6-v2",
        help="Sentence transformer model name"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=32,
        help="Batch size for encoding"
    )

    args = parser.parse_args()

    # Load entries
    console.print(f"[bold]Loading entries from:[/bold] {args.input}")
    entries = load_entries(args.input)
    console.print(f"  [dim]Found {len(entries)} entries[/dim]")

    if not entries:
        console.print("[yellow]No entries found![/yellow]")
        return 1

    # Generate summaries
    console.print("\n[bold]Generating summaries...[/bold]")
    generate_summaries(entries)

    # Generate embeddings
    console.print()
    embeddings = generate_embeddings(entries, args.model, args.batch_size)

    # Save results
    console.print()
    save_embeddings(entries, embeddings, args.output)

    return 0


if __name__ == "__main__":
    exit(main())
