import json

from django.test import TestCase
from django.urls import reverse

from blog.models import Comment, Post, User


class CommentEndpointsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="bob", email="bob@example.com", display_name="Bob")
        cls.post = Post.objects.create(author=cls.user, title="T", body="B")
        cls.draft = Post.objects.create(author=cls.user, title="D", body="B", is_published=False)

    def _post_comment(self, post_id, author_id, body):
        return self.client.post(
            reverse("api-1.0.0:create_comment", args=[post_id]),
            data=json.dumps({"author_id": author_id, "body": body}),
            content_type="application/json",
        )

    def test_create_comment_ok(self):
        resp = self._post_comment(self.post.id, self.user.id, "Nice post!")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.json().keys()), {"id"})
        self.assertTrue(Comment.objects.filter(post=self.post, body="Nice post!").exists())

    def test_create_comment_unknown_post_404(self):
        self.assertEqual(self._post_comment(99999, self.user.id, "x").status_code, 404)

    def test_create_comment_unknown_author_404(self):
        self.assertEqual(self._post_comment(self.post.id, 99999, "x").status_code, 404)

    def test_create_comment_on_unpublished_post_allowed(self):
        # Refs #8 (intentional): no is_published check on the target post
        resp = self._post_comment(self.draft.id, self.user.id, "on a draft")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Comment.objects.filter(post=self.draft, body="on a draft").exists())
