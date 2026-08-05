from django.test import TestCase

from blog.models import Comment, Post, Tag, User

# These assert the query count is CONSTANT regardless of row count, proving the
# N+1 access on author/tags/comment-author is gone. They accompany the perf
# refactor (they assert the target, not the pre-refactor N+1).


class QueryCountTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tags = [Tag.objects.create(name=f"t{i}", slug=f"t{i}") for i in range(3)]
        cls.authors = [
            User.objects.create(username=f"u{i}", email=f"u{i}@e.com", display_name=f"U{i}")
            for i in range(5)
        ]
        cls.posts = []
        for i in range(5):
            p = Post.objects.create(author=cls.authors[i], title=f"p{i}", body="body")
            p.tags.add(cls.tags[i % 3], cls.tags[(i + 1) % 3])
            cls.posts.append(p)

    def test_list_posts_query_count_is_constant(self):
        with self.assertNumQueries(2):
            self.client.get("/api/posts")

    def test_search_query_count_is_constant(self):
        with self.assertNumQueries(2):
            self.client.get("/api/posts/search", {"q": "body"})

    def test_by_tag_query_count_is_constant(self):
        with self.assertNumQueries(3):
            self.client.get(f"/api/posts/by-tag/{self.tags[0].slug}")

    def test_get_post_query_count_constant_regardless_of_comments(self):
        post = self.posts[0]
        for i, author in enumerate(self.authors):
            Comment.objects.create(post=post, author=author, body=f"c{i}")
        with self.assertNumQueries(5):
            self.client.get(f"/api/posts/{post.id}")
