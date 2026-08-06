from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from blog import usecases
from blog.models import Tag
from blog.schemas import PostListOut

router = Router()


@router.get("/posts", response=list[PostListOut])
@paginate(LimitOffsetPagination)
def list_posts(request):
    return usecases.published_posts()


@router.get("/posts/search", response=list[PostListOut])
@paginate(LimitOffsetPagination)
def search_posts(request, q: str):
    return usecases.search_published_posts(q)


@router.get("/posts/by-tag/{slug}", response=list[PostListOut])
@paginate(LimitOffsetPagination)
def posts_by_tag(request, slug: str):
    tag = get_object_or_404(Tag, slug=slug)
    return usecases.published_posts_for_tag(tag)
