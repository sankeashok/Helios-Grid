# GitHub Social Preview Setup Guide

## Issue: Thumbnail Not Loading in LinkedIn Post Inspector

The thumbnail isn't showing up in LinkedIn's post inspector because GitHub doesn't automatically use repository images for social previews. Here's how to fix it:

## Solution 1: Set Repository Social Preview Image (Recommended)

1. **Go to your GitHub repository**: https://github.com/sankeashok/Helios-Grid
2. **Navigate to Settings**: Click on "Settings" tab in your repository
3. **Scroll to Social Preview**: Find the "Social preview" section
4. **Upload Image**: Click "Upload an image..." and select `helios-grid-thumbnail.png`
5. **Save**: The image should be 1280×640px (our image is 1200×630px which is acceptable)

## Solution 2: Create GitHub Pages with Open Graph Meta Tags

If the above doesn't work, we can create a GitHub Pages site with proper meta tags:

1. **Enable GitHub Pages** in repository settings
2. **Create index.html** with Open Graph meta tags
3. **Use the Pages URL** for sharing instead of the repository URL

## Solution 3: Alternative Sharing Strategy

Instead of sharing the repository URL directly, you can:

1. **Create a LinkedIn post** with the thumbnail image attached
2. **Include the repository link** in the post text
3. **Use GitHub's raw image URL** in social media posts

## Current Status

- ✅ **Thumbnail Created**: `helios-grid-thumbnail.png` (24.8 KB, 1200×630px)
- ❌ **Social Preview**: Not configured in GitHub repository settings
- ⏳ **LinkedIn Preview**: Will work once GitHub social preview is set

## Next Steps

1. Follow Solution 1 to set up the repository social preview
2. Test the LinkedIn post inspector again after 24-48 hours (GitHub caching)
3. If still not working, implement Solution 2 with GitHub Pages

## Technical Details

- **Image Size**: 24.8 KB (well under social media limits)
- **Dimensions**: 1200×630px (optimal for social sharing)
- **Format**: PNG (widely supported)
- **Content**: Professional Helios-Grid branding with energy theme