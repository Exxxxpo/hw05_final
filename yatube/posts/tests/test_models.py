from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='7' * 20,
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post, group = PostModelTest.post, PostModelTest.group
        field_str = {
            post: f'{self.post.text[:15]}',
            group: f'{self.group.title}',
        }
        for field, expected_value in field_str.items():
            with self.subTest(field=field):
                self.assertEqual(str(field), expected_value)

    def test_post_model_have_correct_verboses_names(self):
        """verbose_name у модели Post совпадает с ожидаемым."""
        label_verbose = {
            'text': 'Текст',
            'pub_date': 'Дата создания',
            'group': 'Сообщество',
            'author': 'Автор',
        }
        for label, expected_verbose in label_verbose.items():
            with self.subTest(label=label):
                verbose = self.post._meta.get_field(label).verbose_name
                self.assertEqual(verbose, expected_verbose)

    def test_group_model_have_correct_verboses_names(self):
        """verbose_name у модели Group совпадает с ожидаемым."""
        label_verbose = {
            'title': 'Заголовок сообщества',
            'slug': 'Адрес',
            'description': 'Описание сообщества',
        }
        for label, expected_verbose in label_verbose.items():
            with self.subTest(label=label):
                verbose = self.group._meta.get_field(label).verbose_name
                self.assertEqual(verbose, expected_verbose)

    def test_post_model_have_correct_help_text(self):
        """help_text у модели Post совпадает с ожидаемым."""
        label_help_text = {
            'text': 'Введите текст поста',
            'group': 'Группа, к которой будет относиться пост',
        }
        for label, expected_help_text in label_help_text.items():
            with self.subTest(label=label):
                verbose = self.post._meta.get_field(label).help_text
                self.assertEqual(verbose, expected_help_text)
