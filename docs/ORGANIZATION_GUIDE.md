# VisiScure Order - Organization Guide

## 📋 Overview

This guide explains the new organized structure of the VisiScure Order project and how to navigate it effectively.

## 🎯 Organization Principles

### 1. Separation of Concerns
- **Code** - Application modules in root
- **Documentation** - All docs in `docs/`
- **Tests** - All tests in `tests/`
- **Scripts** - Utilities in `scripts/`
- **Assets** - Static files in `static/`

### 2. Logical Grouping
- Related files are grouped together
- Clear folder hierarchy
- Consistent naming conventions

### 3. Easy Discovery
- README files in each major folder
- Clear file naming
- Comprehensive indexes

## 📁 Folder Structure Explained

### Root Level (`Hotel/`)

**Purpose**: Core application files and configuration

**Contains**:
- Main application entry point (`app.py`)
- Configuration files (`config.py`, `.env`)
- Dependencies (`requirements.txt`)
- Documentation entry points (`README.md`, `PROJECT_STRUCTURE.md`)
- Utility scripts (`*.bat` files)

**What's NOT here**:
- ❌ Test files (moved to `tests/`)
- ❌ Documentation files (moved to `docs/`)
- ❌ Temporary files

### Application Modules

**Purpose**: Business logic and features

**Structure**:
```
module_name/
├── models.py          # Database models
├── routes.py          # API endpoints
├── __init__.py        # Module initialization
└── [service.py]       # Business logic (optional)
```

**Modules**:
- `admin/` - Admin management
- `guest_verification/` - Guest verification & OTP
- `hotel_manager/` - Manager operations
- `kitchen/` - Kitchen management
- `menu/` - Menu CRUD
- `orders/` - Order & table management
- `waiter/` - Waiter operations
- `waiter_calls/` - Call system
- `wallet/` - Wallet system

### Documentation (`docs/`)

**Purpose**: All project documentation

**Organization**:
```
docs/
├── README.md                    # Documentation index
├── Setup Guides/                # Installation & setup
├── Feature Documentation/       # Feature details
├── Troubleshooting/            # Fix guides
└── Test Results/               # Test reports
```

**File Types**:
- `.md` files - Detailed technical docs
- `.txt` files - Quick reference guides

**Quick Access**:
- Start with `docs/README.md`
- Use the documentation index
- Search by topic

### Tests (`tests/`)

**Purpose**: All test files and test utilities

**Contains**:
- HTML test pages
- Python test scripts
- Test documentation

**Quick Access**:
- Start with `tests/README.md`
- Run tests from this folder
- Check test results here

### Scripts (`scripts/`)

**Purpose**: Utility and maintenance scripts

**Organization**:
```
scripts/
├── migrations/        # Database migrations
├── setup/            # Initial setup
├── utils/            # Diagnostic tools
└── sms/              # SMS testing
```

**Usage**:
- Run from project root
- Check script documentation
- Use for maintenance tasks

### Static Assets (`static/`)

**Purpose**: Frontend assets

**Organization**:
```
static/
├── css/              # Stylesheets
├── js/               # JavaScript
├── images/           # Images & logos
├── sounds/           # Audio files
└── uploads/          # User uploads
```

### Templates (`templates/`)

**Purpose**: HTML templates

**Organization**:
```
templates/
├── *.html            # Main pages
├── shared/           # Shared components
└── menu/             # Menu templates
```

## 🔍 Finding What You Need

### Common Tasks

| Task | Location | File |
|------|----------|------|
| Start application | Root | `app.py` |
| Configure settings | Root | `config.py`, `.env` |
| Read documentation | `docs/` | `README.md` |
| Run tests | `tests/` | `README.md` |
| Fix common issues | `docs/` | `QUICK_FIX_GUIDE.txt` |
| Setup SMS | `docs/` | `MSG91_SETUP_STEPS.md` |
| Setup voice | `docs/` | `VOICE_SYSTEM_SETUP.md` |
| Check structure | Root | `PROJECT_STRUCTURE.md` |

### By File Type

