import sys
import os
import re
import json
import subprocess
from datetime import datetime
from collections import defaultdict

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# بارگذاری فونت Vazir پس از ایجاد QApplication
def load_vazir_font():
    """بارگذاری فونت Vazir و اعمال آن در صورت وجود QApplication"""
    try:
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        candidates = [
            os.path.join(base_path, "Fonts", "Vazir.ttf"),
            os.path.join(base_path, "Vazir.ttf"),
        ]

        for font_path in candidates:
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    if font_families:
                        font_family = font_families[0]
                        app = QApplication.instance()
                        if app is not None:
                            app.setFont(QFont(font_family, 10))
                        return FontProperties(fname=font_path)
        return None
    except Exception as e:
        print(f"خطا در بارگذاری فونت Vazir: {str(e)}")
        return None


# متغیر سراسری فونت (پس از راه‌اندازی QApplication مقداردهی می‌شود)
vazir_font = None

# شکل‌دهی متن فارسی برای Matplotlib (در صورت نصب کتابخانه‌ها)
try:
    import arabic_reshaper  # type: ignore
    from bidi.algorithm import get_display  # type: ignore

    def shape_text(text: str) -> str:
        if not text:
            return text
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception:
            return text
except Exception:
    def shape_text(text: str) -> str:
        return text

# تبدیل اعداد انگلیسی به فارسی برای برچسب‌های درصد
def fa_digits(text: str) -> str:
    mapping = str.maketrans('0123456789.%', '۰۱۲۳۴۵۶۷۸۹.%')
    try:
        return text.translate(mapping)
    except Exception:
        return text

def fa_autopct(pct: float, fmt: str = '%1.1f%%') -> str:
    try:
        return fa_digits(fmt % pct)
    except Exception:
        return fmt % pct


