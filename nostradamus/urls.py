from django.conf.urls import url
from django.urls import include, path
from django.contrib import admin
from django.http import HttpResponse
from basic import views as basic_views


urlpatterns = [
    path('matches/', include('matches.urls')),
    path('results/', include('results.urls')),
    url(r'^$', basic_views.home, name='home'),
    url(r'^admin/', admin.site.urls),
    url(r'^robots.txt$', lambda r: HttpResponse("User-agent: *\nDisallow: /", mimetype="text/plain"))
]
