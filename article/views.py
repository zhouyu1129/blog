import os
import re

import markdown

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Max
from django.shortcuts import render, redirect
from .forms import ArticleForm
from .models import Article, Image, ImageQuote


def article_list(request):
    """
    文章列表视图
    """
    search_query = request.GET.get('search', '')

    # 获取每个index_id的最新版本文章
    if search_query:
        # 先获取符合条件的所有文章
        all_articles = Article.objects.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query),
            deleted=False
        )

        # 按index_id分组，获取每个index_id的最新版本
        latest_articles = {}
        for article in all_articles:
            if article.index_id not in latest_articles or article.updated_at > latest_articles[
                article.index_id].updated_at:
                latest_articles[article.index_id] = article

        articles = list(latest_articles.values())
        # 按更新时间排序
        articles.sort(key=lambda x: x.updated_at, reverse=True)
    else:
        # 获取所有未删除文章的最新版本
        subquery = Article.objects.filter(
            deleted=False
        ).values('index_id').annotate(
            max_updated=Max('updated_at')
        )

        articles = Article.objects.filter(
            deleted=False,
            updated_at__in=[item['max_updated'] for item in subquery]
        ).order_by('-updated_at')

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

        # 调试信息：检查请求中是否包含文件
        if 'images' in request.FILES:
            uploaded_images = request.FILES.getlist('images')
            print(f"检测到 {len(uploaded_images)} 个上传的图片文件")
        else:
            print("未检测到上传的图片文件")

        if form.is_valid():
            article = form.save(commit=False)
            article.author_id = request.user
            article.save()  # 保存以获取自动生成的index_id

            # 处理上传的图片
            uploaded_images = request.FILES.getlist('images')
            image_map = {}  # 存储图片ID和对应的Image对象
            temp_images = []  # 存储所有创建的图片对象，用于后续清理

            # 确保媒体目录存在
            media_root = settings.MEDIA_ROOT
            images_dir = os.path.join(media_root, 'images')
            os.makedirs(images_dir, exist_ok=True)

            # 先创建所有上传的图片对象，但先不创建ImageQuote关系
            for idx, img_file in enumerate(uploaded_images):
                # 使用简单的顺序ID（从1开始）
                img_id = str(idx + 1)

                print(f"处理第 {idx + 1} 个图片文件: {img_file.name}, 分配ID: {img_id}")

                # 创建Image对象并保存
                image = Image.objects.create(
                    title=f"图片_{img_id}",
                    content=img_file,
                    author_id=request.user
                )

                print(f"已创建Image对象，ID: {image.id}, 文件路径: {image.content.path}")

                image_map[img_id] = image
                temp_images.append((img_id, image))

            # 分析文章内容，找出哪些图片ID被引用
            content = article.content
            referenced_img_ids = set()

            # 查找所有[[img_id=数字]]模式
            img_matches = re.findall(r'\[\[img_id=(\d+)]]', content)
            referenced_img_ids.update(img_matches)

            print(f"文章中引用的图片ID: {referenced_img_ids}")

            # 只为被引用的图片创建ImageQuote关系
            for img_id, image in temp_images:
                if img_id in referenced_img_ids:
                    # 创建ImageQuote关系
                    ImageQuote.objects.create(
                        article=article,
                        image=image
                    )
                    print(f"已为被引用的图片创建ImageQuote关系: {img_id}")
                else:
                    # 删除未被引用的图片
                    print(f"删除未被引用的图片: {img_id}")
                    # 删除图片文件
                    if image.content and image.content.name:
                        try:
                            file_path = os.path.join(settings.MEDIA_ROOT, image.content.name)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                print(f"已删除图片文件: {file_path}")
                        except Exception as e:
                            print(f"删除图片文件时出错: {e}")
                    
                    # 删除Image对象
                    image.delete()
                    print(f"已删除Image对象: {img_id}")

            # 处理文章内容中的图片引用
            content = article.content
            # 使用正则表达式查找[[img_id=id]]模式
            # 先处理转义字符
            content = content.replace(r'\[', '[ESCAPED_LEFT_BRACKET]')
            content = content.replace(r'\]', '[ESCAPED_RIGHT_BRACKET]')

            # 查找并替换图片引用
            def replace_img_reference(match):
                img_id = match.group(1)
                if img_id in image_map:
                    image = image_map[img_id]
                    # 使用Django的url属性获取正确的URL
                    image_url = image.content.url
                    print(f"Django生成的图片URL: {image_url}")

                    return f'![{image.title}]({image_url})'
                return match.group(0)  # 如果找不到对应图片，保持原样

            content = re.sub(r'\[\[img_id=(\d+)]]', replace_img_reference, content)

            # 恢复转义字符
            content = content.replace('[ESCAPED_LEFT_BRACKET]', '[')
            content = content.replace('[ESCAPED_RIGHT_BRACKET]', ']')
            print(content)

            # 更新文章内容
            article.content = content
            article.save()

            messages.success(request, '文章创建成功！')
            return redirect('article:article_detail', pk=article.index_id)
        else:
            # 如果表单无效，打印错误信息
            print("表单验证失败:")
            print(form.errors)
    else:
        form = ArticleForm()

    return render(request, 'create.html', {'form': form})


def article_detail(request, pk):
    """
    文章详情视图
    """
    # 使用index_id获取文章的最新版本
    try:
        article = Article.objects.filter(
            index_id=pk,
            deleted=False
        ).order_by('-updated_at').first()

        if not article:
            raise Article.DoesNotExist
    except Article.DoesNotExist:
        return render(request, '404.html', status=404)

    # 获取与文章相关的文件和图片（通过多对多关系）
    files = article.files.all()
    images = article.images.all()

    # 创建图片ID到图片对象的映射
    image_map = {}
    for idx, image in enumerate(images, 1):
        image_map[str(idx)] = image

    # 处理文章内容中的图片引用
    content = article.content

    # 查找并替换图片引用
    def replace_img_reference(match):
        img_id = match.group(1)
        print('img_id', img_id)
        if img_id in image_map:
            image = image_map[img_id]

            # 使用Django的url属性获取正确的URL
            image_url = image.content.url
            print(f"Django生成的图片URL: {image_url}")

            return f'![{image.title}]({image_url})'
        return match.group(0)  # 如果找不到对应图片，保持原样

    content = re.sub(r'\[\[img_id=(\d+)]]', replace_img_reference, content)
    print('content', content)

    # 将Markdown内容转换为HTML
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
        'markdown.extensions.sane_lists',
        'markdown.extensions.nl2br',
    ])
    article.content_html = md.convert(content)
    article.toc = md.toc

    context = {
        'article': article,
        'files': files,
        'images': images,
    }
    return render(request, 'detail.html', context)
