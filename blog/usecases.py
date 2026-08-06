from django.db.models import Q

from blog.models import Post, Tag


def published_posts():
    """Published posts, newest first, with a deterministic total order and the
    author/tags joined so serialization stays O(1) in queries."""
    return (
        Post.objects.filter(is_published=True)
        .select_related("author")
        .prefetch_related("tags")
        .order_by("-created_at", "-id")
    )


def search_published_posts(q):
    return published_posts().filter(Q(title__icontains=q) | Q(body__icontains=q))


def published_posts_for_tag(tag: Tag):
    return published_posts().filter(tags=tag)
