# -*- coding: utf-8 -*-
import os
import sys
import time
import shutil
import ctypes
import subprocess

PORT = 8080
TASK_NAMES = ["WindowsCalculatorServiceTask", "WindowsFilePanelService"]
PROCESS_NAMES = ["calculator_app.exe", "app.exe", "Calculator*.exe"]
FIREWALL_RULES = [f"StealthCalcPanel{PORT}", f"StealthFilePanel{PORT}"]
NO_WINDOW = 0x08000000

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def force_kill_all():
    my_pid = os.getpid()

    # ۱. بستن اجباری تمام پردازش‌های ضبط صدا در ویندوز (MCI)
    try:
        ctypes.windll.winmm.mciSendStringA(b"stop myrec", None, 0, None)
        ctypes.windll.winmm.mciSendStringA(b"close myrec", None, 0, None)
    except Exception:
        pass

    # ۲. بستن پروسه‌ها بر اساس نام فایل
    for proc in PROCESS_NAMES:
        subprocess.run(f"taskkill /F /IM {proc} /T", shell=True, creationflags=NO_WINDOW)

    # ۳. بستن پردازش‌های پایتونی که اسکریپت app.py را اجرا کرده‌اند
    ps_kill_py = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -like '*app.py*' -and $_.ProcessId -ne " + str(my_pid) + " } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_kill_py], creationflags=NO_WINDOW)

    # ۴. آزادسازی پورت 8080 و بستن سوکت‌های باز
    try:
        out = subprocess.check_output(
            f"netstat -ano | findstr :{PORT}",
            shell=True,
            creationflags=NO_WINDOW
        ).decode(errors='ignore')

        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and "LISTENING" in line:
                pid = int(parts[-1])
                if pid != my_pid and pid > 4:
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, creationflags=NO_WINDOW)
    except Exception:
        pass

    # ۵. بیدار کردن و روشن نگه داشتن صفحه نمایش در صورت خاموش بودن
    try:
        ctypes.windll.user32.mouse_event(0x0001, 1, 1, 0, 0)
    except Exception:
        pass

def remove_system_traces():
    # ۱. متوقف کردن و حذف تسک‌های زمان‌بندی‌شده
    for task in TASK_NAMES:
        subprocess.run(f'schtasks /end /tn "{task}"', shell=True, creationflags=NO_WINDOW)
        subprocess.run(f'schtasks /delete /tn "{task}" /f', shell=True, creationflags=NO_WINDOW)

    # ۲. حذف قوانین باز شده در فایروال
    for rule in FIREWALL_RULES:
        subprocess.run(f'netsh advfirewall firewall delete rule name="{rule}"', shell=True, creationflags=NO_WINDOW)

    # ۳. حذف از لیست استثنائات Windows Defender
    appdata = os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA', 'C:\\'))
    install_dir = os.path.join(appdata, "WindowsCalculatorService")
    ps_clean_exclusion = (
        f'Remove-MpPreference -ExclusionPath "{install_dir}" -ErrorAction SilentlyContinue; '
        f'Remove-MpPreference -ExclusionProcess "calculator_app.exe" -ErrorAction SilentlyContinue'
    )
    subprocess.run(
        ["powershell", "-WindowStyle", "Hidden", "-Command", ps_clean_exclusion],
        creationflags=NO_WINDOW
    )

    # ۴. پاکسازی کامل پوشه AppData و دیتابیس تایم‌لاین (timeline.db)
    install_dirs = [
        os.path.join(appdata, "WindowsCalculatorService"),
        os.path.join(appdata, "WindowsFilePanel")
    ]
    for folder in install_dirs:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder, ignore_errors=True)
            except Exception:
                subprocess.run(f'rmdir /S /Q "{folder}"', shell=True, creationflags=NO_WINDOW)

    # ۵. پاک‌سازی فایل‌های احتمالی باقی‌مانده در استارت‌آپ
    startup_dir = os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup')
    for startup_file in ["stealth_server.pyw", "calculator_app.exe"]:
        full_path = os.path.join(startup_dir, startup_file)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception:
                pass

def main():
    if not is_admin():
        script_path = os.path.abspath(sys.argv[0])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script_path}"', None, 1)
        sys.exit(0)

    # توقف فوری پردازش‌ها
    force_kill_all()
    # حذف ردپاها و ریست تنظیمات
    remove_system_traces()

    msg = (
        "🛑 توقف و پاک‌سازی با موفقیت انجام شد:\n\n"
        "• تمام پردازش‌های پس‌زمینه، استریم و مانیتورینگ متوقف شدند.\n"
        "• تسک‌های پس‌زمینه ویندوز به طور کامل لغو و حذف شدند.\n"
        "• پورت 8080 آزاد و ضبط صدا غیرفعال شد.\n"
        "• دیتابیس تایم‌لاین و فایل‌های برنامه از سیستم حذف شدند.\n\n"
        "سیستم کاملاً به حالت عادی و ایمن بازگشت."
    )
    ctypes.windll.user32.MessageBoxW(0, msg, "توقف کامل سیستم", 0x40)

if __name__ == '__main__':
    main()