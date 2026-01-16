import os
import re
import shutil
import json

import markdown

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Max
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .forms import ArticleForm
from .models import Article, Image, ImageQuote, File, FileQuote, TemporaryFile


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
            deleted=False,
            hidden=False
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
        # 获取所有未删除且未隐藏文章的最新版本
        subquery = Article.objects.filter(
            deleted=False,
            hidden=False
        ).values('index_id').annotate(
            max_updated=Max('updated_at')
        )

        articles = Article.objects.filter(
            deleted=False,
            hidden=False,
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
def upload_file(request):
    """
    文件上传视图（AJAX）
    """
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        # 检查文件大小（100MB限制）
        if uploaded_file.size > 100 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'error': '文件大小超过100MB限制'
            }, status=400)
        
        try:
            # 创建临时文件记录
            temp_file = TemporaryFile.objects.create(
                file=uploaded_file,
                filename=uploaded_file.name,
                file_size=uploaded_file.size,
                author_id=request.user
            )
            
            # 返回文件信息
            return JsonResponse({
                'success': True,
                'file_id': str(temp_file.id),
                'filename': temp_file.filename,
                'file_size': temp_file.file_size,
                'file_url': temp_file.file.url
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'文件上传失败: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': '无效的请求'
    }, status=400)


@login_required
def delete_temp_file(request, file_id):
    """
    删除临时文件视图（AJAX）
    """
    # 检查是否是DELETE请求（直接或通过POST模拟）
    if request.method == 'DELETE' or (request.method == 'POST' and request.POST.get('_method') == 'DELETE'):
        try:
            temp_file = TemporaryFile.objects.get(id=file_id, author_id=request.user)
            
            # 删除文件
            if temp_file.file and temp_file.file.name:
                file_path = os.path.join(settings.MEDIA_ROOT, temp_file.file.name)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # 删除数据库记录
            temp_file.delete()
            
            return JsonResponse({'success': True})
        except TemporaryFile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '文件不存在或无权限删除'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'删除文件失败: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': '无效的请求'
    }, status=400)


@login_required
def get_temp_files(request):
    """
    获取用户的临时文件列表（AJAX）
    """
    if request.method == 'GET':
        try:
            temp_files = TemporaryFile.objects.filter(author_id=request.user)
            
            files_data = []
            for temp_file in temp_files:
                files_data.append({
                    'file_id': str(temp_file.id),
                    'filename': temp_file.filename,
                    'file_size': temp_file.file_size,
                    'file_url': temp_file.file.url,
                    'created_at': temp_file.created_at.isoformat()
                })
            
            return JsonResponse({
                'success': True,
                'files': files_data
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'获取文件列表失败: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': '无效的请求'
    }, status=400)


