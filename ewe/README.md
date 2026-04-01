# Ewé build pipeline, pass 4

Pass 4 keeps the earlier pipeline, templates, and deployment structure, but replaces the simple field-to-template mapping with an ontology-aware interpretation layer.

## What changed in pass 4

- introduces assertion-level modeling through `AssertionModel`
- introduces access evaluation helpers in `access.py`
- preserves intentionality by redacting governed assertions instead of silently hiding them
- treats Lucumí labels as bounded assertions in the public interface
- keeps record-level access visible while allowing field/assertion behavior to differ
- emits JSON-LD with only public-visible assertions
- removes bounded assertions from public search indexing
- comments the code for reuse in future datasets or a later authenticated application

## Files to notice

- `build_ewe.py` orchestrates extraction, modeling, and rendering
- `access.py` contains the pass-4 public access logic
- `model.py` contains reusable assertion/section dataclasses
- `templates/plant.html` renders visible vs redacted assertions

## Run

```bash
python -m pip install -r requirements.txt
python build_ewe.py --ttl Verger_Ewe_Dataset_v4.ttl --config site_config.json --out dist
```

## Why pass 4 does not replace passes 1–3

Pass 1–3 remain the foundation:
- pass 1 = static pipeline
- pass 2 = closer UI parity
- pass 3 = deployment/config extras

Pass 4 sits on top of those and upgrades the data interpretation layer.
