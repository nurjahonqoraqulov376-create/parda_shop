# Saytni ommaviy (probniy) havola bilan ishga tushiradi.
#
# Ishlashi: Django serveri 8765-portda ko'tariladi, so'ng cloudflared uni
# internetga ochadi va https://....trycloudflare.com ko'rinishidagi havola
# beradi. Shu havolani istalgan odamga yuborsangiz - sayt ochiladi.
#
# 8765 porti ataylab tanlangan: odatdagi run.bat 8000-portni band qiladi,
# shuning uchun ikkalasi bir vaqtda ishlay oladi.
#
# MUHIM: havola faqat shu oyna ochiq turganda ishlaydi. Oynani yopsangiz -
# havola ham o'chadi. Har safar ishga tushirganda havola YANGI bo'ladi.
#
# Diqqat: bu fayl faqat ASCII belgilardan iborat bo'lishi kerak. Windows
# PowerShell 5.1 .ps1 fayllarni tizim kodlashida o'qiydi, shuning uchun
# UTF-8 belgilar (uzun tire va h.k.) skriptni buzib qo'yadi.

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$cloudflared = Join-Path $root 'tools\cloudflared.exe'
$port = 8765

if (-not (Test-Path $cloudflared)) {
    Write-Host "tools\cloudflared.exe topilmadi." -ForegroundColor Red
    exit 1
}

# Port bandmi?
$busy = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    Write-Host "$port porti allaqachon band. Avvalgi share oynasini yoping." -ForegroundColor Red
    exit 1
}

# Havola tashqi odamlarga ochiq bo'lgani uchun DEBUG ni o'chiramiz: aks holda
# har qanday xatoda Django to'liq traceback - kod, fayl yo'llari va hatto
# bazadagi mijoz ma'lumotlari - begonalarga ko'rinib qolishi mumkin.
# --insecure: DEBUG=False bo'lsa ham static (css/js) fayllarni beradi.
# SERVE_MEDIA: yuklangan rasmlar ham ko'rinsin.
$env:DEBUG = 'False'
$env:SERVE_MEDIA = 'True'

Write-Host "Django serveri ishga tushmoqda (port $port, DEBUG=False)..." -ForegroundColor Cyan
$server = Start-Process -FilePath $python `
    -ArgumentList 'manage.py', 'runserver', "127.0.0.1:$port", '--noreload', '--insecure' `
    -WorkingDirectory $root -PassThru -WindowStyle Minimized

# Server ko'tarilguncha portni kutamiz
$ready = $false
foreach ($i in 1..40) {
    Start-Sleep -Milliseconds 500
    if ($server.HasExited) { break }
    $listen = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listen) { $ready = $true; break }
}

if (-not $ready) {
    Write-Host "Server $port portda ko'tarilmadi." -ForegroundColor Red
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
    exit 1
}

Write-Host "Server tayyor. Ommaviy havola ochilmoqda..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Quyida 'trycloudflare.com' bilan tugaydigan havola chiqadi." -ForegroundColor Yellow
Write-Host "O'shani nusxalab boshqalarga yuboring." -ForegroundColor Yellow
Write-Host "To'xtatish uchun: Ctrl+C" -ForegroundColor DarkGray
Write-Host ""

try {
    & $cloudflared tunnel --url "http://127.0.0.1:$port"
}
finally {
    Write-Host ""
    Write-Host "To'xtatilmoqda..." -ForegroundColor DarkGray
    if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force }
}