@login_required
def article_create(request):
    """
    文章创建视图
    """
    # 获取用户的临时文件
    temp_files = TemporaryFile.objects.filter(author_id=request.user)
    
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

            # 获取前端传递的图片ID映射
            image_id_mapping = []
            if 'image_id_mapping' in request.POST:
                try:
                    image_id_mapping = json.loads(request.POST.get('image_id_mapping', '[]'))
                    print(f"前端传递的图片ID映射: {image_id_mapping}")
                except json.JSONDecodeError:
                    print("解析图片ID映射失败")

            # 创建前端ID到后端连续ID的映射
            frontend_to_backend_id = {}
            for idx, frontend_id in enumerate(image_id_mapping):
                backend_id = str(idx + 1)
                frontend_to_backend_id[str(frontend_id)] = backend_id
                print(f"ID映射: 前端 {frontend_id} -> 后端 {backend_id}")

            # 确保媒体目录存在
            media_root = settings.MEDIA_ROOT
            images_dir = os.path.join(media_root, 'images')
            os.makedirs(images_dir, exist_ok=True)

            # 先创建所有上传的图片对象，使用连续的后端ID
            for idx, img_file in enumerate(uploaded_images):
                # 使用连续的后端ID（从1开始）
                img_id = str(idx + 1)

                print(f"处理第 {idx + 1} 个图片文件: {img_file.name}, 分配后端ID: {img_id}")

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

            # 将前端ID映射到后端连续ID
            backend_referenced_img_ids = set()
            for frontend_id in referenced_img_ids:
                if frontend_id in frontend_to_backend_id:
                    backend_id = frontend_to_backend_id[frontend_id]
                    backend_referenced_img_ids.add(backend_id)
                    print(f"引用ID映射: 前端 {frontend_id} -> 后端 {backend_id}")

            # 只为被引用的图片创建ImageQuote关系
            for img_id, image in temp_images:
                if img_id in backend_referenced_img_ids:
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

            # 查找并替换图片引用，将前端ID替换为后端连续ID
            def replace_img_reference(match):
                frontend_id = match.group(1)
                if frontend_id in frontend_to_backend_id:
                    backend_id = frontend_to_backend_id[frontend_id]
                    if backend_id in image_map:
                        image = image_map[backend_id]
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
            
            # 处理临时文件，将其转换为正式文件并与文章关联
            selected_file_ids = request.POST.getlist('selected_files')
            print(f"选中的文件ID: {selected_file_ids}")
            
            for file_id in selected_file_ids:
                try:
                    temp_file = TemporaryFile.objects.get(id=file_id, author_id=request.user)
                    print(f"处理临时文件: {temp_file.filename}, ID: {temp_file.id}")
                    
                    # 确保文件目录存在
                    files_dir = os.path.join(settings.MEDIA_ROOT, 'files')
                    os.makedirs(files_dir, exist_ok=True)
                    
                    # 确保文件目录存在
                    files_dir = os.path.join(settings.MEDIA_ROOT, 'files')
                    os.makedirs(files_dir, exist_ok=True)
                    
                    # 获取临时文件路径
                    temp_file_path = temp_file.file.path
                    
                    # 先创建正式文件记录（使用临时文件的路径，稍后会移动）
                    file = File.objects.create(
                        title=temp_file.filename,
                        content=temp_file.file.name,  # 暂时使用临时文件的路径
                        author_id=request.user
                    )
                    
                    # 创建新的文件名，使用File对象的ID确保唯一性
                    file_extension = os.path.splitext(temp_file.filename)[1]
                    new_filename = f"{file.id}{file_extension}"
                    new_file_path = os.path.join(files_dir, new_filename)
                    
                    # 移动文件到正式目录
                    shutil.move(temp_file_path, new_file_path)
                    
                    # 更新File对象的content字段，指向新的文件路径
                    file.content = f"files/{new_filename}"
                    file.save()
                    
                    print(f"已创建正式文件: {file.title}, ID: {file.id}, 路径: {file.content.path}")
                    
                    # 创建文件与文章的关联
                    FileQuote.objects.create(
                        article=article,
                        file=file
                    )
                    
                    print(f"已创建文件与文章的关联")
                    
                    # 删除临时文件记录（但保留实际文件，因为File对象已经引用了它）
                    temp_file.delete()
                    print(f"已删除临时文件记录")
                except TemporaryFile.DoesNotExist:
                    print(f"临时文件不存在: {file_id}")
                    continue
                except Exception as e:
                    print(f"处理临时文件时出错: {file_id}, 错误: {str(e)}")
                    continue
            
            article.save()

            messages.success(request, '文章创建成功！')
            return redirect('article:article_detail', index_id=article.index_id)
        else:
            # 如果表单无效，打印错误信息
            print("表单验证失败:")
            print(form.errors)
    else:
        form = ArticleForm()

    return render(request, 'create.html', {'form': form, 'temp_files': temp_files})


def article_detail(request, index_id):
    """
    文章详情视图
    """
    # 使用index_id获取文章的最新版本
    try:
        article = Article.objects.filter(
            index_id=index_id
        ).order_by('-updated_at').first()

        if not article:
            raise Article.DoesNotExist

        # 检查文章是否已删除
        if article.deleted:
            return render(request, 'article_deleted.html', status=404)

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


