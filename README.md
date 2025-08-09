> **Note**: This project now uses `uv` for Python package management. See [MIGRATION_TO_UV.md](MIGRATION_TO_UV.md) for details.

# 🦊 Fox Detection Report System

A Python-based system for generating and emailing Fox detection reports from Frigate NVR data.

## 📁 Project Structure

```
fox-report/
├── src/                    # Source code
│   ├── fox_report/        # Core package
│   │   ├── database_query.py
│   │   ├── report_generator.py  
│   │   ├── time_resolver.py
│   │   └── email/         # Email functionality
│   │       └── sender.py
│   └── cli/               # Command-line interface
│       └── send_report.py
├── config/                # Configuration files
│   ├── gmail.yaml
│   └── template.yaml
├── tests/                 # Test files
│   ├── unit/
│   └── fixtures/
├── docs/                  # Documentation
│   ├── README.md         # Detailed technical documentation
│   └── ops.md            # Operations and deployment guide
└── pyproject.toml         # Dependencies and project configuration
```

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure environment:**
   ```bash
   cp config/.env.example .env
   # Edit .env with your Gmail credentials
   ```

3. **Send a fox report:**
   ```bash
   uv run python send_fox_report_gmail.py --config config/gmail.yaml --nights 3
   ```

## 📧 Features

- **Mountain Time Support**: All timestamps in local time with DST handling
- **Gmail SMTP**: Direct email sending via Gmail with app passwords
- **Clickable Event IDs**: Direct links to video clips in emails
- **Hierarchical Structure**: Clean, maintainable code organization
- **Comprehensive Testing**: Unit and integration tests
- **Automated Scheduling**: Daily cron job with proper timezone handling

## 🔧 Operations

For deployment, scheduling, and maintenance information, see [`docs/ops.md`](docs/ops.md).

## 📖 Documentation

See the `docs/` directory for detailed documentation:
- [`docs/README.md`](docs/README.md) - Technical documentation and API reference
- [`docs/ops.md`](docs/ops.md) - Operations, deployment, and cron configuration
