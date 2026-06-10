# Literature Review Pipeline - Full Sequential Run
# Runs Theme B (--resume from p04) then C through P
# Auto-recovers from Chrome crashes

$projectDir = "C:\Users\balan\IdeaProjects\academic_paper_maker"
$pythonExe = "C:\Users\balan\anaconda3\envs\academic_paper_maker\python.exe"
$writingDir = "C:\Users\balan\My Drive (balandong@ums.edu.my)\iterate_literature_review\writing"
$logFile = "$projectDir\run_lit_review_all_log.txt"
$startTime = Get-Date

function Log($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

function Kill-Chrome {
    Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
}

function Get-ThemeFolder($themeCode) {
    $code = $themeCode.ToLower()
    $folders = Get-ChildItem $writingDir -Directory -ErrorAction SilentlyContinue |
               Where-Object { $_.Name -like "theme_${code}_*" -or $_.Name -eq "theme_${code}_" }
    if ($folders) { return $folders[0].FullName }
    return $null
}

function Check-ReferenceTable($themeCode) {
    $folder = Get-ThemeFolder $themeCode
    if (-not $folder) {
        Log "  WARNING: No output folder found for theme $themeCode"
        return @{ HasFolder=$false; HasRefTable=$false; RefTableHasRows=$false; ParagraphCount=0 }
    }
    $refTable = Join-Path $folder "reference_table.tex"
    $paraDir = Join-Path $folder "paragraphs"
    $paraCount = (Get-ChildItem $paraDir -Filter "*.tex" -ErrorAction SilentlyContinue | Measure-Object).Count

    $hasRefTable = Test-Path $refTable
    $refTableHasRows = $false
    if ($hasRefTable) {
        $content = Get-Content $refTable -Raw -ErrorAction SilentlyContinue
        # Check if it has actual table rows (not just placeholder)
        if ($content -and ($content -match '\\hline' -or $content -match '\\\\') -and
            $content -notmatch 'no studies matched' -and
            ($content | Measure-Object -Line).Lines -gt 5) {
            $refTableHasRows = $true
        } elseif ($content -and $content.Trim().Length -lt 100) {
            $refTableHasRows = $false
        } else {
            $refTableHasRows = $hasRefTable
        }
    }

    return @{
        HasFolder      = $true
        FolderName     = Split-Path $folder -Leaf
        HasRefTable    = $hasRefTable
        RefTableHasRows= $refTableHasRows
        ParagraphCount = $paraCount
    }
}

function Run-Theme($label, $configFile, $extraArgs = "") {
    $cmd = "$pythonExe -m apm.lit_review.run_pipeline --config $configFile $extraArgs"
    Log "=== Starting Theme $label === ($cmd)"

    $maxRetries = 2
    $attempt = 0
    $success = $false

    while ($attempt -le $maxRetries -and -not $success) {
        $attempt++
        if ($attempt -gt 1) {
            Log "  Retry attempt $attempt for Theme $label — killing Chrome first..."
            Kill-Chrome
            # On retry, always add --resume
            if ($extraArgs -notmatch '--resume') {
                $extraArgs = "$extraArgs --resume".Trim()
                $cmd = "$pythonExe -m apm.lit_review.run_pipeline --config $configFile $extraArgs"
            }
        }

        $proc = Start-Process -FilePath $pythonExe `
            -ArgumentList "-m apm.lit_review.run_pipeline --config $configFile $extraArgs" `
            -WorkingDirectory $projectDir `
            -NoNewWindow `
            -PassThru `
            -Wait

        $exitCode = $proc.ExitCode
        Log "  Theme $label finished with exit code: $exitCode"

        if ($exitCode -eq 0) {
            $success = $true
        } else {
            Log "  Theme $label FAILED (exit $exitCode)"
            if ($attempt -le $maxRetries) {
                Log "  Will retry after killing Chrome..."
            }
        }
    }

    # Post-run verification
    $check = Check-ReferenceTable $label
    if ($check.HasFolder) {
        Log "  Folder: $($check.FolderName)"
        Log "  Paragraphs written: $($check.ParagraphCount)"
        if (-not $check.HasRefTable) {
            Log "  WARNING: reference_table.tex NOT FOUND"
        } elseif (-not $check.RefTableHasRows) {
            Log "  WARNING: reference_table.tex appears empty or contains only placeholder"
        } else {
            Log "  reference_table.tex: OK (has rows)"
        }
    } else {
        Log "  WARNING: Output folder not found for theme $label"
    }

    return @{ Theme=$label; Success=$success; Check=$check }
}

# ── START LOG ──────────────────────────────────────────────────────────────────
Log "======================================================================"
Log "Literature Review Pipeline - Full Run Started"
Log "Project: $projectDir"
Log "Writing output: $writingDir"
Log "======================================================================"

$results = @()

# Theme B - resume from p04
$results += Run-Theme "B" "setting/lit_review/config_theme_B.yaml" "--resume"

# Themes C through P (fresh runs)
$themes = @(
    @{ Code="C"; Config="setting/lit_review/config_theme_C.yaml" }
    @{ Code="D"; Config="setting/lit_review/config_theme_D.yaml" }
    @{ Code="E"; Config="setting/lit_review/config_theme_E.yaml" }
    @{ Code="F"; Config="setting/lit_review/config_theme_F.yaml" }
    @{ Code="G"; Config="setting/lit_review/config_theme_G.yaml" }
    @{ Code="H"; Config="setting/lit_review/config_theme_H.yaml" }
    @{ Code="I"; Config="setting/lit_review/config_theme_I.yaml" }
    @{ Code="J"; Config="setting/lit_review/config_theme_J.yaml" }
    @{ Code="K"; Config="setting/lit_review/config_theme_K.yaml" }
    @{ Code="L"; Config="setting/lit_review/config_theme_L.yaml" }
    @{ Code="M"; Config="setting/lit_review/config_theme_M.yaml" }
    @{ Code="P"; Config="setting/lit_review/config_theme_P.yaml" }
)

foreach ($t in $themes) {
    $results += Run-Theme $t.Code $t.Config ""
}

# ── FINAL REPORT ───────────────────────────────────────────────────────────────
$endTime = Get-Date
$elapsed = $endTime - $startTime
$totalMinutes = [math]::Round($elapsed.TotalMinutes, 1)

Log "======================================================================"
Log "FINAL REPORT"
Log "Total run time: $totalMinutes minutes"
Log "======================================================================"

foreach ($r in $results) {
    $c = $r.Check
    $status = if ($r.Success) { "OK" } else { "FAILED" }
    $refStatus = if (-not $c.HasRefTable) { "MISSING" } elseif (-not $c.RefTableHasRows) { "PLACEHOLDER/EMPTY" } else { "OK" }
    $folderName = if ($c.FolderName) { $c.FolderName } else { "(no folder)" }
    Log "  Theme $($r.Theme): [$status] | Folder: $folderName | Paragraphs: $($c.ParagraphCount) | reference_table.tex: $refStatus"
}

# Check for main.tex and references.bib
$mainTex = Get-ChildItem "C:\Users\balan\My Drive (balandong@ums.edu.my)\iterate_literature_review\" -Filter "main.tex" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
$refBib = Get-ChildItem "C:\Users\balan\My Drive (balandong@ums.edu.my)\iterate_literature_review\" -Filter "references.bib" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1

if ($mainTex) { Log "  main.tex: FOUND at $($mainTex.FullName)" } else { Log "  main.tex: NOT FOUND" }
if ($refBib) { Log "  references.bib: FOUND at $($refBib.FullName)" } else { Log "  references.bib: NOT FOUND" }

Log "======================================================================"
Log "Run complete."
Log "======================================================================"

Write-Host "`nFull log saved to: $logFile"