class ThemeManager:
    """مدیریت تم‌های تاریک و روشن"""
    DARK_THEME = {
        'background': '#1f1f23',
        'foreground': '#E6E6E6',
        'button': '#2a2a2e',
        'button_hover': '#3a3a3f',
        'input_bg': '#121214',
        'input_text': '#FFFFFF',
        'tab_bg': '#202024',
        'tab_text': '#CCCCCC',
        'progress': '#0aa0ff',
        'error': '#ff4d4f',
        'success': '#00c853',
        'button_text': '#FFFFFF',
        'toggle_bg': '#555',
        'toggle_active': '#0d6efd',
        'html_bg': '#121214',
        'html_text': '#FFFFFF',
        'html_table_border': '#3a3a3f',
        'html_table_header_bg': '#0aa0ff',
        'html_row_hover': '#2b2b30',
    }

    LIGHT_THEME = {
        'background': '#F7F7FB',
        'foreground': '#1f1f23',
        'button': '#E9E9F0',
        'button_hover': '#dedee6',
        'input_bg': '#FFFFFF',
        'input_text': '#000000',
        'tab_bg': '#FFFFFF',
        'tab_text': '#000000',
        'progress': '#0aa0ff',
        'error': '#ff4d4f',
        'success': '#00a152',
        'button_text': '#000000',
        'toggle_bg': '#CCC',
        'toggle_active': '#0d6efd',
        'html_bg': '#FFFFFF',
        'html_text': '#000000',
        'html_table_border': '#e3e3ea',
        'html_table_header_bg': '#0aa0ff',
        'html_row_hover': '#f3f3f8',
    }

    @staticmethod
    def apply_theme(app, theme_name):
        theme = ThemeManager.DARK_THEME if theme_name == "dark" else ThemeManager.LIGHT_THEME
        app.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['background']};
                color: {theme['foreground']};
            }}
            QPushButton {{
                background-color: {theme['button']};
                color: {theme['button_text']};
                border: 1px solid rgba(0,0,0,0.1);
                padding: 8px 12px;
                border-radius: 6px;
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {theme['input_bg']};
                color: {theme['input_text']};
                border: 1px solid {theme['button']};
                padding: 8px 10px;
                border-radius: 6px;
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QTabWidget::pane {{
                border: 1px solid {theme['button']};
                background-color: {theme['tab_bg']};
                border-radius: 6px;
            }}
            QTabBar::tab {{
                background-color: {theme['tab_bg']};
                color: {theme['tab_text']};
                padding: 10px 16px;
                border: 1px solid {theme['button']};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QTabBar::tab:selected {{
                background-color: {theme['button']};
            }}
            QProgressBar {{
                border: 1px solid {theme['button']};
                border-radius: 6px;
                text-align: center;
                height: 16px;
            }}
            QProgressBar::chunk {{
                background-color: {theme['progress']};
                border-radius: 6px;
            }}
            QLabel {{
                color: {theme['foreground']};
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QCheckBox {{
                color: {theme['foreground']};
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QGroupBox {{
                color: {theme['foreground']};
                border: 1px solid {theme['button']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px 0 6px;
                font-weight: bold;
            }}
            QTableWidget {{
                gridline-color: {theme['button']};
                background: {theme['input_bg']};
            }}
            QHeaderView::section {{
                background-color: {theme['button']};
                color: {theme['button_text']};
                border: none;
                padding: 6px;
            }}
        """)


class ProfileManager:
    """مدیریت پروفایل‌های اسکن"""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROFILES_FILE = os.path.join(BASE_DIR, "scan_profiles.json")

    @staticmethod
    def load_profiles():
        try:
            with open(ProfileManager.PROFILES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def save_profiles(profiles):
        with open(ProfileManager.PROFILES_FILE, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=4, ensure_ascii=False)

    @staticmethod
    def add_profile(name, settings):
        profiles = ProfileManager.load_profiles()
        profiles[name] = settings
        ProfileManager.save_profiles(profiles)

    @staticmethod
    def delete_profile(name):
        profiles = ProfileManager.load_profiles()
        if name in profiles:
            del profiles[name]
            ProfileManager.save_profiles(profiles)


class ScanWorker(QThread):
    """پردازش اسکن در پس‌زمینه"""
    progress_updated = pyqtSignal(int)
    scan_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._is_running = True
        self.results_folder = None
        self.active_ips = set()
        self.process = None
        self.port_data = []

    def run(self):
        try:
            ip_input = self.settings.get('target', '')
            sanitized_ip = re.sub(r'[^\w\-_\. ]', '_', ip_input)
            folder_name = f"scan_results({sanitized_ip})"
            os.makedirs(folder_name, exist_ok=True)
            self.results_folder = folder_name

            log_file_path = os.path.join(folder_name, "scan_log.txt")
            self.log_file = open(log_file_path, 'w', encoding='utf-8')

            start_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] شروع اسکن شبکه برای هدف: {ip_input}\n"
            self.log_message.emit(start_msg)
            self.log_file.write(start_msg)
            self.log_file.flush()

            # مرحله 1: شناسایی آی‌پی‌های فعال
            self.log_message.emit("🔍 شروع شناسایی آی‌پی‌های فعال...\n")
            self.progress_updated.emit(0)

            active_ips_file = os.path.join(folder_name, "active_ips.txt")
            temp_output = os.path.join(folder_name, "scan_temp.txt")

            target = self.settings.get('target', '')

            if target.startswith('-iL'):
                parts = target.split()
                file_path = parts[1] if len(parts) > 1 else ''
                if not os.path.exists(file_path):
                    error_msg = f"❌ فایل لیست آی‌پی وجود ندارد: {file_path}\n"
                    self.log_message.emit(error_msg)
                    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] فایل لیست آی‌پی وجود ندارد: {file_path}\n"
                    self.log_file.write(log_msg)
                    self.log_file.flush()
                    self.log_file.close()
                    self.scan_complete.emit({})
                    return

                with open(file_path, 'r', encoding='utf-8') as f:
                    ips = f.read().strip().split('\n')
                    self.active_ips = set(ip.strip() for ip in ips if ip.strip())

                with open(active_ips_file, 'w', encoding='utf-8') as f:
                    for ip in sorted(self.active_ips):
                        f.write(f"{ip}\n")

                active_count = len(self.active_ips)
                if active_count > 0:
                    msg = f"✅ یافتن {active_count} آی‌پی فعال از فایل.\n"
                    self.log_message.emit(msg)
                    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] یافت {active_count} آی‌پی فعال از فایل\n"
                    self.log_file.write(log_msg)
                    self.log_file.flush()
                else:
                    msg = "❌ هیچ آی‌پی فعالی در فایل یافت نشد.\n"
                    self.log_message.emit(msg)
                    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] هیچ آی‌پی فعالی در فایل یافت نشد\n"
                    self.log_file.write(log_msg)
                    self.log_file.flush()
                    self.log_file.close()
                    self.scan_complete.emit({})
                    return
            else:
                # پشتیبانی از ورودی‌های چندگانه (فاصله یا کاما)
                targets = [t for t in re.split(r'[\s,]+', target) if t]
                nmap_cmd = ['nmap', '-sn', '-oN', temp_output] + targets

                cmd_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DEBUG] اجرای Nmap برای شناسایی آی‌پی‌های فعال: {' '.join(nmap_cmd)}\n"
                self.log_message.emit(cmd_msg)
                self.log_file.write(cmd_msg)
                self.log_file.flush()

                try:
                    self.process = subprocess.Popen(nmap_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, stderr = self.process.communicate()

                    if self.process.returncode == 0:
                        if os.path.exists(temp_output):
                            with open(temp_output, 'r', encoding='utf-8') as f:
                                content = f.read()
                                ips_found = []
                                for line in content.split('\n'):
                                    hdr = re.match(r'^Nmap scan report for (.+)$', line.strip())
                                    if hdr:
                                        rest = hdr.group(1)
                                        ip_in_line = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', rest)
                                        if ip_in_line:
                                            ips_found.append(ip_in_line.group(1))
                                self.active_ips = set(ips_found)

                            with open(active_ips_file, 'w', encoding='utf-8') as f:
                                for ip in sorted(self.active_ips):
                                    f.write(f"{ip}\n")

                            active_count = len(self.active_ips)
                            if active_count > 0:
                                msg = f"✅ یافتن {active_count} آی‌پی فعال.\n"
                                self.log_message.emit(msg)
                                log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] یافت {active_count} آی‌پی فعال\n"
                                self.log_file.write(log_msg)
                                self.log_file.flush()
                            else:
                                msg = "❌ هیچ آی‌پی فعالی یافت نشد.\n"
                                self.log_message.emit(msg)
                                log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] هیچ آی‌پی فعالی یافت نشد\n"
                                self.log_file.write(log_msg)
                                self.log_file.flush()
                                self.log_file.close()
                                self.scan_complete.emit({})
                                return
                        else:
                            error_msg = f"❌ فایل خروجی Nmap یافت نشد: {temp_output}\n"
                            self.log_message.emit(error_msg)
                            log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] فایل خروجی Nmap یافت نشد: {temp_output}\n"
                            self.log_file.write(log_msg)
                            self.log_file.flush()
                            self.log_file.close()
                            self.scan_complete.emit({})
                            return
                    else:
                        error_msg = f"❌ اسکن Nmap با کد خروجی ناموفق بود: {self.process.returncode}\n"
                        self.log_message.emit(error_msg)
                        log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] اسکن Nmap با کد خروجی ناموفق بود: {self.process.returncode}\n"
                        self.log_file.write(log_msg)
                        self.log_file.flush()
                        self.log_file.close()
                        self.scan_complete.emit({})
                        return
                except Exception as e:
                    error_msg = f"❌ خطا در اجرای Nmap: {str(e)}\n"
                    self.log_message.emit(error_msg)
                    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] خطا در اجرای Nmap: {str(e)}\n"
                    self.log_file.write(log_msg)
                    self.log_file.flush()
                    self.log_file.close()
                    self.scan_complete.emit({})
                    return

            # به‌روزرسانی پیشرفت
            self.progress_updated.emit(50)

            # مرحله 2: اسکن پورت‌ها
            self.log_message.emit(f"🔍 شروع اسکن پورت‌ها برای {len(self.active_ips)} آی‌پی فعال...\n")

            port_scan_output = os.path.join(folder_name, "port_scan_results.txt")
            ports = self.settings.get('ports', [])
            port_list = ','.join(ports)
            scan_type = "-sU" if self.settings.get('udp_scan', False) else "-sS"

            if self.settings.get('simple_scan', False):
                nmap_cmd = [
                    'nmap', scan_type,
                    '-p', port_list,
                    '-iL', active_ips_file,
                    '-oN', port_scan_output,
                ]
            else:
                min_rate = self.settings.get('min_rate', 100)
                max_rate = self.settings.get('max_rate', 200)
                scan_delay = self.settings.get('scan_delay', '100ms')
                max_retries = self.settings.get('max_retries', 5)

                nmap_cmd = [
                    'nmap', scan_type,
                    '-p', port_list,
                    '--min-rate', str(min_rate),
                    '--max-rate', str(max_rate),
                    '--scan-delay', scan_delay,
                    '--max-retries', str(max_retries),
                    '--ttl', '64',
                    '-iL', active_ips_file,
                    '-oN', port_scan_output,
                ]

            cmd_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DEBUG] اجرای Nmap برای اسکن پورت: {' '.join(nmap_cmd)}\n"
            self.log_message.emit(cmd_msg)
            self.log_file.write(cmd_msg)
            self.log_file.flush()

            try:
                self.process = subprocess.Popen(nmap_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = self.process.communicate()

                if self.process.returncode == 0:
                    if os.path.exists(port_scan_output):
                        with open(port_scan_output, 'r', encoding='utf-8') as f:
                            content = f.read()

                            current_ip = None
                            for line in content.split('\n'):
                                ip_line_match = re.match(r'^Nmap scan report for (.+)$', line.strip())
                                if ip_line_match:
                                    rest = ip_line_match.group(1)
                                    ip_in_line = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', rest)
                                    if ip_in_line:
                                        current_ip = ip_in_line.group(1)
                                    else:
                                        current_ip = None
                                    continue

                                port_line_match = re.match(r'^(\d+)/(tcp|udp)\s+(\w+)\s+(\S+)', line.strip())
                                if port_line_match and current_ip:
                                    port = port_line_match.group(1)
                                    protocol = port_line_match.group(2).upper()
                                    state = port_line_match.group(3)
                                    service = port_line_match.group(4)

                                    self.port_data.append({
                                        'ip': current_ip,
                                        'port': port,
                                        'protocol': protocol,
                                        'state': state,
                                        'service': service,
                                    })

                                    self.log_message.emit(f"[+] {line.strip()}\n")

                        msg = f"\n✅ اسکن کامل شد. مجموع آی‌پی‌های فعال: {len(self.active_ips)}\n"
                        self.log_message.emit(msg)
                        log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] اسکن پورت با موفقیت انجام شد\n"
                        self.log_file.write(log_msg)
                        self.log_file.flush()
                    else:
                        error_msg = f"❌ فایل خروجی اسکن پورت یافت نشد: {port_scan_output}\n"
                        self.log_message.emit(error_msg)
                        log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] فایل خروجی اسکن پورت یافت نشد: {port_scan_output}\n"
                        self.log_file.write(log_msg)
                        self.log_file.flush()
                else:
                    error_msg = f"❌ اسکن پورت Nmap با کد خروجی ناموفق بود: {self.process.returncode}\n"
                    self.log_message.emit(error_msg)
                    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] اسکن پورت Nmap با کد خروجی ناموفق بود: {self.process.returncode}\n"
                    self.log_file.write(log_msg)
                    self.log_file.flush()
            except Exception as e:
                error_msg = f"❌ خطا در اجرای Nmap برای اسکن پورت: {str(e)}\n"
                self.log_message.emit(error_msg)
                log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] خطا در اجرای Nmap برای اسکن پورت: {str(e)}\n"
                self.log_file.write(log_msg)
                self.log_file.flush()

            # تولید گزارش‌ها (با نمودار و بدون نمودار)
            html_with = self.generate_html_report(
                list(self.active_ips), port_scan_output, folder_name, log_file_path, target, include_charts=True
            )
            html_without = self.generate_html_report(
                list(self.active_ips), port_scan_output, folder_name, log_file_path, target, include_charts=False
            )

            if html_with:
                msg = f"📊 گزارش HTML (با نمودار) در {html_with} تولید شد.\n"
                self.log_message.emit(msg)
                log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] گزارش HTML (با نمودار) در {html_with} تولید شد\n"
                self.log_file.write(log_msg)
                self.log_file.flush()
            if html_without:
                msg = f"📄 گزارش HTML (بدون نمودار) در {html_without} تولید شد.\n"
                self.log_message.emit(msg)
                log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] گزارش HTML (بدون نمودار) در {html_without} تولید شد\n"
                self.log_file.write(log_msg)
                self.log_file.flush()

            self.progress_updated.emit(100)

            self.log_file.close()

            results = {
                '_results_folder': folder_name,
                'active_ips': list(self.active_ips),
                'port_scan_output': port_scan_output,
                'html_report_with_charts': html_with,
                'html_report_no_charts': html_without,
                'port_data': self.port_data,
            }

            self.scan_complete.emit(results)
        except Exception as e:
            error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] اسکن ناموفق بود: {str(e)}\n"
            self.log_message.emit(error_msg)
            if hasattr(self, 'log_file') and self.log_file:
                self.log_file.write(error_msg)
                self.log_file.close()
            self.error_occurred.emit(f"اسکن ناموفق بود: {str(e)}")

    def generate_html_report(self, active_ips, port_scan_output, output_dir, log_file, scanned_range, include_charts=True):
        """تولید گزارش HTML؛ include_charts: اگر True باشد تصاویر نمودارها درج می‌شوند"""
        html_file = os.path.join(output_dir, "report_with_charts.html" if include_charts else "report_no_charts.html")

        port_content = ""
        if os.path.exists(port_scan_output):
            with open(port_scan_output, 'r', encoding='utf-8') as f:
                port_content = f.read()

        current_theme = ThemeManager.DARK_THEME if self.settings.get('theme', 'dark') == 'dark' else ThemeManager.LIGHT_THEME

        # ایجاد ردیف‌های جدول
        html_rows = ""
        if self.port_data:
            for data in self.port_data:
                html_rows += (
                    f"<tr>"
                    f"<td>{data['ip']}</td>"
                    f"<td>{data['port']}</td>"
                    f"<td>{data['protocol']}</td>"
                    f"<td>{data['state']}</td>"
                    f"<td>{data['service']}</td>"
                    f"</tr>\n"
                )

        # بدنه گزارش
        if not self.port_data:
            table_section = "<p class=\"error\">هیچ نتیجه‌ای برای نمایش وجود ندارد.</p>"
        else:
            table_section = f"""
            <table>
                <tr>
                    <th>آی‌پی</th>
                    <th>پورت</th>
                    <th>پروتکل</th>
                    <th>وضعیت</th>
                    <th>سرویس</th>
                </tr>
                {html_rows}
            </table>
            """

        charts_section = ""
        if include_charts:
            charts_section = f"""
            <div class=\"chart-container\"> 
                <div class=\"chart\">\n                    <h3>توزیع وضعیت پورت‌ها</h3>\n                    <img src=\"port_states_pie.png\" alt=\"Port States Distribution\">\n                </div>\n                <div class=\"chart\">\n                    <h3>استفاده از پروتکل‌ها</h3>\n                    <img src=\"protocol_usage_bar.png\" alt=\"Protocol Usage\">\n                </div>\n                <div class=\"chart\">\n                    <h3>تعداد پورت‌های باز بر اساس آی‌پی</h3>\n                    <img src=\"open_ports_per_ip.png\" alt=\"Open Ports per IP\">\n                </div>\n                <div class=\"chart\">\n                    <h3>تعداد میزبان‌ها بر اساس شماره پورت (ستونی)</h3>\n                    <img src=\"counts_per_port_bar.png\" alt=\"Counts per Port (Bar)\">\n                </div>\n                <div class=\"chart\">\n                    <h3>سهم پورت‌ها از بین میزبان‌های دارای پورت باز (دایره‌ای)</h3>\n                    <img src=\"counts_per_port_pie.png\" alt=\"Counts per Port (Pie)\">\n                </div>\n            </div>\n            """

        html_content = f"""<!DOCTYPE html>
<html lang=\"fa\" dir=\"rtl\">
<head>
    <meta charset=\"UTF-8\">
    <title>گزارش اسکن</title>
    <style>
        body {{ font-family: Vazir, Segoe UI, Tahoma; direction: rtl; margin: 20px; background: {current_theme['html_bg']}; color: {current_theme['html_text']}; }}
        h1 {{ font-size: 24px; margin-bottom: 16px; }}
        p {{ margin: 8px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid {current_theme['html_table_border']}; padding: 12px; text-align: right; }}
        th {{ background: {current_theme['html_table_header_bg']}; color: #fff; font-weight: bold; }}
        tr:nth-child(even) {{ background: {'#2b2b2b' if current_theme == ThemeManager.DARK_THEME else '#f7f7f7'}; }}
        tr:hover {{ background: {current_theme['html_row_hover']}; transition: background 0.3s; }}
        .chart-container {{ display: flex; flex-wrap: wrap; justify-content: space-between; margin-top: 20px; }}
        .chart {{ width: 48%; margin-bottom: 20px; }}
        .chart img {{ width: 100%; height: auto; }}
        .error {{ color: #d32f2f; font-weight: bold; }}
    </style>
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
    <meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self' 'unsafe-inline' data:; img-src 'self' data:;\"/>
    
</head>
<body>
    <h1>گزارش اسکن شبکه</h1>
    <p>زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>هدف/رنج: {scanned_range}</p>
    <p>تعداد آی‌پی‌های فعال: {len(active_ips)}</p>
    {table_section}
    {charts_section}
</body>
</html>
"""

        try:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            if include_charts:
                self.generate_charts(output_dir)

            info_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] گزارش HTML در {html_file} تولید شد\n"
            self.log_message.emit(info_msg)
            if hasattr(self, 'log_file') and self.log_file:
                self.log_file.write(info_msg)
                self.log_file.flush()
            return html_file
        except Exception as e:
            error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] خطا در تولید گزارش HTML: {str(e)}\n"
            self.log_message.emit(error_msg)
            if hasattr(self, 'log_file') and self.log_file:
                self.log_file.write(error_msg)
                self.log_file.flush()
            return None

    def generate_charts(self, output_dir):
        """تولید نمودارها برای گزارش HTML"""
        try:
            port_scan_output = os.path.join(output_dir, "port_scan_results.txt")
            if not os.path.exists(port_scan_output):
                return

            with open(port_scan_output, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                return

            port_states = defaultdict(int)
            protocol_counts = defaultdict(int)
            open_ports_per_ip = defaultdict(int)
            counts_per_port = defaultdict(int)  # تعداد بر اساس شماره پورت

            current_ip = None
            for line in content.split('\n'):
                ip_match = re.match(r'^Nmap scan report for (.+)$', line.strip())
                if ip_match:
                    rest = ip_match.group(1)
                    ip_in_line = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', rest)
                    if ip_in_line:
                        current_ip = ip_in_line.group(1)
                    else:
                        current_ip = None
                    continue

                port_match = re.match(r'^(\d+)/(tcp|udp)\s+(\w+)', line)
                if port_match and current_ip:
                    port_no = port_match.group(1)
                    protocol = port_match.group(2).upper()
                    state = port_match.group(3)

                    port_states[state] += 1
                    protocol_counts[protocol] += 1
                    if state == 'open':
                        open_ports_per_ip[current_ip] += 1
                        counts_per_port[port_no] += 1

            # فونت نمودار
            font_prop = vazir_font if (vazir_font and hasattr(vazir_font, 'get_file') and vazir_font.get_file()) else FontProperties()

            if port_states:
                plt.figure(figsize=(6, 4))
                plt.pie(port_states.values(), labels=[shape_text(k) for k in port_states.keys()], autopct=fa_autopct,
                        textprops={'fontproperties': font_prop})
                plt.title(shape_text("توزیع وضعیت پورت‌ها"), fontproperties=font_prop)
                plt.savefig(os.path.join(output_dir, "port_states_pie.png"), dpi=300, bbox_inches='tight')
                plt.close()

            if protocol_counts:
                plt.figure(figsize=(6, 4))
                plt.bar(list(protocol_counts.keys()), list(protocol_counts.values()))
                plt.title(shape_text("استفاده از پروتکل‌ها"), fontproperties=font_prop)
                plt.xlabel(shape_text("پروتکل"), fontproperties=font_prop)
                plt.ylabel(shape_text("تعداد"), fontproperties=font_prop)
                plt.savefig(os.path.join(output_dir, "protocol_usage_bar.png"), dpi=300, bbox_inches='tight')
                plt.close()

            if open_ports_per_ip:
                plt.figure(figsize=(10, 6))
                ips = list(open_ports_per_ip.keys())
                counts = list(open_ports_per_ip.values())
                if len(ips) > 20:
                    ips = ips[:20]
                    counts = counts[:20]
                plt.bar(range(len(ips)), counts)
                plt.xticks(range(len(ips)), ips, rotation=45, ha='right')
                plt.title(shape_text("تعداد پورت‌های باز بر اساس آی‌پی"), fontproperties=font_prop)
                plt.xlabel(shape_text("آی‌پی"), fontproperties=font_prop)
                plt.ylabel(shape_text("تعداد پورت‌های باز"), fontproperties=font_prop)
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, "open_ports_per_ip.png"), dpi=300, bbox_inches='tight')
                plt.close()

            # نمودار جدید: تعداد میزبان‌های دارای پورت باز بر اساس شماره پورت
            if counts_per_port:
                sorted_items = sorted(counts_per_port.items(), key=lambda kv: kv[1], reverse=True)[:25]
                ports, counts = zip(*sorted_items)

                # ستونی
                plt.figure(figsize=(10, 6))
                plt.bar(range(len(ports)), counts)
                plt.xticks(range(len(ports)), ports, rotation=45, ha='right')
                plt.title(shape_text("تعداد میزبان‌های دارای پورت باز بر اساس شماره پورت"), fontproperties=font_prop)
                plt.xlabel(shape_text("پورت"), fontproperties=font_prop)
                plt.ylabel(shape_text("تعداد میزبان"), fontproperties=font_prop)
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, "counts_per_port_bar.png"), dpi=300, bbox_inches='tight')
                plt.close()

                # دایره‌ای
                plt.figure(figsize=(6, 6))
                plt.pie(counts, labels=ports, autopct=fa_autopct, textprops={'fontproperties': font_prop})
                plt.title(shape_text("سهم پورت‌ها از بین میزبان‌های دارای پورت باز"), fontproperties=font_prop)
                plt.savefig(os.path.join(output_dir, "counts_per_port_pie.png"), dpi=300, bbox_inches='tight')
                plt.close()
        except Exception as e:
            error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] خطا در تولید نمودارها: {str(e)}\n"
            self.log_message.emit(error_msg)
            if hasattr(self, 'log_file') and self.log_file:
                self.log_file.write(error_msg)
                self.log_file.flush()

    def stop(self):
        """متوقف کردن اسکن"""
        self._is_running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class SimpleScanTab(QWidget):
    """تب اسکن ساده"""
    scan_complete = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_worker = None
        self.ip_file_loaded = False
        self.profiles = ProfileManager.load_profiles()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        ip_group = QGroupBox("🟢 ورودی (رنج آی‌پی یا CIDR):")
        ip_layout = QVBoxLayout()

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("مثال: 192.168.1.1  یا 192.168.1.1-100 یا 192.168.1.0/24 (با فاصله یا کاما جدا کنید)")
        ip_layout.addWidget(self.ip_input)

        file_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("مسیر فایل لیست آی‌پی")
        self.file_path.setEnabled(False)
        self.file_btn = QPushButton("مرور")
        self.file_btn.setToolTip("انتخاب فایل شامل لیست آی‌پی‌ها (هر سطر یک آی‌پی)")
        self.file_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(self.file_btn)
        ip_layout.addLayout(file_layout)

        ip_group.setLayout(ip_layout)
        layout.addWidget(ip_group)

        port_group = QGroupBox("🎯 پورت‌ها (جدا با کاما، مثل 80,443 یا 1-65535):")
        port_layout = QVBoxLayout()

        self.port_input = QLineEdit()
        self.port_input.setText("445,8291")
        self.port_input.setPlaceholderText("مثال: 22,80,443 یا 1-1024")
        port_layout.addWidget(self.port_input)

        self.udp_checkbox = QCheckBox("اسکن UDP")
        port_layout.addWidget(self.udp_checkbox)

        port_group.setLayout(port_layout)
        layout.addWidget(port_group)

        profile_group = QGroupBox("📁 پروفایل‌ها")
        profile_layout = QVBoxLayout()

        profile_select_layout = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("انتخاب پروفایل...")
        self.update_profile_combo()
        profile_select_layout.addWidget(self.profile_combo)

        self.load_profile_btn = QPushButton("بارگیری")
        self.load_profile_btn.clicked.connect(self.load_profile)
        profile_select_layout.addWidget(self.load_profile_btn)

        self.delete_profile_btn = QPushButton("حذف")
        self.delete_profile_btn.clicked.connect(self.delete_profile)
        profile_select_layout.addWidget(self.delete_profile_btn)

        profile_layout.addLayout(profile_select_layout)

        profile_save_layout = QHBoxLayout()
        self.profile_name_input = QLineEdit()
        self.profile_name_input.setPlaceholderText("نام پروفایل جدید")
        profile_save_layout.addWidget(self.profile_name_input)

        self.save_profile_btn = QPushButton("ذخیره")
        self.save_profile_btn.clicked.connect(self.save_profile)
        profile_save_layout.addWidget(self.save_profile_btn)

        profile_layout.addLayout(profile_save_layout)

        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)

        scan_buttons_layout = QHBoxLayout()

        self.scan_btn = QPushButton("▶️ اسکن شبکه")
        self.scan_btn.setToolTip("شروع اسکن با تنظیمات فعلی")
        self.scan_btn.clicked.connect(self.start_scan)
        self.scan_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        scan_buttons_layout.addWidget(self.scan_btn)

        self.stop_btn = QPushButton("⏹️ توقف اسکن")
        self.stop_btn.setToolTip("توقف فرآیند اسکن در حال اجرا")
        self.stop_btn.clicked.connect(self.stop_scan)
        self.stop_btn.setEnabled(False)
        scan_buttons_layout.addWidget(self.stop_btn)

        layout.addLayout(scan_buttons_layout)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.output = QTextEdit()
        self.output.setToolTip("گزارش رویدادها و خروجی اسکن")
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        layout.addStretch()
        self.setLayout(layout)

    def update_profile_combo(self):
        self.profile_combo.clear()
        self.profile_combo.addItem("انتخاب پروفایل...")
        for profile_name in self.profiles.keys():
            self.profile_combo.addItem(profile_name)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "باز کردن لیست آی‌پی", "", "فایل‌های متنی (*.txt)")
        if file_path:
            self.file_path.setText(file_path)
            self.file_path.setEnabled(True)
            self.ip_input.setEnabled(False)
            self.ip_file_loaded = True
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    ips = f.read().strip()
                    self.ip_input.setText(ips)
            except Exception:
                pass

    def start_scan(self):
        if self.ip_file_loaded:
            file_path = self.file_path.text()
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "خطای ورودی", "فایل لیست آی‌پی وجود ندارد")
                return
            target = f"-iL {file_path}"
        else:
            ip_input = self.ip_input.text().strip()
            if not ip_input:
                QMessageBox.warning(self, "خطای ورودی", "لطفاً آی‌پی هدف را وارد کنید")
                return
            target = ip_input

        ports = self.port_input.text().strip()
        if not ports:
            QMessageBox.warning(self, "خطای ورودی", "لطفاً پورت(ها) را وارد کنید")
            return

        main_window = None
        widget = self
        while widget is not None:
            if isinstance(widget, QMainWindow):
                main_window = widget
                break
            widget = widget.parent()
        current_theme = main_window.current_theme if main_window else 'dark'

        settings = {
            'target': target,
            'ports': [p.strip() for p in ports.split(',') if p.strip()],
            'udp_scan': self.udp_checkbox.isChecked(),
            'simple_scan': True,
            'theme': current_theme,
        }

        self.scan_worker = ScanWorker(settings)
        self.scan_worker.progress_updated.connect(self.update_progress)
        self.scan_worker.scan_complete.connect(self.handle_scan_complete)
        self.scan_worker.error_occurred.connect(self.show_error)
        self.scan_worker.log_message.connect(self.update_log)
        self.scan_worker.start()

        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.output.clear()
        self.output.append("⏳ در حال آماده‌سازی اسکن...")

    def stop_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.stop()
            self.scan_worker.wait()
            self.scan_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.output.append("⏹️ اسکن متوقف شد.")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_log(self, message):
        self.output.append(message)

    def handle_scan_complete(self, results):
        self.output.append("\n✅ اسکن کامل شد!")
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.scan_complete.emit(results)

    def show_error(self, message):
        self.output.append(f"\n❌ خطا: {message}")
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def save_profile(self):
        profile_name = self.profile_name_input.text().strip()
        if not profile_name:
            QMessageBox.warning(self, "خطا", "لطفاً نام پروفایل را وارد کنید")
            return

        settings = {
            'target': self.ip_input.text(),
            'ports': [p.strip() for p in self.port_input.text().split(',') if p.strip()],
            'udp_scan': self.udp_checkbox.isChecked(),
            'simple_scan': True,
        }

        ProfileManager.add_profile(profile_name, settings)
        self.profiles = ProfileManager.load_profiles()
        self.update_profile_combo()
        self.profile_name_input.clear()
        QMessageBox.information(self, "موفقیت", f"پروفایل '{profile_name}' با موفقیت ذخیره شد")

    def load_profile(self):
        profile_name = self.profile_combo.currentText()
        if profile_name == "انتخاب پروفایل...":
            return

        if profile_name in self.profiles:
            profile = self.profiles[profile_name]
            self.ip_input.setText(profile.get('target', ''))
            self.port_input.setText(','.join(profile.get('ports', [])))
            self.udp_checkbox.setChecked(profile.get('udp_scan', False))
            # بازنشانی حالت فایل ورودی
            self.ip_file_loaded = False
            self.file_path.clear()
            self.file_path.setEnabled(False)
            self.ip_input.setEnabled(True)
            QMessageBox.information(self, "موفقیت", f"پروفایل '{profile_name}' بارگیری شد")

    def delete_profile(self):
        profile_name = self.profile_combo.currentText()
        if profile_name == "انتخاب پروفایل...":
            return

        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف پروفایل '{profile_name}' مطمئن هستید؟",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            ProfileManager.delete_profile(profile_name)
            self.profiles = ProfileManager.load_profiles()
            self.update_profile_combo()
            QMessageBox.information(self, "موفقیت", f"پروفایل '{profile_name}' حذف شد")


