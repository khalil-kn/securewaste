# Diagrams

Every diagram exists in **two editable forms**:

| Form | Folder | Best for |
|---|---|---|
| **PlantUML** text source → SVG | [`src/`](src/) → [`svg/`](svg/) | Version control: diagrams are code, so pull requests show exactly what changed. The SVGs are what the Markdown docs embed. |
| **draw.io** native file | [`drawio/`](drawio/) | Visual editing by drag-and-drop in [app.diagrams.net](https://app.diagrams.net) or the draw.io desktop app. |

`png/` holds PNG copies of the PlantUML renders for Word/PDF documents. `svg/roadmap.svg` is the one exception: a hand-written SVG (the milestone roadmap), edited directly in any text editor.

> **Rule of thumb:** the PlantUML source is the reference. When you change a design, edit the `.puml` first, re-export the SVG, then update the matching `.drawio` file in the same pull request so both stay in sync.

## Index

| Diagram | What it shows | PlantUML | draw.io |
|---|---|---|---|
| Use case | Actors and the goals they achieve | [src](src/use-case.puml) · [svg](svg/use-case.svg) | [drawio](drawio/use-case.drawio) |
| Class (domain) | Core classes, attributes, operations, relationships | [src](src/class-domain.puml) · [svg](svg/class-domain.svg) | [drawio](drawio/class-domain.drawio) |
| Data model | SQLite tables, keys, cardinalities | [src](src/data-model.puml) · [svg](svg/data-model.svg) | [drawio](drawio/data-model.drawio) |
| State machines | Scan job lifecycle and finding review status | [src](src/state-machines.puml) · [svg](svg/state-machines.svg) | [drawio](drawio/state-machines.drawio) |
| Sequence — upload & scan | Main scenario, synchronous pipeline | [src](src/seq-upload-scan.puml) · [svg](svg/seq-upload-scan.svg) | [drawio](drawio/seq-upload-scan.drawio) |
| Sequence — review finding | JSON PATCH, transition check, risk re-assessment | [src](src/seq-review-finding.puml) · [svg](svg/seq-review-finding.svg) | [drawio](drawio/seq-review-finding.drawio) |
| Sequence — redaction | Re-locate values, redact, verify | [src](src/seq-redaction.puml) · [svg](svg/seq-redaction.svg) | [drawio](drawio/seq-redaction.drawio) |
| Activity (swimlanes) | End-to-end workflow by responsibility | [src](src/activity-scan-review-redact.puml) · [svg](svg/activity-scan-review-redact.svg) | [drawio](drawio/activity-scan-review-redact.drawio) |
| Component | Modules and their dependencies | [src](src/component.puml) · [svg](svg/component.svg) | [drawio](drawio/component.drawio) |
| Deployment | Where each artifact runs (MVP, Docker, CI) | [src](src/deployment.puml) · [svg](svg/deployment.svg) | [drawio](drawio/deployment.drawio) |
| Trust boundaries | Data flows DF1–DF7 crossing TB1–TB5 | [src](src/trust-boundaries.puml) · [svg](svg/trust-boundaries.svg) | [drawio](drawio/trust-boundaries.drawio) |

## Editing PlantUML

1. Install **Java 17+** (`java -version` to check).
2. Download `plantuml.jar` from the [PlantUML releases page](https://github.com/plantuml/plantuml/releases) into `docs/diagrams/tools/` (that folder is git-ignored). PlantUML uses Graphviz internally for some layouts; recent jars include what they need, otherwise install [Graphviz](https://graphviz.org/download/).
3. Edit a file in `src/`. Shared colours and fonts live in [`src/_style.iuml`](src/_style.iuml) — every diagram includes it with `!include _style.iuml`, so change the look in one place.
4. Re-export (Git Bash, from the repository root):

   ```bash
   cd docs/diagrams
   java -jar tools/plantuml.jar -tsvg -o ../svg src/*.puml   # SVGs for GitHub
   java -jar tools/plantuml.jar -tpng -o ../png src/*.puml   # PNGs for Word/PDF
   ```

   `-o ../svg` is relative to the source folder, which is why it points one level up.
5. Open the SVG and check it: no overlapping labels, no lines crossing boxes.

**Tip:** the VS Code extension *PlantUML* (jebbs) shows a live preview with `Alt+D`.

## Editing draw.io

1. Open [app.diagrams.net](https://app.diagrams.net) (or install draw.io desktop) → *File → Open from → Device* → choose a `.drawio` file.
2. Shapes are real draw.io UML shapes (actors, use-case ellipses, class boxes with one row per attribute, lifelines, frames, swimlanes, components, folders, cubes, cylinders) and every arrow is connected to its shapes, so moving a box drags its arrows along.
3. *File → Save* keeps the `.drawio` format. To export an image: *File → Export as → SVG/PNG*, tick *Transparent background* off so the background stays white.

The VS Code extension *Draw.io Integration* (hediet) edits `.drawio` files directly inside the editor.

## Conventions

- File names: `kebab-case`, same stem across `src/`, `svg/`, `png/` and `drawio/`.
- Titles start with "SecureWaste — ".
- White backgrounds; colours only from `_style.iuml` (draw.io files use the same hex values).
- Fictional data only — never put real names, IDs or keys in a diagram.
