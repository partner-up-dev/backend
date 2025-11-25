---
applyTo: "**"
---

## Overview

This project is a Python backend project.

## Dependencies

- blue-firmament: backend framework to use.

## File Structure

- `run.py`
- `dal.py`: Data Access Layer config
- `data/`
  - `keys`: Certificates, private / public keys
  - `json/`: JSON type files
- `settings/`
  - `<module_name>.py`: Setting of the module.
- `<service_name>/`
  - `managers/`: Business Layer
    - `<module_name>/`
  - `schemas/`: Data Model Layer
    - `<module_name/>`
- `utils/`: Common utils shared between services.
- `tests/`

## Coding Standard

- Use `enum.Enum` instead of `typing.Literal` for better extendability.
