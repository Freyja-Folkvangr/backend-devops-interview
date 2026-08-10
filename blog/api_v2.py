from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from blog import usecases
from blog.models import Comment, Post, Tag, User
from blog.schemas import (
    CommentCreateIn,
    CommentCreateOut,
    PostCreateIn,
    PostCreateOut,
    PostDetailOut,
    PostListOut,
    UserDetailOut,
)

router = Router()


@router.get("/posts", response=list[PostListOut], url_name="v2_list_posts")
@paginate(LimitOffsetPagination)
def list_posts(request):
    return usecases.published_posts()


@router.get("/posts/search", response=list[PostListOut], url_name="v2_search_posts")
@paginate(LimitOffsetPagination)
def search_posts(request, q: str = Query(..., min_length=1)):
    # Refs #6: an empty q is rejected (422) instead of matching every post.
    return usecases.search_published_posts(q)


@router.get("/posts/by-tag/{slug}", response=list[PostListOut], url_name="v2_posts_by_tag")
@paginate(LimitOffsetPagination)
def posts_by_tag(request, slug: str):
    tag = get_object_or_404(Tag, slug=slug)
    return usecases.published_posts_for_tag(tag)


@router.get("/posts/{post_id}", response=PostDetailOut, url_name="v2_get_post")
def get_post(request, post_id: int):
    # Refs #3: drafts are hidden (404). Refs #2: the view count is bumped
    # atomically without a full save, so updated_at is not touched and there is
    # no read-modify-write race.
    post = get_object_or_404(Post.objects.select_related("author"), id=post_id, is_published=True)
    usecases.bump_view_count(post)
    return {
        "id": post.id,
        "title": post.title,
        "body": post.body,
        "author": post.author,
        "tags": post.tags.all(),
        "comments": post.comments.select_related("author").order_by("created_at", "id"),
        "view_count": post.view_count,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }


@router.post("/posts", response={201: PostCreateOut}, url_name="v2_create_post")
def create_post(request, payload: PostCreateIn):
    # Refs #4: an unknown tag slug yields 404 (not 500), and the whole write is
    # atomic, so a bad slug never leaves an orphaned post behind.
    with transaction.atomic():
        author = get_object_or_404(User, id=payload.author_id)
        post = Post.objects.create(author=author, title=payload.title, body=payload.body)
        for slug in payload.tag_slugs:
            post.tags.add(get_object_or_404(Tag, slug=slug))
    return 201, {"id": post.id, "title": post.title}


@router.post(
    "/posts/{post_id}/comments", response={201: CommentCreateOut}, url_name="v2_create_comment"
)
def create_comment(request, post_id: int, payload: CommentCreateIn):
    # Refs #8: comments can only be added to published posts.
    post = get_object_or_404(Post, id=post_id, is_published=True)
    author = get_object_or_404(User, id=payload.author_id)
    comment = Comment.objects.create(post=post, author=author, body=payload.body)
    return 201, {"id": comment.id}


@router.get("/users/find", response=UserDetailOut, url_name="v2_find_user")
def find_user_by_email(request, email: str):
    # Refs #5: duplicate emails resolve to the first match instead of a 500.
    user = User.objects.filter(email=email).order_by("id").first()
    if user is None:
        raise Http404("User not found")
    return usecases.user_detail(user)


@router.get("/users/{user_id}", response=UserDetailOut, url_name="v2_get_user")
def get_user(request, user_id: int):
    return usecases.user_detail(get_object_or_404(User, id=user_id))