@login_required
def article_update(request, index_id):
    """
    文章修改视图 - 创建新版本而不是直接修改
    """
    # 使用index_id获取文章的最新版本
    try:
        old_article = Article.objects.filter(
            index_id=index_id
        ).order_by('-updated_at').first()

        if not old_article:
            raise Article.DoesNotExist

        # 检查文章是否已删除
        if old_article.deleted:
            messages.error(request, '该文章已被删除，无法编辑')
            return redirect('article:article_list')

    except Article.DoesNotExist:
        return render(request, '404.html', status=404)

    # 验证用户是否为文章作者
    if old_article.author_id != request.user:
        messages.error(request, '您没有权限修改这篇文章')
        return redirect('article:article_detail', index_id=index_id)

    # 获取用户的临时文件
    temp_files = TemporaryFile.objects.filter(author_id=request.user)

    # 获取文章已有的文件
    existing_files = old_article.files.all()

    # 获取文章已有的图片
    existing_images = old_article.images.all()

    if request.method == 'POST':
        form = ArticleForm(request.POST)

        if form.is_valid():
            # 创建新版本文章，使用相同的index_id
            article = Article(
                index_id=old_article.index_id,
                title=form.cleaned_data['title'],
                content=form.cleaned_data['content'],
                author_id=request.user,
                hidden=old_article.hidden
            )
            article.save()

            # 复制原有的文件关联到新文章
            for file_quote in FileQuote.objects.filter(article=old_article):
                FileQuote.objects.create(
                    article=article,
                    file=file_quote.file
                )

            # 复制原有的图片关联到新文章
            for image_quote in ImageQuote.objects.filter(article=old_article):
                ImageQuote.objects.create(
                    article=article,
                    image=image_quote.image
                )

            # 处理上传的新图片
            uploaded_images = request.FILES.getlist('images')
            image_map = {}
            temp_images = []

            # 获取前端传递的图片ID映射
            image_id_mapping = []
            if 'image_id_mapping' in request.POST:
                try:
                    image_id_mapping = json.loads(request.POST.get('image_id_mapping', '[]'))
                    print(f"前端传递的图片ID映射: {image_id_mapping}")
                except json.JSONDecodeError:
                    print("解析图片ID映射失败")

            # 获取现有图片数量，用于新图片的ID
            existing_images_count = article.images.count()
            next_image_id = existing_images_count + 1

            # 创建前端ID到后端连续ID的映射
            frontend_to_backend_id = {}
            for idx, frontend_id in enumerate(image_id_mapping):
                backend_id = str(next_image_id + idx)
                frontend_to_backend_id[str(frontend_id)] = backend_id
                print(f"ID映射: 前端 {frontend_id} -> 后端 {backend_id}")

            # 确保媒体目录存在
            media_root = settings.MEDIA_ROOT
            images_dir = os.path.join(media_root, 'images')
            os.makedirs(images_dir, exist_ok=True)

            # 先创建所有上传的图片对象，使用连续的后端ID
            for idx, img_file in enumerate(uploaded_images):
                # 使用连续的后端ID
                img_id = str(next_image_id + idx)

                print(f"处理第 {idx + 1} 个图片文件: {img_file.name}, 分配后端ID: {img_id}")

                # 创建Image对象并保存
                image = Image.objects.create(
                    title=f"图片_{img_id}",
                    content=img_file,
                    author_id=request.user
                )

                print(f"已创建Image对象，ID: {image.id}")
                print(f"文件路径: {image.content.path}")
                print(f"文件名: {image.content.name}")
                print(f"文件URL: {image.content.url}")
                print(f"文件是否存在: {os.path.exists(image.content.path)}")

                image_map[img_id] = image
                temp_images.append((img_id, image))

            # 分析文章内容，找出哪些新图片ID被引用
            content = article.content
            referenced_img_ids = set()

            img_matches = re.findall(r'\[\[img_id=(\d+)]]', content)
            referenced_img_ids.update(img_matches)

            # 将前端ID映射到后端连续ID
            backend_referenced_img_ids = set()
            for frontend_id in referenced_img_ids:
                if frontend_id in frontend_to_backend_id:
                    backend_id = frontend_to_backend_id[frontend_id]
                    backend_referenced_img_ids.add(backend_id)
                    print(f"引用ID映射: 前端 {frontend_id} -> 后端 {backend_id}")

            # 只为被引用的新图片创建ImageQuote关系
            referenced_imgs = []
            for img_id, image in temp_images:
                if img_id in backend_referenced_img_ids:
                    ImageQuote.objects.create(
                        article=article,
                        image=image
                    )
                    print(img_id, '被引用', image.content.path)
                    referenced_imgs.append(image)
                else:
                    # 修复：使用Django的delete()方法删除文件和数据库记录
                    try:
                        # FileField.delete()会自动删除物理文件和数据库记录
                        image.content.delete(save=False)  # 先删除文件
                        image.delete()  # 再删除Image对象
                        print(f"已删除未被引用的图片: {image.title}")
                    except Exception as e:
                        print(f"删除图片文件时出错: {e}")
                        image.delete()  # 至少删除数据库记录

            # 处理已有图片的删除（只删除新文章中的关联，不删除图片文件本身）
            keep_image_ids = request.POST.getlist('keep_images')
            current_images = article.images.all()
            for image in current_images:
                if (str(image.id) not in keep_image_ids) and (image not in referenced_imgs or image not in image_map.values()):
                    # 只删除新文章中的关联，保留图片文件供其他版本使用
                    ImageQuote.objects.filter(article=article, image=image).delete()
                    print(f"已从新版本中移除图片: {image.title}")

            # 处理文章内容中的图片引用
            content = article.content
            content = content.replace(r'\[', '[ESCAPED_LEFT_BRACKET]')
            content = content.replace(r'\]', '[ESCAPED_RIGHT_BRACKET]')

            # 创建包含新旧图片的映射（注意：此时已删除的图片已经不在数据库中了，新图片已经关联）
            full_image_map = {}
            for idx, image in enumerate(article.images.all(), 1):
                full_image_map[str(idx)] = image
                print(f"已有图片映射: {idx} -> {image.title}, URL: {image.content.url}")

            for img_id, image in image_map.items():
                full_image_map[img_id] = image
                print(f"新图片映射: {img_id} -> {image.title}, URL: {image.content.url}")

            print(f"完整图片映射: {list(full_image_map.keys())}")

            def replace_img_reference(match):
                frontend_id = match.group(1)
                print(f"处理图片引用: {frontend_id}")
                # 先尝试使用前端ID映射
                if frontend_id in frontend_to_backend_id:
                    backend_id = frontend_to_backend_id[frontend_id]
                    print(f"前端ID {frontend_id} 映射到后端ID {backend_id}")
                    if backend_id in full_image_map:
                        image = full_image_map[backend_id]
                        image_url = image.content.url
                        print(f"找到图片: {image.title}, URL: {image_url}")
                        return f'![{image.title}]({image_url})'
                # 如果没有映射，直接使用ID查找
                if frontend_id in full_image_map:
                    image = full_image_map[frontend_id]
                    image_url = image.content.url
                    print(f"直接找到图片: {image.title}, URL: {image_url}")
                    return f'![{image.title}]({image_url})'
                # 如果找不到对应的图片，返回空字符串（删除该引用）
                print(f"警告：找不到ID为{frontend_id}的图片，删除该引用")
                return ''

            content = re.sub(r'\[\[img_id=(\d+)]]', replace_img_reference, content)
            content = content.replace('[ESCAPED_LEFT_BRACKET]', '[')
            content = content.replace('[ESCAPED_RIGHT_BRACKET]', ']')

            article.content = content

            # 处理临时文件，将其转换为正式文件并与文章关联
            selected_file_ids = request.POST.getlist('selected_files')

            for file_id in selected_file_ids:
                try:
                    temp_file = TemporaryFile.objects.get(id=file_id, author_id=request.user)

                    files_dir = os.path.join(settings.MEDIA_ROOT, 'files')
                    os.makedirs(files_dir, exist_ok=True)

                    # 修复：正确获取临时文件的物理路径
                    temp_file_path = temp_file.file.path if hasattr(temp_file.file, 'path') else None
                    if not temp_file_path or not os.path.exists(temp_file_path):
                        print(f"临时文件不存在或无法访问: {file_id}")
                        continue

                    file = File.objects.create(
                        title=temp_file.filename,
                        content=temp_file.file.name,
                        author_id=request.user
                    )

                    file_extension = os.path.splitext(temp_file.filename)[1]
                    new_filename = f"{file.id}{file_extension}"
                    new_file_path = os.path.join(files_dir, new_filename)

                    shutil.move(temp_file_path, new_file_path)

                    file.content = f"files/{new_filename}"
                    file.save()

                    FileQuote.objects.create(
                        article=article,
                        file=file
                    )

                    # 删除临时文件记录（物理文件已经移动了）
                    temp_file.delete()
                except TemporaryFile.DoesNotExist:
                    continue
                except Exception as e:
                    print(f"处理临时文件时出错: {file_id}, 错误: {str(e)}")
                    continue

            # 处理已有文件的删除（只删除新文章中的关联，不删除文件本身）
            keep_file_ids = request.POST.getlist('keep_files')
            current_files = article.files.all()
            for file in current_files:
                if str(file.id) not in keep_file_ids:
                    # 只删除新文章中的关联，保留文件供其他版本使用
                    FileQuote.objects.filter(article=article, file=file).delete()
                    print(f"已从新版本中移除文件: {file.title}")

            messages.success(request, '文章修改成功！新版本已创建')
            return redirect('article:article_detail', index_id=article.index_id)
        else:
            print("表单验证失败:")
            print(form.errors)
    else:
        # 将文章内容中的Markdown图片引用转换回[[img_id=X]]格式
        # 创建图片URL到ID的映射
        image_url_to_id = {}
        for idx, image in enumerate(existing_images, 1):
            image_url_to_id[image.content.url] = idx

        # 替换Markdown图片引用为[[img_id=X]]格式
        content = old_article.content

        def markdown_to_img_id(match):
            alt_text = match.group(1)
            url = match.group(2)
            if url in image_url_to_id:
                img_id = image_url_to_id[url]
                return f'[[img_id={img_id}]]'
            return match.group(0)

        content = re.sub(r'!\[([^]]*)]\(([^)]+)\)', markdown_to_img_id, content)

        # 更新form的初始值
        form = ArticleForm(initial={
            'title': old_article.title,
            'content': content
        })
    article = Article.objects.filter(
        index_id=index_id,
        deleted=False
    ).order_by('-updated_at').first()

    return render(request, 'edit.html', {
        'form': form,
        'article': article,
        'temp_files': temp_files,
        'existing_files': existing_files,
        'existing_images': existing_images
    })


@login_required
def article_delete(request, index_id):
    """
    文章删除视图 - 软删除所有版本
    """
    # 使用index_id获取文章的所有版本
    try:
        article = Article.objects.filter(
            index_id=index_id
        ).order_by('-updated_at').first()

        if not article:
            raise Article.DoesNotExist

        # 检查文章是否已删除
        if article.deleted:
            messages.error(request, '该文章已被删除')
            return redirect('article:article_list')

        # 验证用户权限：只有作者或管理员可以删除
        if article.author_id != request.user and not request.user.is_staff:
            messages.error(request, '您没有权限删除这篇文章')
            return redirect('article:article_detail', index_id=index_id)

    except Article.DoesNotExist:
        return render(request, '404.html', status=404)

    if request.method == 'POST':
        # 软删除所有版本
        Article.objects.filter(index_id=index_id).update(deleted=True)
        messages.success(request, '文章已删除')
        return redirect('article:article_list')

    return render(request, 'delete_confirm.html', {'article': article})
