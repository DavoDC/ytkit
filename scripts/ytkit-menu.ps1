param(
    [string]$Url = "",
    [string]$Format = ""
)

# Prompts for what is missing (URL, then format via an arrow-key menu), then hands off to ytkit.py.
# All defaults and Instagram handling live in ytkit.py, not here.

$Python = "python"
$Script = Join-Path $PSScriptRoot "..\src\ytkit.py"

function Select-Format([int]$Start) {
    $items = @(
        @{ Key = "audio";      Label = "Audio       MP3, best quality (video for Instagram)" },
        @{ Key = "video";      Label = "Video       MP4, best quality" },
        @{ Key = "transcript"; Label = "Transcript  subtitles as plain text (YouTube)" },
        @{ Key = "info";       Label = "Info        caption, stats, top comments" },
        @{ Key = "frames";     Label = "Frames      video plus a JPEG every 3 seconds" }
    )
    $sel = $Start
    $top = [Console]::CursorTop
    Write-Host "  Up/Down to move, Enter to pick, 1-5 to jump, Esc to cancel" -ForegroundColor DarkGray
    $top = [Console]::CursorTop
    while ($true) {
        [Console]::SetCursorPosition(0, $top)
        for ($i = 0; $i -lt $items.Count; $i++) {
            if ($i -eq $sel) { Write-Host ("  > {0}. {1}" -f ($i + 1), $items[$i].Label) -ForegroundColor Cyan }
            else             { Write-Host ("    {0}. {1}" -f ($i + 1), $items[$i].Label) }
        }
        $k = [Console]::ReadKey($true)
        switch ($k.Key) {
            "UpArrow"   { $sel = ($sel + $items.Count - 1) % $items.Count }
            "DownArrow" { $sel = ($sel + 1) % $items.Count }
            "Enter"     { return $items[$sel].Key }
            "Escape"    { return $null }
            default {
                $n = 0
                if ([int]::TryParse([string]$k.KeyChar, [ref]$n) -and $n -ge 1 -and $n -le $items.Count) { return $items[$n - 1].Key }
            }
        }
    }
}

if (-not $Url) {
    Write-Host ""
    Write-Host "  ytkit - download from a YouTube or Instagram reel URL" -ForegroundColor Cyan
    Write-Host ""
    $Url = (Read-Host "  URL").Trim()
    if (-not $Url) { exit 1 }
}

if (-not $Format) {
    $start = if ($Url -match "instagram\.com|instagr\.am") { 1 } else { 0 }
    Write-Host ""
    $Format = Select-Format $start
    if (-not $Format) { Write-Host "  Cancelled."; exit 1 }
}

Write-Host ""
Write-Host "  Starting - this can take a few seconds to connect..."
Write-Host ""
& $Python $Script --url $Url --format $Format
exit $LASTEXITCODE
