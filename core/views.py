from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import ContactForm, EmailAuthenticationForm
from .models import News, Service, SiteSetting

def setting():
    return SiteSetting.objects.first()


def language_template(request, pashto_name):
    """Choose the matching English interface template when English was selected on Welcome."""
    if request.session.get('language') == 'en':
        stem, extension = pashto_name.rsplit('.', 1)
        return f'{stem}_en.{extension}'
    return pashto_name

def home(request):
    return render(request, language_template(request, 'core/welcome.html'), {'site': setting(), 'services': Service.objects.filter(is_active=True)[:3]})


def set_language(request):
    """Persist the visitor's chosen display language in their browser session."""
    if request.method == 'POST' and request.POST.get('language') in {'ps', 'en'}:
        request.session['language'] = request.POST['language']
    next_url = request.POST.get('next') or request.GET.get('next') or '/'
    if not url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        next_url = '/'
    return redirect(next_url)

def welcome(request):
    return redirect('home')

def about(request): return render(request, language_template(request, 'core/about.html'), {'site': setting()})
def services(request): return render(request, language_template(request, 'core/services.html'), {'site': setting(), 'services': Service.objects.filter(is_active=True)})
def news_list(request): return render(request, language_template(request, 'core/news_list.html'), {'site': setting(), 'news': News.objects.filter(is_published=True)})
def news_detail(request, pk): return render(request, language_template(request, 'core/news_detail.html'), {'site': setting(), 'item': News.objects.get(pk=pk, is_published=True)})

def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save(); messages.success(request, 'ستاسو پیغام ثبت شو. مننه!'); return redirect('contact')
    return render(request, language_template(request, 'core/contact.html'), {'site': setting(), 'form': form})


class EmailLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = EmailAuthenticationForm

    def get_template_names(self):
        return ['registration/login_en.html' if self.request.session.get('language') == 'en' else self.template_name]