class AdvancedScanTab(SimpleScanTab):
    """تب اسکن پیشرفته"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_advanced_ui()

    def init_advanced_ui(self):
        advanced_group = QGroupBox("تنظیمات پیشرفته Nmap")
        advanced_layout = QFormLayout()

        self.min_rate_spin = QSpinBox()
        self.min_rate_spin.setRange(0, 10000)
        self.min_rate_spin.setValue(100)
        self.min_rate_spin.setToolTip("حداقل نرخ ارسال بسته (پکت بر ثانیه)")
        advanced_layout.addRow("📉 MIN_RATE:", self.min_rate_spin)

        self.max_rate_spin = QSpinBox()
        self.max_rate_spin.setRange(0, 10000)
        self.max_rate_spin.setValue(200)
        self.max_rate_spin.setToolTip("حداکثر نرخ ارسال بسته (پکت بر ثانیه)")
        advanced_layout.addRow("📈 MAX_RATE:", self.max_rate_spin)

        self.scan_delay_input = QLineEdit()
        self.scan_delay_input.setText("100ms")
        self.scan_delay_input.setToolTip("تاخیر بین پکت‌ها (مانند 100ms یا 1s)")
        advanced_layout.addRow("⏱ SCAN_DELAY:", self.scan_delay_input)

        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(0, 10)
        self.max_retries_spin.setValue(5)
        self.max_retries_spin.setToolTip("حداکثر تلاش مجدد")
        advanced_layout.addRow("🔄 MAX_RETRIES:", self.max_retries_spin)

        advanced_group.setLayout(advanced_layout)

        main_layout = self.layout()
        main_layout.insertWidget(3, advanced_group)

    def start_scan(self):
        if self.ip_file_loaded:
            file_path = self.file_path.text()
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "خطای ورودی", "فایل لیست آی‌پی وجود ندارد")
                return
            target = f"-iL {file_path}"
        else:
            ip_input = self.ip_input.text().strip()
            if not ip_input:
                QMessageBox.warning(self, "خطای ورودی", "لطفاً آی‌پی هدف را وارد کنید")
                return
            target = ip_input

        ports = self.port_input.text().strip()
        if not ports:
            QMessageBox.warning(self, "خطای ورودی", "لطفاً پورت(ها) را وارد کنید")
            return

        main_window = None
        widget = self
        while widget is not None:
            if isinstance(widget, QMainWindow):
                main_window = widget
                break
            widget = widget.parent()
        current_theme = main_window.current_theme if main_window else 'dark'

        settings = {
            'target': target,
            'ports': [p.strip() for p in ports.split(',') if p.strip()],
            'udp_scan': self.udp_checkbox.isChecked(),
            'min_rate': self.min_rate_spin.value(),
            'max_rate': self.max_rate_spin.value(),
            'scan_delay': self.scan_delay_input.text(),
            'max_retries': self.max_retries_spin.value(),
            'simple_scan': False,
            'theme': current_theme,
        }

        self.scan_worker = ScanWorker(settings)
        self.scan_worker.progress_updated.connect(self.update_progress)
        self.scan_worker.scan_complete.connect(self.handle_scan_complete)
        self.scan_worker.error_occurred.connect(self.show_error)
        self.scan_worker.log_message.connect(self.update_log)
        self.scan_worker.start()

        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.output.clear()
        self.output.append("⏳ در حال آماده‌سازی اسکن پیشرفته...")

    def save_profile(self):
        profile_name = self.profile_name_input.text().strip()
        if not profile_name:
            QMessageBox.warning(self, "خطا", "لطفاً نام پروفایل را وارد کنید")
            return

        settings = {
            'target': self.ip_input.text(),
            'ports': [p.strip() for p in self.port_input.text().split(',') if p.strip()],
            'udp_scan': self.udp_checkbox.isChecked(),
            'min_rate': self.min_rate_spin.value(),
            'max_rate': self.max_rate_spin.value(),
            'scan_delay': self.scan_delay_input.text(),
            'max_retries': self.max_retries_spin.value(),
            'simple_scan': False,
        }

        ProfileManager.add_profile(profile_name, settings)
        self.profiles = ProfileManager.load_profiles()
        self.update_profile_combo()
        self.profile_name_input.clear()
        QMessageBox.information(self, "موفقیت", f"پروفایل '{profile_name}' با موفقیت ذخیره شد")

    def load_profile(self):
        profile_name = self.profile_combo.currentText()
        if profile_name == "انتخاب پروفایل...":
            return

        if profile_name in self.profiles:
            profile = self.profiles[profile_name]
            self.ip_input.setText(profile.get('target', ''))
            self.port_input.setText(','.join(profile.get('ports', [])))
            self.udp_checkbox.setChecked(profile.get('udp_scan', False))
            self.min_rate_spin.setValue(profile.get('min_rate', 100))
            self.max_rate_spin.setValue(profile.get('max_rate', 200))
            self.scan_delay_input.setText(profile.get('scan_delay', '100ms'))
            self.max_retries_spin.setValue(profile.get('max_retries', 5))
            # بازنشانی حالت فایل ورودی
            self.ip_file_loaded = False
            self.file_path.clear()
            self.file_path.setEnabled(False)
            self.ip_input.setEnabled(True)
            QMessageBox.information(self, "موفقیت", f"پروفایل '{profile_name}' بارگیری شد")


class ReportsTab(QWidget):
    """تب گزارش‌گیری بصری"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_results = {}
        self.results_folder = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        output_group = QGroupBox("گزینه‌های خروجی")
        output_layout = QHBoxLayout()

        self.html_btn_with = QPushButton("📄 HTML (با نمودار)")
        self.html_btn_with.clicked.connect(self.export_html_with_charts)
        output_layout.addWidget(self.html_btn_with)

        self.html_btn_without = QPushButton("📄 HTML (بدون نمودار)")
        self.html_btn_without.clicked.connect(self.export_html_no_charts)
        output_layout.addWidget(self.html_btn_without)

        self.csv_btn = QPushButton("📊 خروجی CSV")
        self.csv_btn.clicked.connect(self.export_csv)
        output_layout.addWidget(self.csv_btn)

        self.excel_btn = QPushButton("📈 خروجی Excel")
        self.excel_btn.clicked.connect(self.export_excel)
        output_layout.addWidget(self.excel_btn)

        self.chart_btn = QPushButton("📉 خروجی نمودارها")
        self.chart_btn.clicked.connect(self.export_charts)
        output_layout.addWidget(self.chart_btn)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        charts_group = QGroupBox("نمودارهای تحلیلی")
        charts_layout = QVBoxLayout()

        # گزینه نمودار بر اساس پورت
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("نمودار بر اساس پورت:"))
        self.port_chart_type_combo = QComboBox()
        self.port_chart_type_combo.addItems(["ستونی", "دایره‌ای"])
        self.port_chart_type_combo.currentIndexChanged.connect(self.update_charts)
        controls_layout.addWidget(self.port_chart_type_combo)
        controls_layout.addStretch()
        charts_layout.addLayout(controls_layout)

        self.pie_chart = FigureCanvas(plt.figure(figsize=(5, 4)))
        charts_layout.addWidget(self.pie_chart)

        self.bar_chart = FigureCanvas(plt.figure(figsize=(5, 4)))
        charts_layout.addWidget(self.bar_chart)

        self.ports_chart = FigureCanvas(plt.figure(figsize=(5, 4)))
        charts_layout.addWidget(self.ports_chart)

        # نمودار تعداد بر اساس پورت (نمایش بر اساس انتخاب)
        self.counts_per_port_chart = FigureCanvas(plt.figure(figsize=(5, 4)))
        charts_layout.addWidget(self.counts_per_port_chart)

        charts_group.setLayout(charts_layout)
        layout.addWidget(charts_group)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels(["آی‌پی", "پورت", "پروتکل", "وضعیت", "سرویس", "محصول", "نسخه"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setSortingEnabled(True)
        layout.addWidget(self.results_table)

        layout.addStretch()
        self.setLayout(layout)

    def update_results(self, results):
        self.scan_results = results
        self.results_folder = results.get('_results_folder', None)
        self.parse_results()
        self.update_charts()

    def parse_results(self):
        self.results_table.setRowCount(0)

        port_data = self.scan_results.get('port_data', [])
        if not port_data:
            return

        try:
            for data in port_data:
                row_position = self.results_table.rowCount()
                self.results_table.insertRow(row_position)

                self.results_table.setItem(row_position, 0, QTableWidgetItem(data['ip']))
                self.results_table.setItem(row_position, 1, QTableWidgetItem(data['port']))
                self.results_table.setItem(row_position, 2, QTableWidgetItem(data['protocol']))
                self.results_table.setItem(row_position, 3, QTableWidgetItem(data['state']))
                self.results_table.setItem(row_position, 4, QTableWidgetItem(data['service']))
                self.results_table.setItem(row_position, 5, QTableWidgetItem(""))
                self.results_table.setItem(row_position, 6, QTableWidgetItem(""))
        except Exception as e:
            error_msg = f"خطا در تجزیه نتایج: {str(e)}"
            QMessageBox.critical(self, "خطا", error_msg)
            print(f"Error parsing results: {e}")

    def update_charts(self):
        port_states = defaultdict(int)
        protocol_counts = defaultdict(int)
        open_ports_per_ip = defaultdict(int)
        counts_per_port = defaultdict(int)

        port_data = self.scan_results.get('port_data', [])
        if not port_data:
            return

        try:
            for data in port_data:
                protocol = data['protocol']
                state = data['state']
                ip = data['ip']
                port_no = data['port']

                port_states[state] += 1
                protocol_counts[protocol] += 1
                if state == 'open':
                    open_ports_per_ip[ip] += 1
                    counts_per_port[port_no] += 1

            font_prop = vazir_font if (vazir_font and hasattr(vazir_font, 'get_file') and vazir_font.get_file()) else FontProperties()

            # نمودار دایره‌ای وضعیت پورت‌ها
            self.pie_chart.figure.clear()
            ax = self.pie_chart.figure.add_subplot(111)
            if port_states:
                ax.pie(list(port_states.values()), labels=[shape_text(k) for k in port_states.keys()], autopct=fa_autopct,
                       textprops={'fontproperties': font_prop})
                ax.set_title(shape_text("توزیع وضعیت پورت‌ها"), fontproperties=font_prop)
            self.pie_chart.draw()

            # نمودار میله‌ای پروتکل‌ها
            self.bar_chart.figure.clear()
            ax = self.bar_chart.figure.add_subplot(111)
            if protocol_counts:
                ax.bar(list(protocol_counts.keys()), list(protocol_counts.values()))
                ax.set_title(shape_text("استفاده از پروتکل‌ها"), fontproperties=font_prop)
                ax.set_xlabel(shape_text("پروتکل"), fontproperties=font_prop)
                ax.set_ylabel(shape_text("تعداد"), fontproperties=font_prop)
            self.bar_chart.draw()

            # نمودار پورت‌های باز بر اساس آی‌پی
            self.ports_chart.figure.clear()
            ax = self.ports_chart.figure.add_subplot(111)
            if open_ports_per_ip:
                ips = list(open_ports_per_ip.keys())
                counts = list(open_ports_per_ip.values())
                if len(ips) > 20:
                    ips = ips[:20]
                    counts = counts[:20]
                ax.bar(range(len(ips)), counts)
                ax.set_xticks(range(len(ips)))
                ax.set_xticklabels(ips, rotation=45, ha='right')
                ax.set_title(shape_text("تعداد پورت‌های باز بر اساس آی‌پی"), fontproperties=font_prop)
                ax.set_xlabel(shape_text("آی‌پی"), fontproperties=font_prop)
                ax.set_ylabel(shape_text("تعداد پورت‌های باز"), fontproperties=font_prop)
                plt.tight_layout()
            self.ports_chart.draw()

            # نمودار تعداد بر اساس پورت (قابل انتخاب بین ستونی/دایره‌ای)
            self.counts_per_port_chart.figure.clear()
            ax = self.counts_per_port_chart.figure.add_subplot(111)
            if counts_per_port:
                sorted_items = sorted(counts_per_port.items(), key=lambda kv: kv[1], reverse=True)
                top_items = sorted_items[:25]
                ports = [p for p, _ in top_items]
                counts = [c for _, c in top_items]
                if self.port_chart_type_combo.currentText() == "دایره‌ای":
                    ax.pie(counts, labels=ports, autopct=fa_autopct, textprops={'fontproperties': font_prop})
                    ax.set_title(shape_text("سهم پورت‌ها از بین میزبان‌های دارای پورت باز"), fontproperties=font_prop)
                else:
                    ax.bar(range(len(ports)), counts)
                    ax.set_xticks(range(len(ports)))
                    ax.set_xticklabels(ports, rotation=45, ha='right')
                    ax.set_title(shape_text("تعداد میزبان‌های دارای پورت باز بر اساس شماره پورت"), fontproperties=font_prop)
                    ax.set_xlabel(shape_text("پورت"), fontproperties=font_prop)
                    ax.set_ylabel(shape_text("تعداد میزبان"), fontproperties=font_prop)
                    plt.tight_layout()
            self.counts_per_port_chart.draw()
        except Exception as e:
            error_msg = f"خطا در به‌روزرسانی نمودارها: {str(e)}"
            QMessageBox.critical(self, "خطا", error_msg)
            print(f"Error updating charts: {e}")

    def export_html_with_charts(self):
        if not self.scan_results:
            QMessageBox.warning(self, "هشدار", "هیچ نتیجه اسکنی برای خروجی وجود ندارد")
            return
        html_file = self.scan_results.get('html_report_with_charts', '')
        if html_file and os.path.exists(html_file):
            QDesktopServices.openUrl(QUrl.fromLocalFile(html_file))
        else:
            QMessageBox.warning(self, "هشدار", "فایل گزارش HTML (با نمودار) یافت نشد")

    def export_html_no_charts(self):
        if not self.scan_results:
            QMessageBox.warning(self, "هشدار", "هیچ نتیجه اسکنی برای خروجی وجود ندارد")
            return
        html_file = self.scan_results.get('html_report_no_charts', '')
        if html_file and os.path.exists(html_file):
            QDesktopServices.openUrl(QUrl.fromLocalFile(html_file))
        else:
            QMessageBox.warning(self, "هشدار", "فایل گزارش HTML (بدون نمودار) یافت نشد")

    def export_csv(self):
        if not self.scan_results:
            QMessageBox.warning(self, "هشدار", "هیچ نتیجه اسکنی برای خروجی وجود ندارد")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره گزارش CSV", "", "فایل‌های CSV (*.csv)")
        if file_path:
            try:
                data = []
                port_data = self.scan_results.get('port_data', [])
                if port_data:
                    for item in port_data:
                        data.append({
                            "IP": item['ip'],
                            "Port": item['port'],
                            "Protocol": item['protocol'],
                            "State": item['state'],
                            "Service": item['service'],
                            "Product": "",
                            "Version": "",
                            "Extra Info": "",
                        })
                df = pd.DataFrame(data)
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "موفقیت", "گزارش CSV با موفقیت صادر شد")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در صادر کردن CSV: {str(e)}")

    def export_excel(self):
        if not self.scan_results:
            QMessageBox.warning(self, "هشدار", "هیچ نتیجه اسکنی برای خروجی وجود ندارد")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره گزارش Excel", "", "فایل‌های Excel (*.xlsx)")
        if file_path:
            try:
                data = []
                port_data = self.scan_results.get('port_data', [])
                if port_data:
                    for item in port_data:
                        data.append({
                            "IP": item['ip'],
                            "Port": item['port'],
                            "Protocol": item['protocol'],
                            "State": item['state'],
                            "Service": item['service'],
                            "Product": "",
                            "Version": "",
                            "Extra Info": "",
                        })
                df = pd.DataFrame(data)
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "موفقیت", "گزارش Excel با موفقیت صادر شد")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در صادر کردن Excel: {str(e)}")

    def export_charts(self):
        if not self.results_folder:
            QMessageBox.warning(self, "هشدار", "هیچ نتیجه اسکنی برای خروجی وجود ندارد")
            return

        try:
            pie_path = os.path.join(self.results_folder, "port_states_pie.png")
            bar_path = os.path.join(self.results_folder, "protocol_usage_bar.png")
            ports_path = os.path.join(self.results_folder, "open_ports_per_ip.png")
            byport_bar = os.path.join(self.results_folder, "counts_per_port_bar.png")
            byport_pie = os.path.join(self.results_folder, "counts_per_port_pie.png")

            avail = [p for p in [pie_path, bar_path, ports_path, byport_bar, byport_pie] if os.path.exists(p)]
            if avail:
                save_dir = QFileDialog.getExistingDirectory(self, "انتخاب پوشه برای ذخیره نمودارها")
                if save_dir:
                    import shutil
                    for p in avail:
                        shutil.copy2(p, os.path.join(save_dir, os.path.basename(p)))
                    QMessageBox.information(self, "موفقیت", "نمودارها با موفقیت صادر شدند")
            else:
                QMessageBox.warning(self, "هشدار", "فایل‌های نمودار یافت نشدند")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در صادر کردن نمودارها: {str(e)}")


