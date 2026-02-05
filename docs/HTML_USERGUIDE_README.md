# HTML User Guide - Complete Documentation

## Overview

The AWS End-of-Support Tool now includes a comprehensive HTML user guide with 40 embedded screenshots, accessible directly from the application's Help button (F1).

## Features

### Two-Tier Help System

1. **Quick Help Dialog** (F1 or Help button)
   - Instant access to essential information
   - Keyboard shortcuts and basic usage
   - Button to open detailed visual guide

2. **Detailed Visual Guide** (HTML)
   - Complete documentation with 40 screenshots
   - All images embedded as base64 (no external dependencies)
   - Professional styling with AWS color scheme
   - Fully self-contained (3.51 MB single file)

## File Structure

```
docs/
├── USERGUIDE.html              # Complete HTML guide (3.51 MB)
├── images/                     # Source screenshots (40 PNG files)
│   ├── gui-*.png              # GUI screenshots (10)
│   ├── cli-*.png              # CLI screenshots (3)
│   ├── html-*.png             # HTML report screenshots (10)
│   ├── excel-*.png            # Excel screenshots (10)
│   ├── console-output.png     # Output formats (5)
│   └── error-*.png            # Error dialogs (2)
├── SCREENSHOT_STATUS.md        # Screenshot inventory
├── HTML_USERGUIDE_README.md    # This file
├── GUI_SCREENSHOT_AUTOMATION.md # PyAutoGUI guide
├── SCREENSHOTS_GUIDE.md        # Manual capture guide
└── CAPTURING_SCREENSHOTS.md    # General instructions

USERGUIDE_VISUAL.md             # Markdown source (root)
```

## How It Works

### 1. Markdown Source
`USERGUIDE_VISUAL.md` contains the documentation with image references:
```markdown
![Description](docs/images/screenshot.png)
```

### 2. HTML Generation
`src/html_userguide_generator.py` converts markdown to HTML:
- Parses markdown syntax
- Embeds images as base64 data URIs
- Applies professional CSS styling
- Generates single self-contained HTML file

### 3. GUI Integration
`src/gui.py` provides access:
- F1 keyboard shortcut
- Help button in toolbar
- Quick help dialog with link to detailed guide
- Opens HTML in default browser

## Usage

### For End Users

**Access Help:**
1. Launch the application: `python -m src.gui`
2. Press **F1** or click **Help** button
3. Click **"Open Detailed Visual Guide"** button
4. HTML guide opens in your default browser

**Direct Access:**
```bash
# Windows
start docs/USERGUIDE.html

# macOS
open docs/USERGUIDE.html

# Linux
xdg-open docs/USERGUIDE.html
```

### For Developers

**Regenerate HTML Guide:**
```bash
python src/html_userguide_generator.py
```

**Update Screenshots:**
```bash
# 1. Capture new screenshots
python tests/capture_all_screenshots.py

# 2. Update markdown references
python scripts/update_screenshots.py

# 3. Regenerate HTML
python src/html_userguide_generator.py
```

**Add New Screenshot:**
1. Capture and save to `docs/images/screenshot-name.png`
2. Add to `USERGUIDE_VISUAL.md`:
   ```markdown
   ![Description](docs/images/screenshot-name.png)
   ```
3. Regenerate HTML:
   ```bash
   python src/html_userguide_generator.py
   ```

## Screenshot Automation

### Automated Capture (37 screenshots)

**Playwright (HTML Reports):**
```bash
python tests/capture_screenshots.py
```
- Captures 7 HTML report screenshots
- Uses sanitized sample data
- Fully automated browser control

**PIL/Pillow (CLI & Diagrams):**
```bash
python tests/capture_all_screenshots.py
```
- Generates 3 CLI output images
- Creates status diagram
- Text-to-image rendering

**PyAutoGUI (GUI):**
```bash
python tests/capture_gui_screenshots.py
```
- Captures 10 GUI screenshots
- Automated keyboard/mouse control
- Requires user to position window

### Manual Capture (3 screenshots)

Some screenshots require manual capture:
- Excel screenshots (open Excel and capture)
- Error dialogs (trigger errors and capture)
- Output format examples (open files and capture)

See `docs/SCREENSHOTS_GUIDE.md` for detailed instructions.

## Technical Details

### HTML Generation

**Input:** `USERGUIDE_VISUAL.md` (Markdown)
**Output:** `docs/USERGUIDE.html` (HTML with embedded images)

**Process:**
1. Read markdown file
2. Parse markdown syntax (headers, lists, code, tables)
3. Find image references
4. Read image files from `docs/images/`
5. Convert images to base64 data URIs
6. Embed images inline in HTML
7. Apply CSS styling
8. Write complete HTML document

**Benefits:**
- Single file distribution
- No broken image links
- Works offline
- Easy to share
- Professional appearance

### CSS Styling

