# Read-only repository checks. Windows PowerShell 5.1. ASCII only.
# Does not edit tracked files or mutate git state. pytest may write caches and delete its own rows in local Supabase.
# Parameters: -AllowList (required), -Base (default main).
# Exit 0 when all eleven checks pass, 1 when any check fails, 2 on usage errors. The Repo review row is information only.

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

function Get-GrepSource {
    param([string] $GrepLine)
    $match = [regex]::Match($GrepLine, '^(.*?):(\d+):(.*)$')
    if ($match.Success) {
        return $match.Groups[3].Value
    }
    return $GrepLine
}

function Invoke-GrepCheck {
    param(
        [string] $Name,
        [string[]] $Patterns,
        [string[]] $PathSpecs,
        [string] $Allow = ""
    )
    # Header, then git grep lines from Get-GrepSummary, same text as the old blocks.
    Write-Host ("--- {0} ---" -f $Name)
    $results = @()
    foreach ($pattern in @($Patterns)) {
        $gitArgs = @("grep", "-n", "--untracked", "-E", $pattern, "--") + @($PathSpecs)
        $grep = Invoke-GitRead -GitArguments $gitArgs
        $results += $grep
    }
    if ($Allow -ne "") {
        foreach ($result in @($results)) {
            if ($result.Code -ne 0) {
                continue
            }
            $kept = New-Object System.Collections.Generic.List[string]
            foreach ($line in @($result.Lines)) {
                $source = Get-GrepSource -GrepLine $line
                if ($source -notmatch $Allow) {
                    [void]$kept.Add($line)
                }
            }
            if ($kept.Count -eq 0) {
                $result.Code = 1
                $result.Lines = New-Object System.Collections.Generic.List[string]
            } else {
                $result.Lines = $kept
            }
        }
    }
    $summary = Get-GrepSummary -Results $results
    if ($summary.Bad) {
        $checkResult = "fail"
        $checkDetail = "command failed"
    } elseif ($summary.SawMatchCode) {
        $checkResult = "fail"
        if ($summary.MatchCount -eq 1) {
            $checkDetail = "1 match"
        } elseif ($summary.MatchCount -eq 0) {
            $checkDetail = "matches found"
        } else {
            $checkDetail = ("{0} matches" -f $summary.MatchCount)
        }
    } else {
        $checkResult = "pass"
        $checkDetail = "no matches"
    }
    return (New-Object PSObject -Property @{
        Result = $checkResult
        Detail = $checkDetail
    })
}

if ($MyInvocation.InvocationName -eq '.') {
    return
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
    & uv run pytest --fail-on-skip
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
    $testDetail = "pytest exit 0"
} elseif ($pytestCode -eq 6) {
    $testResult = "fail"
    $testDetail = "pytest exit 6 (tests skipped)"
    Write-Host "some tests were skipped; if a local service is not configured, see the Supabase local lines in AGENTS.md."
} else {
    $testResult = "fail"
    $testDetail = "pytest exit $pytestCode"
}

Write-Host "--- Changed files ---"
$committed = Invoke-GitRead -GitArguments @("diff", "--name-only", "--no-renames", "${Base}...HEAD")
$unstaged = Invoke-GitRead -GitArguments @("diff", "--name-only", "--no-renames", "HEAD")
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

$corePattern = '^\s*(from|import)\s+(fastapi|pydantic|tools|db)\b'
$coreRelativePattern = '^\s*from\s+\.+(tools|db)\b'
$core = Invoke-GrepCheck -Name "Core imports" -Patterns @($corePattern, $coreRelativePattern) -PathSpecs @("src/core")

$workersPattern = '^\s*(from|import)\s+workers\b'
$workers = Invoke-GrepCheck -Name "Workers imports" -Patterns @($workersPattern) -PathSpecs @("src", ":!src/entry.py")

$turnsPattern = '^\s*(from|import)\s+(clients|db|config|anthropic)\b'
$turnsRelativePattern = '^\s*from\s+\.+(clients|db|config|anthropic)\b'
$turns = Invoke-GrepCheck -Name "Turns imports" -Patterns @($turnsPattern, $turnsRelativePattern) -PathSpecs @("src/turns")

$updatePattern = '^\s*(from|import)\s+(clients|db|config|anthropic)\b'
$updateRelativePattern = '^\s*from\s+\.+(clients|db|config|anthropic)\b'
$updateImports = Invoke-GrepCheck -Name "Update imports" -Patterns @($updatePattern, $updateRelativePattern) -PathSpecs @("src/api/telegram_update.py")

$toolsPattern = '^\s*(from|import)\s+db\b'
$toolsRelativePattern = '^\s*from\s+\.+db\b'
$tools = Invoke-GrepCheck -Name "Tools imports" -Patterns @($toolsPattern, $toolsRelativePattern) -PathSpecs @("src/tools")