class NetworkScannerApp(QMainWindow):
    """پنجره اصلی برنامه"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔎 اسکنر شبکه پیشرفته")
        self.setGeometry(100, 100, 1100, 760)

        self.current_theme = "dark"
        self.init_ui()

    def init_ui(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("فایل")
        exit_action = QAction("خروج", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("نمایش")
        theme_group = QActionGroup(self)

        self.dark_theme_action = QAction("تم تاریک", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.setChecked(True)
        self.dark_theme_action.triggered.connect(lambda: self.change_theme("dark"))
        theme_group.addAction(self.dark_theme_action)
        view_menu.addAction(self.dark_theme_action)

        self.light_theme_action = QAction("تم روشن", self)
        self.light_theme_action.setCheckable(True)
        self.light_theme_action.setChecked(False)
        self.light_theme_action.triggered.connect(lambda: self.change_theme("light"))
        theme_group.addAction(self.light_theme_action)
        view_menu.addAction(self.light_theme_action)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.simple_tab = SimpleScanTab(self)
        self.tabs.addTab(self.simple_tab, "اسکن ساده")

        self.advanced_tab = AdvancedScanTab(self)
        self.tabs.addTab(self.advanced_tab, "اسکن پیشرفته")

        self.reports_tab = ReportsTab(self)
        self.tabs.addTab(self.reports_tab, "گزارش‌گیری بصری")

        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)

        self.simple_tab.scan_complete.connect(self.reports_tab.update_results)
        self.advanced_tab.scan_complete.connect(self.reports_tab.update_results)

        ThemeManager.apply_theme(QApplication.instance(), self.current_theme)

    def change_theme(self, theme_name):
        self.current_theme = theme_name
        ThemeManager.apply_theme(QApplication.instance(), theme_name)

        if theme_name == "dark":
            self.dark_theme_action.setChecked(True)
        else:
            self.light_theme_action.setChecked(True)


def main():
    app = QApplication(sys.argv)

    # بارگذاری فونت (پس از ایجاد QApplication)
    global vazir_font
    vazir_font = load_vazir_font()

    ThemeManager.apply_theme(app, "dark")

    window = NetworkScannerApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

import sys
import os
import re
import json
import subprocess
from datetime import datetime
from collections import defaultdict

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# بارگذاری فونت Vazir پس از ایجاد QApplication
def load_vazir_font():
    """بارگذاری فونت Vazir و اعمال آن در صورت وجود QApplication"""
    try:
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        candidates = [
            os.path.join(base_path, "Fonts", "Vazir.ttf"),
            os.path.join(base_path, "Vazir.ttf"),
        ]

        for font_path in candidates:
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    if font_families:
                        font_family = font_families[0]
                        app = QApplication.instance()
                        if app is not None:
                            app.setFont(QFont(font_family, 10))
                        return FontProperties(fname=font_path)
        return None
    except Exception as e:
        print(f"خطا در بارگذاری فونت Vazir: {str(e)}")
        return None


# متغیر سراسری فونت (پس از راه‌اندازی QApplication مقداردهی می‌شود)
vazir_font = None

# شکل‌دهی متن فارسی برای Matplotlib (در صورت نصب کتابخانه‌ها)
try:
    import arabic_reshaper  # type: ignore
    from bidi.algorithm import get_display  # type: ignore

    def shape_text(text: str) -> str:
        if not text:
            return text
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception:
            return text
except Exception:
    def shape_text(text: str) -> str:
        return text


class ThemeManager:
    """مدیریت تم‌های تاریک و روشن"""
    DARK_THEME = {
        'background': '#1f1f23',
        'foreground': '#E6E6E6',
        'button': '#2a2a2e',
        'button_hover': '#3a3a3f',
        'input_bg': '#121214',
        'input_text': '#FFFFFF',
        'tab_bg': '#202024',
        'tab_text': '#CCCCCC',
        'progress': '#0aa0ff',
        'error': '#ff4d4f',
        'success': '#00c853',
        'button_text': '#FFFFFF',
        'toggle_bg': '#555',
        'toggle_active': '#0d6efd',
        'html_bg': '#121214',
        'html_text': '#FFFFFF',
        'html_table_border': '#3a3a3f',
        'html_table_header_bg': '#0aa0ff',
        'html_row_hover': '#2b2b30',
    }

    LIGHT_THEME = {
        'background': '#F7F7FB',
        'foreground': '#1f1f23',
        'button': '#E9E9F0',
        'button_hover': '#dedee6',
        'input_bg': '#FFFFFF',
        'input_text': '#000000',
        'tab_bg': '#FFFFFF',
        'tab_text': '#000000',
        'progress': '#0aa0ff',
        'error': '#ff4d4f',
        'success': '#00a152',
        'button_text': '#000000',
        'toggle_bg': '#CCC',
        'toggle_active': '#0d6efd',
        'html_bg': '#FFFFFF',
        'html_text': '#000000',
        'html_table_border': '#e3e3ea',
        'html_table_header_bg': '#0aa0ff',
        'html_row_hover': '#f3f3f8',
    }

    @staticmethod
    def apply_theme(app, theme_name):
        theme = ThemeManager.DARK_THEME if theme_name == "dark" else ThemeManager.LIGHT_THEME
        app.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['background']};
                color: {theme['foreground']};
            }}
            QPushButton {{
                background-color: {theme['button']};
                color: {theme['button_text']};
                border: 1px solid rgba(0,0,0,0.1);
                padding: 8px 12px;
                border-radius: 6px;
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {theme['input_bg']};
                color: {theme['input_text']};
                border: 1px solid {theme['button']};
                padding: 8px 10px;
                border-radius: 6px;
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QTabWidget::pane {{
                border: 1px solid {theme['button']};
                background-color: {theme['tab_bg']};
                border-radius: 6px;
            }}
            QTabBar::tab {{
                background-color: {theme['tab_bg']};
                color: {theme['tab_text']};
                padding: 10px 16px;
                border: 1px solid {theme['button']};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QTabBar::tab:selected {{
                background-color: {theme['button']};
            }}
            QProgressBar {{
                border: 1px solid {theme['button']};
                border-radius: 6px;
                text-align: center;
                height: 16px;
            }}
            QProgressBar::chunk {{
                background-color: {theme['progress']};
                border-radius: 6px;
            }}
            QLabel {{
                color: {theme['foreground']};
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QCheckBox {{
                color: {theme['foreground']};
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QGroupBox {{
                color: {theme['foreground']};
                border: 1px solid {theme['button']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-family: Vazir, Segoe UI, Tahoma;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px 0 6px;
                font-weight: bold;
            }}
            QTableWidget {{
                gridline-color: {theme['button']};
                background: {theme['input_bg']};
            }}
            QHeaderView::section {{
                background-color: {theme['button']};
                color: {theme['button_text']};
                border: none;
                padding: 6px;
            }}
        """)