| Type | Location |
|------|----------|
| Python modules | Root folders |
| Documentation | `docs/` |
| Tests | `tests/` |
| Scripts | `scripts/` |
| Templates | `templates/` |
| Styles | `static/css/` |
| Images | `static/images/` |

### By Purpose

| Purpose | Location |
|---------|----------|
| Development | Root modules |
| Learning | `docs/`, `README.md` |
| Testing | `tests/`, `scripts/utils/` |
| Troubleshooting | `docs/QUICK_FIX_GUIDE.txt` |
| Setup | `docs/`, `scripts/setup/` |
| Maintenance | `scripts/migrations/` |

## 📖 Documentation Navigation

### For New Developers

1. **Start Here**:
   - `README.md` (root)
   - `PROJECT_STRUCTURE.md`
   - `docs/README.md`

2. **Setup**:
   - `docs/QUICK_MSG91_SETUP.txt`
   - `docs/QUICK_START_VOICE.txt`

3. **Development**:
   - Review module structure
   - Check `docs/` for features
   - Use `scripts/utils/` for testing

### For Troubleshooting

1. **Quick Fixes**:
   - `docs/QUICK_FIX_GUIDE.txt`

2. **Specific Issues**:
   - Dashboard: `docs/DASHBOARD_LAYOUT_FIX.md`
   - Logo: `docs/LOGO_DISPLAY_FIXES.md`
   - Templates: `docs/TEMPLATE_FIX.md`

3. **System Verification**:
   - Run scripts in `scripts/utils/`
   - Check test results in `tests/`

### For Feature Documentation

1. **SMS/OTP**:
   - `docs/MSG91_SETUP_STEPS.md`
   - `docs/QUICK_MSG91_SETUP.txt`

2. **Voice System**:
   - `docs/WAITER_CALL_VOICE_SYSTEM.md`
   - `docs/VOICE_SYSTEM_SETUP.md`

3. **Logo System**:
   - `docs/LOGO_SYSTEM_DOCUMENTATION.md`
   - `docs/LOGO_DISPLAY_FIXES.md`

## 🎨 Naming Conventions

### Files

- `*_dashboard.html` - Dashboard pages
- `*_page.html` - Content pages
- `*_mobile.html` - Mobile versions
- `test_*.py` - Test scripts
- `check_*.py` - Verification scripts
- `setup_*.py` - Setup scripts
- `fix_*.py` - Fix scripts

### Folders

- Lowercase with underscores
- Descriptive names
- Grouped by purpose

## 🚀 Best Practices

### When Adding New Files

1. **Code Files**:
   - Add to appropriate module
   - Follow module structure
   - Update `__init__.py`

2. **Documentation**:
   - Add to `docs/`
   - Update `docs/README.md`
   - Use clear naming

3. **Tests**:
   - Add to `tests/`
   - Update `tests/README.md`
   - Follow naming convention

4. **Scripts**:
   - Add to appropriate `scripts/` subfolder
   - Document usage
   - Add to relevant README

### When Looking for Files

1. **Check the README** in the relevant folder
2. **Use file search** with naming patterns
3. **Check documentation index** in `docs/README.md`
4. **Review PROJECT_STRUCTURE.md** for overview

## 📊 Quick Reference

### Essential Files

| File | Purpose |
|------|---------|
| `README.md` | Main documentation |
| `PROJECT_STRUCTURE.md` | Structure guide |
| `CLEANUP_SUMMARY.md` | Organization changes |
| `docs/README.md` | Documentation index |
| `tests/README.md` | Test documentation |

### Essential Folders

| Folder | Purpose |
|--------|---------|
| Root modules | Application code |
| `docs/` | All documentation |
| `tests/` | All tests |
| `scripts/` | Utilities |
| `static/` | Frontend assets |
| `templates/` | HTML templates |

## 🆘 Getting Help

1. **Check Documentation**:
   - Start with `docs/README.md`
   - Look for relevant guide

2. **Run Diagnostics**:
   - Use `scripts/utils/` tools
   - Check system status

3. **Review Tests**:
   - Check `tests/` folder
   - Run relevant tests

4. **Contact Team**:
   - Provide error details
   - Reference documentation
   - Share diagnostic results

---

**Last Updated**: March 2026  
**Maintained By**: VisiScure Order Development Team
