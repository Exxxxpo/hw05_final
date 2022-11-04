import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(username='auth')
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def merge_same_asserts(self, response, post, form_data, posts_count):
        """Общие тесты"""
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.user)
        self.assertEqual(Post.objects.count(), posts_count + 1)

    def test_authorized_user_can_create_post(self):
        """Валидная форма авторизованного пользователя создает запись"""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif', content=small_gif, content_type='image/gif'
        )
        posts_count = Post.objects.count()
        form_data = {
            'text': 'some_text',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.merge_same_asserts(
            response, Post.objects.first(), form_data, posts_count
        )
        self.assertEqual(Post.objects.first().group.id, form_data['group'])
        self.assertEqual(
            Post.objects.first().image, f"posts/{str(form_data['image'])}"
        )

    def test_authorized_user_can_create_post_without_group(self):
        """Валидная форма без указания группы,
        отправленная авторизованным пользователем создает запись.
        """
        posts_count = Post.objects.count()
        form_data = {
            'text': 'This post has no group',
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.merge_same_asserts(
            response, Post.objects.first(), form_data, posts_count
        )
        self.assertFalse(Post.objects.first().group)

    def test_anonymous_user_cant_create_post(self):
        """Неавторизованный пользователь не создает запись"""
        form_data = {
            'text': 'text created by anonymous',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), 0)  # не создалась ли запись


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostEditFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(username='auth')
        self.author = User.objects.create_user(username='qwerty')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.post = Post.objects.create(
            author=self.author,
            text='Тестовый пост',
            group=self.group,
        )

    def merge_same_asserts(self, response, post, form_data, posts_count):
        """Общие тесты"""
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author.username, self.author.username)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_author_user_can_edit_post(self):
        """Валидная форма, отправленная автором редактирует запись."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif', content=small_gif, content_type='image/gif'
        )
        form_data = {
            'text': 'this text was changed',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.author_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Post.objects.first().group_id, form_data['group'])
        self.merge_same_asserts(
            response, Post.objects.first(), form_data, posts_count
        )
        self.assertEqual(
            Post.objects.first().image, f"posts/{str(form_data['image'])}"
        )

    def test_author_user_can_edit_post_without_group(self):
        """Валидная форма без группы, отправл. автором редактирует запись."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'group has been removed',
        }
        response = self.author_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.merge_same_asserts(
            response, Post.objects.first(), form_data, posts_count
        )
        self.assertFalse(Post.objects.first().group)

    def test_authorized_user_can_edit_post(self):
        """Только автор может редактировать свой пост"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'this text was changed',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.merge_same_asserts(
            response,
            Post.objects.first(),
            {"text": "Тестовый пост"},
            posts_count,
        )
        self.assertEqual(Post.objects.first().group.id, self.group.id)


class PostCommentFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            text='Тестовая группа',
            author=cls.user,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_authorized_client_can_comment(self):
        """Авторизованный пользователь может комментировать пост"""
        form_data = {
            'text': 'comment_text',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.first().text, form_data['text'])
        self.assertEqual(Comment.objects.first().author, self.user)

    def test_non_authorized_client_can_comment(self):
        """Не авторизованный пользователь не может комментировать пост"""
        form_data = {
            'text': '1' * 15,
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(Comment.objects.first())
