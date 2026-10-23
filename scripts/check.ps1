# Read-only repository checks. Windows PowerShell 5.1. ASCII only.
# Does not create, edit, or delete files, and does not mutate git state.
# Parameters: -AllowList (required), -Base (default main).
# Exit 0 when all four checks pass, 1 when any check fails, 2 on usage errors.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $AllowList,

    [string] $Base = "main"
)

$ErrorActionPreference = "Continue"
if (Test-Path -Path "variable:PSNativeCommandUseErrorActionPreference") {
    $PSNativeCommandUseErrorActionPreference = $false
}

function Exit-WithCode {
    param([int] $Code)
    # cmd sets $LASTEXITCODE for an in-process caller. exit sets the process code.
    & cmd.exe /c "exit $Code"
    exit $Code
}

function Invoke-GitRead {
    param([string[]] $GitArguments)
    $resultCode = 0
    $ok = $true
    $errorText = ""
    $lines = New-Object System.Collections.Generic.List[string]
    try {
        $raw = & git --no-pager @GitArguments
        if ($null -eq $LASTEXITCODE) {
            $resultCode = 128
            $ok = $false
            $errorText = "git did not return an exit code."
        } else {
            $resultCode = $LASTEXITCODE
        }
        if ($null -ne $raw) {
            foreach ($item in @($raw)) {
                $text = ("$item").Trim()
                if ($text.Length -gt 0) {
                    [void]$lines.Add($text)
                }
            }
        }
    } catch {
        $ok = $false
        $resultCode = 128
        $errorText = $_.Exception.Message
    }
    return (New-Object PSObject -Property @{
        Code = $resultCode
        Lines = $lines
        Ok = $ok
        Error = $errorText
    })
}

function Add-UniqueLines {
    param($RawLines, $Dest, $Seen)
    if ($null -eq $RawLines) {
        return
    }
    foreach ($item in @($RawLines)) {
        $text = ("$item").Trim()
        if ($text.Length -eq 0) {
            continue
        }
        if ($Seen.Add($text)) {
            [void]$Dest.Add($text)
        }
    }
}

function Update-AllowMatch {
    param(
        [string] $RelativePath,
        $EntryKind,
        $EntryKey,
        $Used
    )
    $found = $false
    for ($i = 0; $i -lt $EntryKind.Count; $i++) {
        $isMatch = $false
        $kind = $EntryKind[$i]
        $key = $EntryKey[$i]
        if ($kind -eq "exact") {
            if ([string]::Equals($RelativePath, $key, [System.StringComparison]::Ordinal)) {
                $isMatch = $true
            }
        } elseif ($key.Length -eq 0) {
            $isMatch = $true
        } else {
            $needle = $key + "/"
            if ($RelativePath.StartsWith($needle, [System.StringComparison]::Ordinal)) {
                $isMatch = $true
            }
        }
        if ($isMatch) {
            $found = $true
            [void]$Used.Add($i)
        }
    }
    return $found
}

function Get-GrepSummary {
    param($Results)
    $matchCount = 0
    $bad = $false
    $sawMatchCode = $false
    foreach ($result in @($Results)) {
        $code = $result.Code
        $valid = $result.Ok -and (($code -eq 0) -or ($code -eq 1))
        if (-not $valid) {
            $bad = $true
            if ($result.Error) {
                Write-Host ("ERROR: git grep failed with exit code {0}. {1}" -f $code, $result.Error)
            } else {
                Write-Host ("ERROR: git grep failed with exit code {0}." -f $code)
            }
            continue
        }
        if ($code -eq 0) {
            $sawMatchCode = $true
            foreach ($line in @($result.Lines)) {
                Write-Host $line
                $matchCount = $matchCount + 1
            }
        }
    }
    return (New-Object PSObject -Property @{
        Bad = $bad
        MatchCount = $matchCount
        SawMatchCode = $sawMatchCode
    })
}

$rootRaw = $null
$rootCode = 128
try {
    $rootRaw = & git rev-parse --show-toplevel
    if ($null -eq $LASTEXITCODE) {
        $rootCode = 128
    } else {
        $rootCode = $LASTEXITCODE
    }
} catch {
    Write-Host "ERROR: git rev-parse --show-toplevel failed."
    Write-Host $_.Exception.Message
    Exit-WithCode 2
}

if ($rootCode -ne 0) {
    Write-Host "ERROR: git rev-parse --show-toplevel failed."
    Exit-WithCode 2
}

$rootText = $null
if ($null -ne $rootRaw) {
    foreach ($item in @($rootRaw)) {
        $candidate = ("$item").Trim()
        if ($candidate.Length -gt 0) {
            $rootText = $candidate
            break
        }
    }
}
if ([string]::IsNullOrWhiteSpace($rootText)) {
    Write-Host "ERROR: git rev-parse --show-toplevel returned no path."
    Exit-WithCode 2
}

