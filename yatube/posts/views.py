from core.utils import paginate
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post

User = get_user_model()


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
    following = (
        request.user.is_authenticated
        and Follow.objects.filter(user=request.user)
        .filter(author=author)
        .exists()
    )
    context = {
        'page_obj': paginate(posts, request),
        'author': author,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    context = {
        'post': post,
        'form': CommentForm(),
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
    posts = Post.objects.filter(
        author__following__user=request.user
    ).select_related('author', 'group')
    context = {
        'page_obj': paginate(posts, request),
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    # проверка, юзер не подписывается на себя и автора, которого уже подписан
    if (
        request.user != author
        and not Follow.objects.filter(user=request.user)
        .filter(author=author)
        .exists()
    ):
        Follow.objects.create(
            user=request.user,
            author=author,
        )
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    record_id = get_object_or_404(Follow, author=author).pk
    Follow.objects.filter(pk=record_id).delete()
    return redirect('posts:follow_index')
