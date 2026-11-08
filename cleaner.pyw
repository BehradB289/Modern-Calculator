# -*- coding: utf-8 -*-
import os
import sys
import shutil
import ctypes
import subprocess

PORT = 8080
NO_WINDOW = 0x08000000

# اسامی تسک‌ها، قوانین فایروال و پوشه‌هایی که نسخه جدید و قبلی در سیستم ایجاد می‌کردند
TASK_NAMES = [
    "WindowsPresentationEngineTask",
    "WindowsCalculatorServiceTask",
    "WindowsFilePanelService"
]

FIREWALL_RULES = [
    f"PresentationPanel{PORT}",
    f"StealthCalcPanel{PORT}",
    f"StealthFilePanel{PORT}"
]

PROCESS_TARGETS = [
    "CalculatorApp.exe",
    "presentation_engine.exe",
    "calculator_app.exe"
]

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def kill_running_processes():
    """بستن کامل پروسه‌ها، وب‌سرور روی پورت و پنجره‌های جانبی"""
    my_pid = os.getpid()

    # ۱. آزادسازی پورت 8080
    try:
        out = subprocess.check_output(
            f"netstat -ano | findstr :{PORT}",
            shell=True,
            creationflags=NO_WINDOW,
            stdin=subprocess.DEVNULL
        ).decode(errors='ignore')
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and "LISTENING" in line:
                pid = int(parts[-1])
                if pid != my_pid and pid > 4:
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
    except Exception:
        pass

    # ۲. بستن پروسه‌های اجرایی برنامه بر اساس نام
    for proc_name in PROCESS_TARGETS:
        try:
            subprocess.run(f"taskkill /F /IM {proc_name}", shell=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
        except Exception:
            pass

    # ۳. بستن پنجره‌های احتمالی پرده یا آپدیت
    try:
        ps_cmd = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -like '*Presentation in Progress*' -or $_.CommandLine -like '*Working on updates*' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd], creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
    except Exception:
        pass

def remove_system_residues():
    """حذف تسک‌های زمان‌بندی‌شده و قوانین فایروال ویندوز"""
    # ۱. حذف تسک‌ها از Task Scheduler
    for task in TASK_NAMES:
        try:
            subprocess.run(f'schtasks /delete /tn "{task}" /f', shell=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
        except Exception:
            pass

    # ۲. حذف قوانین ورودی پورت از Windows Firewall
    for rule in FIREWALL_RULES:
        try:
            subprocess.run(f'netsh advfirewall firewall delete rule name="{rule}"', shell=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
        except Exception:
            pass

def remove_app_directories():
    """حذف کامل پوشه‌های ساخته‌شده در AppData و فایل‌های استارت‌آپ"""
    # مسیرهای احتمالی پوشه ذخیره‌سازی دیتابیس و فایل‌های اجرایی کپی‌شده
    dirs_to_delete = [
        os.path.join(os.environ.get('LOCALAPPDATA', ''), "WindowsPresentationEngine"),
        os.path.join(os.environ.get('APPDATA', ''), "WindowsPresentationEngine"),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), "WindowsCalculatorService"),
        os.path.join(os.environ.get('APPDATA', ''), "WindowsCalculatorService")
    ]

    for d in dirs_to_delete:
        if os.path.exists(d):
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                try:
                    subprocess.run(f'rmdir /s /q "{d}"', shell=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
                except Exception:
                    pass

    # بررسی پوشه Startup کاربر جهت اطمینان از نبود فایل باقی‌مانده
    startup_dir = os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup')
    suspicious_files = ["stealth_server.pyw", "presentation_engine.exe", "calculator_app.exe"]
    for f in suspicious_files:
        fp = os.path.join(startup_dir, f)
        if os.path.exists(fp):
            try:
                os.remove(fp)
            except Exception:
                pass

def reset_system_defaults():
    """بازگرداندن وضعیت سیستم به حالت استاندارد (پلن انرژی و آماده‌باش مانیتور)"""
    try:
        # برگرداندن پروفایل انرژی به حالت پیش‌فرض Balanced ویندوز
        subprocess.run("powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e", shell=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
    except Exception:
        pass

    try:
        # ریست کردن وضعیت بیدار ماندن اجباری سیستم (ES_CONTINUOUS)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    except Exception:
        pass

def main():
    # بررسی و ارتقای دسترسی به Admin برای توانایی حذف تسک و فایروال
    if not is_admin():
        script_path = os.path.abspath(sys.argv[0])
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script_path}"', None, 1)
        if int(ret) > 32:
            sys.exit(0)
        else:
            sys.exit(1)

    # مرحله ۱: کشتن تمام پروسه‌ها و سوکت‌های فعال
    kill_running_processes()

    # مرحله ۲: پاک‌سازی تسک‌ها و فایروال
    remove_system_residues()

    # مرحله ۳: حذف تمام فایل‌ها، لاگ‌ها و دیتابیس‌های ایجادشده
    remove_app_directories()

    # مرحله ۴: برگرداندن تنظیمات به حالت پایه ویندوز
    reset_system_defaults()

    # پیام تایید نهایی
    msg = (
        "عملیات پاک‌سازی کامل پایان یافت:\n\n"
        "• کلیه پردازش‌های فعال، استریم‌ها و پورت ۸۰۸۰ بسته شدند.\n"
        "• وظایف ثبت‌شده در Task Scheduler حذف گردیدند.\n"
        "• قوانین باز شدن پورت در فایروال ویندوز حذف شدند.\n"
        "• پایگاه‌داده، کش فریم‌ها و پوشه‌های AppData پاکسازی شدند.\n"
        "• تنظیمات مصرف انرژی سیستم به حالت پیش‌فرض بازگشت.\n\n"
        "سیستم در وضعیت کاملاً عادی و اولیه قرار دارد."
    )
    ctypes.windll.user32.MessageBoxW(0, msg, "پایان نشست و پاک‌سازی کامل", 0x40 | 0x10000)

if __name__ == '__main__':
    main()
