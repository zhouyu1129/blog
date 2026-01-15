import markdown

from article.models import Article
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from .forms import CommentForm
from .models import Comment


def comment_list(request, article_index_id, page=1):
    try:
        article = Article.objects.filter(
            index_id=article_index_id,
            deleted=False
        ).order_by('-updated_at').first()

        if not article:
            raise Article.DoesNotExist

        if article.deleted:
            return render(request, 'article_deleted.html', status=404)

    except Article.DoesNotExist:
        return render(request, '404.html', status=404)

    all_comments = Comment.objects.filter(
        article_index_id=article_index_id,
        deleted=False,
        hidden=False
    ).order_by('-update_time')

    latest_comments = {}
    for comment in all_comments:
        if comment.index_id not in latest_comments:
            latest_comments[comment.index_id] = comment

    comments = list(latest_comments.values())
    comments.sort(key=lambda x: (not x.top, x.create_time), reverse=True)

    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.sane_lists',
        'markdown.extensions.nl2br',
    ])

    for comment in comments:
        comment.content_html = md.convert(comment.content)

    paginator = Paginator(comments, 15)
    page_obj = paginator.get_page(page)

    context = {
        'article': article,
        'page_obj': page_obj,
    }
    return render(request, 'comment_list.html', context)


@login_required
def comment_create(request, article_index_id):
    try:
        article = Article.objects.filter(
            index_id=article_index_id,
            deleted=False
        ).order_by('-updated_at').first()

        if not article:
            raise Article.DoesNotExist

        if article.deleted:
            messages.error(request, '该文章已被删除，无法评论')
            return redirect('comment:comment_list', article_index_id=article_index_id, page=1)

    except Article.DoesNotExist:
        return render(request, '404.html', status=404)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.article_index_id = article_index_id
            comment.author = request.user
            comment.save()
            messages.success(request, '评论发布成功')
            return redirect('comment:comment_list', article_index_id=article_index_id, page=1)
    else:
        form = CommentForm()

    context = {
        'form': form,
        'article': article,
    }
    return render(request, 'comment_create.html', context)


@login_required
def comment_update(request, comment_index_id):
    try:
        old_comment = Comment.objects.filter(
            index_id=comment_index_id
        ).order_by('-update_time').first()

        if not old_comment:
            raise Comment.DoesNotExist

        if old_comment.deleted:
            messages.error(request, '该评论已被删除')
            return redirect('comment:comment_list', article_index_id=old_comment.article_index_id, page=1)

        if old_comment.author != request.user and not request.user.is_staff:
            messages.error(request, '您没有权限修改这条评论')
            return redirect('comment:comment_list', article_index_id=old_comment.article_index_id, page=1)

    except Comment.DoesNotExist:
        return render(request, '404.html', status=404)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.index_id = old_comment.index_id
            comment.article_index_id = old_comment.article_index_id
            comment.author = old_comment.author
            comment.top = old_comment.top
            comment.hidden = old_comment.hidden
            comment.save()
            messages.success(request, '评论修改成功')
            return redirect('comment:comment_list', article_index_id=old_comment.article_index_id, page=1)
    else:
        form = CommentForm(initial={'content': old_comment.content})

    context = {
        'form': form,
        'comment': old_comment,
    }
    return render(request, 'comment_update.html', context)


@login_required
def comment_delete(request, comment_index_id):
    try:
        comment = Comment.objects.filter(
            index_id=comment_index_id
        ).order_by('-update_time').first()

        if not comment:
            raise Comment.DoesNotExist

        if comment.deleted:
            messages.error(request, '该评论已被删除')
            return redirect('comment:comment_list', article_index_id=comment.article_index_id, page=1)

        if comment.author != request.user and not request.user.is_staff:
            messages.error(request, '您没有权限删除这条评论')
            return redirect('comment:comment_list', article_index_id=comment.article_index_id, page=1)

    except Comment.DoesNotExist:
        return render(request, '404.html', status=404)

    if request.method == 'POST':
        Comment.objects.filter(index_id=comment_index_id).update(deleted=True)
        messages.success(request, '评论已删除')
        return redirect('comment:comment_list', article_index_id=comment.article_index_id, page=1)

    context = {
        'comment': comment,
    }
    return render(request, 'comment_delete_confirm.html', context)
