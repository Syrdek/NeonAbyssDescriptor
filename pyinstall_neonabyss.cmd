rmdir /s /q dist\neondb\
pyinstaller main.py --noconfirm --clean --onefile --name neonabyss_item_finder
xcopy.exe neondb\ dist\neondb\ /E