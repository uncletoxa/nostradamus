from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
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