class ProfileManager:
    """مدیریت پروفایل‌های اسکن"""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROFILES_FILE = os.path.join(BASE_DIR, "scan_profiles.json")

    @staticmethod
    def load_profiles():
        try:
            with open(ProfileManager.PROFILES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def save_profiles(profiles):
        with open(ProfileManager.PROFILES_FILE, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=4, ensure_ascii=False)

    @staticmethod
    def add_profile(name, settings):
        profiles = ProfileManager.load_profiles()
        profiles[name] = settings
        ProfileManager.save_profiles(profiles)

    @staticmethod
    def delete_profile(name):
        profiles = ProfileManager.load_profiles()
        if name in profiles:
            del profiles[name]
            ProfileManager.save_profiles(profiles)


class ScanWorker(QThread):
    """پردازش اسکن در پس‌زمینه"""
    progress_updated = pyqtSignal(int)
    scan_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._is_running = True
        self.results_folder = None
        self.active_ips = set()
        self.process = None
        self.port_data = []

    def run(self):
        try:
            ip_input = self.settings.get('target', '')
            sanitized_ip = re.sub(r'[^\w\-_\. ]', '_', ip_input)
            folder_name = f"scan_results({sanitized_ip})"
            os.makedirs(folder_name, exist_ok=True)
            self.results_folder = folder_name

            log_file_path = os.path.join(folder_name, "scan_log.txt")
            self.log_file = open(log_file_path, 'w', encoding='utf-8')

            start_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] شروع اسکن شبکه برای هدف: {ip_input}\n"
            self.log_message.emit(start_msg)
            self.log_file.write(start_msg)
            self.log_file.flush()

            # مرحله 1: شناسایی آی‌پی‌های فعال
            self.log_message.emit("🔍 شروع شناسایی آی‌پی‌های فعال...\n")
            self.progress_updated.emit(0)

            active_ips_file = os.path.join(folder_name, "active_ips.txt")
            temp_output = os.path.join(folder_name, "scan_temp.txt")

            target = self.settings.get('target', '')

            if target.startswith('-iL'):
                parts = target.split()
                file_path = parts[1] if len(parts) > 1 else ''
                if not os.path.exists(file_path):
                    error_msg = f"❌ فایل لیست آی‌پی وجود ندارد: {file_path}\n"
                    self.log_message.emit(error_msg)
                    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] فایل لیست آی‌پی وجود ندارد: {file_path}\n"
                    self.log_file.write(log_msg)
                    self.log_file.flush()
                    self.log_file.close()
                    self.scan_complete.emit({})
                    return

                with open(file_path, 'r', encoding='utf-8') as f:
                    ips = f.read().strip().split('\n')
                    self.active_ips = set(ip.strip() for ip in ips if ip.strip())

                with open(active_ips_file, 'w', encoding='utf-8') as f:
                    for ip in sorted(self.active_ips):
                        f.write(f"{ip}\n")

                active_count = len(self.active_ips)
                if active_count > 0:
                    msg = f"✅ یافتن {active_count} آی‌پی فعال از فایل.\n"
                    self.log_message.emit(msg)
                    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] یافت {active_count} آی‌پی فعال از فایل\n"
                    self.log_file.write(log_msg)
                    self.log_file.flush()
                else:
                    msg = "❌ هیچ آی‌پی فعالی در فایل یافت نشد.\n"
                    self.log_message.emit(msg)
                    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] هیچ آی‌پی فعالی در فایل یافت نشد\n"
                    self.log_file.write(log_msg)
                    self.log_file.flush()
                    self.log_file.close()
                    self.scan_complete.emit({})
                    return
            else:
                # پشتیبانی از ورودی‌های چندگانه (فاصله یا کاما)
                targets = [t for t in re.split(r'[\s,]+', target) if t]
                nmap_cmd = ['nmap', '-sn', '-oN', temp_output] + targets

                cmd_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DEBUG] اجرای Nmap برای شناسایی آی‌پی‌های فعال: {' '.join(nmap_cmd)}\n"
                self.log_message.emit(cmd_msg)
                self.log_file.write(cmd_msg)
                self.log_file.flush()

                try:
                    self.process = subprocess.Popen(nmap_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, stderr = self.process.communicate()

                    if self.process.returncode == 0:
                        if os.path.exists(temp_output):
                            with open(temp_output, 'r', encoding='utf-8') as f:
                                content = f.read()
                                ips_found = []
                                for line in content.split('\n'):
                                    hdr = re.match(r'^Nmap scan report for (.+)$', line.strip())
                                    if hdr:
                                        rest = hdr.group(1)
                                        ip_in_line = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', rest)
                                        if ip_in_line:
                                            ips_found.append(ip_in_line.group(1))
                                self.active_ips = set(ips_found)

                            with open(active_ips_file, 'w', encoding='utf-8') as f:
                                for ip in sorted(self.active_ips):
                                    f.write(f"{ip}\n")

                            active_count = len(self.active_ips)
                            if active_count > 0:
                                msg = f"✅ یافتن {active_count} آی‌پی فعال.\n"
                                self.log_message.emit(msg)
                                log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] یافت {active_count} آی‌پی فعال\n"
                                self.log_file.write(log_msg)
                                self.log_file.flush()
                            else:
                                msg = "❌ هیچ آی‌پی فعالی یافت نشد.\n"
                                self.log_message.emit(msg)
                                log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] هیچ آی‌پی فعالی یافت نشد\n"
                                self.log_file.write(log_msg)
                                self.log_file.flush()
                                self.log_file.close()
                                self.scan_complete.emit({})
                                return
                        else:
                            error_msg = f"❌ فایل خروجی Nmap یافت نشد: {temp_output}\n"
                            self.log_message.emit(error_msg)
                            log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] فایل خروجی Nmap یافت نشد: {temp_output}\n"
                            self.log_file.write(log_msg)
                            self.log_file.flush()
                            self.log_file.close()
                            self.scan_complete.emit({})
                            return
                    else:
                        error_msg = f"❌ اسکن Nmap با کد خروجی ناموفق بود: {self.process.returncode}\n"
                        self.log_message.emit(error_msg)
                        log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] اسکن Nmap با کد خروجی ناموفق بود: {self.process.returncode}\n"
                        self.log_file.write(log_msg)
                        self.log_file.flush()
                        self.log_file.close()
                        self.scan_complete.emit({})
                        return
                except Exception as e:
                    error_msg = f"❌ خطا در اجرای Nmap: {str(e)}\n"
                    self.log_message.emit(error_msg)
                    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] خطا در اجرای Nmap: {str(e)}\n"
                    self.log_file.write(log_msg)
                    self.log_file.flush()
                    self.log_file.close()
                    self.scan_complete.emit({})
                    return

            # به‌روزرسانی پیشرفت
            self.progress_updated.emit(50)

            # مرحله 2: اسکن پورت‌ها
            self.log_message.emit(f"🔍 شروع اسکن پورت‌ها برای {len(self.active_ips)} آی‌پی فعال...\n")

            port_scan_output = os.path.join(folder_name, "port_scan_results.txt")
            ports = self.settings.get('ports', [])
            port_list = ','.join(ports)
            scan_type = "-sU" if self.settings.get('udp_scan', False) else "-sS"

            if self.settings.get('simple_scan', False):
                nmap_cmd = [
                    'nmap', scan_type,
                    '-p', port_list,
                    '-iL', active_ips_file,
                    '-oN', port_scan_output,
                ]
            else:
                min_rate = self.settings.get('min_rate', 100)
                max_rate = self.settings.get('max_rate', 200)
                scan_delay = self.settings.get('scan_delay', '100ms')
                max_retries = self.settings.get('max_retries', 5)

                nmap_cmd = [
                    'nmap', scan_type,
                    '-p', port_list,
                    '--min-rate', str(min_rate),
                    '--max-rate', str(max_rate),
                    '--scan-delay', scan_delay,
                    '--max-retries', str(max_retries),
                    '--ttl', '64',
                    '-iL', active_ips_file,
                    '-oN', port_scan_output,
                ]

            cmd_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DEBUG] اجرای Nmap برای اسکن پورت: {' '.join(nmap_cmd)}\n"
            self.log_message.emit(cmd_msg)
            self.log_file.write(cmd_msg)
            self.log_file.flush()

            try:
                self.process = subprocess.Popen(nmap_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = self.process.communicate()

                if self.process.returncode == 0:
                    if os.path.exists(port_scan_output):
                        with open(port_scan_output, 'r', encoding='utf-8') as f:
                            content = f.read()

                            current_ip = None
                            for line in content.split('\n'):
                                ip_line_match = re.match(r'^Nmap scan report for (.+)$', line.strip())
                                if ip_line_match:
                                    rest = ip_line_match.group(1)
                                    ip_in_line = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', rest)
                                    if ip_in_line:
                                        current_ip = ip_in_line.group(1)
                                    else:
                                        current_ip = None
                                    continue

                                port_line_match = re.match(r'^(\d+)/(tcp|udp)\s+(\w+)\s+(\S+)', line.strip())
                                if port_line_match and current_ip:
                                    port = port_line_match.group(1)
                                    protocol = port_line_match.group(2).upper()
                                    state = port_line_match.group(3)
                                    service = port_line_match.group(4)

                                    self.port_data.append({
                                        'ip': current_ip,
                                        'port': port,
                                        'protocol': protocol,
                                        'state': state,
                                        'service': service,
                                    })

                                    self.log_message.emit(f"[+] {line.strip()}\n")

                        msg = f"\n✅ اسکن کامل شد. مجموع آی‌پی‌های فعال: {len(self.active_ips)}\n"
                        self.log_message.emit(msg)
                        log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] اسکن پورت با موفقیت انجام شد\n"
                        self.log_file.write(log_msg)
                        self.log_file.flush()
                    else:
                        error_msg = f"❌ فایل خروجی اسکن پورت یافت نشد: {port_scan_output}\n"
                        self.log_message.emit(error_msg)
                        log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] فایل خروجی اسکن پورت یافت نشد: {port_scan_output}\n"
                        self.log_file.write(log_msg)
                        self.log_file.flush()
                else:
                    error_msg = f"❌ اسکن پورت Nmap با کد خروجی ناموفق بود: {self.process.returncode}\n"
                    self.log_message.emit(error_msg)
                    log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] اسکن پورت Nmap با کد خروجی ناموفق بود: {self.process.returncode}\n"
                    self.log_file.write(log_msg)
                    self.log_file.flush()
            except Exception as e:
                error_msg = f"❌ خطا در اجرای Nmap برای اسکن پورت: {str(e)}\n"
                self.log_message.emit(error_msg)
                log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] خطا در اجرای Nmap برای اسکن پورت: {str(e)}\n"
                self.log_file.write(log_msg)
                self.log_file.flush()

            # تولید گزارش‌ها (با نمودار و بدون نمودار)
            html_with = self.generate_html_report(
                list(self.active_ips), port_scan_output, folder_name, log_file_path, target, include_charts=True
            )
            html_without = self.generate_html_report(
                list(self.active_ips), port_scan_output, folder_name, log_file_path, target, include_charts=False
            )

            if html_with:
                msg = f"📊 گزارش HTML (با نمودار) در {html_with} تولید شد.\n"
                self.log_message.emit(msg)
                log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] گزارش HTML (با نمودار) در {html_with} تولید شد\n"
                self.log_file.write(log_msg)
                self.log_file.flush()
            if html_without:
                msg = f"📄 گزارش HTML (بدون نمودار) در {html_without} تولید شد.\n"
                self.log_message.emit(msg)
                log_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] گزارش HTML (بدون نمودار) در {html_without} تولید شد\n"
                self.log_file.write(log_msg)
                self.log_file.flush()

            self.progress_updated.emit(100)

            self.log_file.close()

            results = {
                '_results_folder': folder_name,
                'active_ips': list(self.active_ips),
                'port_scan_output': port_scan_output,
                'html_report_with_charts': html_with,
                'html_report_no_charts': html_without,
                'port_data': self.port_data,
            }

            self.scan_complete.emit(results)
        except Exception as e:
            error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] اسکن ناموفق بود: {str(e)}\n"
            self.log_message.emit(error_msg)
            if hasattr(self, 'log_file') and self.log_file:
                self.log_file.write(error_msg)
                self.log_file.close()
            self.error_occurred.emit(f"اسکن ناموفق بود: {str(e)}")

    def generate_html_report(self, active_ips, port_scan_output, output_dir, log_file, scanned_range, include_charts=True):
        """تولید گزارش HTML؛ include_charts: اگر True باشد تصاویر نمودارها درج می‌شوند"""
        html_file = os.path.join(output_dir, "report_with_charts.html" if include_charts else "report_no_charts.html")

        port_content = ""
        if os.path.exists(port_scan_output):
            with open(port_scan_output, 'r', encoding='utf-8') as f:
                port_content = f.read()

        current_theme = ThemeManager.DARK_THEME if self.settings.get('theme', 'dark') == 'dark' else ThemeManager.LIGHT_THEME

        # ایجاد ردیف‌های جدول
        html_rows = ""
        if self.port_data:
            for data in self.port_data:
                html_rows += (
                    f"<tr>"
                    f"<td>{data['ip']}</td>"
                    f"<td>{data['port']}</td>"
                    f"<td>{data['protocol']}</td>"
                    f"<td>{data['state']}</td>"
                    f"<td>{data['service']}</td>"
                    f"</tr>\n"
                )

        # بدنه گزارش
        if not self.port_data:
            table_section = "<p class=\"error\">هیچ نتیجه‌ای برای نمایش وجود ندارد.</p>"
        else:
            table_section = f"""
            <table>
                <tr>
                    <th>آی‌پی</th>
                    <th>پورت</th>
                    <th>پروتکل</th>
                    <th>وضعیت</th>
                    <th>سرویس</th>
                </tr>
                {html_rows}
            </table>
            """

        charts_section = ""
        if include_charts:
            charts_section = f"""
            <div class=\"chart-container\"> 
                <div class=\"chart\">\n                    <h3>توزیع وضعیت پورت‌ها</h3>\n                    <img src=\"port_states_pie.png\" alt=\"Port States Distribution\">\n                </div>\n                <div class=\"chart\">\n                    <h3>استفاده از پروتکل‌ها</h3>\n                    <img src=\"protocol_usage_bar.png\" alt=\"Protocol Usage\">\n                </div>\n                <div class=\"chart\">\n                    <h3>تعداد پورت‌های باز بر اساس آی‌پی</h3>\n                    <img src=\"open_ports_per_ip.png\" alt=\"Open Ports per IP\">\n                </div>\n                <div class=\"chart\">\n                    <h3>تعداد میزبان‌ها بر اساس شماره پورت (ستونی)</h3>\n                    <img src=\"counts_per_port_bar.png\" alt=\"Counts per Port (Bar)\">\n                </div>\n                <div class=\"chart\">\n                    <h3>سهم پورت‌ها از بین میزبان‌های دارای پورت باز (دایره‌ای)</h3>\n                    <img src=\"counts_per_port_pie.png\" alt=\"Counts per Port (Pie)\">\n                </div>\n            </div>\n            """

        html_content = f"""<!DOCTYPE html>
<html lang=\"fa\" dir=\"rtl\">
<head>
    <meta charset=\"UTF-8\">
    <title>گزارش اسکن</title>
    <style>
        body {{ font-family: Vazir, Segoe UI, Tahoma; direction: rtl; margin: 20px; background: {current_theme['html_bg']}; color: {current_theme['html_text']}; }}
        h1 {{ font-size: 24px; margin-bottom: 16px; }}
        p {{ margin: 8px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid {current_theme['html_table_border']}; padding: 12px; text-align: right; }}
        th {{ background: {current_theme['html_table_header_bg']}; color: #fff; font-weight: bold; }}
        tr:nth-child(even) {{ background: {'#2b2b2b' if current_theme == ThemeManager.DARK_THEME else '#f7f7f7'}; }}
        tr:hover {{ background: {current_theme['html_row_hover']}; transition: background 0.3s; }}
        .chart-container {{ display: flex; flex-wrap: wrap; justify-content: space-between; margin-top: 20px; }}
        .chart {{ width: 48%; margin-bottom: 20px; }}
        .chart img {{ width: 100%; height: auto; }}
        .error {{ color: #d32f2f; font-weight: bold; }}
    </style>
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
    <meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self' 'unsafe-inline' data:; img-src 'self' data:;\"/>
    
</head>
<body>
    <h1>گزارش اسکن شبکه</h1>
    <p>زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>هدف/رنج: {scanned_range}</p>
    <p>تعداد آی‌پی‌های فعال: {len(active_ips)}</p>
    {table_section}
    {charts_section}
</body>
</html>
"""

        try:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            if include_charts:
                self.generate_charts(output_dir)

            info_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] گزارش HTML در {html_file} تولید شد\n"
            self.log_message.emit(info_msg)
            if hasattr(self, 'log_file') and self.log_file:
                self.log_file.write(info_msg)
                self.log_file.flush()
            return html_file
        except Exception as e:
            error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] خطا در تولید گزارش HTML: {str(e)}\n"
            self.log_message.emit(error_msg)
            if hasattr(self, 'log_file') and self.log_file:
                self.log_file.write(error_msg)
                self.log_file.flush()
            return None

    def generate_charts(self, output_dir):
        """تولید نمودارها برای گزارش HTML"""
        try:
            port_scan_output = os.path.join(output_dir, "port_scan_results.txt")
            if not os.path.exists(port_scan_output):
                return

            with open(port_scan_output, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                return

            port_states = defaultdict(int)
            protocol_counts = defaultdict(int)
            open_ports_per_ip = defaultdict(int)
            counts_per_port = defaultdict(int)  # تعداد بر اساس شماره پورت

            current_ip = None
            for line in content.split('\n'):
                ip_match = re.match(r'^Nmap scan report for (.+)$', line.strip())
                if ip_match:
                    rest = ip_match.group(1)
                    ip_in_line = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', rest)
                    if ip_in_line:
                        current_ip = ip_in_line.group(1)
                    else:
                        current_ip = None
                    continue

                port_match = re.match(r'^(\d+)/(tcp|udp)\s+(\w+)', line)
                if port_match and current_ip:
                    port_no = port_match.group(1)
                    protocol = port_match.group(2).upper()
                    state = port_match.group(3)

                    port_states[state] += 1
                    protocol_counts[protocol] += 1
                    if state == 'open':
                        open_ports_per_ip[current_ip] += 1
                        counts_per_port[port_no] += 1

            # فونت نمودار
            font_prop = vazir_font if (vazir_font and hasattr(vazir_font, 'get_file') and vazir_font.get_file()) else FontProperties()

            if port_states:
                plt.figure(figsize=(6, 4))
                plt.pie(port_states.values(), labels=[shape_text(k) for k in port_states.keys()], autopct='%1.1f%%',
                        textprops={'fontproperties': font_prop})
                plt.title(shape_text("توزیع وضعیت پورت‌ها"), fontproperties=font_prop)
                plt.savefig(os.path.join(output_dir, "port_states_pie.png"), dpi=300, bbox_inches='tight')
                plt.close()

            if protocol_counts:
                plt.figure(figsize=(6, 4))
                plt.bar(list(protocol_counts.keys()), list(protocol_counts.values()))
                plt.title(shape_text("استفاده از پروتکل‌ها"), fontproperties=font_prop)
                plt.xlabel(shape_text("پروتکل"), fontproperties=font_prop)
                plt.ylabel(shape_text("تعداد"), fontproperties=font_prop)
                plt.savefig(os.path.join(output_dir, "protocol_usage_bar.png"), dpi=300, bbox_inches='tight')
                plt.close()

            if open_ports_per_ip:
                plt.figure(figsize=(10, 6))
                ips = list(open_ports_per_ip.keys())
                counts = list(open_ports_per_ip.values())
                if len(ips) > 20:
                    ips = ips[:20]
                    counts = counts[:20]
                plt.bar(range(len(ips)), counts)
                plt.xticks(range(len(ips)), ips, rotation=45, ha='right')
                plt.title(shape_text("تعداد پورت‌های باز بر اساس آی‌پی"), fontproperties=font_prop)
                plt.xlabel(shape_text("آی‌پی"), fontproperties=font_prop)
                plt.ylabel(shape_text("تعداد پورت‌های باز"), fontproperties=font_prop)
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, "open_ports_per_ip.png"), dpi=300, bbox_inches='tight')
                plt.close()

            # نمودار جدید: تعداد میزبان‌های دارای پورت باز بر اساس شماره پورت
            if counts_per_port:
                sorted_items = sorted(counts_per_port.items(), key=lambda kv: kv[1], reverse=True)[:25]
                ports, counts = zip(*sorted_items)

                # ستونی
                plt.figure(figsize=(10, 6))
                plt.bar(range(len(ports)), counts)
                plt.xticks(range(len(ports)), ports, rotation=45, ha='right')
                plt.title(shape_text("تعداد میزبان‌های دارای پورت باز بر اساس شماره پورت"), fontproperties=font_prop)
                plt.xlabel(shape_text("پورت"), fontproperties=font_prop)
                plt.ylabel(shape_text("تعداد میزبان"), fontproperties=font_prop)
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, "counts_per_port_bar.png"), dpi=300, bbox_inches='tight')
                plt.close()

                # دایره‌ای
                plt.figure(figsize=(6, 6))
                plt.pie(counts, labels=ports, autopct='%1.1f%%', textprops={'fontproperties': font_prop})
                plt.title(shape_text("سهم پورت‌ها از بین میزبان‌های دارای پورت باز"), fontproperties=font_prop)
                plt.savefig(os.path.join(output_dir, "counts_per_port_pie.png"), dpi=300, bbox_inches='tight')
                plt.close()
        except Exception as e:
            error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] خطا در تولید نمودارها: {str(e)}\n"
            self.log_message.emit(error_msg)
            if hasattr(self, 'log_file') and self.log_file:
                self.log_file.write(error_msg)
                self.log_file.flush()

    def stop(self):
        """متوقف کردن اسکن"""
        self._is_running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class SimpleScanTab(QWidget):
    """تب اسکن ساده"""
    scan_complete = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_worker = None
        self.ip_file_loaded = False
        self.profiles = ProfileManager.load_profiles()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        ip_group = QGroupBox("🟢 ورودی (رنج آی‌پی یا CIDR):")
        ip_layout = QVBoxLayout()

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("مثال: 192.168.1.1  یا 192.168.1.1-100 یا 192.168.1.0/24 (با فاصله یا کاما جدا کنید)")
        ip_layout.addWidget(self.ip_input)

        file_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("مسیر فایل لیست آی‌پی")
        self.file_path.setEnabled(False)
        self.file_btn = QPushButton("مرور")
        self.file_btn.setToolTip("انتخاب فایل شامل لیست آی‌پی‌ها (هر سطر یک آی‌پی)")
        self.file_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(self.file_btn)
        ip_layout.addLayout(file_layout)

        ip_group.setLayout(ip_layout)
        layout.addWidget(ip_group)

        port_group = QGroupBox("🎯 پورت‌ها (جدا با کاما، مثل 80,443 یا 1-65535):")
        port_layout = QVBoxLayout()

        self.port_input = QLineEdit()
        self.port_input.setText("445,8291")
        self.port_input.setPlaceholderText("مثال: 22,80,443 یا 1-1024")
        port_layout.addWidget(self.port_input)

        self.udp_checkbox = QCheckBox("اسکن UDP")
        port_layout.addWidget(self.udp_checkbox)

        port_group.setLayout(port_layout)
        layout.addWidget(port_group)

        profile_group = QGroupBox("📁 پروفایل‌ها")
        profile_layout = QVBoxLayout()

        profile_select_layout = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("انتخاب پروفایل...")
        self.update_profile_combo()
        profile_select_layout.addWidget(self.profile_combo)

        self.load_profile_btn = QPushButton("بارگیری")
        self.load_profile_btn.clicked.connect(self.load_profile)
        profile_select_layout.addWidget(self.load_profile_btn)

        self.delete_profile_btn = QPushButton("حذف")
        self.delete_profile_btn.clicked.connect(self.delete_profile)
        profile_select_layout.addWidget(self.delete_profile_btn)

        profile_layout.addLayout(profile_select_layout)

        profile_save_layout = QHBoxLayout()
        self.profile_name_input = QLineEdit()
        self.profile_name_input.setPlaceholderText("نام پروفایل جدید")
        profile_save_layout.addWidget(self.profile_name_input)

        self.save_profile_btn = QPushButton("ذخیره")
        self.save_profile_btn.clicked.connect(self.save_profile)
        profile_save_layout.addWidget(self.save_profile_btn)

        profile_layout.addLayout(profile_save_layout)

        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)

        scan_buttons_layout = QHBoxLayout()

        self.scan_btn = QPushButton("▶️ اسکن شبکه")
        self.scan_btn.setToolTip("شروع اسکن با تنظیمات فعلی")
        self.scan_btn.clicked.connect(self.start_scan)
        self.scan_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        scan_buttons_layout.addWidget(self.scan_btn)

        self.stop_btn = QPushButton("⏹️ توقف اسکن")
        self.stop_btn.setToolTip("توقف فرآیند اسکن در حال اجرا")
        self.stop_btn.clicked.connect(self.stop_scan)
        self.stop_btn.setEnabled(False)
        scan_buttons_layout.addWidget(self.stop_btn)

        layout.addLayout(scan_buttons_layout)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.output = QTextEdit()
        self.output.setToolTip("گزارش رویدادها و خروجی اسکن")
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        layout.addStretch()
        self.setLayout(layout)

    def update_profile_combo(self):
        self.profile_combo.clear()
        self.profile_combo.addItem("انتخاب پروفایل...")
        for profile_name in self.profiles.keys():
            self.profile_combo.addItem(profile_name)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "باز کردن لیست آی‌پی", "", "فایل‌های متنی (*.txt)")
        if file_path:
            self.file_path.setText(file_path)
            self.file_path.setEnabled(True)
            self.ip_input.setEnabled(False)
            self.ip_file_loaded = True
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    ips = f.read().strip()
                    self.ip_input.setText(ips)
            except Exception:
                pass

    def start_scan(self):
        if self.ip_file_loaded:
            file_path = self.file_path.text()
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "خطای ورودی", "فایل لیست آی‌پی وجود ندارد")
                return
            target = f"-iL {file_path}"
        else:
            ip_input = self.ip_input.text().strip()
            if not ip_input:
                QMessageBox.warning(self, "خطای ورودی", "لطفاً آی‌پی هدف را وارد کنید")
                return
            target = ip_input

        ports = self.port_input.text().strip()
        if not ports:
            QMessageBox.warning(self, "خطای ورودی", "لطفاً پورت(ها) را وارد کنید")
            return

        main_window = None
        widget = self
        while widget is not None:
            if isinstance(widget, QMainWindow):
                main_window = widget
                break
            widget = widget.parent()
        current_theme = main_window.current_theme if main_window else 'dark'

        settings = {
            'target': target,
            'ports': [p.strip() for p in ports.split(',') if p.strip()],
            'udp_scan': self.udp_checkbox.isChecked(),
            'simple_scan': True,
            'theme': current_theme,
        }

        self.scan_worker = ScanWorker(settings)
        self.scan_worker.progress_updated.connect(self.update_progress)
        self.scan_worker.scan_complete.connect(self.handle_scan_complete)
        self.scan_worker.error_occurred.connect(self.show_error)
        self.scan_worker.log_message.connect(self.update_log)
        self.scan_worker.start()

        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.output.clear()
        self.output.append("⏳ در حال آماده‌سازی اسکن...")

    def stop_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.stop()
            self.scan_worker.wait()
            self.scan_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.output.append("⏹️ اسکن متوقف شد.")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_log(self, message):
        self.output.append(message)

    def handle_scan_complete(self, results):
        self.output.append("\n✅ اسکن کامل شد!")
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.scan_complete.emit(results)

    def show_error(self, message):
        self.output.append(f"\n❌ خطا: {message}")
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def save_profile(self):
        profile_name = self.profile_name_input.text().strip()
        if not profile_name:
            QMessageBox.warning(self, "خطا", "لطفاً نام پروفایل را وارد کنید")
            return

        settings = {
            'target': self.ip_input.text(),
            'ports': [p.strip() for p in self.port_input.text().split(',') if p.strip()],
            'udp_scan': self.udp_checkbox.isChecked(),
            'simple_scan': True,
        }

        ProfileManager.add_profile(profile_name, settings)
        self.profiles = ProfileManager.load_profiles()
        self.update_profile_combo()
        self.profile_name_input.clear()
        QMessageBox.information(self, "موفقیت", f"پروفایل '{profile_name}' با موفقیت ذخیره شد")

    def load_profile(self):
        profile_name = self.profile_combo.currentText()
        if profile_name == "انتخاب پروفایل...":
            return

        if profile_name in self.profiles:
            profile = self.profiles[profile_name]
            self.ip_input.setText(profile.get('target', ''))
            self.port_input.setText(','.join(profile.get('ports', [])))
            self.udp_checkbox.setChecked(profile.get('udp_scan', False))
            # بازنشانی حالت فایل ورودی
            self.ip_file_loaded = False
            self.file_path.clear()
            self.file_path.setEnabled(False)
            self.ip_input.setEnabled(True)
            QMessageBox.information(self, "موفقیت", f"پروفایل '{profile_name}' بارگیری شد")

    def delete_profile(self):
        profile_name = self.profile_combo.currentText()
        if profile_name == "انتخاب پروفایل...":
            return

        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف پروفایل '{profile_name}' مطمئن هستید؟",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            ProfileManager.delete_profile(profile_name)
            self.profiles = ProfileManager.load_profiles()
            self.update_profile_combo()
            QMessageBox.information(self, "موفقیت", f"پروفایل '{profile_name}' حذف شد")


