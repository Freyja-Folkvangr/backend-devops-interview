import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from blog.models import Comment, Post, Tag, User

# Note: the nondeterministic tie-break on equal created_at is documented in
# issue #9 (not pinned here: asserting an arbitrary order would be flaky).


class PostEndpointsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(
            username="alice", email="alice@example.com", display_name="Alice"
        )
        cls.tag_py = Tag.objects.create(name="Python", slug="python")
        cls.tag_dj = Tag.objects.create(name="Django", slug="django")

        base = timezone.now()
        cls.older = Post.objects.create(
            author=cls.author,
            title="Older published",
            body="hello world alpha",
            created_at=base - timedelta(hours=2),
        )
        cls.older.tags.add(cls.tag_py)
        cls.newer = Post.objects.create(
            author=cls.author,
            title="Newer published",
            body="hello world beta",
            created_at=base - timedelta(hours=1),
        )
        cls.newer.tags.add(cls.tag_py, cls.tag_dj)
        cls.draft = Post.objects.create(
            author=cls.author,
            title="Secret draft",
            body="unpublished body",
            is_published=False,
            created_at=base,
        )
        cls.draft.tags.add(cls.tag_dj)

    def test_list_returns_only_published_newest_first(self):
        resp = self.client.get(reverse("api-1.0.0:list_posts"))
        self.assertEqual(resp.status_code, 200)
        titles = [p["title"] for p in resp.json()]
        self.assertEqual(titles, ["Newer published", "Older published"])

    def test_list_item_shape(self):
        item = self.client.get(reverse("api-1.0.0:list_posts")).json()[0]
        self.assertEqual(
            set(item.keys()),
            {"id", "title", "author", "tags", "view_count", "created_at"},
        )
        self.assertEqual(set(item["author"].keys()), {"id", "username", "display_name"})
        self.assertEqual(set(item["tags"][0].keys()), {"id", "name", "slug"})

    def test_list_empty_returns_empty_list(self):
        Post.objects.all().delete()
        self.assertEqual(self.client.get(reverse("api-1.0.0:list_posts")).json(), [])

    def test_search_matches_title_and_body_case_insensitive(self):
        url = reverse("api-1.0.0:search_posts")
        self.assertEqual(
            [p["title"] for p in self.client.get(url, {"q": "BETA"}).json()],
            ["Newer published"],
        )
        self.assertEqual(
            [p["title"] for p in self.client.get(url, {"q": "published"}).json()],
            ["Newer published", "Older published"],
        )

    def test_search_excludes_unpublished(self):
        # "unpublished" only appears in the draft body, which must be filtered out
        url = reverse("api-1.0.0:search_posts")
        self.assertEqual(self.client.get(url, {"q": "unpublished"}).json(), [])

    def test_search_empty_q_returns_all_published(self):
        # Refs #6 (intentional): empty q -> ILIKE '%%' matches every published post
        url = reverse("api-1.0.0:search_posts")
        self.assertEqual(
            [p["title"] for p in self.client.get(url, {"q": ""}).json()],
            ["Newer published", "Older published"],
        )

    def test_search_missing_q_returns_422(self):
        self.assertEqual(self.client.get(reverse("api-1.0.0:search_posts")).status_code, 422)

    def test_by_tag_returns_published_newest_first(self):
        resp = self.client.get(reverse("api-1.0.0:posts_by_tag", args=["python"]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([p["title"] for p in resp.json()], ["Newer published", "Older published"])

    def test_by_tag_excludes_unpublished(self):
        # the draft carries the "django" tag but must not appear
        resp = self.client.get(reverse("api-1.0.0:posts_by_tag", args=["django"]))
        self.assertEqual([p["title"] for p in resp.json()], ["Newer published"])

    def test_by_tag_unknown_slug_404(self):
        resp = self.client.get(reverse("api-1.0.0:posts_by_tag", args=["nope"]))
        self.assertEqual(resp.status_code, 404)

    def test_get_post_detail_shape_and_comment_order(self):
        Comment.objects.create(
            post=self.newer,
            author=self.author,
            body="first",
            created_at=timezone.now() - timedelta(minutes=5),
        )
        Comment.objects.create(
            post=self.newer, author=self.author, body="second", created_at=timezone.now()
        )
        data = self.client.get(reverse("api-1.0.0:get_post", args=[self.newer.id])).json()
        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "title",
                "body",
                "author",
                "tags",
                "comments",
                "view_count",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual([c["body"] for c in data["comments"]], ["first", "second"])

    def test_get_post_increments_view_count_each_call(self):
        # Refs #2 (intentional): GET is non-idempotent
        url = reverse("api-1.0.0:get_post", args=[self.newer.id])
        first = self.client.get(url).json()["view_count"]
        second = self.client.get(url).json()["view_count"]
        self.assertEqual((first, second), (1, 2))

    def test_get_post_returns_unpublished_draft(self):
        # Refs #3 (intentional): detail has no is_published filter
        resp = self.client.get(reverse("api-1.0.0:get_post", args=[self.draft.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Secret draft")

    def test_get_post_unknown_id_404(self):
        resp = self.client.get(reverse("api-1.0.0:get_post", args=[99999]))
        self.assertEqual(resp.status_code, 404)

    def test_create_post_returns_id_and_title(self):
        payload = {
            "author_id": self.author.id,
            "title": "Fresh",
            "body": "b",
            "tag_slugs": ["python"],
        }
        resp = self.client.post(
            reverse("api-1.0.0:create_post"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(set(data.keys()), {"id", "title"})
        self.assertTrue(Post.objects.filter(id=data["id"], title="Fresh").exists())

    def test_create_post_unknown_author_404(self):
        resp = self.client.post(
            reverse("api-1.0.0:create_post"),
            data=json.dumps({"author_id": 99999, "title": "X", "body": "b"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_create_post_unknown_tag_raises_and_orphans_post(self):
        # Refs #4 (intentional): bare Tag.objects.get raises DoesNotExist (500) and
        # the post is already persisted (non-atomic partial write).
        payload = {
            "author_id": self.author.id,
            "title": "Orphan",
            "body": "b",
            "tag_slugs": ["does-not-exist"],
        }
        with self.assertRaises(Tag.DoesNotExist):
            self.client.post(
                reverse("api-1.0.0:create_post"),
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertTrue(Post.objects.filter(title="Orphan").exists())
