# Organic Chemistry Feeds

A static website that aggregates latest articles (default last 3 days) from major **organic chemistry** journals via RSS/Atom feeds. Builds on GitHub Actions and renders on GitHub Pages.

## Journals included
- JACS, Angew. Chem. Int. Ed., Chemistry–A European Journal, Eur. J. Org. Chem., Advanced Synthesis & Catalysis
- Organic & Biomolecular Chemistry, Organic Chemistry Frontiers
- Tetrahedron, Tetrahedron Letters
- Beilstein J. Org. Chem., Nature Chemistry, Chemical Science

## Deploy
1. Create a public repo, push these files.
2. Enable GitHub Pages (from `main` / root).
3. Run workflow **Fetch latest journal feeds (3-day window)** once.
