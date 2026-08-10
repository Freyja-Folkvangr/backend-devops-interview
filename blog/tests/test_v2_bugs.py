import json

from django.test import TestCase

from blog.models import Comment, Post, Tag, User

# The v2 endpoints CORRECT the eight quirks that v1 preserves (issues #2-#9).
# v1's behavior stays pinned in the other test modules; here we assert the fixes.


class V2FixedBehaviorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(
            username="alice", email="alice@example.com", display_name="Alice"
        )
        cls.tag = Tag.objects.create(name="Python", slug="python")
        cls.post = Post.objects.create(author=cls.author, title="Published", body="hello")
        cls.post.tags.add(cls.tag)
        cls.draft = Post.objects.create(
            author=cls.author, title="Draft", body="secret", is_published=False
        )

    def _post_json(self, path, payload):
        return self.client.post(path, data=json.dumps(payload), content_type="application/json")

    # Refs #3: detail hides drafts
    def test_detail_returns_404_for_draft(self):
        self.assertEqual(self.client.get(f"/api/v2/posts/{self.draft.id}").status_code, 404)

    def test_detail_returns_published(self):
        resp = self.client.get(f"/api/v2/posts/{self.post.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Published")

    # Refs #2: view_count increments atomically without bumping updated_at
    def test_detail_increments_view_count_without_bumping_updated_at(self):
        first = self.client.get(f"/api/v2/posts/{self.post.id}").json()
        second = self.client.get(f"/api/v2/posts/{self.post.id}").json()
        self.assertEqual(second["view_count"], first["view_count"] + 1)
        self.assertEqual(second["updated_at"], first["updated_at"])

    # Refs #4: unknown tag -> 404 and the post is NOT persisted (atomic)
    def test_create_post_unknown_tag_404_and_not_persisted(self):
        payload = {
            "author_id": self.author.id,
            "title": "Orphan",
            "body": "b",
            "tag_slugs": ["nope"],
        }
        resp = self._post_json("/api/v2/posts", payload)
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(Post.objects.filter(title="Orphan").exists())

    def test_create_post_ok_returns_201(self):
        payload = {
            "author_id": self.author.id,
            "title": "Fresh",
            "body": "b",
            "tag_slugs": ["python"],
        }
        resp = self._post_json("/api/v2/posts", payload)
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(Post.objects.filter(title="Fresh").exists())

    def test_create_post_unknown_author_404(self):
        resp = self._post_json("/api/v2/posts", {"author_id": 99999, "title": "X", "body": "b"})
        self.assertEqual(resp.status_code, 404)

    # Refs #8: cannot comment on a draft
    def test_comment_on_draft_returns_404(self):
        resp = self._post_json(
            f"/api/v2/posts/{self.draft.id}/comments", {"author_id": self.author.id, "body": "x"}
        )
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(Comment.objects.filter(post=self.draft).exists())

    def test_comment_on_published_returns_201(self):
        resp = self._post_json(
            f"/api/v2/posts/{self.post.id}/comments", {"author_id": self.author.id, "body": "nice"}
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(Comment.objects.filter(post=self.post, body="nice").exists())

    # Refs #7: user counts exclude unpublished content
    def test_user_counts_exclude_unpublished(self):
        Comment.objects.create(post=self.post, author=self.author, body="c-pub")
        Comment.objects.create(post=self.draft, author=self.author, body="c-draft")
        data = self.client.get(f"/api/v2/users/{self.author.id}").json()
        self.assertEqual(data["post_count"], 1)
        self.assertEqual(data["comment_count"], 1)

    # Refs #5: duplicate email -> first match, no 500
    def test_find_user_duplicate_email_returns_first(self):
        User.objects.create(username="alice2", email="alice@example.com", display_name="Alice2")
        resp = self.client.get("/api/v2/users/find", {"email": "alice@example.com"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["username"], "alice")

    def test_find_user_unknown_404(self):
        resp = self.client.get("/api/v2/users/find", {"email": "nobody@example.com"})
        self.assertEqual(resp.status_code, 404)

    # Refs #6: empty or missing q -> 422
    def test_search_empty_q_returns_422(self):
        self.assertEqual(self.client.get("/api/v2/posts/search", {"q": ""}).status_code, 422)

    def test_search_missing_q_returns_422(self):
        self.assertEqual(self.client.get("/api/v2/posts/search").status_code, 422)
