from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post

User = get_user_model()


def paginate(post_list, request):
    page_number = request.GET.get('page')
    paginator = Paginator(post_list, settings.PAGINATE_LIMIT)
    return paginator.get_page(page_number)


@cache_page(20, key_prefix='index_page')
def index(request):
    posts = Post.objects.select_related('group', 'author')
    context = {
        'page_obj': paginate(posts, request),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author')
    context = {
        'group': group,
        'page_obj': paginate(posts, request),
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related('group')
    context = {
        'page_obj': paginate(posts, request),
        'author': author,
    }
    if request.user.is_authenticated:
        context['following'] = Follow.objects.filter(user=request.user).filter(author=author).exists()
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:post_detail', post_id)
    context = {
        'post': post,
        'form': form,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', request.user.username)
    context = {'form': form}
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST or None, files=request.FILES or None, instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post.id)
    context = {'form': form, 'is_edit': True}
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    form = CommentForm(request.POST or None)
    post = Post.objects.get(id=post_id)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Получаем QuerySet авторов, на которых подписан юзер, затем вытаскиваем их
    id из QuerySet в список, далее фильтруем Post по этим id"""
    authors_query = Follow.objects.filter(
        user_id=request.user.id
    ).values_list('author_id')
    authors_id_list = []
    for id_tuple in authors_query:
        authors_id_list.append(id_tuple[0])
    posts = (
        Post.objects.select_related('author')
        .filter(author_id__in=authors_id_list)
        .select_related('group')
    )
    context = {
        'page_obj': paginate(posts, request),
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author and not Follow.objects.filter(user=request.user).filter(author=author).exists():
        record_to_create = [Follow(user_id=request.user.id, author=author)]
        Follow.objects.bulk_create(record_to_create)
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    record_id = get_object_or_404(Follow, author=author).pk
    Follow.objects.filter(pk=record_id).delete()
    return redirect('posts:follow_index')
