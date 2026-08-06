from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from blog.models import Post, Tag, User


class V2PostsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username="a", email="a@e.com", display_name="A")
        cls.tag = Tag.objects.create(name="Python", slug="python")
        base = timezone.now()
        for i in range(25):
            p = Post.objects.create(
                author=cls.author,
                title=f"post {i:02d}",
                body=f"body {i} keyword",
                created_at=base - timedelta(minutes=i),
            )
            p.tags.add(cls.tag)
        cls.draft = Post.objects.create(
            author=cls.author, title="draft", body="x keyword", is_published=False
        )
        cls.draft.tags.add(cls.tag)

    def test_envelope_and_default_limit(self):
        data = self.client.get("/api/v2/posts").json()
        self.assertEqual(set(data.keys()), {"items", "count"})
        self.assertEqual(data["count"], 25)  # published only
        self.assertEqual(len(data["items"]), 20)  # NINJA_PAGINATION_PER_PAGE

    def test_item_shape_matches_v1(self):
        item = self.client.get("/api/v2/posts").json()["items"][0]
        self.assertEqual(
            set(item.keys()), {"id", "title", "author", "tags", "view_count", "created_at"}
        )
        self.assertEqual(set(item["author"].keys()), {"id", "username", "display_name"})

    def test_limit_and_offset_no_overlap(self):
        page1 = self.client.get("/api/v2/posts", {"limit": 5, "offset": 0}).json()["items"]
        page2 = self.client.get("/api/v2/posts", {"limit": 5, "offset": 5}).json()["items"]
        self.assertEqual(len(page1), 5)
        self.assertEqual(len(page2), 5)
        self.assertEqual(set(p["id"] for p in page1) & set(p["id"] for p in page2), set())

    def test_deterministic_order_newest_first(self):
        titles = [
            p["title"] for p in self.client.get("/api/v2/posts", {"limit": 3}).json()["items"]
        ]
        self.assertEqual(titles, ["post 00", "post 01", "post 02"])

    def test_excludes_unpublished(self):
        titles = [
            p["title"] for p in self.client.get("/api/v2/posts", {"limit": 100}).json()["items"]
        ]
        self.assertNotIn("draft", titles)

    def test_limit_over_max_is_rejected(self):
        self.assertEqual(self.client.get("/api/v2/posts", {"limit": 1000}).status_code, 422)

    def test_search_paginated(self):
        data = self.client.get("/api/v2/posts/search", {"q": "keyword", "limit": 10}).json()
        self.assertEqual(data["count"], 25)
        self.assertEqual(len(data["items"]), 10)

    def test_by_tag_paginated(self):
        data = self.client.get("/api/v2/posts/by-tag/python", {"limit": 10}).json()
        self.assertEqual(data["count"], 25)
        self.assertEqual(len(data["items"]), 10)

    def test_by_tag_unknown_slug_404(self):
        self.assertEqual(self.client.get("/api/v2/posts/by-tag/nope").status_code, 404)

    def test_query_count_is_constant(self):
        with self.assertNumQueries(3):
            self.client.get("/api/v2/posts", {"limit": 10})
