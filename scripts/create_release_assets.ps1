# Create Release Assets for GitHub Release v0.1
# Packages demo results and creates a ZIP file for release

param(
    [string]$Version = "0.1.0",
    [string]$OutputDir = "release-assets"
)

$ErrorActionPreference = "Stop"

Write-Host "Creating release assets for ChangeLens v$Version..." -ForegroundColor Green

# Create output directory
if (Test-Path $OutputDir) {
    Remove-Item -Recurse -Force $OutputDir
}
New-Item -ItemType Directory -Path $OutputDir | Out-Null

# Package demo results
$DemoZip = Join-Path $OutputDir "changelens-demo-results-v$Version.zip"
Write-Host "Packaging demo results..." -ForegroundColor Yellow

$TempDir = Join-Path $env:TEMP "changelens-demo-$([System.Guid]::NewGuid())"
New-Item -ItemType Directory -Path $TempDir | Out-Null

try {
    # Copy demo directory contents
    Copy-Item -Recurse -Force "results\demo\*" -Destination $TempDir
    
    # Create ZIP
    Compress-Archive -Path "$TempDir\*" -DestinationPath $DemoZip -Force
    Write-Host "✓ Created: $DemoZip" -ForegroundColor Green
    
    # Get file size
    $Size = (Get-Item $DemoZip).Length / 1MB
    Write-Host "  Size: $([math]::Round($Size, 2)) MB" -ForegroundColor Gray
}
finally {
    # Cleanup temp directory
    if (Test-Path $TempDir) {
        Remove-Item -Recurse -Force $TempDir
    }
}

# Copy one-pager markdown (for PDF conversion)
$OnePagerSource = "docs\changelens-onepager.md"
if (Test-Path $OnePagerSource) {
    Copy-Item $OnePagerSource -Destination $OutputDir
    Write-Host "✓ Copied one-pager template: $OnePagerSource" -ForegroundColor Green
    Write-Host "  Note: Convert to PDF manually using pandoc or online converter" -ForegroundColor Gray
    Write-Host "  Command: pandoc $OnePagerSource -o $OutputDir\changelens-onepager.pdf" -ForegroundColor Gray
}

Write-Host "`nRelease assets created in: $OutputDir" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Review the demo results ZIP" -ForegroundColor White
Write-Host "2. Convert changelens-onepager.md to PDF (optional)" -ForegroundColor White
Write-Host "3. Create GitHub Release and upload these assets" -ForegroundColor White
Write-Host "   - Go to: https://github.com/chenyuxiangAK47/changelens/releases/new" -ForegroundColor White
Write-Host "   - Tag: v$Version" -ForegroundColor White
Write-Host "   - Title: ChangeLens v$Version" -ForegroundColor White
Write-Host "   - Upload: $DemoZip" -ForegroundColor White