class AdvancedScanTab(SimpleScanTab):
    """تب اسکن پیشرفته"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_advanced_ui()

    def init_advanced_ui(self):
        advanced_group = QGroupBox("تنظیمات پیشرفته Nmap")
        advanced_layout = QFormLayout()

        self.min_rate_spin = QSpinBox()
        self.min_rate_spin.setRange(0, 10000)
        self.min_rate_spin.setValue(100)
        self.min_rate_spin.setToolTip("حداقل نرخ ارسال بسته (پکت بر ثانیه)")
        advanced_layout.addRow("📉 MIN_RATE:", self.min_rate_spin)

        self.max_rate_spin = QSpinBox()
        self.max_rate_spin.setRange(0, 10000)
        self.max_rate_spin.setValue(200)
        self.max_rate_spin.setToolTip("حداکثر نرخ ارسال بسته (پکت بر ثانیه)")
        advanced_layout.addRow("📈 MAX_RATE:", self.max_rate_spin)

        self.scan_delay_input = QLineEdit()
        self.scan_delay_input.setText("100ms")
        self.scan_delay_input.setToolTip("تاخیر بین پکت‌ها (مانند 100ms یا 1s)")
        advanced_layout.addRow("⏱ SCAN_DELAY:", self.scan_delay_input)

        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(0, 10)
        self.max_retries_spin.setValue(5)
        self.max_retries_spin.setToolTip("حداکثر تلاش مجدد")
        advanced_layout.addRow("🔄 MAX_RETRIES:", self.max_retries_spin)

        advanced_group.setLayout(advanced_layout)

        main_layout = self.layout()
        main_layout.insertWidget(3, advanced_group)

    def start_scan(self):
        if self.ip_file_loaded:
            file_path = self.file_path.text()
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "خطای ورودی", "فایل لیست آی‌پی وجود ندارد")
                return
            target = f"-iL {file_path}"
        else:
            ip_input = self.ip_input.text().strip()
            if not ip_input:
                QMessageBox.warning(self, "خطای ورودی", "لطفاً آی‌پی هدف را وارد کنید")
                return
            target = ip_input

        ports = self.port_input.text().strip()
        if not ports:
            QMessageBox.warning(self, "خطای ورودی", "لطفاً پورت(ها) را وارد کنید")
            return

        main_window = None
        widget = self
        while widget is not None:
            if isinstance(widget, QMainWindow):
                main_window = widget
                break
            widget = widget.parent()
        current_theme = main_window.current_theme if main_window else 'dark'

        settings = {
            'target': target,
            'ports': [p.strip() for p in ports.split(',') if p.strip()],
            'udp_scan': self.udp_checkbox.isChecked(),
            'min_rate': self.min_rate_spin.value(),
            'max_rate': self.max_rate_spin.value(),
            'scan_delay': self.scan_delay_input.text(),
            'max_retries': self.max_retries_spin.value(),
            'simple_scan': False,
            'theme': current_theme,
        }

        self.scan_worker = ScanWorker(settings)
        self.scan_worker.progress_updated.connect(self.update_progress)
        self.scan_worker.scan_complete.connect(self.handle_scan_complete)
        self.scan_worker.error_occurred.connect(self.show_error)
        self.scan_worker.log_message.connect(self.update_log)
        self.scan_worker.start()

        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.output.clear()
        self.output.append("⏳ در حال آماده‌سازی اسکن پیشرفته...")

    def save_profile(self):
        profile_name = self.profile_name_input.text().strip()
        if not profile_name:
            QMessageBox.warning(self, "خطا", "لطفاً نام پروفایل را وارد کنید")
            return

        settings = {
            'target': self.ip_input.text(),
            'ports': [p.strip() for p in self.port_input.text().split(',') if p.strip()],
            'udp_scan': self.udp_checkbox.isChecked(),
            'min_rate': self.min_rate_spin.value(),
            'max_rate': self.max_rate_spin.value(),
            'scan_delay': self.scan_delay_input.text(),
            'max_retries': self.max_retries_spin.value(),
            'simple_scan': False,
        }

        ProfileManager.add_profile(profile_name, settings)
        self.profiles = ProfileManager.load_profiles()
        self.update_profile_combo()
        self.profile_name_input.clear()
        QMessageBox.information(self, "موفقیت", f"پروفایل '{profile_name}' با موفقیت ذخیره شد")

    def load_profile(self):
        profile_name = self.profile_combo.currentText()
        if profile_name == "انتخاب پروفایل...":
            return

        if profile_name in self.profiles:
            profile = self.profiles[profile_name]
            self.ip_input.setText(profile.get('target', ''))
            self.port_input.setText(','.join(profile.get('ports', [])))
            self.udp_checkbox.setChecked(profile.get('udp_scan', False))
            self.min_rate_spin.setValue(profile.get('min_rate', 100))
            self.max_rate_spin.setValue(profile.get('max_rate', 200))
            self.scan_delay_input.setText(profile.get('scan_delay', '100ms'))
            self.max_retries_spin.setValue(profile.get('max_retries', 5))
            # بازنشانی حالت فایل ورودی
            self.ip_file_loaded = False
            self.file_path.clear()
            self.file_path.setEnabled(False)
            self.ip_input.setEnabled(True)
            QMessageBox.information(self, "موفقیت", f"پروفایل '{profile_name}' بارگیری شد")


class ReportsTab(QWidget):
    """تب گزارش‌گیری بصری"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_results = {}
        self.results_folder = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        output_group = QGroupBox("گزینه‌های خروجی")
        output_layout = QHBoxLayout()

        self.html_btn_with = QPushButton("📄 HTML (با نمودار)")
        self.html_btn_with.clicked.connect(self.export_html_with_charts)
        output_layout.addWidget(self.html_btn_with)

        self.html_btn_without = QPushButton("📄 HTML (بدون نمودار)")
        self.html_btn_without.clicked.connect(self.export_html_no_charts)
        output_layout.addWidget(self.html_btn_without)

        self.csv_btn = QPushButton("📊 خروجی CSV")
        self.csv_btn.clicked.connect(self.export_csv)
        output_layout.addWidget(self.csv_btn)

        self.excel_btn = QPushButton("📈 خروجی Excel")
        self.excel_btn.clicked.connect(self.export_excel)
        output_layout.addWidget(self.excel_btn)

        self.chart_btn = QPushButton("📉 خروجی نمودارها")
        self.chart_btn.clicked.connect(self.export_charts)
        output_layout.addWidget(self.chart_btn)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        charts_group = QGroupBox("نمودارهای تحلیلی")
        charts_layout = QVBoxLayout()

        # گزینه نمودار بر اساس پورت
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("نمودار بر اساس پورت:"))
        self.port_chart_type_combo = QComboBox()
        self.port_chart_type_combo.addItems(["ستونی", "دایره‌ای"])
        self.port_chart_type_combo.currentIndexChanged.connect(self.update_charts)
        controls_layout.addWidget(self.port_chart_type_combo)
        controls_layout.addStretch()
        charts_layout.addLayout(controls_layout)

        self.pie_chart = FigureCanvas(plt.figure(figsize=(5, 4)))
        charts_layout.addWidget(self.pie_chart)

        self.bar_chart = FigureCanvas(plt.figure(figsize=(5, 4)))
        charts_layout.addWidget(self.bar_chart)

        self.ports_chart = FigureCanvas(plt.figure(figsize=(5, 4)))
        charts_layout.addWidget(self.ports_chart)

        # نمودار تعداد بر اساس پورت (نمایش بر اساس انتخاب)
        self.counts_per_port_chart = FigureCanvas(plt.figure(figsize=(5, 4)))
        charts_layout.addWidget(self.counts_per_port_chart)

        charts_group.setLayout(charts_layout)
        layout.addWidget(charts_group)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels(["آی‌پی", "پورت", "پروتکل", "وضعیت", "سرویس", "محصول", "نسخه"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setSortingEnabled(True)
        layout.addWidget(self.results_table)

        layout.addStretch()
        self.setLayout(layout)

    def update_results(self, results):
        self.scan_results = results
        self.results_folder = results.get('_results_folder', None)
        self.parse_results()
        self.update_charts()

    def parse_results(self):
        self.results_table.setRowCount(0)

        port_data = self.scan_results.get('port_data', [])
        if not port_data:
            return

        try:
            for data in port_data:
                row_position = self.results_table.rowCount()
                self.results_table.insertRow(row_position)

                self.results_table.setItem(row_position, 0, QTableWidgetItem(data['ip']))
                self.results_table.setItem(row_position, 1, QTableWidgetItem(data['port']))
                self.results_table.setItem(row_position, 2, QTableWidgetItem(data['protocol']))
                self.results_table.setItem(row_position, 3, QTableWidgetItem(data['state']))
                self.results_table.setItem(row_position, 4, QTableWidgetItem(data['service']))
                self.results_table.setItem(row_position, 5, QTableWidgetItem(""))
                self.results_table.setItem(row_position, 6, QTableWidgetItem(""))
        except Exception as e:
            error_msg = f"خطا در تجزیه نتایج: {str(e)}"
            QMessageBox.critical(self, "خطا", error_msg)
            print(f"Error parsing results: {e}")

    def update_charts(self):
        port_states = defaultdict(int)
        protocol_counts = defaultdict(int)
        open_ports_per_ip = defaultdict(int)
        counts_per_port = defaultdict(int)

        port_data = self.scan_results.get('port_data', [])
        if not port_data:
            return

        try:
            for data in port_data:
                protocol = data['protocol']
                state = data['state']
                ip = data['ip']
                port_no = data['port']

                port_states[state] += 1
                protocol_counts[protocol] += 1
                if state == 'open':
                    open_ports_per_ip[ip] += 1
                    counts_per_port[port_no] += 1

            font_prop = vazir_font if (vazir_font and hasattr(vazir_font, 'get_file') and vazir_font.get_file()) else FontProperties()

            # نمودار دایره‌ای وضعیت پورت‌ها
            self.pie_chart.figure.clear()
            ax = self.pie_chart.figure.add_subplot(111)
            if port_states:
                ax.pie(list(port_states.values()), labels=[shape_text(k) for k in port_states.keys()], autopct='%1.1f%%',
                       textprops={'fontproperties': font_prop})
                ax.set_title(shape_text("توزیع وضعیت پورت‌ها"), fontproperties=font_prop)
            self.pie_chart.draw()

            # نمودار میله‌ای پروتکل‌ها
            self.bar_chart.figure.clear()
            ax = self.bar_chart.figure.add_subplot(111)
            if protocol_counts:
                ax.bar(list(protocol_counts.keys()), list(protocol_counts.values()))
                ax.set_title(shape_text("استفاده از پروتکل‌ها"), fontproperties=font_prop)
                ax.set_xlabel(shape_text("پروتکل"), fontproperties=font_prop)
                ax.set_ylabel(shape_text("تعداد"), fontproperties=font_prop)
            self.bar_chart.draw()

            # نمودار پورت‌های باز بر اساس آی‌پی
            self.ports_chart.figure.clear()
            ax = self.ports_chart.figure.add_subplot(111)
            if open_ports_per_ip:
                ips = list(open_ports_per_ip.keys())
                counts = list(open_ports_per_ip.values())
                if len(ips) > 20:
                    ips = ips[:20]
                    counts = counts[:20]
                ax.bar(range(len(ips)), counts)
                ax.set_xticks(range(len(ips)))
                ax.set_xticklabels(ips, rotation=45, ha='right')
                ax.set_title(shape_text("تعداد پورت‌های باز بر اساس آی‌پی"), fontproperties=font_prop)
                ax.set_xlabel(shape_text("آی‌پی"), fontproperties=font_prop)
                ax.set_ylabel(shape_text("تعداد پورت‌های باز"), fontproperties=font_prop)
                plt.tight_layout()
            self.ports_chart.draw()

            # نمودار تعداد بر اساس پورت (قابل انتخاب بین ستونی/دایره‌ای)
            self.counts_per_port_chart.figure.clear()
            ax = self.counts_per_port_chart.figure.add_subplot(111)
            if counts_per_port:
                sorted_items = sorted(counts_per_port.items(), key=lambda kv: kv[1], reverse=True)
                top_items = sorted_items[:25]
                ports = [p for p, _ in top_items]
                counts = [c for _, c in top_items]
                if self.port_chart_type_combo.currentText() == "دایره‌ای":
                    ax.pie(counts, labels=ports, autopct='%1.1f%%', textprops={'fontproperties': font_prop})
                    ax.set_title(shape_text("سهم پورت‌ها از بین میزبان‌های دارای پورت باز"), fontproperties=font_prop)
                else:
                    ax.bar(range(len(ports)), counts)
                    ax.set_xticks(range(len(ports)))
                    ax.set_xticklabels(ports, rotation=45, ha='right')
                    ax.set_title(shape_text("تعداد میزبان‌های دارای پورت باز بر اساس شماره پورت"), fontproperties=font_prop)
                    ax.set_xlabel(shape_text("پورت"), fontproperties=font_prop)
                    ax.set_ylabel(shape_text("تعداد میزبان"), fontproperties=font_prop)
                    plt.tight_layout()
            self.counts_per_port_chart.draw()
        except Exception as e:
            error_msg = f"خطا در به‌روزرسانی نمودارها: {str(e)}"
            QMessageBox.critical(self, "خطا", error_msg)
            print(f"Error updating charts: {e}")

    def export_html_with_charts(self):
        if not self.scan_results:
            QMessageBox.warning(self, "هشدار", "هیچ نتیجه اسکنی برای خروجی وجود ندارد")
            return
        html_file = self.scan_results.get('html_report_with_charts', '')
        if html_file and os.path.exists(html_file):
            QDesktopServices.openUrl(QUrl.fromLocalFile(html_file))
        else:
            QMessageBox.warning(self, "هشدار", "فایل گزارش HTML (با نمودار) یافت نشد")

    def export_html_no_charts(self):
        if not self.scan_results:
            QMessageBox.warning(self, "هشدار", "هیچ نتیجه اسکنی برای خروجی وجود ندارد")
            return
        html_file = self.scan_results.get('html_report_no_charts', '')
        if html_file and os.path.exists(html_file):
            QDesktopServices.openUrl(QUrl.fromLocalFile(html_file))
        else:
            QMessageBox.warning(self, "هشدار", "فایل گزارش HTML (بدون نمودار) یافت نشد")

    def export_csv(self):
        if not self.scan_results:
            QMessageBox.warning(self, "هشدار", "هیچ نتیجه اسکنی برای خروجی وجود ندارد")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره گزارش CSV", "", "فایل‌های CSV (*.csv)")
        if file_path:
            try:
                data = []
                port_data = self.scan_results.get('port_data', [])
                if port_data:
                    for item in port_data:
                        data.append({
                            "IP": item['ip'],
                            "Port": item['port'],
                            "Protocol": item['protocol'],
                            "State": item['state'],
                            "Service": item['service'],
                            "Product": "",
                            "Version": "",
                            "Extra Info": "",
                        })
                df = pd.DataFrame(data)
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "موفقیت", "گزارش CSV با موفقیت صادر شد")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در صادر کردن CSV: {str(e)}")

    def export_excel(self):
        if not self.scan_results:
            QMessageBox.warning(self, "هشدار", "هیچ نتیجه اسکنی برای خروجی وجود ندارد")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره گزارش Excel", "", "فایل‌های Excel (*.xlsx)")
        if file_path:
            try:
                data = []
                port_data = self.scan_results.get('port_data', [])
                if port_data:
                    for item in port_data:
                        data.append({
                            "IP": item['ip'],
                            "Port": item['port'],
                            "Protocol": item['protocol'],
                            "State": item['state'],
                            "Service": item['service'],
                            "Product": "",
                            "Version": "",
                            "Extra Info": "",
                        })
                df = pd.DataFrame(data)
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "موفقیت", "گزارش Excel با موفقیت صادر شد")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در صادر کردن Excel: {str(e)}")

    def export_charts(self):
        if not self.results_folder:
            QMessageBox.warning(self, "هشدار", "هیچ نتیجه اسکنی برای خروجی وجود ندارد")
            return

        try:
            pie_path = os.path.join(self.results_folder, "port_states_pie.png")
            bar_path = os.path.join(self.results_folder, "protocol_usage_bar.png")
            ports_path = os.path.join(self.results_folder, "open_ports_per_ip.png")
            byport_bar = os.path.join(self.results_folder, "counts_per_port_bar.png")
            byport_pie = os.path.join(self.results_folder, "counts_per_port_pie.png")

            avail = [p for p in [pie_path, bar_path, ports_path, byport_bar, byport_pie] if os.path.exists(p)]
            if avail:
                save_dir = QFileDialog.getExistingDirectory(self, "انتخاب پوشه برای ذخیره نمودارها")
                if save_dir:
                    import shutil
                    for p in avail:
                        shutil.copy2(p, os.path.join(save_dir, os.path.basename(p)))
                    QMessageBox.information(self, "موفقیت", "نمودارها با موفقیت صادر شدند")
            else:
                QMessageBox.warning(self, "هشدار", "فایل‌های نمودار یافت نشدند")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در صادر کردن نمودارها: {str(e)}")


