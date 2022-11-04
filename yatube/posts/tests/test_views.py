import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group_second = Group.objects.create(
            title='Вторая тестовая группа',
            slug='test-slug-second',
            description='some text',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif', content=cls.small_gif, content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:profile', kwargs={'username': self.user.username}
            ): 'posts/profile.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id}
            ): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def merge_same_asserts(self, post_object):
        """В шаблон передан правильный текст, автор, группа, картинка"""
        self.assertEqual(post_object.text, self.post.text),
        self.assertEqual(post_object.author, self.post.author),
        self.assertEqual(post_object.group, self.group),
        self.assertEqual(post_object.image, 'posts/' + str(self.uploaded)),

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.client.get(reverse('posts:index'))
        self.merge_same_asserts(response.context['page_obj'][0])

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        group_object = response.context['group']
        self.merge_same_asserts(response.context['page_obj'][0])
        self.assertEqual(group_object.title, self.group.title)
        self.assertEqual(group_object.description, self.group.description)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        author = response.context['author']
        self.merge_same_asserts(response.context['page_obj'][0])
        self.assertEqual(author.username, self.user.username)
        self.assertEqual(author.posts.count(), self.user.posts.count())

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        count = response.context['post'].author.posts.count()  # исправить
        self.merge_same_asserts(response.context['post'])
        self.assertEqual(count, self.user.posts.count())

    def test_post_create_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон edit_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_another_group(self):
        """Пост не находится в другой группе"""
        response = self.client.get(
            reverse(
                'posts:group_list', kwargs={'slug': self.group_second.slug}
            )
        )
        self.assertNotIn(self.post, response.context['page_obj'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Тестовое описание',
        )
        posts_to_create = []
        for i in range(13):
            posts_to_create.append(
                Post(author=cls.user, text=f'{i} Test', group=cls.group)
            )
        Post.objects.bulk_create(posts_to_create)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()

    def test_correct_paginate_limit(self):
        """Проверка актуального лимита пагинации"""
        expected_limit = 10
        self.assertEqual(settings.PAGINATE_LIMIT, expected_limit)

    def test_first_page_contains_ten_records(self):
        """Проверка работы пагинатора"""
        urls_lengths = (
            (reverse('posts:index'), 10),
            (
                reverse('posts:group_list', kwargs={'slug': self.group.slug}),
                10,
            ),
            (
                reverse(
                    'posts:profile', kwargs={'username': self.user.username}
                ),
                10,
            ),
            (reverse('posts:index') + '?page=2', 3),
            (
                reverse('posts:group_list', kwargs={'slug': self.group.slug})
                + '?page=2',
                3,
            ),
            (
                reverse(
                    'posts:profile', kwargs={'username': self.user.username}
                )
                + '?page=2',
                3,
            ),
        )
        for url, lengths in urls_lengths:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    len(response.context['page_obj'].object_list), lengths
                )


class CacheViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        self.guest_client = Client()

    def test_cache_index_page(self):
        """Проверка кэширования главной страницы"""
        # делаем запрос к главной странице, запоминаем контент
        response = self.guest_client.get(reverse('posts:index'))
        content = response.content
        # удаляем пост, и проверяем остался ли он в контенте
        Post.objects.first().delete()
        response_last = self.guest_client.get(reverse('posts:index'))
        content_last = response_last.content
        self.assertEqual(content, content_last)
        # очищаем кэш, контент должен измениться
        cache.clear()
        response_last = self.guest_client.get(reverse('posts:index'))
        content_last = response_last.content
        self.assertNotEqual(content, content_last)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='auth')
        cls.follower = User.objects.create_user(username='follower')
        cls.user = User.objects.create_user(username='jack')
        cls.post = Post.objects.create(
            author=cls.author,
            text='5' * 20,
        )

    def setUp(self):
        self.guest_client = Client()
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)

    def test_authorized_client_can_follow_and_unfollow(self):
        """Авторизованный пользователь может подписываться и отписываться"""
        self.follower_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username},
            )
        )
        self.assertEqual(Follow.objects.first().user, self.follower)
        self.assertEqual(Follow.objects.first().author, self.author)
        # подписка оформилась, теперь выполним проверку на отписку
        self.follower_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author.username},
            )
        )
        self.assertFalse(Follow.objects.first())

    def test_follow_page_show_correct_context(self):
        """Новая запись пользователя появляется в ленте тех, кто на него
        подписан и не появляется в ленте тех, кто не подписан."""
        # подпишем follower на author
        Follow.objects.create(
            author_id=self.author.id, user_id=self.follower.id
        )
        # у подсписчика должна появиться запись
        response = self.follower_client.get(reverse('posts:follow_index'))
        post = response.context['page_obj'][0]
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.text, self.post.text)
        # у обычного юзера не должно быть записей
        response = self.guest_client.get(reverse('posts:follow_index'))
        self.assertIsNone(response.context)

    def test_authorized_client_can_follow_only_one_time(self):
        """Подписаться можно только 1 раз"""
        # несколько раз пробуем подписаться
        for _ in range(3):
            self.follower_client.get(
                reverse(
                    'posts:profile_follow',
                    kwargs={'username': self.author.username},
                )
            )
        self.assertEqual(Follow.objects.all().count(), 1)
        # проверяем корректность записи в БД
        self.assertEqual(Follow.objects.first().user, self.follower)
        self.assertEqual(Follow.objects.first().author, self.author)
