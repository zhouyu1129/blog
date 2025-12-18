from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
import markdown
from .models import Article, File, Image
from .forms import ArticleForm


def article_list(request):
    """
    文章列表视图
    """
    search_query = request.GET.get('search', '')
    
    if search_query:
        articles = Article.objects.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query)
        ).order_by('-created_at')
    else:
        articles = Article.objects.all().order_by('-created_at')
    
    # 为每篇文章生成Markdown摘要
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.sane_lists',
        'markdown.extensions.nl2br',
    ])
    
    for article in articles:
        # 获取前200个字符作为摘要
        content_preview = article.content[:200] + '...' if len(article.content) > 200 else article.content
        article.content_preview = md.convert(content_preview)
    
    # 分页处理
    paginator = Paginator(articles, 10)  # 每页显示10篇文章
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'list.html', context)


@login_required
def article_create(request):
    """
    文章创建视图
    """
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            article.author_id = request.user
            article.save()
            messages.success(request, '文章创建成功！')
            return redirect('article:article_detail', pk=article.pk)
    else:
        form = ArticleForm()
    
    return render(request, 'create.html', {'form': form})


def article_detail(request, pk):
    """
    文章详情视图
    """
    article = get_object_or_404(Article, pk=pk)
    
    # 将Markdown内容转换为HTML
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
        'markdown.extensions.sane_lists',
        'markdown.extensions.nl2br',
    ])
    article.content_html = md.convert(article.content)
    article.toc = md.toc
    
    # 获取与文章相关的文件和图片
    files = File.objects.filter(article_id=article)
    images = Image.objects.filter(article_id=article)
    
    context = {
        'article': article,
        'files': files,
        'images': images,
    }
    return render(request, 'detail.html', context)