class NetworkScannerApp(QMainWindow):
    """پنجره اصلی برنامه"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔎 اسکنر شبکه پیشرفته")
        self.setGeometry(100, 100, 1100, 760)

        self.current_theme = "dark"
        self.init_ui()

    def init_ui(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("فایل")
        exit_action = QAction("خروج", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("نمایش")
        theme_group = QActionGroup(self)

        self.dark_theme_action = QAction("تم تاریک", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.setChecked(True)
        self.dark_theme_action.triggered.connect(lambda: self.change_theme("dark"))
        theme_group.addAction(self.dark_theme_action)
        view_menu.addAction(self.dark_theme_action)

        self.light_theme_action = QAction("تم روشن", self)
        self.light_theme_action.setCheckable(True)
        self.light_theme_action.setChecked(False)
        self.light_theme_action.triggered.connect(lambda: self.change_theme("light"))
        theme_group.addAction(self.light_theme_action)
        view_menu.addAction(self.light_theme_action)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.simple_tab = SimpleScanTab(self)
        self.tabs.addTab(self.simple_tab, "اسکن ساده")

        self.advanced_tab = AdvancedScanTab(self)
        self.tabs.addTab(self.advanced_tab, "اسکن پیشرفته")

        self.reports_tab = ReportsTab(self)
        self.tabs.addTab(self.reports_tab, "گزارش‌گیری بصری")

        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)

        self.simple_tab.scan_complete.connect(self.reports_tab.update_results)
        self.advanced_tab.scan_complete.connect(self.reports_tab.update_results)

        ThemeManager.apply_theme(QApplication.instance(), self.current_theme)

    def change_theme(self, theme_name):
        self.current_theme = theme_name
        ThemeManager.apply_theme(QApplication.instance(), theme_name)

        if theme_name == "dark":
            self.dark_theme_action.setChecked(True)
        else:
            self.light_theme_action.setChecked(True)


def main():
    app = QApplication(sys.argv)

    # بارگذاری فونت (پس از ایجاد QApplication)
    global vazir_font
    vazir_font = load_vazir_font()

    ThemeManager.apply_theme(app, "dark")

    window = NetworkScannerApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

