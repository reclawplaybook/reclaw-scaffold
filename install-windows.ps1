Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoUrl = $env:RECLAW_REPO_URL
if (-not $RepoUrl) { $RepoUrl = "https://github.com/reclawplaybook/reclaw-scaffold.git" }

$InstallDir = $env:RECLAW_INSTALL_DIR
if (-not $InstallDir) { $InstallDir = Join-Path $HOME "my-reclaw" }

function Need-Command($Name) {
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Ensure-WingetPackage($CommandName, $PackageId) {
  if (Need-Command $CommandName) { return }
  if (-not (Need-Command "winget")) {
    throw "Missing $CommandName and winget is not available. Install $CommandName manually, then rerun this file."
  }
  Write-Host "Installing $PackageId with winget..."
  winget install --id $PackageId --silent --accept-package-agreements --accept-source-agreements
}

Write-Host ""
Write-Host "ReClaw Windows demo installer"
Write-Host "This installs a free demo-mode agent first. No Claude, ChatGPT, or API key is required."
Write-Host ""

Ensure-WingetPackage "git" "Git.Git"
Ensure-WingetPackage "node" "OpenJS.NodeJS.LTS"

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

if (Test-Path $InstallDir) {
  Write-Host "Install folder already exists: $InstallDir"
} else {
  Write-Host "Cloning ReClaw scaffold to $InstallDir..."
  git clone --depth 1 $RepoUrl $InstallDir
}

Set-Location $InstallDir
npm install

$Name = Read-Host "Your name [Operator]"
if (-not $Name) { $Name = "Operator" }

$Work = Read-Host "What do you do? One sentence [I run work that needs reliable follow-through.]"
if (-not $Work) { $Work = "I run work that needs reliable follow-through." }

$AgentName = Read-Host "Agent name [ReClaw]"
if (-not $AgentName) { $AgentName = "ReClaw" }

node bin/write-env.mjs .env `
  "AGENT_NAME=$AgentName" `
  "RECLAW_PROVIDER=demo" `
  "USER_NAME=$Name" `
  "USER_WORK=$Work" `
  "CLAUDE_TIER=pro" `
  "HEARTBEAT_INTERVAL=60" `
  "HEARTBEAT_ON_START=false" `
  "ANTHROPIC_API_KEY=" `
  "DISCORD_BOT_TOKEN=" `
  "DISCORD_CHANNEL_ID=" `
  "RECLAW_HOME=$InstallDir" `
  "MEMORY_DIR=memory" `
  "LOG_LEVEL=info"

node -e "const fs=require('fs'); const path=require('path'); for (const f of ['SOUL.md','USER.md','DIRECTIVE.md']) { const t=fs.readFileSync(path.join('templates',f),'utf8').replaceAll('{{AGENT_NAME}}', process.env.AGENT_NAME || '$AgentName').replaceAll('{{USER_NAME}}', '$Name').replaceAll('{{USER_WORK}}', '$Work'); fs.writeFileSync(f,t); } fs.copyFileSync(path.join('templates','AGENTS.md'),'AGENTS.md'); fs.mkdirSync('memory',{recursive:true});"

Write-Host ""
Write-Host "Running doctor..."
$Bash = Get-Command bash -ErrorAction SilentlyContinue
if ($Bash) {
  bash reclaw-doctor.sh
} elseif (Test-Path "$env:ProgramFiles\Git\bin\bash.exe") {
  & "$env:ProgramFiles\Git\bin\bash.exe" reclaw-doctor.sh
} else {
  Write-Host "Git Bash was not found in PATH yet. Open a new PowerShell and run:"
  Write-Host "  cd $InstallDir"
  Write-Host "  bash reclaw-doctor.sh"
}

Write-Host ""
Write-Host "Try it:"
Write-Host "  cd $InstallDir"
Write-Host "  node src/main.js --test-message `"What are you?`""
Write-Host "  node src/main.js --remember `"Follow up Friday.`""
Write-Host "  node src/main.js --memory-search `"Friday`""
Write-Host ""
Write-Host "Demo install complete. Connect Claude later by setting RECLAW_PROVIDER=claude in .env."