try {
    $rootFull = (Get-Item -LiteralPath $rootText).FullName.TrimEnd('\', '/')
    $cwdFull = (Get-Item -LiteralPath $PWD.Path).FullName.TrimEnd('\', '/')
} catch {
    Write-Host "ERROR: cannot resolve the git repository root."
    Write-Host $_.Exception.Message
    Exit-WithCode 2
}
if ($rootFull -ne $cwdFull) {
    Write-Host "ERROR: current directory is not the git repository root."
    Write-Host "current: $cwdFull"
    Write-Host "root: $rootFull"
    Exit-WithCode 2
}

if (-not (Test-Path -LiteralPath $AllowList -PathType Leaf)) {
    Write-Host "ERROR: allow list file not found: $AllowList"
    Exit-WithCode 2
}

$rawLines = @()
try {
    $rawLines = @(Get-Content -LiteralPath $AllowList -ErrorAction Stop)
} catch {
    Write-Host "ERROR: cannot read allow list file: $AllowList"
    Write-Host $_.Exception.Message
    Exit-WithCode 2
}

$entryText = New-Object System.Collections.Generic.List[string]
$entryKind = New-Object System.Collections.Generic.List[string]
$entryKey = New-Object System.Collections.Generic.List[string]

foreach ($line in $rawLines) {
    if ($null -eq $line) {
        continue
    }
    $trimmed = ("$line").Trim()
    if ($trimmed.Length -eq 0) {
        continue
    }
    if ($trimmed.StartsWith("#")) {
        continue
    }
    $suffix = "/**"
    if ($trimmed.EndsWith($suffix, [System.StringComparison]::Ordinal)) {
        $prefix = $trimmed.Substring(0, $trimmed.Length - $suffix.Length)
        if ($prefix.IndexOf("*") -ge 0) {
            Write-Host "ERROR: malformed allow list line: $trimmed"
            Exit-WithCode 2
        }
        [void]$entryText.Add($trimmed)
        [void]$entryKind.Add("dir")
        [void]$entryKey.Add($prefix)
    } elseif ($trimmed.IndexOf("*") -ge 0) {
        Write-Host "ERROR: malformed allow list line: $trimmed"
        Exit-WithCode 2
    } else {
        [void]$entryText.Add($trimmed)
        [void]$entryKind.Add("exact")
        [void]$entryKey.Add($trimmed)
    }
}

Write-Host "--- Test ---"
$pytestCode = 1
try {
    & uv run pytest
    if ($null -eq $LASTEXITCODE) {
        $pytestCode = 1
    } else {
        $pytestCode = $LASTEXITCODE
    }
} catch {
    Write-Host "ERROR: pytest command failed."
    Write-Host $_.Exception.Message
    $pytestCode = 1
}
if ($pytestCode -eq 0) {
    $testResult = "pass"
} else {
    $testResult = "fail"
}
$testDetail = "pytest exit $pytestCode"

Write-Host "--- Changed files ---"
$committed = Invoke-GitRead -GitArguments @("diff", "--name-only", "${Base}...HEAD")
$unstaged = Invoke-GitRead -GitArguments @("diff", "--name-only", "HEAD")
$untracked = Invoke-GitRead -GitArguments @("ls-files", "--others", "--exclude-standard")

$listingOk = $committed.Ok -and $unstaged.Ok -and $untracked.Ok
$listingOk = $listingOk -and ($committed.Code -eq 0) -and ($unstaged.Code -eq 0) -and ($untracked.Code -eq 0)

$changedResult = "fail"
$changedDetail = "command failed"
if (-not $listingOk) {
    if ((-not $committed.Ok) -or ($committed.Code -ne 0)) {
        if ($committed.Error) {
            Write-Host ("ERROR: git diff --name-only {0}...HEAD failed with exit code {1}. {2}" -f $Base, $committed.Code, $committed.Error)
        } else {
            Write-Host ("ERROR: git diff --name-only {0}...HEAD failed with exit code {1}." -f $Base, $committed.Code)
        }
    }
    if ((-not $unstaged.Ok) -or ($unstaged.Code -ne 0)) {
        if ($unstaged.Error) {
            Write-Host ("ERROR: git diff --name-only HEAD failed with exit code {0}. {1}" -f $unstaged.Code, $unstaged.Error)
        } else {
            Write-Host ("ERROR: git diff --name-only HEAD failed with exit code {0}." -f $unstaged.Code)
        }
    }
    if ((-not $untracked.Ok) -or ($untracked.Code -ne 0)) {
        if ($untracked.Error) {
            Write-Host ("ERROR: git ls-files --others --exclude-standard failed with exit code {0}. {1}" -f $untracked.Code, $untracked.Error)
        } else {
            Write-Host ("ERROR: git ls-files --others --exclude-standard failed with exit code {0}." -f $untracked.Code)
        }
    }
} else {
    $changed = New-Object System.Collections.Generic.List[string]
    $changedSeen = New-Object "System.Collections.Generic.HashSet[string]"
    Add-UniqueLines -RawLines $committed.Lines -Dest $changed -Seen $changedSeen
    Add-UniqueLines -RawLines $unstaged.Lines -Dest $changed -Seen $changedSeen
    Add-UniqueLines -RawLines $untracked.Lines -Dest $changed -Seen $changedSeen

    $used = New-Object "System.Collections.Generic.HashSet[int]"
    $bad = New-Object System.Collections.Generic.List[string]
    foreach ($rel in $changed) {
        $found = Update-AllowMatch -RelativePath $rel -EntryKind $entryKind -EntryKey $entryKey -Used $used
        if (-not $found) {
            [void]$bad.Add($rel)
        }
    }

    if ($bad.Count -eq 0) {
        Write-Host "All changed files are in the allow list."
    } else {
        Write-Host "Not in allow list:"
        foreach ($rel in $bad) {
            Write-Host $rel
        }
    }

    $unusedCount = 0
    for ($i = 0; $i -lt $entryText.Count; $i++) {
        if (-not $used.Contains($i)) {
            if ($unusedCount -eq 0) {
                Write-Host "Allow list entries with no matching changed file:"
            }
            Write-Host $entryText[$i]
            $unusedCount = $unusedCount + 1
        }
    }

    if ($bad.Count -eq 0) {
        $changedResult = "pass"
        if ($changed.Count -eq 1) {
            $changedDetail = "1 file allowed"
        } else {
            $changedDetail = ("{0} files allowed" -f $changed.Count)
        }
    } else {
        $changedResult = "fail"
        if ($bad.Count -eq 1) {
            $changedDetail = "1 file not allowed"
        } else {
            $changedDetail = ("{0} files not allowed" -f $bad.Count)
        }
    }
}

Write-Host "--- Core imports ---"
$corePattern = '^\s*(from|import)\s+(fastapi|pydantic|tools|db)\b'
$coreRelativePattern = '^\s*from\s+\.+(tools|db)\b'
$coreDirect = Invoke-GitRead -GitArguments @("grep", "-n", "--untracked", "-E", $corePattern, "--", "src/core")
$coreRelative = Invoke-GitRead -GitArguments @("grep", "-n", "--untracked", "-E", $coreRelativePattern, "--", "src/core")
$coreSummary = Get-GrepSummary -Results @($coreDirect, $coreRelative)
if ($coreSummary.Bad) {
    $coreResult = "fail"
    $coreDetail = "command failed"
} elseif ($coreSummary.SawMatchCode) {
    $coreResult = "fail"
    if ($coreSummary.MatchCount -eq 1) {
        $coreDetail = "1 match"
    } elseif ($coreSummary.MatchCount -eq 0) {
        $coreDetail = "matches found"
    } else {
        $coreDetail = ("{0} matches" -f $coreSummary.MatchCount)
    }
} else {
    $coreResult = "pass"
    $coreDetail = "no matches"
}

Write-Host "--- Workers imports ---"
$workersPattern = '^\s*(from|import)\s+workers\b'
$workers = Invoke-GitRead -GitArguments @("grep", "-n", "--untracked", "-E", $workersPattern, "--", "src", ":!src/entry.py")
$workersSummary = Get-GrepSummary -Results @($workers)
if ($workersSummary.Bad) {
    $workersResult = "fail"
    $workersDetail = "command failed"
} elseif ($workersSummary.SawMatchCode) {
    $workersResult = "fail"
    if ($workersSummary.MatchCount -eq 1) {
        $workersDetail = "1 match"
    } elseif ($workersSummary.MatchCount -eq 0) {
        $workersDetail = "matches found"
    } else {
        $workersDetail = ("{0} matches" -f $workersSummary.MatchCount)
    }
} else {
    $workersResult = "pass"
    $workersDetail = "no matches"
}

Write-Host ""
Write-Host "check | pass/fail | detail"
Write-Host ("Test | {0} | {1}" -f $testResult, $testDetail)
Write-Host ("Changed files | {0} | {1}" -f $changedResult, $changedDetail)
Write-Host ("Core imports | {0} | {1}" -f $coreResult, $coreDetail)
Write-Host ("Workers imports | {0} | {1}" -f $workersResult, $workersDetail)

$anyFail = $false
if ($testResult -ne "pass") {
    $anyFail = $true
}
if ($changedResult -ne "pass") {
    $anyFail = $true
}
if ($coreResult -ne "pass") {
    $anyFail = $true
}
if ($workersResult -ne "pass") {
    $anyFail = $true
}
if ($anyFail) {
    Exit-WithCode 1
}
Exit-WithCode 0
