from django.urls import path
from .views import attendance_csv, dashboard, notification_list, payment_receipt, reports, result_sheet, student_profile

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('reports/', reports, name='mis_reports'),
    path('reports/attendance.csv', attendance_csv, name='attendance_csv'),
    path('students/<int:pk>/', student_profile, name='student_profile'),
    path('payments/<int:pk>/receipt/', payment_receipt, name='payment_receipt'),
    path('results/<int:exam_id>/sheet/', result_sheet, name='result_sheet'),
    path('notifications/', notification_list, name='notifications'),
]
