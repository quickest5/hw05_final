from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User
from .utils import page_content


@cache_page(20)
def index(request):
    posts = Post.objects.all()
    context = page_content(posts, request)
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    context = {
        'group': group,
        'posts': posts,
    }
    context.update(page_content(posts, request))
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    if request.user.is_authenticated:
        following = Follow.objects.filter(user=request.user, author=author)
        context = {
            'author': author,
            'following': following,
        }
    else:
        context = {
            'author': author,
        }
    context.update(page_content(posts, request))
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all()
    form = CommentForm()

    context = {
        'post': post,
        'form': form,
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            form_object = form.save(commit=False)
            form_object.author = request.user
            form_object.save()
            return redirect('posts:profile', request.user.username)
        return render(request, 'posts/create.html', {'form': form})
    return render(request, 'posts/create.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    is_edit = True
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    if form.is_valid():
        form_object = form.save(commit=False)
        form_object.author = request.user
        form_object.save()
        return redirect('posts:post_detail', post_id)
    return render(request, 'posts/create.html', {
        'form': form,
        'is_edit': is_edit,
    })


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    context = page_content(posts, request)
    return render(request, 'posts/index.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    follower = Follow.objects.filter(
        user=user,
        author=author
    )
    if not follower.exists() and user != author:
        Follow.objects.create(
            user=user,
            author=author
        )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    follower = Follow.objects.filter(
        user=user,
        author=author
    )
    if follower.exists() and user != author:
        Follow.objects.filter(
            user=user,
            author=author
        ).delete()
    return redirect('posts:profile', username=username)
