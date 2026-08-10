from django.test import TestCase
from django.urls import reverse

from blog.models import Comment, Post, User


class UserEndpointsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(
            username="carol", email="carol@example.com", display_name="Carol", bio="hi"
        )
        pub = Post.objects.create(author=cls.user, title="p", body="b")
        draft = Post.objects.create(author=cls.user, title="d", body="b", is_published=False)
        Comment.objects.create(post=pub, author=cls.user, body="c1")
        Comment.objects.create(post=draft, author=cls.user, body="c2")

    def test_get_user_detail_shape(self):
        resp = self.client.get(reverse("api-1.0.0:get_user", args=[self.user.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            set(resp.json().keys()),
            {"id", "username", "display_name", "email", "bio", "post_count", "comment_count"},
        )

    def test_get_user_unknown_404(self):
        resp = self.client.get(reverse("api-1.0.0:get_user", args=[99999]))
        self.assertEqual(resp.status_code, 404)

    def test_find_user_by_email_ok(self):
        url = reverse("api-1.0.0:find_user_by_email")
        resp = self.client.get(url, {"email": "carol@example.com"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["username"], "carol")

    def test_find_user_by_email_missing_param_422(self):
        self.assertEqual(self.client.get(reverse("api-1.0.0:find_user_by_email")).status_code, 422)

    def test_find_user_by_email_unknown_404(self):
        url = reverse("api-1.0.0:find_user_by_email")
        resp = self.client.get(url, {"email": "nobody@example.com"})
        self.assertEqual(resp.status_code, 404)

    def test_find_user_by_email_duplicate_raises(self):
        # Refs #5 (intentional): email is not unique -> MultipleObjectsReturned
        User.objects.create(username="carol2", email="carol@example.com", display_name="Carol2")
        url = reverse("api-1.0.0:find_user_by_email")
        with self.assertRaises(User.MultipleObjectsReturned):
            self.client.get(url, {"email": "carol@example.com"})

    def test_user_counts_include_unpublished(self):
        # Refs #7 (intentional): counts ignore is_published (post + comment on a draft)
        data = self.client.get(reverse("api-1.0.0:get_user", args=[self.user.id])).json()
        self.assertEqual((data["post_count"], data["comment_count"]), (2, 2))

    def test_find_resolves_before_user_id_route(self):
        # /users/find must match the static route, not be parsed as {user_id}
        url = reverse("api-1.0.0:find_user_by_email")
        self.assertEqual(self.client.get(url, {"email": "carol@example.com"}).status_code, 200)
