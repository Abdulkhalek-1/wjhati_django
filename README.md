pip install -r requirements.txt

python manage.py makemigrations 

python manage.py migrate

python manage.py createsuperuser

python manage.py runserver

تثبيت  Redis  عبر Chocolatey

اولا تثبيت   Chocolatey

Set-ExecutionPolicy Bypass -Scope Process -Force; `
  [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
  iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))


ثبّت Redis:

choco install redis-64 -y

اخيرا    

net start Redis



لتشغيل الجدولة   


celery -A backend worker --loglevel=info --pool=solo

ثم هذا في ترمينال اخرى    

celery -A backend beat --loglevel=info


