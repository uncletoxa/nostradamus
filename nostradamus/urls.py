from django.urls import include, path, re_path
from django.contrib import admin
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from accounts import views as accounts_views
from basic import views as basic_views
from notifications import views as notifications_views


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('matches/', include('matches.urls')),
    path('predictions/', include('predictions.urls')),
    path('results/', include('results.urls')),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^$', login_required(basic_views.home), name='home'),
    re_path(r'^signup/$', accounts_views.signup, name='signup'),
    re_path(r'^login/$', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    re_path(r'^logout/$', auth_views.LogoutView.as_view(), name='logout'),

    re_path(r'^news/$', basic_views.news_list, name='news_list'),
    re_path(r'^history/$', basic_views.history, name='history'),
    re_path(r'^intro/$', basic_views.intro, name='intro'),
    re_path(r'^install/$', basic_views.install_app, name='install_app'),
    re_path(r'^how-odds-work/$', basic_views.how_odds_work, name='how_odds_work'),
    re_path(r'^funny-stats/$', basic_views.funny_stats, name='funny_stats'),
    re_path(r'^news/(?P<pk>\d+)/$', basic_views.news_detail, name='news_detail'),
    re_path(r'^participants/$', accounts_views.participants, name='participants'),
    re_path(r'^settings/account/$', accounts_views.my_account, name='my_account'),
    re_path(r'^settings/password/$',
        auth_views.PasswordChangeView.as_view(template_name='password_change.html'),
        name='password_change'),
    re_path(r'^settings/password/done/$',
        auth_views.PasswordChangeDoneView.as_view(template_name='password_change_done.html'),
        name='password_change_done'),

    path('chat/', include('chat.urls')),
    path('push/', include('notifications.urls')),
    path('sw.js', notifications_views.service_worker, name='service_worker'),
    re_path(r'^robots.txt$', lambda r: HttpResponse("User-agent: *\nDisallow: /", content_type="text/plain"))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