$sdkPattern = '^\s*(from|import)\s+anthropic\b'
$sdkRelativePattern = '^\s*from\s+\.+anthropic\b'
$sdk = Invoke-GrepCheck -Name "SDK imports" -Patterns @($sdkPattern, $sdkRelativePattern) -PathSpecs @("src", ":!src/clients/anthropic_model.py", "evals")

$envCallPattern = '\bos\.(getenv|environ)\b'
$envImportPattern = '^\s*from\s+os\s+import\s+.*\b(getenv|environ)\b'
$envReads = Invoke-GrepCheck -Name "Env reads" -Patterns @($envCallPattern, $envImportPattern) -PathSpecs @("src")

$evalTestsAllow = '^\s*(from|import)\s+tests\.fakes\.memory_plan_store(\s|$)'
$evalTests = Invoke-GrepCheck -Name "Eval tests imports" -Patterns @('^\s*(from|import)\s+tests\b') -PathSpecs @("evals") -Allow $evalTestsAllow

$evalEnv = Invoke-GrepCheck -Name "Eval env reads" -Patterns @($envCallPattern, $envImportPattern) -PathSpecs @("evals", ":!evals/runner.py")

$reviewResult = "info"
$reviewDetail = "no review record in docs/reviews"
$reviewDue = $false
$reviewFiles = @()
if (Test-Path -LiteralPath "docs/reviews") {
    $reviewFiles = @(Get-ChildItem -LiteralPath "docs/reviews" -Filter "*-repo-review.md" -File)
}
if ($reviewFiles.Count -gt 0) {
    $latestReview = $reviewFiles | Sort-Object -Property Name -Descending | Select-Object -First 1
    $reviewText = @(Get-Content -LiteralPath $latestReview.FullName -Encoding UTF8)
    $reviewBase = $null
    foreach ($reviewLine in $reviewText) {
        if ($reviewLine -match '^review-base:\s*([0-9a-f]{7,40})\s*$') {
            $reviewBase = $Matches[1]
            break
        }
    }
    if ($null -eq $reviewBase) {
        $reviewDetail = "review record has no review-base line"
    } else {
        $reviewDiff = Invoke-GitRead -GitArguments @("diff", "--name-only", "--no-renames", $reviewBase, "--", "src")
        if ((-not $reviewDiff.Ok) -or ($reviewDiff.Code -ne 0)) {
            $reviewDetail = "git diff failed"
        } else {
            $reviewCount = $reviewDiff.Lines.Count
            $reviewDetail = ("{0} src files changed since {1} (threshold 15)" -f $reviewCount, $reviewBase)
            if ($reviewCount -ge 15) {
                $reviewResult = "due"
                $reviewDue = $true
            }
        }
    }
}

Write-Host ""
if ($reviewDue) {
    Write-Host "Repo review due: see the review lines in AGENTS.md."
}
Write-Host "check | pass/fail | detail"
Write-Host ("Test | {0} | {1}" -f $testResult, $testDetail)
Write-Host ("Changed files | {0} | {1}" -f $changedResult, $changedDetail)
Write-Host ("Core imports | {0} | {1}" -f $core.Result, $core.Detail)
Write-Host ("Workers imports | {0} | {1}" -f $workers.Result, $workers.Detail)
Write-Host ("Turns imports | {0} | {1}" -f $turns.Result, $turns.Detail)
Write-Host ("Update imports | {0} | {1}" -f $updateImports.Result, $updateImports.Detail)
Write-Host ("Tools imports | {0} | {1}" -f $tools.Result, $tools.Detail)
Write-Host ("SDK imports | {0} | {1}" -f $sdk.Result, $sdk.Detail)
Write-Host ("Env reads | {0} | {1}" -f $envReads.Result, $envReads.Detail)
Write-Host ("Eval tests imports | {0} | {1}" -f $evalTests.Result, $evalTests.Detail)
Write-Host ("Eval env reads | {0} | {1}" -f $evalEnv.Result, $evalEnv.Detail)
Write-Host ("Repo review | {0} | {1}" -f $reviewResult, $reviewDetail)

$anyFail = $false
if ($testResult -ne "pass") {
    $anyFail = $true
}
if ($changedResult -ne "pass") {
    $anyFail = $true
}
if ($core.Result -ne "pass") {
    $anyFail = $true
}
if ($workers.Result -ne "pass") {
    $anyFail = $true
}
if ($turns.Result -ne "pass") {
    $anyFail = $true
}
if ($updateImports.Result -ne "pass") {
    $anyFail = $true
}
if ($tools.Result -ne "pass") {
    $anyFail = $true
}
if ($sdk.Result -ne "pass") {
    $anyFail = $true
}
if ($envReads.Result -ne "pass") {
    $anyFail = $true
}
if ($evalTests.Result -ne "pass") {
    $anyFail = $true
}
if ($evalEnv.Result -ne "pass") {
    $anyFail = $true
}
if ($anyFail) {
    Exit-WithCode 1
}
Exit-WithCode 0
