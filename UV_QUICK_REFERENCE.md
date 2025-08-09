# uv Quick Reference Guide for fox-report

## ✅ Migration Complete!
**Date:** August 9, 2025, 2:09 PM MDT
**Status:** Successfully migrated from pip/venv to uv

## 🚀 How to Run Your Script

### Option 1: Direct execution with uv (Recommended)
```bash
cd /home/hunter/fox-report
uv run python send_fox_report_gmail.py --nights 10 --verbose --config config/gmail.yaml
```

### Option 2: Activate venv first (Traditional)
```bash
cd /home/hunter/fox-report
source .venv/bin/activate
python send_fox_report_gmail.py --nights 10 --verbose --config config/gmail.yaml
deactivate  # when done
```

## 📦 Package Management

### Add a new package
```bash
uv add package-name
```

### Remove a package
```bash
uv remove package-name
```

### Update all packages
```bash
uv sync --upgrade
```

### List installed packages
```bash
uv pip list
```

## 🔧 Key Files

- **pyproject.toml** - Project configuration and dependencies
- **uv.lock** - Locked dependency versions (auto-managed)
- **.venv/** - Virtual environment directory
- **run_fox_report_cron.sh** - Updated cron script using uv

## 💡 What Changed

### Before (pip/venv):
```bash
cd /home/hunter/fox-report && source venv/bin/activate && python send_fox_report_gmail.py --nights 10 --verbose --config config/gmail.yaml
```

### After (uv):
```bash
cd /home/hunter/fox-report && uv run python send_fox_report_gmail.py --nights 10 --verbose --config config/gmail.yaml
```

## 🎯 Benefits of uv

1. **Speed**: 10-100x faster than pip
2. **Simplicity**: No need to manually activate venv
3. **Reproducibility**: uv.lock ensures consistent environments
4. **Modern**: Uses pyproject.toml standard
5. **Convenience**: Single tool for all Python package management

## 📝 Notes

- The old `venv/` directory has been removed
- New virtual environment is in `.venv/`
- Cron script updated to use uv
- All dependencies preserved and working

## 🆘 Troubleshooting

If you encounter issues:
1. Ensure uv is in PATH: `which uv`
2. Recreate venv: `rm -rf .venv && uv venv && uv sync`
3. Check Python version: `uv run python --version`

---
*Generated: August 9, 2025, 2:09 PM MDT*