The HTML guide uses a professional AWS-inspired theme:
- **Colors**: AWS orange (#ff9900), dark blue (#232f3e)
- **Typography**: System fonts for readability
- **Layout**: Responsive container with max-width
- **Components**: Styled tables, code blocks, images
- **Print**: Optimized for printing

### Image Embedding

Images are embedded as base64 data URIs:
```html
<img src="data:image/png;base64,iVBORw0KGgoAAAANS..." alt="Description">
```

**Advantages:**
- No external dependencies
- Single file distribution
- No broken links
- Works offline

**Disadvantages:**
- Larger file size (3.51 MB vs ~2 MB with external images)
- Slower initial load
- Cannot cache images separately

## Data Privacy

✅ **All screenshots use sanitized data** from:
- `C:/Users/savely/OneDrive - amazon.com/Presentations to Keep/EndOfSupportTool/Versions.html`
- `C:/Users/savely/OneDrive - amazon.com/Presentations to Keep/EndOfSupportTool/Versions.xlsx`

❌ **No customer data** from `example.csv` is used in screenshots.

## Distribution

### Include in Release

When building releases, include:
```
dist/
├── EndOfSupportTool.exe        # Windows executable
└── docs/
    └── USERGUIDE.html          # HTML user guide
```

### PyInstaller Configuration

Update `EndOfSupportTool.spec`:
```python
datas=[
    ('docs/USERGUIDE.html', 'docs'),
],
```

### Installer Package

For installer packages (MSI, DMG, etc.):
- Install `USERGUIDE.html` to application directory
- Create Start Menu shortcut to HTML guide
- Add "Help" menu item in application

## Maintenance

### Regular Updates

Update screenshots when:
- UI changes significantly
- New features are added
- Bug fixes affect appearance
- User feedback indicates confusion

### Version Control

Track changes to:
- `USERGUIDE_VISUAL.md` - Documentation content
- `docs/images/*.png` - Screenshot files
- `docs/USERGUIDE.html` - Generated HTML (optional)

Consider `.gitignore` for generated HTML:
```gitignore
# Generated documentation
docs/USERGUIDE.html
```

Then regenerate during build process.

### Quality Checks

Before release:
1. ✅ All screenshots are current
2. ✅ No placeholder images remain
3. ✅ HTML opens in browser correctly
4. ✅ All images display properly
5. ✅ Links work (internal anchors)
6. ✅ No customer data visible
7. ✅ File size is reasonable (<5 MB)
8. ✅ Help button opens guide correctly

## Troubleshooting

### HTML Guide Not Found

**Symptom:** "User Guide Not Found" error when clicking Help

**Solutions:**
1. Verify `docs/USERGUIDE.html` exists
2. Check file path in `src/gui.py`
3. Regenerate HTML: `python src/html_userguide_generator.py`
4. For frozen executable, verify file is included in build

### Images Not Displaying

**Symptom:** Broken image icons in HTML

**Solutions:**
1. Check image files exist in `docs/images/`
2. Verify image paths in `USERGUIDE_VISUAL.md`
3. Regenerate HTML to re-embed images
4. Check browser console for errors

### File Size Too Large

**Symptom:** HTML file is very large (>10 MB)

**Solutions:**
1. Optimize PNG files: `optipng docs/images/*.png`
2. Reduce screenshot dimensions
3. Use JPEG for photos (PNG for UI screenshots)
4. Consider external images instead of embedding

### Styling Issues

**Symptom:** HTML looks broken or unstyled

**Solutions:**
1. Check CSS in `src/html_userguide_generator.py`
2. Test in different browsers
3. Verify HTML structure is valid
4. Check for JavaScript errors (if any)

## Future Enhancements

### Planned Features

1. **Search Functionality**
   - Add JavaScript search box
   - Highlight search results
   - Jump to sections

2. **Dark Mode**
   - CSS dark theme
   - Toggle button
   - Respect system preference

3. **Interactive Examples**
   - Embedded code samples
   - Copy-to-clipboard buttons
   - Live demos

4. **Video Tutorials**
   - Embed video walkthroughs
   - Screen recordings
   - Animated GIFs

5. **Localization**
   - Multi-language support
   - Translated screenshots
   - Language selector

6. **PDF Export**
   - Generate PDF from HTML
   - Print-optimized layout
   - Bookmarks and TOC

### Community Contributions

To contribute screenshots or documentation:
1. Fork the repository
2. Add/update screenshots in `docs/images/`
3. Update `USERGUIDE_VISUAL.md`
4. Regenerate HTML
5. Submit pull request

## Resources

### Documentation
- `USERGUIDE_VISUAL.md` - Markdown source
- `docs/USERGUIDE.html` - Generated HTML
- `docs/SCREENSHOT_STATUS.md` - Screenshot inventory

### Scripts
- `src/html_userguide_generator.py` - HTML generator
- `tests/capture_all_screenshots.py` - Automation script
- `scripts/update_screenshots.py` - Markdown updater

### Guides
- `docs/GUI_SCREENSHOT_AUTOMATION.md` - PyAutoGUI guide
- `docs/SCREENSHOTS_GUIDE.md` - Manual capture
- `docs/CAPTURING_SCREENSHOTS.md` - General instructions

## Support

For issues or questions:
1. Check this README
2. Review `docs/SCREENSHOT_STATUS.md`
3. Check `docs/SCREENSHOTS_GUIDE.md`
4. Open GitHub issue

---

**Status**: ✅ Complete and ready for production use!

**Last Updated**: February 5, 2026
