from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from basic.utils import get_funny_stats_context
from .models import NewsPost


@login_required
def home(request):
    latest_news = NewsPost.objects.first()
    return render(request, 'home.html', {'latest_news': latest_news})


@login_required
def news_list(request):
    posts = NewsPost.objects.all()
    return render(request, 'news_list.html', {'posts': posts})


@login_required
def news_detail(request, pk):
    post = get_object_or_404(NewsPost, pk=pk)
    return render(request, 'news_detail.html', {'post': post})


@login_required
def history(request):
    return render(request, 'history.html')


@login_required
def intro(request):
    return render(request, 'intro.html')


def install_app(request):
    return render(request, 'install_app.html')


@login_required
def how_odds_work(request):
    return render(request, 'how_odds_work.html')


@login_required
def funny_stats(request):
    return render(request, 'funny_stats.html', get_funny_stats_context())
