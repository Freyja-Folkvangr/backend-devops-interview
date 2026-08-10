from django.db.models import F, Q

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


def bump_view_count(post):
    """Refs #2: atomic increment that avoids the read-modify-write race and does
    not bump updated_at (a queryset .update() does not fire auto_now)."""
    Post.objects.filter(pk=post.pk).update(view_count=F("view_count") + 1)
    post.refresh_from_db(fields=["view_count"])


def user_detail(user):
    """Refs #7: counts only cover published content, consistent with the list
    endpoints (v1 counts everything)."""
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "bio": user.bio,
        "post_count": user.posts.filter(is_published=True).count(),
        "comment_count": user.comments.filter(post__is_published=True).count(),
    }
