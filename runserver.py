import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog.settings')
    
    if getattr(sys, 'frozen', False):
        sys.path.insert(0, os.path.join(sys._MEIPASS, '_internal'))
    
    import django
    django.setup()
    from django.core.management import call_command
    print("Running migrations, please wait...")
    call_command("migrate", verbosity=1, interactive=False)
    from django.core.management import execute_from_command_line
    execute_from_command_line([sys.argv[0], 'runserver', '--noreload', '0.0.0.0:8000'])
