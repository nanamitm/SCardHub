param(
    [Parameter(Mandatory = $true)][string]$ScratchDirectory,
    [string]$HubDll = "$PSScriptRoot\..\x64\Release\WinSCard.dll"
)
$ErrorActionPreference = 'Stop'
$scratch = New-Item -ItemType Directory -Force -Path $ScratchDirectory
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vs = & $vswhere -latest -products * -property installationPath
$vcvars = Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat'
$source = Join-Path $PSScriptRoot 'status_reader.c'
$modernDef = Join-Path $PSScriptRoot 'status_reader.def'
$legacyDef = Join-Path $PSScriptRoot 'legacy_reader.def'
Push-Location $scratch.FullName
try {
    & cmd /c "`"$vcvars`" >nul && cl /nologo /utf-8 /LD /MD /DWINSCARDAPI= `"$source`" /Fo:status_reader.obj /link /def:`"$modernDef`" /out:status_reader.dll"
    if ($LASTEXITCODE) { throw 'Mock reader build failed' }
    & cmd /c "`"$vcvars`" >nul && link /nologo /dll status_reader.obj kernel32.lib /def:`"$legacyDef`" /out:legacy_reader.dll"
    if ($LASTEXITCODE) { throw 'Legacy mock reader build failed' }
    foreach ($kind in @('modern', 'legacy')) {
        $stage = New-Item -ItemType Directory -Force -Path $kind
        Copy-Item -LiteralPath $HubDll -Destination (Join-Path $stage.FullName 'winscard.dll')
        $reader = if ($kind -eq 'modern') { 'status_reader.dll' } else { 'legacy_reader.dll' }
        Set-Content -LiteralPath (Join-Path $stage.FullName 'SCardHub.ini') -Encoding ascii -Value '[option]',("dll00=" + (Join-Path $scratch.FullName $reader))
        $arguments = @("$PSScriptRoot\status_proxy_test.py", (Join-Path $stage.FullName 'winscard.dll'))
        if ($kind -eq 'legacy') { $arguments += '--legacy' }
        & python @arguments
        if ($LASTEXITCODE) { throw "$kind status proxy test failed" }
    }
} finally {
    Pop-Location
}
