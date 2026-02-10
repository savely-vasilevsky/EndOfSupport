# Help System Documentation

## Overview

The AWS End-of-Support Tool now includes a comprehensive help system with visual user guides and in-app help access.

## Components

### 1. User Guide Files

#### USERGUIDE.md (Original)
- **Location**: Root directory
- **Purpose**: Comprehensive text-based user guide
- **Format**: Markdown without screenshots
- **Access**: Via Help button or F1 key in GUI

#### USERGUIDE_VISUAL.md (New)
- **Location**: Root directory
- **Purpose**: Enhanced visual user guide with screenshot placeholders
- **Format**: Markdown with `[SCREENSHOT: description]` placeholders
- **Status**: Ready for screenshots to be added
- **Features**:
  - Step-by-step instructions with visual aids
  - Screenshot placeholders for all major features
  - Detailed explanations of GUI, CLI, Excel, and HTML outputs
  - Troubleshooting section with visual examples

### 2. GUI Help Integration

#### Help Button
- **Location**: Main GUI window, button frame
- **Keyboard Shortcut**: F1
- **Behavior**:
  1. Attempts to open USERGUIDE.md with default application
  2. Falls back to built-in quick help dialog if file not found
  3. Shows link to full user guide at top of quick help

#### Quick Help Dialog
- **Trigger**: When USERGUIDE.md cannot be found
- **Content**: Condensed help information
- **Features**:
  - Scrollable text widget
  - Reference to full USERGUIDE.md
  - Key features and shortcuts
  - Modal dialog (blocks main window)

### 3. Documentation Files

#### docs/SCREENSHOTS_GUIDE.md
- **Purpose**: Instructions for capturing and adding screenshots
- **Content**:
  - List of required screenshots (38 total)
  - Screenshot capture guidelines
  - Platform-specific instructions (Windows/macOS/Linux)
  - Image optimization tips
  - Step-by-step workflow

#### docs/HELP_SYSTEM_README.md (This File)
- **Purpose**: Overview of the help system
- **Content**: Architecture and usage documentation

## Help System Flow

```
User Presses F1 or Clicks Help Button
           ↓
    Try to open USERGUIDE.md
           ↓
    ┌──────┴──────┐
    │             │
File Found    File Not Found
    │             │
    ↓             ↓
Open with     Show Quick Help
Default App   Dialog with Link
```

## Implementation Details

### GUI Changes (src/gui.py)

1. **Help Button Added**:
   ```python
   ttk.Button(button_frame, text="Help", command=self._show_help).grid(row=0, column=2, padx=5)
   ```

2. **F1 Keyboard Shortcut**:
   ```python
   self.root.bind("<F1>", lambda e: self._show_help())
   ```

3. **_show_help() Method**:
   - Locates USERGUIDE.md in multiple possible locations
   - Opens file with platform-specific command
   - Falls back to quick help dialog

4. **_show_quick_help() Method**:
   - Creates modal dialog window
   - Displays condensed help text
   - Includes reference to full user guide
   - Scrollable text widget

### Platform-Specific File Opening

- **Windows**: `os.startfile(userguide_path)`
- **macOS**: `subprocess.run(["open", userguide_path])`
- **Linux**: `subprocess.run(["xdg-open", userguide_path])`

## Adding Screenshots

To complete the visual user guide:

1. **Review Required Screenshots**:
   - See `docs/SCREENSHOTS_GUIDE.md` for complete list
   - 38 screenshots covering GUI, CLI, Excel, and HTML

2. **Capture Screenshots**:
   - Follow platform-specific instructions
   - Use consistent styling and sample data
   - Ensure text is readable

3. **Organize Files**:
   ```bash
   mkdir -p docs/images
   # Save all screenshots to docs/images/
   ```

4. **Update USERGUIDE_VISUAL.md**:
   - Replace `[SCREENSHOT: description]` with:
   ```markdown
   ![Description](docs/images/screenshot-name.png)
   ```

5. **Optimize Images**:
   ```bash
   # Compress images
   optipng -o7 docs/images/*.png
   ```

6. **Verify**:
   - Check all image links work
   - Ensure images display in markdown viewers
   - Test on different platforms

## Usage

### For End Users

**GUI**:
1. Launch the application
2. Press F1 or click the Help button
3. User guide opens in default markdown viewer

**CLI**:
```bash
# View user guide manually
cat USERGUIDE.md
# Or open in browser/editor
```

### For Developers

**Testing Help System**:
```python
# Run GUI
python -m src.gui

# Press F1 to test help
# Or click Help button
```

**Updating Help Content**:
1. Edit `USERGUIDE.md` or `USERGUIDE_VISUAL.md`
2. Add/update screenshots in `docs/images/`
3. Test help button functionality
4. Commit changes

## Future Enhancements

### Potential Improvements

1. **HTML Help**:
   - Convert markdown to HTML for better formatting
   - Include embedded screenshots
   - Add search functionality

2. **Context-Sensitive Help**:
   - Show help for specific features
   - Tooltips on hover
   - "What's This?" mode

3. **Video Tutorials**:
   - Screen recordings of common workflows
   - Embedded in HTML help or linked from guide

4. **Interactive Tour**:
   - First-run tutorial
   - Highlight features step-by-step
   - Skip/replay options

5. **Online Documentation**:
   - Host on GitHub Pages
   - Always up-to-date
   - Searchable and indexed

6. **Localization**:
   - Translate user guide to multiple languages
   - Language selection in GUI

## Maintenance

### Regular Updates

- **After Feature Changes**: Update relevant sections in user guide
- **After UI Changes**: Recapture affected screenshots
- **Version Updates**: Update version number and date in guides
- **Bug Fixes**: Update troubleshooting section

### Quality Checks

- [ ] All screenshots are current
- [ ] All links work correctly
- [ ] Text is accurate and clear
- [ ] Examples use current syntax
- [ ] No broken image links
- [ ] Consistent formatting throughout

## Troubleshooting

### Help Button Not Working

**Issue**: Help button doesn't open user guide

**Solutions**:
1. Verify USERGUIDE.md exists in project root
2. Check file permissions
3. Ensure default markdown viewer is configured
4. Quick help dialog should appear as fallback

### Screenshots Not Displaying

**Issue**: Images don't show in markdown viewer

**Solutions**:
1. Verify image paths are correct
2. Check images exist in docs/images/
3. Use relative paths from USERGUIDE_VISUAL.md
4. Ensure markdown viewer supports images

### File Not Found Errors

**Issue**: USERGUIDE.md not found when running as executable

**Solutions**:
1. Include USERGUIDE.md in PyInstaller spec
2. Update path detection in _show_help()
3. Ensure file is bundled with executable

## Contact

For questions or issues with the help system:
- Open an issue on GitHub
- Contact the development team
- See CONTRIBUTING.md for guidelines

---

*Last updated: February 10, 2026*
