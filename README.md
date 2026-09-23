# Education Center MIS

Django-based public website and education-center MIS.

## Run locally

```powershell
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/` for the public website and `http://127.0.0.1:8000/admin/` to manage all dynamic content and MIS records.

## Production

Before publishing the site, set the variables shown in `.env.example` in your hosting environment. Use a long, random `DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=False`, configure the real domain names in `DJANGO_ALLOWED_HOSTS`, run `python manage.py collectstatic`, and use HTTPS. Back up the database daily; SQLite is suitable for a small local installation, while PostgreSQL is recommended as the centre grows.

## Dynamic modules

- Website settings, services, news, and contact messages
- Courses, teachers, classes, students, enrollments, attendance
- Invoices, payments, exam results, and dashboard totals

Use the Django Admin Panel to create the first Site Setting, courses, users, and all other records.
