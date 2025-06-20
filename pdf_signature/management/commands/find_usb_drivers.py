#!/usr/bin/env python3
"""
Django management command to find USB key drivers and PKCS#11 libraries.
Helps identify where USB key software is installed.
"""

import os
import glob
import winreg
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Find USB key drivers and PKCS#11 libraries on the system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Searching for USB key drivers and PKCS#11 libraries...'))
        
        # Search common file patterns
        self.search_file_patterns()
        
        # Search Windows registry
        self.search_registry()
        
        # Search Program Files
        self.search_program_files()
        
        # Search Windows system directories
        self.search_system_directories()

    def search_file_patterns(self):
        """Search for common PKCS#11 library file patterns."""
        self.stdout.write('\n📁 Searching for PKCS#11 library files...')
        
        patterns = [
            'C:\\**\\*pkcs11*.dll',
            'C:\\**\\*cryptoki*.dll',
            'C:\\**\\eps2003*.dll',
            'C:\\**\\eTPkcs11*.dll',
            'C:\\**\\emudhra*.dll',
            'C:\\**\\gclib*.dll',
            'C:\\**\\wdpkcs*.dll',
            'C:\\**\\asepkcs*.dll',
        ]
        
        found_files = []
        for pattern in patterns:
            try:
                files = glob.glob(pattern, recursive=True)
                for file in files:
                    if os.path.isfile(file):
                        found_files.append(file)
                        self.stdout.write(f'   📄 Found: {file}')
            except Exception as e:
                self.stdout.write(f'   ❌ Error searching {pattern}: {e}')
                
        if not found_files:
            self.stdout.write('   ❌ No PKCS#11 libraries found with common patterns')
        else:
            self.stdout.write(f'   ✅ Found {len(found_files)} potential PKCS#11 libraries')

    def search_registry(self):
        """Search Windows registry for USB key software."""
        self.stdout.write('\n🔧 Searching Windows registry...')
        
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
        ]
        
        usb_key_keywords = [
            'emudhra', 'safenet', 'gemalto', 'feitian', 'epass', 'ncode',
            'watchdata', 'athena', 'pkcs11', 'cryptoki', 'token', 'smartcard'
        ]
        
        found_software = []
        for hkey, subkey in registry_paths:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as app_key:
                                try:
                                    display_name = winreg.QueryValueEx(app_key, 'DisplayName')[0]
                                    install_location = None
                                    try:
                                        install_location = winreg.QueryValueEx(app_key, 'InstallLocation')[0]
                                    except FileNotFoundError:
                                        pass
                                    
                                    # Check if this might be USB key software
                                    for keyword in usb_key_keywords:
                                        if keyword.lower() in display_name.lower():
                                            found_software.append({
                                                'name': display_name,
                                                'location': install_location,
                                                'registry_key': subkey_name
                                            })
                                            self.stdout.write(f'   🔑 Found: {display_name}')
                                            if install_location:
                                                self.stdout.write(f'      📍 Location: {install_location}')
                                            break
                                except FileNotFoundError:
                                    pass
                            i += 1
                        except OSError:
                            break
            except Exception as e:
                self.stdout.write(f'   ❌ Error searching registry {subkey}: {e}')
                
        if not found_software:
            self.stdout.write('   ❌ No USB key software found in registry')

    def search_program_files(self):
        """Search Program Files directories for USB key software."""
        self.stdout.write('\n📂 Searching Program Files directories...')
        
        program_dirs = [
            r'C:\Program Files',
            r'C:\Program Files (x86)',
        ]
        
        usb_key_vendors = [
            'eMudhra', 'SafeNet', 'Gemalto', 'Feitian', 'nCode',
            'WatchData', 'Athena', 'ePass', 'emSign', 'emClient'
        ]
        
        found_dirs = []
        for prog_dir in program_dirs:
            if os.path.exists(prog_dir):
                for vendor in usb_key_vendors:
                    vendor_path = os.path.join(prog_dir, vendor)
                    if os.path.exists(vendor_path):
                        found_dirs.append(vendor_path)
                        self.stdout.write(f'   📁 Found vendor directory: {vendor_path}')
                        
                        # Look for DLL files in vendor directory
                        for root, dirs, files in os.walk(vendor_path):
                            for file in files:
                                if file.lower().endswith('.dll') and any(keyword in file.lower() for keyword in ['pkcs11', 'cryptoki']):
                                    dll_path = os.path.join(root, file)
                                    self.stdout.write(f'      📄 Found DLL: {dll_path}')
                                    
        if not found_dirs:
            self.stdout.write('   ❌ No USB key vendor directories found')

    def search_system_directories(self):
        """Search Windows system directories."""
        self.stdout.write('\n🖥️ Searching Windows system directories...')
        
        system_dirs = [
            r'C:\Windows\System32',
            r'C:\Windows\SysWOW64',
        ]
        
        dll_patterns = ['*pkcs11*.dll', '*cryptoki*.dll', '*emudhra*.dll', '*etp*.dll']
        
        found_dlls = []
        for sys_dir in system_dirs:
            if os.path.exists(sys_dir):
                self.stdout.write(f'   🔍 Searching {sys_dir}...')
                for pattern in dll_patterns:
                    search_pattern = os.path.join(sys_dir, pattern)
                    files = glob.glob(search_pattern)
                    for file in files:
                        found_dlls.append(file)
                        self.stdout.write(f'      📄 Found: {file}')
                        
        if not found_dlls:
            self.stdout.write('   ❌ No PKCS#11 DLLs found in system directories')
        else:
            self.stdout.write(f'   ✅ Found {len(found_dlls)} DLLs in system directories')

        # Final recommendations
        self.stdout.write('\n💡 Recommendations:')
        self.stdout.write('1. If no USB key software found, install your USB key drivers')
        self.stdout.write('2. Common USB key software:')
        self.stdout.write('   - eMudhra emSign Client')
        self.stdout.write('   - SafeNet Authentication Client')
        self.stdout.write('   - Feitian ePass2003 drivers')
        self.stdout.write('   - Gemalto Classic Client')
        self.stdout.write('3. After installation, run: python manage.py usb_key_sign --detect')
        self.stdout.write('4. If you know where your PKCS#11 library is, use:')
        self.stdout.write('   python manage.py usb_key_sign --library "path\\to\\your\\library.dll" --sign document.pdf')
